#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Token 失效并发模拟脚本

目标：
- 模拟小程序端在 token 失效时的并发请求行为；
- 验证 401 → 单飞刷新 → 重放 的流程是否会引发 429；
- 统计不同状态码与刷新次数，辅助定位是否存在请求风暴。

使用方法：
  环境变量（可选）：
    BASE_URL        默认: http://localhost:8083/api/v1
    USER_ID         默认: test-user
    INITIAL_TOKEN   默认: invalid-token (用于触发401)
    REFRESH_TOKEN   默认: 空（若提供，将调用 /miniprogram/auth/refresh 刷新）
    CONCURRENCY     默认: 6 （与小程序默认并发接近）
    BATCH_SIZE      默认: 6 （单次批量请求数量）
    ROUNDS          默认: 1 （批次数）

  运行：
    python tests/integration/token_expiry_simulation.py

说明：
- 若提供 REFRESH_TOKEN，脚本在遇到401时会以“单飞”方式调用刷新接口，并将后续请求用新 token 重放一次；
- 若未提供 REFRESH_TOKEN，则保持 401，不进行刷新，仅用于观察是否会进一步触发 429；
- 请求集合选择与小程序一致的典型端点（userinfo、quota、list），均携带 Authorization（若存在）。
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Tuple

import httpx


class Metrics:
    def __init__(self) -> None:
        self.total_requests_sent = 0
        self.total_responses = 0
        self.status_counts: Dict[int, int] = {}
        self.errors: List[str] = []
        self.refresh_calls = 0
        self.start_time = time.time()

    def inc_status(self, status_code: int) -> None:
        self.total_responses += 1
        self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1

    def inc_sent(self) -> None:
        self.total_requests_sent += 1

    def inc_refresh(self) -> None:
        self.refresh_calls += 1

    def snapshot(self) -> Dict[str, object]:
        elapsed = max(0.0001, time.time() - self.start_time)
        rps = self.total_responses / elapsed
        return {
            "total_requests_sent": self.total_requests_sent,
            "total_responses": self.total_responses,
            "status_counts": self.status_counts,
            "refresh_calls": self.refresh_calls,
            "elapsed_sec": round(elapsed, 3),
            "responses_per_sec": round(rps, 2),
        }


class TokenManager:
    def __init__(self, base_url: str, initial_token: Optional[str], refresh_token: Optional[str], metrics: Metrics) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = initial_token
        self.refresh_token = refresh_token
        self._refresh_lock = asyncio.Lock()
        self.metrics = metrics

    def get_auth_header(self) -> Dict[str, str]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    async def refresh_if_needed(self, client: httpx.AsyncClient) -> bool:
        if not self.refresh_token:
            return False
        if self._refresh_lock.locked():
            # 单飞：等待已有刷新结束
            async with self._refresh_lock:
                return self.token is not None
        async with self._refresh_lock:
            try:
                self.metrics.inc_refresh()
                url = f"{self.base_url}/miniprogram/auth/refresh"
                resp = await client.post(url, json={"refreshToken": self.refresh_token}, headers={"Content-Type": "application/json"})
                if resp.status_code != 200:
                    return False
                data = resp.json()
                # 适配网关规范：{ code, data }
                if isinstance(data, dict) and "code" in data and data.get("code") == 0:
                    payload = data.get("data", {})
                else:
                    payload = data
                new_token = payload.get("token")
                if new_token:
                    self.token = new_token
                    return True
                return False
            except Exception:
                return False


async def request_once(client: httpx.AsyncClient, token_mgr: TokenManager, method: str, url: str, params: Optional[Dict]=None) -> Tuple[int, Optional[Dict]]:
    headers = {"X-Client-Type": "test-simulator"}
    headers.update(token_mgr.get_auth_header())
    try:
        resp = await client.request(method, url, params=params, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = None
        # 统一打印非200响应，便于定位
        if resp.status_code != 200:
            try:
                print(json.dumps({
                    "event": "non_200_response",
                    "method": method,
                    "url": url,
                    "status": resp.status_code,
                    "blocked_by": (body or {}).get("details", {}).get("blocked_by") if isinstance(body, dict) else None,
                    "retry_after": (body or {}).get("details", {}).get("retry_after") if isinstance(body, dict) else None
                }, ensure_ascii=False))
            except Exception:
                pass
        return resp.status_code, body
    except Exception:
        return -1, None


async def request_with_refresh(client: httpx.AsyncClient, token_mgr: TokenManager, method: str, url: str, params: Optional[Dict], metrics: Metrics) -> int:
    metrics.inc_sent()
    status, _ = await request_once(client, token_mgr, method, url, params)
    if status == 401:
        # 401 → 尝试单飞刷新 → 重放一次
        refreshed = await token_mgr.refresh_if_needed(client)
        if refreshed:
            metrics.inc_sent()
            status, _ = await request_once(client, token_mgr, method, url, params)
    metrics.inc_status(status)
    return status


async def run_round(client: httpx.AsyncClient, token_mgr: TokenManager, base_url: str, user_id: str, concurrency: int, metrics: Metrics) -> None:
    # 端点集合（与小程序常用场景一致，均为 GET）
    endpoints: List[Tuple[str, str, Optional[Dict]]] = [
        ("GET", f"{base_url}/miniprogram/auth/userinfo", None),
        ("GET", f"{base_url}/miniprogram/users/{user_id}/quota", None),
        ("GET", f"{base_url}/miniprogram/postcards/user", {"user_id": user_id, "page": 1, "limit": 10}),
    ]

    sem = asyncio.Semaphore(concurrency)

    async def worker(method: str, url: str, params: Optional[Dict]) -> None:
        async with sem:
            await request_with_refresh(client, token_mgr, method, url, params, metrics)

    tasks: List[asyncio.Task] = []
    for method, url, params in endpoints:
        tasks.append(asyncio.create_task(worker(method, url, params)))
    await asyncio.gather(*tasks)


async def main() -> None:
    base_url = os.getenv("BASE_URL", "http://localhost:8083/api/v1")
    user_id = os.getenv("USER_ID", "test-user")
    initial_token = os.getenv("INITIAL_TOKEN", "invalid-token")
    refresh_token = os.getenv("REFRESH_TOKEN", "") or None
    concurrency = int(os.getenv("CONCURRENCY", "6"))
    batch_size = int(os.getenv("BATCH_SIZE", "6"))  # 本脚本内置3个端点/批，可重复执行 batch_size//3 轮
    rounds = int(os.getenv("ROUNDS", "1"))

    metrics = Metrics()
    token_mgr = TokenManager(base_url, initial_token, refresh_token, metrics)

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        print("=== Token Expiry Concurrency Simulation ===")
        print(json.dumps({
            "base_url": base_url,
            "user_id": user_id,
            "initial_token": (initial_token[:6] + "..." if initial_token else None),
            "has_refresh_token": bool(refresh_token),
            "concurrency": concurrency,
            "batch_size": batch_size,
            "rounds": rounds,
        }, ensure_ascii=False, indent=2))

        # 计算实际轮数（每轮3个端点），按 batch_size 重复
        per_round = 3
        batches_per_round = max(1, batch_size // per_round)

        for r in range(rounds):
            for b in range(batches_per_round):
                await run_round(client, token_mgr, base_url, user_id, concurrency, metrics)

    print("=== Metrics ===")
    print(json.dumps(metrics.snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())


