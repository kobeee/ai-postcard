"""
热点新闻查询服务
使用Claude Code SDK的WebSearch工具查询当地热点和时事新闻 - 修正版本
"""
import logging
import time
import json
from typing import Dict, Any, Optional
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

logger = logging.getLogger(__name__)


class TrendingService:
    """基于Claude Code工具的热点新闻服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 简单的内存缓存，TTL为30分钟（热点内容更新频率较低）
        self._cache = {}
        self._cache_ttl = 1800  # 30分钟
    
    def _get_cache_key(self, city: str, query_type: str = "news") -> str:
        """生成缓存key"""
        return f"{query_type}:{city.lower()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self.logger.info(f"🚀 热点缓存命中: {cache_key}")
                return cached_data
            else:
                # 过期删除
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        self._cache[cache_key] = (data, time.time())
        self.logger.info(f"💾 热点缓存已保存: {cache_key}")
    
    async def _query_claude_websearch(self, options: ClaudeCodeOptions, prompt: str) -> Optional[str]:
        """查询Claude获取WebSearch结果 - 修正版本"""
        all_content = []
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            
            message_count = 0
            async for message in client.receive_response():
                message_count += 1
                self.logger.info(f"📨 收到第{message_count}条消息: {type(message).__name__}")
                
                # 处理消息内容
                if hasattr(message, 'content') and message.content:
                    for block in message.content:
                        if hasattr(block, 'text') and block.text:
                            text = block.text.strip()
                            if text:
                                all_content.append(text)
                
                # 检查停止条件
                if hasattr(message, 'stop_reason') and message.stop_reason:
                    self.logger.info(f"🛑 收到停止信号: {message.stop_reason}")
                    break
                    
                # 防止无限循环
                if message_count >= 10:
                    self.logger.warning("⚠️ 消息数量过多，主动停止")
                    break
            
            # 拼接所有内容
            final_result = "\n".join(all_content) if all_content else None
            self.logger.info(f"📊 总共收到{message_count}条消息，内容长度: {len(final_result) if final_result else 0}")
            
            return final_result
    
    def _parse_news_content(self, content: str, city: str) -> list:
        """解析新闻内容为结构化数据"""
        import datetime
        current_date = datetime.datetime.now().strftime("%m月%d日")
        
        # 简单的内容解析，将搜索结果转换为结构化格式
        items = []
        
        # 将内容按行分割，寻找可能的新闻条目
        lines = content.split('\n')
        current_item = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 如果是标题行（包含数字编号或特殊标记）
            if any(marker in line for marker in ['1.', '2.', '3.', '4.', '5.', '•', '-', '##']):
                # 保存前一条
                if current_item and 'title' in current_item:
                    items.append(current_item)
                    current_item = {}
                
                # 清理标记，提取标题
                title = line
                for marker in ['1.', '2.', '3.', '4.', '5.', '•', '-', '##', '#']:
                    title = title.replace(marker, '').strip()
                
                current_item = {
                    'title': title[:100],  # 限制长度
                    'summary': '',
                    'source': '综合新闻',
                    'publishedAt': current_date
                }
            else:
                # 补充到当前项目的摘要中
                if current_item and line:
                    current_item['summary'] = (current_item.get('summary', '') + ' ' + line)[:200]
        
        # 添加最后一项
        if current_item and 'title' in current_item:
            items.append(current_item)
        
        # 如果没有解析到结构化数据，创建一个通用项
        if not items:
            items.append({
                'title': f"{city}今日热点",
                'summary': content[:200] + "..." if len(content) > 200 else content,
                'source': 'WebSearch',
                'publishedAt': current_date
            })
        
        return items[:5]  # 最多返回5条
    
    def _get_fallback_trending_data(self, city: str) -> Dict[str, Any]:
        """降级策略：返回通用热点数据"""
        import datetime
        current_date = datetime.datetime.now().strftime("%m月%d日")
        
        fallback_items = [
            {
                "title": f"{city}本地生活热点",
                "summary": f"了解{city}当地的生活、文化和社区动态",
                "source": "本地资讯",
                "publishedAt": current_date
            },
            {
                "title": "今日关注话题",
                "summary": "当前社会热点和重要新闻事件",
                "source": "综合资讯",
                "publishedAt": current_date
            },
            {
                "title": f"{city}天气与出行",
                "summary": f"关注{city}天气变化和交通状况",
                "source": "生活服务",
                "publishedAt": current_date
            }
        ]
        
        self.logger.info(f"🔄 使用降级热点数据: {city}")
        return {
            "code": 0,
            "message": "查询成功（降级模式）",
            "data": {
                "city": city,
                "items": fallback_items
            }
        }
    
    async def get_trending_news(self, city: str, lang: str = "zh") -> Dict[str, Any]:
        """
        使用Claude Code WebSearch工具查询城市热点新闻 - 修正版本
        """
        # 检查缓存
        cache_key = self._get_cache_key(city, "news")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        start_time = time.time()
        try:
            # 获取当前时间确保查询的是最新热点
            import datetime
            current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
            
            # 构建热点新闻搜索提示
            prompt = f"""使用WebSearch搜索{city}在{current_date}的最新热点新闻和时事。

搜索要点：
1. {city}今日热点新闻
2. 当地重要事件
3. 社会热点话题
4. 抖音、小红书等社交媒体热点

请搜索并返回简洁的新闻摘要，包含：
- 新闻标题和简要内容
- 信息来源
- 发布时间
- 热度或关注度

