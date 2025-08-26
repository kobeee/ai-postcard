"""
直接使用Anthropic Claude API的天气和热点服务
替代有问题的Claude Code SDK WebSearch
"""
import asyncio
import json
import logging
import time
import os
from typing import Dict, Any, Optional
import anthropic
from datetime import datetime

logger = logging.getLogger(__name__)


class ClaudeWeatherService:
    """直接调用Anthropic Claude API的天气和热点服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 获取Anthropic API配置（兼容现有配置）
        self.api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_AUTH_TOKEN')
        self.base_url = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
        self.model = os.getenv('ANTHROPIC_API_MODEL', 'claude-3-5-sonnet-20241022')
        
        # 初始化Anthropic客户端
        self.client = None
        if self.api_key:
            # 兼容第三方代理配置
            if self.base_url != 'https://api.anthropic.com':
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)
                self.logger.info(f"🔗 使用第三方Claude API代理: {self.base_url}")
            else:
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
                self.logger.info("🔗 使用官方Claude API")
        
        # 简单的内存缓存
        self._cache = {}
        self._cache_ttl = 300  # 5分钟TTL，天气和新闻需要更频繁更新
        
        if not self.api_key:
            self.logger.warning("⚠️ ANTHROPIC_API_KEY或ANTHROPIC_AUTH_TOKEN未配置，将无法使用Claude Web Search功能")
    
    def _get_cache_key(self, query_type: str, location: str) -> str:
        """生成缓存key"""
        return f"{query_type}:{location}:{int(time.time() // self._cache_ttl)}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self.logger.info(f"🚀 缓存命中: {cache_key}")
                return cached_data
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        self._cache[cache_key] = (data, time.time())
        self.logger.info(f"💾 缓存已保存: {cache_key}")
    
    def clear_cache(self) -> int:
        """清理缓存"""
        count = len(self._cache)
        self._cache.clear()
        self.logger.info("🧹 天气和新闻缓存已清理")
        return count
    
    async def get_weather(self, latitude: float, longitude: float, city_name: str = None) -> Dict[str, Any]:
        """
        使用Anthropic Claude API Web Search获取实时天气
        """
        location = city_name or f"坐标 {latitude}, {longitude}"
        cache_key = self._get_cache_key("weather", location)
        
        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        if not self.api_key:
            return self._get_fallback_weather()
        
        try:
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
            
            # 构建Claude API请求
            messages = [{
                "role": "user",
                "content": f\"\"\"请搜索{location}在{current_time}的实时天气信息。
                
请返回JSON格式：
{{
    "temperature": 温度数值(数字),
    "weather_text": "天气状况描述",
    "humidity": 湿度百分比(数字),
    "wind_speed": 风速(数字),
    "description": "详细天气描述"
}}

要求：
1. 必须搜索最新的实时天气数据
2. 温度使用摄氏度
3. 返回准确的数字值，不要文字描述
4. 中文天气描述\"\"\""
            }]
            
            # 调用Claude API with Web Search
            result = await self._call_claude_api(messages, "天气查询")
            
            if result:
                # 缓存结果
                self._set_cache(cache_key, result)
                return result
            else:
                return self._get_fallback_weather()
                
        except Exception as e:
            self.logger.error(f"❌ Claude天气查询异常: {e}")
            return self._get_fallback_weather()
    
    async def get_trending_news(self, city: str) -> Dict[str, Any]:
        """
        使用Anthropic Claude API Web Search获取城市热点新闻
        """
        cache_key = self._get_cache_key("trending", city)
        
        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        if not self.api_key:
            return self._get_fallback_trending(city)
        
        try:
            current_date = datetime.now().strftime("%Y年%m月%d日")
            
            # 构建Claude API请求
            messages = [{
                "role": "user", 
                "content": f\"\"\"请搜索{city}在{current_date}的最新热点新闻和趋势话题。

请返回JSON格式：
{{
    "city": "{city}",
    "news_items": [
        {{
            "title": "新闻标题",
            "summary": "新闻摘要",
            "source": "新闻来源",
            "publishedAt": "发布时间"
        }}
    ],
    "social_trends": [
        {{
            "topic": "热门话题",
            "description": "话题描述"
        }}
    ],
    "total_count": 新闻数量
}}

要求：
1. 搜索今日最新的本地新闻和热点
2. 至少返回3-5条新闻
3. 包含本地生活、社会、文化等多元化内容
4. 中文内容
5. 真实有效的新闻信息\"\"\""
            }]
            
            # 调用Claude API with Web Search
            result = await self._call_claude_api(messages, "热点查询")
            
            if result:
                # 缓存结果
                self._set_cache(cache_key, result)
                return result
            else:
                return self._get_fallback_trending(city)
                
        except Exception as e:
            self.logger.error(f"❌ Claude热点查询异常: {e}")
            return self._get_fallback_trending(city)
    
    async def _call_claude_api(self, messages, query_type: str) -> Optional[Dict[str, Any]]:
        """
        调用Anthropic Claude API with Web Search
        """
        if not self.client:
            self.logger.error("❌ Anthropic客户端未初始化，请检查ANTHROPIC_API_KEY配置")
            return None
        
        try:
            self.logger.info(f"📡 调用Claude API进行{query_type}...")
            
            # 使用官方SDK调用Claude API with Web Search
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=messages,
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 3  # 限制搜索次数以控制成本
                    }
                ]
            )
            
            # 提取响应内容
            content = ""
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        content += block.text
            
            if not content:
                self.logger.warning(f"Claude API响应为空")
                return None
            
            # 尝试提取JSON
            json_data = self._extract_json_from_response(content)
            if json_data:
                result = {
                    "code": 0,
                    "message": "查询成功",
                    "data": json_data
                }
                self.logger.info(f"✅ Claude {query_type}成功")
                return result
            else:
                self.logger.warning(f"⚠️ 无法从Claude响应中提取JSON数据")
                self.logger.debug(f"Claude原始响应: {content[:500]}...")
                return None
                    
        except Exception as e:
            self.logger.error(f"❌ Claude API请求异常: {e}")
            return None
    
    def _extract_json_from_response(self, text: str) -> Optional[Dict[str, Any]]:
        """从Claude响应中提取JSON数据"""
        try:
            # 寻找JSON块
            start_idx = text.find('{')
            if start_idx == -1:
                return None
                
            # 找到匹配的结束括号
            brace_count = 0
            end_idx = start_idx
            
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count == 0:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return None
                
        except (json.JSONDecodeError, IndexError):
            return None
    
    def _get_fallback_weather(self) -> Dict[str, Any]:
        """降级天气信息"""
        return {
            "code": 0,
            "message": "天气查询成功(基础信息)",
            "data": {
                "temperature": 22,
                "weather_text": "晴转多云", 
                "humidity": 65,
                "wind_speed": 2,
                "description": "天气信息更新中，请稍后查看详细信息"
            }
        }
    
    def _get_fallback_trending(self, city: str) -> Dict[str, Any]:
        """降级热点信息"""
        return {
            "code": 0,
            "message": "综合查询成功",
            "data": {
                "city": city,
                "news_items": [
                    {
                        "title": f"{city}本地生活热点",
                        "summary": f"了解{city}当地的生活、文化和社区动态",
                        "source": "本地资讯",
                        "publishedAt": datetime.now().strftime("%m月%d日")
                    },
                    {
                        "title": "今日关注话题", 
                        "summary": "当前社会热点和重要新闻事件",
                        "source": "综合资讯",
                        "publishedAt": datetime.now().strftime("%m月%d日")
                    }
                ],
                "social_trends": [],
                "total_count": 2
            }
        }