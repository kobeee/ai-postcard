# 2025-08-30 - 删除API修复验证

## 环境准备
- 启动容器（按需）：`sh scripts/dev.sh up gateway postcard`
- 网关地址：`http://localhost:8083`

## 验证步骤
1. 创建一张测试明信片（可复用现有流程获取 `postcard_id`）。
2. 通过网关删除：
   ```bash
   curl -i -X DELETE "http://localhost:8083/api/v1/miniprogram/postcards/<postcard_id>"
   ```
   - 期望：HTTP/1.1 200，响应体 `{ "code": 0, "message": "删除成功" }`

3. 再次删除（验证幂等提示）：
   ```bash
   curl -i -X DELETE "http://localhost:8083/api/v1/miniprogram/postcards/<postcard_id>"
   ```
   - 期望：`{"code": -1, "message": "明信片不存在或已被删除"}`

## 日志查看
- 网关：`src/gateway-service/logs/gateway-service.log`
- 明信片服务：容器日志 `sh scripts/dev.sh logs postcard`

## 判定标准
- 不再出现 `Too little data for declared Content-Length`
- DELETE 请求不携带 `Content-Type`/`Content-Length`，上游转发无异常
- 服务端返回结构：`{"code":0, "message":"删除成功"}`

## 常见问题与排查
- 若仍报错：
  - 确认网关已更新并重启：`docker-compose up --build gateway-service`
  - 确认小程序端 DELETE 未携带 body（见 `src/miniprogram/utils/request.js` 修改）
  - 通过 `curl -v` 检查请求头中无 `Content-Type`/`Content-Length`

## 变更说明
- 网关：移除转发时的 `content-length`、`transfer-encoding`，无体方法不转发 `content-type`
- 小程序：无体方法不默认附加 `data`，且不设置 `Content-Type`


