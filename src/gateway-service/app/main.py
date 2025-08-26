from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from typing import Any, Dict

app = FastAPI(
    title="Gateway Service",
    description="AI明信片项目API网关，支持微信小程序",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志配置
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(log_dir, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = RotatingFileHandler(os.path.join(log_dir, 'gateway-service.log'), maxBytes=10*1024*1024, backupCount=5)
fh.setFormatter(fmt)
fh.setLevel(logging.INFO)
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(fh)

logger = logging.getLogger(__name__)

# 服务URL配置
SERVICES = {
    "user-service": os.getenv("USER_SERVICE_URL", "http://user-service:8000"),
    "postcard-service": os.getenv("POSTCARD_SERVICE_URL", "http://postcard-service:8000"), 
    "ai-agent-service": os.getenv("AI_AGENT_SERVICE_URL", "http://ai-agent-service:8000")
}

@app.get("/")
async def read_root():
    return {
        "message": "AI明信片项目网关服务",
        "status": "运行正常",
        "version": "1.0.0",
        "services": SERVICES
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gateway-service", 
        "version": "1.0.0"
    }

# 代理请求的通用函数
async def proxy_request(
    target_url: str,
    method: str,
    path: str,
    request: Request,
    timeout: int = 30
) -> Dict[Any, Any]:
    """代理HTTP请求到目标服务"""
    try:
        # 构建完整URL
        full_url = f"{target_url}{path}"
        
        # 准备请求头
        headers = dict(request.headers)
        headers.pop("host", None)  # 移除原始host头
        headers["X-Client-Type"] = "miniprogram"
        headers["X-Forwarded-For"] = request.client.host
        
        # 获取请求体
        body = None
        if method.upper() in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # 发起请求
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=full_url,
                params=dict(request.query_params),
                headers=headers,
                content=body
            )
            
            logger.info(f"代理请求: {method} {full_url} -> {response.status_code}")
            
            # 返回响应
            try:
                return response.json()
            except:
                return {"code": 0, "message": "成功", "data": response.text}
                
    except httpx.TimeoutException:
        logger.error(f"请求超时: {target_url}{path}")
        return {"code": -1, "message": "服务请求超时", "data": None}
    except Exception as e:
        logger.error(f"代理请求失败: {str(e)}")
        return {"code": -1, "message": f"服务暂时不可用: {str(e)}", "data": None}

# 小程序用户认证路由
@app.api_route("/api/v1/miniprogram/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def miniprogram_auth_proxy(path: str, request: Request):
    """小程序认证服务代理"""
    return await proxy_request(
        SERVICES["user-service"],
        request.method,
        f"/api/v1/miniprogram/auth/{path}",
        request
    )

# 小程序明信片服务路由  
@app.api_route("/api/v1/miniprogram/postcards/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def miniprogram_postcards_proxy(path: str, request: Request):
    """小程序明信片服务代理"""
    return await proxy_request(
        SERVICES["postcard-service"],
        request.method,
        f"/api/v1/miniprogram/postcards/{path}",
        request
    )

# 小程序AI生成服务路由
@app.api_route("/api/v1/miniprogram/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def miniprogram_ai_proxy(path: str, request: Request):
    """小程序AI服务代理"""
    return await proxy_request(
        SERVICES["ai-agent-service"],
        request.method,
        f"/api/v1/miniprogram/ai/{path}",
        request,
        timeout=120  # AI服务需要更长超时时间
    )

# 小程序健康检查
@app.get("/api/v1/miniprogram/health")
async def miniprogram_health():
    """小程序API健康检查"""
    return {
        "code": 0,
        "message": "小程序API网关正常运行",
        "data": {
            "services": SERVICES,
            "status": "healthy"
        }
    }

# 小程序版本信息
@app.get("/api/v1/miniprogram/version")
async def miniprogram_version():
    """小程序API版本信息"""
    return {
        "code": 0,
        "message": "版本信息获取成功",
        "data": {
            "version": "1.0.0",
            "features": [
                "微信登录认证",
                "情绪罗盘卡片生成",
                "AI明信片创作",
                "作品管理",
                "分享功能"
            ]
        }
    }

# -----------------------------
# 环境感知服务：位置与天气（基于AI Agent Service）
# -----------------------------

@app.get("/api/v1/miniprogram/location/reverse")
async def reverse_geocode(latitude: float, longitude: float, language: str = "zh"):
    """使用 AI Agent Service 的 Claude WebSearch 工具进行逆地理解析
    替代第三方API，提供更智能和稳定的地理位置查询
    """
    try:
        # 调用AI Agent Service的环境感知API
        target_url = SERVICES["ai-agent-service"]
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "language": language
        }
        
        async with httpx.AsyncClient(timeout=60) as client:  # AI环境查询需要更长超时
            resp = await client.get(
                f"{target_url}/api/v1/environment/location/reverse",
                params=params
            )
            resp.raise_for_status()
            result = resp.json()
            
            logger.info(f"📍 AI地理位置查询: {latitude}, {longitude} -> {result.get('data', {}).get('city', 'Unknown')}")
            return result
            
    except httpx.TimeoutException:
        logger.error(f"AI地理位置查询超时: {latitude}, {longitude}")
        return {"code": -1, "message": "地理位置查询超时", "data": None}
    except Exception as e:
        logger.error(f"AI地理位置查询失败: {e}")
        return {"code": -1, "message": f"地理位置查询失败: {str(e)}", "data": None}


@app.get("/api/v1/miniprogram/environment/weather")
async def get_weather(latitude: float, longitude: float):
    """使用 AI Agent Service 的 Claude WebSearch 工具查询天气信息
    替代第三方API，提供更智能和准确的天气查询
    """
    try:
        # 调用AI Agent Service的环境感知API
        target_url = SERVICES["ai-agent-service"]
        params = {
            "latitude": latitude,
            "longitude": longitude
        }
        
        async with httpx.AsyncClient(timeout=60) as client:  # AI环境查询需要更长超时
            resp = await client.get(
                f"{target_url}/api/v1/environment/weather",
                params=params
            )
            resp.raise_for_status()
            result = resp.json()
            
            weather_text = result.get('data', {}).get('weather_text', 'Unknown')
            temperature = result.get('data', {}).get('temperature', 'N/A')
            logger.info(f"🌤️ AI天气查询: {latitude}, {longitude} -> {weather_text}, {temperature}°C")
            return result
            
    except httpx.TimeoutException:
        logger.error(f"AI天气查询超时: {latitude}, {longitude}")
        return {"code": -1, "message": "天气查询超时", "data": None}
    except Exception as e:
        logger.error(f"AI天气查询失败: {e}")
        return {"code": -1, "message": f"天气查询失败: {str(e)}", "data": None}


@app.get("/api/v1/miniprogram/trending")
async def get_trending(city: str, lang: str = "zh"):
    """使用Gemini实时热点查询，支持中文城市名，提供快速可靠的推荐类热点内容"""
    try:
        # 优先使用Gemini热点推荐API - 快速且专门针对推荐内容优化
        target_url = SERVICES["ai-agent-service"]
        params = {"city": city}
        
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(
                f"{target_url}/api/v1/environment/trending/gemini",
                params=params
            )
            resp.raise_for_status()
            result = resp.json()
            
            # 转换Gemini响应格式为小程序兼容格式
            if result.get("code") == 0:
                data = result.get('data', {})
                gemini_items = data.get('items', [])
                
                # 转换为小程序期望的格式
                items = []
                for item in gemini_items:
                    items.append({
                        "title": item.get("title", ""),
                        "url": "",  # Gemini推荐不提供具体URL
                        "source": item.get("source", "Gemini推荐"),
                        "publishedAt": item.get("publishedAt", ""),
                        "type": "recommendation",
                        "summary": item.get("summary", ""),
                        "category": item.get("category", ""),
                        "location": item.get("location", ""),
                        "mood_tag": item.get("mood_tag", ""),
                        "highlight": item.get("highlight", "")
                    })
                
                total_count = len(items)
                elapsed_time = data.get('elapsed_time', 0)
                logger.info(f"🔍 Gemini热点查询成功: {city} -> {total_count}条推荐, 耗时{elapsed_time}秒")
                
                return {
                    "code": 0,
                    "message": "热点查询成功", 
                    "data": {
                        "city": city,
                        "items": items,
                        "total_count": total_count,
                        "source": "Gemini实时搜索",
                        "elapsed_time": elapsed_time,
                        "note": "✅ 基于Google搜索的实时推荐内容"
                    }
                }
            else:
                # Gemini服务返回错误，使用降级方案
                logger.warning(f"Gemini热点查询失败: {result.get('message', 'Unknown error')}")
                raise Exception(f"Gemini API错误: {result.get('message')}")
            
    except Exception as e:
        logger.error(f"Gemini热点查询异常: {e}")
        # 降级到快速热点API
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{target_url}/api/v1/environment/trending/fast",
                    params=params
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("code") == 0:
                        data = result.get('data', {})
                        items = data.get('items', [])
                        logger.info(f"⚡ 快速热点降级成功: {city} -> {len(items)}条")
                        return {
                            "code": 0,
                            "message": "热点查询成功(降级模式)",
                            "data": {
                                "city": city,
                                "items": items[:5],  # 限制数量
                                "total_count": len(items),
                                "source": "快速API降级"
                            }
                        }
        except:
            pass
        
        # 最终降级：返回空结果但不报错，保证小程序正常运行
        logger.error(f"所有热点查询方案都失败: {city}")
        return {
            "code": 0,
            "message": "热点查询暂时不可用",
            "data": {
                "city": city,
                "items": [],
                "total_count": 0,
                "source": "降级模式"
            }
        }
