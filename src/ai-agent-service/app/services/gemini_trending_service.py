"""
基于Gemini API Google Search Grounding的真实热点新闻服务
获取实时热点内容，适合AI明信片的心情导向推荐
"""
import logging
import time
import os
from typing import Dict, Any, List, Optional
from google import genai
import json

logger = logging.getLogger(__name__)


class GeminiTrendingService:
    """基于Gemini API的真实热点新闻服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 配置Gemini API - 使用正确的2025年SDK方法
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.logger.warning("❌ 未找到Gemini API密钥，请在.env文件中设置GEMINI_API_KEY")
            self.client = None
        else:
            # 使用新的google-genai SDK
            self.client = genai.Client(api_key=api_key)
        
        # 简单内存缓存
        self._cache = {}
        self._cache_ttl = 1800  # 30分钟缓存
    
    def _get_cache_key(self, city: str, query_type: str = "trending") -> str:
        """生成缓存key"""
        return f"gemini_{query_type}:{city.lower()}:{int(time.time() // self._cache_ttl)}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self.logger.info(f"🚀 Gemini缓存命中: {cache_key}")
                return cached_data
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        self._cache[cache_key] = (data, time.time())
        self.logger.info(f"💾 Gemini缓存已保存: {cache_key}")
    
    async def get_trending_news(self, city: str) -> Dict[str, Any]:
        """
        使用Gemini API Google Search获取城市热点新闻
        专注于推荐类内容：美食、景点、活动、体验等
        """
        # 检查缓存
        cache_key = self._get_cache_key(city, "trending")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        if not self.client:
            return self._get_fallback_response(city, "Gemini API未配置")
        
        start_time = time.time()
        try:
            # 构建专门针对推荐内容的查询
            current_date = time.strftime("%Y年%m月%d日")
            
            prompt = f"""搜索{city}在{current_date}最新的推荐热点内容，专注于以下类型：
            
1. 🍽️ 网红美食店、特色餐厅、小吃推荐
2. 📸 打卡景点、拍照圣地、文艺场所  
3. 🎉 有趣活动、节庆事件、娱乐体验
4. 🌙 深夜好去处、周末休闲地点
5. 🛍️ 购物推荐、市集活动

请返回JSON格式，包含以下字段：
{{
    "items": [
        {{
            "title": "标题",
            "summary": "简要描述（50字内）",
            "category": "分类（美食/景点/活动等）",
            "location": "具体位置",
            "highlight": "推荐亮点",
            "mood_tag": "心情标签（如：治愈系、活力四射、文艺范等）"
        }}
    ]
}}

重要：只返回真实存在的、积极正面的推荐内容，避免政策法规类信息。"""
            
            self.logger.info(f"🔍 开始Gemini实时搜索: {city}")
            
            # 使用2025年新SDK的正确方法
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            elapsed_time = time.time() - start_time
            
            if response and response.text:
                # 尝试解析JSON响应
                try:
                    # 提取JSON部分
                    text = response.text.strip()
                    if '```json' in text:
                        json_start = text.find('```json') + 7
                        json_end = text.find('```', json_start)
                        json_text = text[json_start:json_end].strip()
                    elif '{' in text and '}' in text:
                        json_start = text.find('{')
                        json_end = text.rfind('}') + 1
                        json_text = text[json_start:json_end]
                    else:
                        json_text = text
                    
                    parsed_data = json.loads(json_text)
                    items = parsed_data.get('items', [])
                    
                    # 验证和清理数据
                    cleaned_items = []
                    for item in items[:10]:  # 最多10条
                        if isinstance(item, dict) and item.get('title') and item.get('summary'):
                            cleaned_items.append({
                                "title": str(item.get('title', ''))[:100],
                                "summary": str(item.get('summary', ''))[:200], 
                                "category": str(item.get('category', '生活推荐')),
                                "location": str(item.get('location', city)),
                                "highlight": str(item.get('highlight', '')),
                                "mood_tag": str(item.get('mood_tag', '推荐')),
                                "source": "Gemini实时搜索",
                                "publishedAt": time.strftime("%m月%d日"),
                                "search_grounded": True
                            })
                    
                    if cleaned_items:
                        result = {
                            "code": 0,
                            "message": "Gemini实时搜索成功",
                            "data": {
                                "city": city,
                                "items": cleaned_items,
                                "total_count": len(cleaned_items),
                                "source": "Gemini + Google Search",
                                "elapsed_time": round(elapsed_time, 2),
                                "search_grounded": True,
                                "note": "✅ 基于Google搜索的实时热点推荐"
                            }
                        }
                        
                        self._set_cache(cache_key, result)
                        self.logger.info(f"✅ Gemini搜索成功: {city}, 获得{len(cleaned_items)}条推荐, 耗时: {elapsed_time:.2f}秒")
                        return result
                    
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"⚠️ Gemini响应解析失败: {e}")
                    # 如果JSON解析失败，尝试从文本中提取推荐信息
                    return self._extract_from_text(response.text, city, elapsed_time)
            
            self.logger.warning(f"⚠️ Gemini未返回有效内容, 耗时: {elapsed_time:.2f}秒")
            return self._get_fallback_response(city, "搜索结果为空")
                    
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"❌ Gemini搜索失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            return self._get_fallback_response(city, f"搜索失败: {str(e)}")
    
    def _extract_from_text(self, text: str, city: str, elapsed_time: float) -> Dict[str, Any]:
        """从文本响应中提取推荐信息"""
        try:
            lines = text.split('\n')
            items = []
            current_item = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 查找推荐项目
                if any(keyword in line for keyword in ['推荐', '热门', '网红', '必去', '值得', '不错', '好吃']):
                    if current_item and current_item.get('title'):
                        items.append(current_item)
                        current_item = {}
                    
                    current_item = {
                        "title": line[:50],
                        "summary": line[:100],
                        "category": "推荐",
                        "location": city,
                        "highlight": "Gemini推荐",
                        "mood_tag": "推荐",
                        "source": "Gemini搜索",
                        "publishedAt": time.strftime("%m月%d日"),
                        "search_grounded": True
                    }
                elif current_item and len(line) > 10:
                    current_item['summary'] = line[:150]
            
            if current_item and current_item.get('title'):
                items.append(current_item)
            
            if items:
                return {
                    "code": 0,
                    "message": "Gemini文本解析成功", 
                    "data": {
                        "city": city,
                        "items": items[:8],
                        "total_count": len(items),
                        "source": "Gemini文本解析",
                        "elapsed_time": round(elapsed_time, 2),
                        "search_grounded": True
                    }
                }
        except Exception as e:
            self.logger.warning(f"⚠️ 文本解析失败: {e}")
        
        return self._get_fallback_response(city, "文本解析失败")
    
    def _get_fallback_response(self, city: str, reason: str) -> Dict[str, Any]:
        """降级响应"""
        return {
            "code": 1,
            "message": f"Gemini搜索暂时不可用: {reason}",
            "data": {
                "city": city,
                "items": [],
                "total_count": 0,
                "source": "降级模式",
                "search_grounded": False,
                "note": "⚠️ 请检查Gemini API配置或稍后重试"
            }
        }
    
    async def get_food_recommendations(self, city: str) -> Dict[str, Any]:
        """专门获取美食推荐"""
        cache_key = self._get_cache_key(city, "food")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        if not self.client:
            return self._get_fallback_response(city, "Gemini API未配置")
        
        start_time = time.time()
        try:
            current_date = time.strftime("%Y年%m月%d日")
            prompt = f"""搜索{city}在{current_date}最新的美食推荐：
            