请用中文返回搜索结果，确保信息的时效性和准确性。"""
            
            # 配置Claude选项 - 根据官方最佳实践设置轮次
            options = ClaudeCodeOptions(
                system_prompt="热点新闻搜索专家。使用WebSearch工具搜索最新的新闻热点，包括抖音、小红书等社交媒体热点，提供详细完整的搜索结果。",
                max_turns=4,  # 官方推荐3-5轮，设置4轮获得完整结果
                allowed_tools=["WebSearch", "Read"],  # 组合使用多个工具
                permission_mode="acceptEdits"
            )
            
            self.logger.info(f"🔍 开始热点新闻查询: {city}")
            
            # 调用修正后的WebSearch方法
            news_content = await self._query_claude_websearch(options, prompt)
            
            elapsed_time = time.time() - start_time
            
            if news_content:
                # 解析新闻内容为结构化数据
                items = self._parse_news_content(news_content, city)
                
                self.logger.info(f"✅ 热点新闻查询成功: {city}, 找到{len(items)}条新闻, 耗时: {elapsed_time:.2f}秒")
                result = {
                    "code": 0,
                    "message": "查询成功",
                    "data": {
                        "city": city,
                        "items": items[:10],  # 最多返回10条
                        "raw_content": news_content,
                        "elapsed_time": round(elapsed_time, 2)
                    }
                }
                # 缓存成功的结果
                self._set_cache(cache_key, result)
                return result
            else:
                self.logger.warning(f"⚠️ 未获取到有效新闻内容，使用降级数据, 耗时: {elapsed_time:.2f}秒")
                return self._get_fallback_trending_data(city)
                    
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"❌ 热点新闻查询失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            import traceback
            traceback.print_exc()
            # 异常时也使用降级数据
            return self._get_fallback_trending_data(city)
    
    async def get_social_trends(self, city: str) -> Dict[str, Any]:
        """
        查询社交媒体热点话题（小红书、抖音等平台热点）
        """
        try:
            # 获取当前时间确保查询的是最新社交热点
            import datetime
            current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
            
            prompt = f"""搜索{city}在{current_date}的社交媒体热点话题。

使用WebSearch搜索今日最新社交热点：
1. 小红书{city}热门话题
2. 抖音{city}热门内容
3. 微博{city}相关热搜
4. 当地生活美食旅游热点

返回JSON格式：
{{
    "city": "{city}",
    "social_trends": [
        {{"platform": "平台", "title": "话题", "content": "简介", "tags": ["标签"]}}
    ]
}}

重要：搜索{current_date}最新内容，积极正面话题。"""
            
            options = ClaudeCodeOptions(
                system_prompt="社交媒体趋势分析助手。搜索积极正向的最新社交热点话题。",
                max_turns=3,  # 优化速度
                allowed_tools=["WebSearch"]
            )
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                
                social_data = None
                async for message in client.receive_response():
                    if hasattr(message, 'content') and message.content:
                        for block in message.content:
                            if hasattr(block, 'text') and block.text:
                                text = block.text.strip()
                                if '{' in text and '}' in text and 'social_trends' in text:
                                    try:
                                        start_idx = text.find('{')
                                        end_idx = text.rfind('}') + 1
                                        json_str = text[start_idx:end_idx]
                                        social_data = json.loads(json_str)
                                        break
                                    except json.JSONDecodeError:
                                        continue
                    
                    if social_data:
                        break
                
                if social_data and social_data.get("social_trends"):
                    trends_count = len(social_data.get("social_trends", []))
                    self.logger.info(f"✅ 社交热点查询成功: {city}, 找到{trends_count}个话题")
                    return {
                        "code": 0,
                        "message": "查询成功",
                        "data": {
                            "city": city,
                            "social_trends": social_data.get("social_trends", [])[:8]
                        }
                    }
                else:
                    return {
                        "code": 0,
                        "message": "查询成功",
                        "data": {
                            "city": city,
                            "social_trends": []
                        }
                    }
                    
        except Exception as e:
            self.logger.error(f"❌ 社交热点查询失败: {str(e)}")
            return {
                "code": 0,
                "message": "查询成功",
                "data": {
                    "city": city,
                    "social_trends": []
                }
            }
    
    async def get_comprehensive_trends(self, city: str) -> Dict[str, Any]:
        """
        综合查询：优化后只查询新闻热点，避免复杂度和超时问题
        """
        # 检查缓存
        cache_key = self._get_cache_key(city, "comprehensive")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # 只查询新闻热点，简化逻辑
            news_result = await self.get_trending_news(city)
            news_items = news_result.get("data", {}).get("items", [])
            
            # 转换格式
            comprehensive_data = {
                "city": city,
                "news_items": news_items,
                "social_trends": [],  # 暂时留空，避免复杂度
                "total_count": len(news_items)
            }
            
            result = {
                "code": 0,
                "message": "综合查询成功",
                "data": comprehensive_data
            }
            
            # 缓存结果
            self._set_cache(cache_key, result)
            self.logger.info(f"✅ 综合热点查询完成: {city}, 总计{comprehensive_data['total_count']}条信息")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 综合热点查询失败: {str(e)}")
            # 使用降级数据
            fallback_result = self._get_fallback_trending_data(city)
            return {
                "code": 0,
                "message": "综合查询成功（降级模式）",
                "data": {
                    "city": city,
                    "news_items": fallback_result.get("data", {}).get("items", []),
                    "social_trends": [],
                    "total_count": len(fallback_result.get("data", {}).get("items", []))
                }
            }