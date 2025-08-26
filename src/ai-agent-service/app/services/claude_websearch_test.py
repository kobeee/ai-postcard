"""
Claude Code SDK + WebSearch 测试服务
基于官方文档示例，正确使用WebSearch工具
"""
import logging
import time
from typing import Dict, Any, Optional
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

logger = logging.getLogger(__name__)


class ClaudeWebSearchTest:
    """Claude Code SDK WebSearch 测试服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def test_websearch(self, query: str, city: str = None) -> Dict[str, Any]:
        """
        测试Claude Code SDK的WebSearch功能 - 不设置超时，完整测试功能和耗时
        """
        start_time = time.time()
        try:
            # 构建搜索提示词
            search_prompt = self._build_search_prompt(query, city)
            
            # 配置Claude选项 - 优化对话轮次减少耗时
            options = ClaudeCodeOptions(
                system_prompt="你是一个网络搜索助手。使用WebSearch工具搜索最新信息，然后提供简洁准确的搜索结果摘要。",
                max_turns=2,  # 减少对话轮次，提高响应速度
                allowed_tools=["WebSearch"],
                permission_mode="acceptEdits"  # 自动接受工具使用
            )
            
            self.logger.info(f"🔍 开始WebSearch测试查询: {query}")
            
            # 调用Claude Code SDK，不设置超时
            search_result = await self._query_claude_websearch(options, search_prompt)
            
            elapsed_time = time.time() - start_time
            
            if search_result:
                self.logger.info(f"✅ WebSearch测试成功: {query}, 耗时: {elapsed_time:.2f}秒")
                return {
                    "code": 0,
                    "message": "查询成功",
                    "data": {
                        "query": query,
                        "city": city,
                        "result": search_result,
                        "elapsed_time": round(elapsed_time, 2)
                    }
                }
            else:
                self.logger.warning(f"⚠️ WebSearch未返回有效结果, 耗时: {elapsed_time:.2f}秒")
                return {
                    "code": 1,
                    "message": "未获取到有效结果",
                    "data": {
                        "query": query, 
                        "result": "未获取到有效搜索结果",
                        "elapsed_time": round(elapsed_time, 2)
                    }
                }
                    
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"❌ WebSearch测试失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            import traceback
            traceback.print_exc()
            return {
                "code": 1,
                "message": f"查询失败: {str(e)}",
                "data": {
                    "query": query, 
                    "error": str(e),
                    "elapsed_time": round(elapsed_time, 2)
                }
            }
    
    async def _query_claude_websearch(self, options: ClaudeCodeOptions, prompt: str) -> Optional[str]:
        """查询Claude获取WebSearch结果的辅助方法 - 参考官方示例"""
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
                                self.logger.info(f"📄 内容片段: {text[:100]}...")
                
                # 检查停止条件
                if hasattr(message, 'stop_reason') and message.stop_reason:
                    self.logger.info(f"🛑 收到停止信号: {message.stop_reason}")
                    break
                    
                # 防止无限循环
                if message_count >= 20:
                    self.logger.warning("⚠️ 消息数量过多，主动停止")
                    break
            
            # 拼接所有内容
            final_result = "\n".join(all_content) if all_content else None
            self.logger.info(f"📊 总共收到{message_count}条消息，内容长度: {len(final_result) if final_result else 0}")
            
            return final_result
    
    def _build_search_prompt(self, query: str, city: str = None) -> str:
        """构建搜索提示词"""
        
        if city:
            search_query = f"{city} {query}"
            context = f"针对{city}地区"
        else:
            search_query = query
            context = "通用"
        
        prompt = f"""
使用WebSearch工具搜索以下内容：

搜索关键词：{search_query}
查询背景：{context}查询

请按以下要求执行搜索：
1. 使用WebSearch工具搜索最新、最相关的信息
2. 关注信息的时效性和准确性
3. 返回简洁清晰的搜索结果摘要

搜索完成后，请用简洁的中文总结搜索到的关键信息。
"""
        
        return prompt
    
    async def test_trending_news(self, city: str) -> Dict[str, Any]:
        """
        专门测试热点新闻搜索功能
        """
        start_time = time.time()
        try:
            # 获取当前时间确保查询最新内容
            import datetime
            current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
            
            # 构建热点新闻搜索提示
            news_prompt = f"""
使用WebSearch搜索{city}在{current_date}的最新热点新闻和时事。

搜索要点：
1. {city}今日热点新闻
2. 当地重要事件
3. 社会热点话题
4. 抖音、小红书等社交媒体热点

请搜索并返回：
- 新闻标题和简要内容
- 信息来源
- 发布时间
- 热度或关注度

请用中文返回搜索结果，确保信息的时效性和准确性。
"""
            
            # 配置专门的新闻搜索选项 - 优化轮次
            options = ClaudeCodeOptions(
                system_prompt="新闻热点搜索专家。使用WebSearch工具快速搜索最新的新闻热点，提供简洁摘要。",
                max_turns=2,  # 减少轮次提高速度
                allowed_tools=["WebSearch"],
                permission_mode="acceptEdits"
            )
            
            self.logger.info(f"📰 开始热点新闻测试查询: {city}")
            
            # 执行搜索，不设置超时
            news_result = await self._query_claude_websearch(options, news_prompt)
            
            elapsed_time = time.time() - start_time
            
            if news_result:
                self.logger.info(f"✅ 热点新闻测试成功: {city}, 耗时: {elapsed_time:.2f}秒")
                return {
                    "code": 0,
                    "message": "热点新闻查询成功",
                    "data": {
                        "city": city,
                        "date": current_date,
                        "news_content": news_result,
                        "elapsed_time": round(elapsed_time, 2)
                    }
                }
            else:
                self.logger.warning(f"⚠️ 未获取到新闻内容, 耗时: {elapsed_time:.2f}秒")
                return {
                    "code": 1,
                    "message": "未获取到新闻内容",
                    "data": {
                        "city": city, 
                        "error": "搜索结果为空",
                        "elapsed_time": round(elapsed_time, 2)
                    }
                }
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"❌ 热点新闻测试失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            import traceback
            traceback.print_exc()
            return {
                "code": 1,
                "message": f"查询失败: {str(e)}",
                "data": {
                    "city": city, 
                    "error": str(e),
                    "elapsed_time": round(elapsed_time, 2)
                }
            }