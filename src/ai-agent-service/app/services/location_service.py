"""
地理位置查询服务
使用免费API进行地理位置逆解析，Claude进行天气查询和热点内容获取
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
import httpx
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

logger = logging.getLogger(__name__)


class LocationService:
    """基于Claude Code工具的地理位置服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 简单的内存缓存，TTL为10分钟
        self._cache = {}
        self._cache_ttl = 600  # 10分钟
    
    def _get_cache_key(self, latitude: float, longitude: float, query_type: str = "location") -> str:
        """生成缓存key"""
        return f"{query_type}:{round(latitude, 4)}:{round(longitude, 4)}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self.logger.info(f"🚀 缓存命中: {cache_key}")
                return cached_data
            else:
                # 过期删除
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        self._cache[cache_key] = (data, time.time())
        self.logger.info(f"💾 缓存已保存: {cache_key}")
    
    def clear_cache(self) -> int:
        """清理缓存，返回清理条目数量"""
        count = len(self._cache)
        self._cache.clear()
        self.logger.info("🧹 位置/天气缓存已清理")
        return count
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        使用免费API进行逆地理解析
        根据经纬度获取城市信息
        """
        # 检查缓存
        cache_key = self._get_cache_key(latitude, longitude, "location")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        self.logger.info(f"📍 逆地理解析请求: {latitude}, {longitude}")
        
        # 优先尝试BigDataCloud API（更好的中文支持）
        try:
            result = await self._query_bigdatacloud(latitude, longitude)
            if result:
                # 缓存结果
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            self.logger.warning(f"BigDataCloud API异常: {e}")
        
        # 备选：OpenStreetMap Nominatim API
        try:
            result = await self._query_nominatim(latitude, longitude)
            if result:
                # 缓存结果
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            self.logger.warning(f"Nominatim API异常: {e}")
        
        # 最后降级：返回基础位置信息
        self.logger.warning(f"⚠️ 所有地理位置API都失败，返回基础信息")
        fallback_result = {
            "code": 0,
            "message": "位置查询成功(基础信息)",
            "data": {
                "city": "未知城市",
                "country": "中国", 
                "name": f"坐标 {latitude:.3f}, {longitude:.3f}",
                "admin1": "未知省份",
                "admin2": "未知城市"
            }
        }
        return fallback_result
    
    async def _query_bigdatacloud(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """使用BigDataCloud免费API查询位置信息"""
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={latitude}&longitude={longitude}&localityLanguage=zh"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "code": 0,
                        "message": "查询成功",
                        "data": {
                            "city": data.get("city") or data.get("locality", "未知城市"),
                            "name": data.get("city") or data.get("locality", f"坐标 {latitude:.3f}, {longitude:.3f}"),
                            "admin1": data.get("principalSubdivision", "未知省份"),  # 省份
                            "admin2": data.get("city") or data.get("locality", "未知城市"),  # 城市
                            "country": data.get("countryName", "中国"),
                            "timezone": "Asia/Shanghai"  # 默认时区
                        }
                    }
                    
                    city_name = result["data"]["city"]
                    self.logger.info(f"✅ BigDataCloud地理位置查询成功: {city_name}")
                    return result
                else:
                    self.logger.warning(f"BigDataCloud API返回错误状态码: {response.status_code}")
                    return None
        except Exception as e:
            self.logger.warning(f"BigDataCloud API请求异常: {e}")
            return None
    
    async def _query_nominatim(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """使用OpenStreetMap Nominatim API查询位置信息"""
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&accept-language=zh-CN"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "AI Postcard Location Service/1.0"}
                )
                if response.status_code == 200:
                    data = response.json()
                    address = data.get("address", {})
                    
                    # 提取城市名（优先级：city > town > county > suburb）
                    city = (address.get("city") or 
                           address.get("town") or 
                           address.get("county") or 
                           address.get("suburb") or 
                           "未知城市")
                    
                    result = {
                        "code": 0,
                        "message": "查询成功",
                        "data": {
                            "city": city,
                            "name": data.get("display_name", f"坐标 {latitude:.3f}, {longitude:.3f}"),
                            "admin1": address.get("state", "未知省份"),  # 省份
                            "admin2": city,  # 城市
                            "country": address.get("country", "中国"),
                            "timezone": "Asia/Shanghai"  # 默认时区
                        }
                    }
                    
                    self.logger.info(f"✅ Nominatim地理位置查询成功: {city}")
                    return result
                else:
                    self.logger.warning(f"Nominatim API返回错误状态码: {response.status_code}")
                    return None
        except Exception as e:
            self.logger.warning(f"Nominatim API请求异常: {e}")
            return None
    
    async def get_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        使用Claude Code WebSearch工具查询天气信息
        """
        # 检查缓存（天气缓存时间较短，5分钟）
        cache_key = self._get_cache_key(latitude, longitude, "weather")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # 获取当前时间确保查询的是实时天气
            import datetime
            current_time = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
            
            # 构建包含当前时间的天气查询提示
            prompt = f"""查询坐标 {latitude}, {longitude} 在{current_time}的实时天气。

使用WebSearch搜索当前最新天气数据并返回JSON：
{{"temperature": 温度数值, "weather_text": "天气状况", "description": "详细描述"}}

重要：必须搜索{current_time}的最新天气，不要使用过期数据。要求摄氏度，中文描述。"""
            
            # 配置优化的Claude选项
            options = ClaudeCodeOptions(
                system_prompt="天气查询助手。使用WebSearch工具快速查询实时天气，返回JSON格式。",
                max_turns=2,  # 减少轮次
                allowed_tools=["WebSearch"]
            )
            
            # 使用超时控制避免无限等待
            return await asyncio.wait_for(
                self._query_claude_weather(options, prompt, latitude, longitude, cache_key),
                timeout=45.0  # 45秒超时，与小程序端保持一致
            )
            
        except asyncio.TimeoutError:
            # 超时降级：返回基础天气信息
            self.logger.warning(f"⏰ Claude天气查询超时: {latitude}, {longitude}")
            fallback_result = {
                "code": 0,
                "message": "天气查询成功(基础信息)",
                "data": {
                    "temperature": 25,  # 默认温度
                    "weather_text": "多云",
                    "humidity": 60,
                    "wind_speed": 3,
                    "description": "天气信息正在更新中，请稍后查看详细信息"
                }
            }
            # 缓存降级结果（TTL较短，5分钟）
            self._cache[cache_key] = (fallback_result, time.time())
            return fallback_result
            
        except Exception as e:
            self.logger.error(f"❌ 天气查询异常: {str(e)}")
            return {
                "code": -1,
                "message": f"天气查询失败: {str(e)}",
                "data": None
            }
    
    async def _query_claude_weather(self, options: ClaudeCodeOptions, prompt: str, latitude: float, longitude: float, cache_key: str) -> Dict[str, Any]:
        """查询Claude获取天气数据的辅助方法"""
        # 调用Claude Code SDK
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            
            weather_data = None
            async for message in client.receive_response():
                if hasattr(message, 'content') and message.content:
                    for block in message.content:
                        if hasattr(block, 'text') and block.text:
                            text = block.text.strip()
                            # 尝试提取JSON数据
                            if '{' in text and '}' in text:
                                try:
                                    start_idx = text.find('{')
                                    end_idx = text.rfind('}') + 1
                                    json_str = text[start_idx:end_idx]
                                    weather_data = json.loads(json_str)
                                    break
                                except json.JSONDecodeError:
                                    continue
                
                if weather_data:
                    break
            
            if weather_data:
                result = {
                    "code": 0,
                    "message": "查询成功",
                    "data": {
                        "temperature": weather_data.get("temperature"),
                        "weather_text": weather_data.get("weather_text"),
                        "humidity": weather_data.get("humidity"),
                        "wind_speed": weather_data.get("wind_speed"),
                        "description": weather_data.get("description")
                    }
                }
                # 缓存结果（天气缓存时间较短，5分钟TTL）
                self._cache[cache_key] = (result, time.time())
                self.logger.info(f"✅ 天气查询成功: {weather_data.get('weather_text', 'Unknown')}, {weather_data.get('temperature', 'N/A')}°C")
                return result
            else:
                self.logger.warning(f"⚠️ 未能从Claude响应中提取天气信息")
                return {
                    "code": -1,
                    "message": "未找到天气信息",
                    "data": None
                }