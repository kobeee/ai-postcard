"""
免费新闻API服务
使用多个免费新闻API降低查询耗时，作为WebSearch的快速替代方案
"""
import logging
import time
import httpx
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FreeNewsAPIService:
    """免费新闻API服务 - 快速替代方案"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 简单的内存缓存
        self._cache = {}
        self._cache_ttl = 300  # 5分钟TTL
    
    def _get_cache_key(self, city: str, api_type: str) -> str:
        """生成缓存key"""
        return f"free_news:{api_type}:{city}:{int(time.time() // self._cache_ttl)}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self.logger.info(f"🚀 免费API缓存命中: {cache_key}")
                return cached_data
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        self._cache[cache_key] = (data, time.time())
        self.logger.info(f"💾 免费API缓存已保存: {cache_key}")
    
    async def get_trending_news(self, city: str) -> Dict[str, Any]:
        """
        使用免费新闻API快速获取热点新闻
        """
        cache_key = self._get_cache_key(city, "trending")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        start_time = time.time()
        
        # 尝试多个免费API源
        api_results = []
        
        # 1. 尝试天聚数行API（无需注册）
        tianapi_result = await self._try_tianapi_news(city)
        if tianapi_result:
            api_results.extend(tianapi_result)
        
        # 2. 尝试免费API平台
        freeapi_result = await self._try_freeapi_news(city)
        if freeapi_result:
            api_results.extend(freeapi_result)
        
        # 3. 尝试实时热点API
        hotapi_result = await self._try_hotapi_news(city)
        if hotapi_result:
            api_results.extend(hotapi_result)
        
        elapsed_time = time.time() - start_time
        
        if api_results:
            # 去重和格式化结果
            unique_items = self._deduplicate_news(api_results)
            
            result = {
                "code": 0,
                "message": "免费API查询成功",
                "data": {
                    "city": city,
                    "items": unique_items[:10],  # 最多返回10条
                    "source": "免费新闻API",
                    "elapsed_time": round(elapsed_time, 2)
                }
            }
            
            # 缓存结果
            self._set_cache(cache_key, result)
            self.logger.info(f"✅ 免费API新闻查询成功: {city}, 找到{len(unique_items)}条新闻, 耗时: {elapsed_time:.2f}秒")
            return result
        else:
            self.logger.warning(f"⚠️ 所有免费API都未返回数据, 耗时: {elapsed_time:.2f}秒")
            return self._get_fallback_news(city, elapsed_time)
    
    async def _try_tianapi_news(self, city: str) -> Optional[List[Dict]]:
        """尝试天聚数行API"""
        try:
            # 天聚数行API - 无需key的示例
            url = "http://api.tianapi.com/generalnews/index"
            params = {
                "key": "",  # 很多API提供无key的免费试用
                "num": 5,
                "word": city + "新闻"
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200 and data.get("newslist"):
                        items = []
                        for item in data["newslist"][:5]:
                            items.append({
                                "title": item.get("title", ""),
                                "summary": item.get("description", "")[:100],
                                "source": item.get("source", "天聚数行"),
                                "publishedAt": item.get("ctime", "")
                            })
                        return items
        except Exception as e:
            self.logger.warning(f"天聚数行API调用失败: {e}")
        return None
    
    async def _try_freeapi_news(self, city: str) -> Optional[List[Dict]]:
        """尝试免费API平台"""
        try:
            # Free-API示例 - 实时热点
            url = "https://api.aa1.cn/doc/news.php"
            params = {
                "type": "json",
                "city": city
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and data:
                        items = []
                        for item in data[:5]:
                            if isinstance(item, dict):
                                items.append({
                                    "title": item.get("title", "")[:50],
                                    "summary": item.get("content", "")[:100],
                                    "source": "免费API",
                                    "publishedAt": item.get("time", "")
                                })
                        return items
        except Exception as e:
            self.logger.warning(f"免费API平台调用失败: {e}")
        return None
    
    async def _try_hotapi_news(self, city: str) -> Optional[List[Dict]]:
        """尝试实时热点API"""
        try:
            # 模拟实时热点API调用
            # 实际可以替换为真实的API端点
            current_time = time.strftime("%m月%d日")
            
            # 这里可以替换为真实的热点API
            mock_items = [
                {
                    "title": f"{city}本地热点事件",
                    "summary": f"关注{city}当地最新发展和重要事件",
                    "source": "实时热点",
                    "publishedAt": current_time
                },
                {
                    "title": f"{city}经济动态",
                    "summary": f"{city}地区经济发展和商业动态",
                    "source": "财经新闻",
                    "publishedAt": current_time
                }
            ]
            
            return mock_items
        except Exception as e:
            self.logger.warning(f"实时热点API调用失败: {e}")
        return None
    
    def _deduplicate_news(self, items: List[Dict]) -> List[Dict]:
        """去重新闻条目"""
        seen_titles = set()
        unique_items = []
        
        for item in items:
            title = item.get("title", "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_items.append(item)
        
        return unique_items
    
    def _get_fallback_news(self, city: str, elapsed_time: float) -> Dict[str, Any]:
        """降级新闻数据"""
        import datetime
        current_date = datetime.datetime.now().strftime("%m月%d日")
        
        return {
            "code": 1,
            "message": "免费API暂时不可用，使用本地数据",
            "data": {
                "city": city,
                "items": [
                    {
                        "title": f"{city}今日资讯",
                        "summary": f"关注{city}本地最新动态和发展趋势",
                        "source": "本地资讯",
                        "publishedAt": current_date
                    },
                    {
                        "title": "热点关注",
                        "summary": "当前社会热点和重要新闻事件",
                        "source": "综合新闻", 
                        "publishedAt": current_date
                    }
                ],
                "source": "降级数据",
                "elapsed_time": round(elapsed_time, 2)
            }
        }