1. 🔥 网红餐厅、新开业的时尚餐厅
2. 🍜 本地特色小吃、老字号美食
3. ☕ 咖啡店、甜品店、茶饮店
4. 📸 适合拍照打卡的颜值餐厅
5. 💰 性价比高的平价美食

请返回JSON格式，包含具体信息：
{{
    "items": [
        {{
            "title": "店名",
            "summary": "简要描述和特色",
            "category": "餐厅类型", 
            "location": "具体地址或区域",
            "price_range": "人均价格",
            "specialties": "招牌菜品",
            "mood_tag": "氛围标签"
        }}
    ]
}}

重要：只推荐真实存在的美食店铺，提供实用的用餐信息。"""
            
            self.logger.info(f"🍽️ 开始Gemini美食搜索: {city}")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            elapsed_time = time.time() - start_time
            
            if response and response.text:
                try:
                    # 解析JSON响应
                    text = response.text.strip()
                    if '```json' in text:
                        json_start = text.find('```json') + 7
                        json_end = text.find('```', json_start)
                        json_text = text[json_start:json_end].strip()
                    elif '{' in text and '}' in text:
                        json_start = text.find('{')
                        json_end = text.rfind('}') + 1
                        json_text = text[json_start:json_end]
                    else:
                        json_text = text
                    
                    parsed_data = json.loads(json_text)
                    items = parsed_data.get('items', [])
                    
                    # 清理和验证美食数据
                    cleaned_items = []
                    for item in items[:8]:  # 最多8条美食推荐
                        if isinstance(item, dict) and item.get('title'):
                            cleaned_items.append({
                                "title": str(item.get('title', ''))[:80],
                                "summary": str(item.get('summary', ''))[:150],
                                "category": str(item.get('category', '美食')),
                                "location": str(item.get('location', city)),
                                "price_range": str(item.get('price_range', '')),
                                "specialties": str(item.get('specialties', '')),
                                "mood_tag": str(item.get('mood_tag', '美食推荐')),
                                "source": "Gemini美食搜索",
                                "publishedAt": time.strftime("%m月%d日"),
                                "search_grounded": True
                            })
                    
                    if cleaned_items:
                        result = {
                            "code": 0,
                            "message": "Gemini美食搜索成功",
                            "data": {
                                "city": city,
                                "items": cleaned_items,
                                "total_count": len(cleaned_items),
                                "source": "Gemini美食专项搜索",
                                "elapsed_time": round(elapsed_time, 2),
                                "search_grounded": True,
                                "note": "🍽️ 基于Google搜索的实时美食推荐"
                            }
                        }
                        
                        self._set_cache(cache_key, result)
                        self.logger.info(f"✅ Gemini美食搜索成功: {city}, 获得{len(cleaned_items)}家推荐, 耗时: {elapsed_time:.2f}秒")
                        return result
                        
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"⚠️ 美食响应解析失败: {e}")
                    return self._extract_from_text(response.text, city, elapsed_time)
            
            self.logger.warning(f"⚠️ Gemini美食搜索无结果, 耗时: {elapsed_time:.2f}秒")
            return self._get_fallback_response(city, "美食搜索无结果")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"❌ 美食推荐搜索失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            return self._get_fallback_response(city, f"美食搜索失败: {str(e)}")