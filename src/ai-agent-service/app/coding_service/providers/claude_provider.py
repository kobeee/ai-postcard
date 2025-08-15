import asyncio
import logging
import os
import time
import traceback
from typing import AsyncGenerator
from .base import BaseCodeProvider
from ..config import settings

# 导入Claude Code SDK
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

# 配置增强日志
import colorlog

# 创建彩色日志处理器
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# 性能监控辅助函数
def log_timing(action: str, start_time: float):
    """记录操作耗时"""
    duration = time.time() - start_time
    logger.info(f"⏱️  {action} 耗时: {duration:.2f}s")
    return duration

class ClaudeCodeProvider(BaseCodeProvider):
    """
    使用 Claude Code SDK 与 Anthropic API 交互的代码生成提供者。
    
    这个类封装了 claude-code-sdk 的所有交互逻辑，
    将其流式响应转换为标准化的事件格式。
    """
    
    def __init__(self):
        # 优先兼容两种环境变量命名：ANTHROPIC_AUTH_TOKEN（Claude Code风格）与 ANTHROPIC_API_KEY（标准Anthropic风格）
        api_key = (
            os.getenv("ANTHROPIC_AUTH_TOKEN")
            or settings.ANTHROPIC_API_KEY
            or os.getenv("ANTHROPIC_API_KEY")
        )

        if not api_key:
            logger.error("未检测到API密钥，请设置 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY")
            raise ValueError("ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN is required")

        # 统一导出为两种变量，确保SDK和我们代码均可读取
        os.environ["ANTHROPIC_AUTH_TOKEN"] = api_key
        os.environ["ANTHROPIC_API_KEY"] = api_key

        # 记录初始化信息
        logger.info(f"ClaudeCodeProvider initialized with API key prefix: {api_key[:10]}...")
        logger.info(f"Default model: {settings.CLAUDE_DEFAULT_MODEL}")

        # BASE_URL 同样兼容常见命名
        base_url = (
            os.getenv("ANTHROPIC_BASE_URL")
            or os.getenv("ANTHROPIC_API_BASE")
            or settings.ANTHROPIC_BASE_URL
        )
        if base_url:
            os.environ["ANTHROPIC_BASE_URL"] = base_url
            logger.info(f"Using custom Anthropic BASE_URL: {base_url}")
        else:
            logger.info("Using default Anthropic API endpoint")
    
    async def generate(
        self, 
        prompt: str,
        session_id: str,
        model: str | None = None
    ) -> AsyncGenerator[dict, None]:
        """
        使用 Claude Code SDK 流式生成前端代码。
        
        Args:
            prompt: 用户的编码需求描述。
            session_id: 会话标识符。
            model: 要使用的具体模型，如果为None则使用默认模型。
        
        Yields:
            标准化的事件字典。
        """
        target_model = model or settings.CLAUDE_DEFAULT_MODEL
        generation_start_time = time.time()
        
        logger.info(f"🚀 === 开始代码生成会话: {session_id} ===")
        logger.info(f"📝 用户提示: {prompt[:200]}...")
        logger.info(f"🤖 使用模型: {target_model}")
        logger.info(f"⏰ 开始时间: {time.strftime('%H:%M:%S')}")
        
        try:
            # 首先验证API端点配置
            logger.info("🔍 验证API端点配置...")
            try:
                self._validate_api_endpoint()
                logger.info("✅ API端点验证成功")
            except ValueError as api_error:
                logger.error(f"❌ API端点配置错误: {str(api_error)}")
                yield {
                    "type": "error",
                    "content": f"🚨 API配置错误\n\n{str(api_error)}\n\n💡 解决建议：\n1. 检查 ANTHROPIC_BASE_URL 是否指向有效的API服务\n2. 确认URL返回JSON而非HTML页面\n3. 验证API密钥是否正确配置"
                }
                return
                
            # 构建专门用于前端代码生成的系统提示
            logger.debug("🔧 构建系统提示...")
            system_prompt = self._build_system_prompt()
            logger.debug(f"📄 系统提示长度: {len(system_prompt)} 字符")
            
            # 构建完整的编码提示
            logger.debug("📝 构建用户提示...")
            full_prompt = self._build_coding_prompt(prompt)
            logger.debug(f"📄 完整提示长度: {len(full_prompt)} 字符")
            logger.debug(f"📄 完整提示内容: {full_prompt[:200]}...")
            
            yield {"type": "status", "content": f"🔄 初始化 {target_model} 模型..."}
            logger.info("📤 发送初始化状态")
            
            yield {"type": "status", "content": "🧠 分析您的需求描述..."}
            logger.info("📤 发送分析状态")
            
            # 使用Claude Code SDK配置选项
            # 注意：ANTHROPIC_BASE_URL通过环境变量自动被Claude SDK读取，不需要在选项中传递
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=3,  # 允许多轮对话来完善代码
                allowed_tools=["Read", "WebSearch", "Bash"]  # 允许的工具
            )
            
            # 记录BASE_URL配置情况
            if settings.ANTHROPIC_BASE_URL:
                logger.info(f"Claude SDK will use base URL from env: {settings.ANTHROPIC_BASE_URL}")
            else:
                logger.info("Claude SDK will use default Anthropic API endpoint")
            logger.info(f"Created ClaudeCodeOptions with max_turns=3, tools={options.allowed_tools}")
            
            # 创建Claude SDK客户端
            logger.info("🔧 初始化 ClaudeSDKClient...")
            client_start_time = time.time()
            generated_code_chunks = []  # 初始化代码片段列表
            try:
                async with ClaudeSDKClient(options=options) as client:
                    client_init_duration = time.time() - client_start_time
                    logger.info(f"✅ ClaudeSDKClient 初始化成功，耗时 {client_init_duration:.2f}s")
                    
                    yield {"type": "status", "content": "💭 Claude 正在制定代码方案..."}
                    logger.info("📤 发送制定方案状态")
                    
                    # 发送查询
                    logger.info("📨 发送查询到 Claude...")
                    query_start_time = time.time()
                    await client.query(full_prompt)
                    query_duration = time.time() - query_start_time
                    logger.info(f"✅ 查询发送成功，耗时 {query_duration:.2f}s，开始接收响应...")
                    
                    generated_code_chunks = []
                    current_phase = "thinking"  # thinking, coding, reviewing
                    message_count = 0
                    timeout_counter = 0
                    max_timeout = 120  # 2分钟超时
                    response_start_time = time.time()
                    
                    # 流式接收响应
                    try:
                        logger.info("🔄 开始流式接收 Claude 响应...")
                        async for message in client.receive_response():
                            message_count += 1
                            response_elapsed = time.time() - response_start_time
                            logger.debug(f"📨 收到消息 #{message_count}: {type(message).__name__} (已用时 {response_elapsed:.1f}s)")
                            
                            # 处理消息内容
                            if hasattr(message, 'content'):
                                logger.debug(f"📄 消息包含 {len(message.content)} 个内容块")
                                for block_idx, block in enumerate(message.content):
                                    if hasattr(block, 'text'):
                                        text = block.text
                                        # 记录完整的原始响应以便调试
                                        if "error" in text.lower() or "api error" in text.lower():
                                            logger.warning(f"⚠️ 检测到错误响应: {text}")
                                            
                                        logger.debug(f"📝 处理文本块 {block_idx}: {text[:100]}...")
                                        logger.debug(f"📊 文本块长度: {len(text)} 字符")
                                        
                                        # 分析消息内容，确定当前阶段
                                        phase_info = self._analyze_phase(text)
                                        if phase_info != current_phase:
                                            current_phase = phase_info
                                            logger.info(f"Phase changed to: {current_phase}")
                                            yield {"type": "phase_change", "content": self._get_phase_description(current_phase)}
                                        
                                        # 检查是否包含代码块
                                        if self._contains_code(text):
                                            generated_code_chunks.append(text)
                                            logger.info(f"Found code block, total chunks: {len(generated_code_chunks)}")
                                            yield {"type": "code_generation", "content": text, "phase": current_phase}
                                        else:
                                            # 这是思考过程或分析文字
                                            logger.debug("Text is analysis content")
                                            yield {"type": "analysis", "content": text, "phase": current_phase}
                        
                            # 处理工具调用
                            if hasattr(message, 'tool_calls'):
                                logger.info(f"Message has {len(message.tool_calls)} tool calls")
                                for tool_call in message.tool_calls:
                                    logger.info(f"Tool call: {tool_call.name}")
                                    yield {
                                        "type": "tool_use", 
                                        "content": f"🔧 使用工具: {tool_call.name}",
                                        "tool_name": tool_call.name,
                                        "tool_args": getattr(tool_call, 'arguments', {})
                                    }
                            
                            # 处理思考步骤
                            if hasattr(message, 'role') and message.role == 'assistant':
                                if hasattr(message, 'thinking_steps'):
                                    logger.info(f"Message has {len(message.thinking_steps)} thinking steps")
                                    for i, step in enumerate(message.thinking_steps):
                                        yield {
                                            "type": "thinking_step",
                                            "content": f"步骤 {i+1}: {step}",
                                            "step_number": i+1
                                        }
                            
                            # 检查是否为最终结果消息
                            if type(message).__name__ == "ResultMessage":
                                logger.info("Received ResultMessage, completing generation")
                                yield {"type": "status", "content": "✅ 代码生成完成，正在优化..."}
                                
                                # 整合所有生成的代码片段
                                final_code = self._extract_and_clean_code(generated_code_chunks)
                                logger.info(f"Final code length: {len(final_code)} characters")
                                
                                yield {
                                    "type": "complete",
                                    "final_code": final_code,
                                    "metadata": {
                                        "model_used": target_model,
                                        "session_id": session_id,
                                        "cost_usd": getattr(message, 'total_cost_usd', 0),
                                        "duration_ms": getattr(message, 'duration_ms', 0),
                                        "total_tokens": getattr(message, 'total_tokens', 0)
                                    }
                                }
                                logger.info("Code generation completed successfully")
                                return
                        
                        total_response_time = time.time() - response_start_time
                        logger.warning(f"⚠️  响应接收完毕但未找到 ResultMessage，总用时 {total_response_time:.2f}s")
                        
                        # 如果收集到了代码片段，仍然尝试生成结果
                        if generated_code_chunks:
                            logger.info(f"🔧 尝试从 {len(generated_code_chunks)} 个代码片段生成最终结果")
                            final_code = self._extract_and_clean_code(generated_code_chunks)
                            yield {
                                "type": "complete",
                                "final_code": final_code,
                                "metadata": {
                                    "model_used": target_model,
                                    "session_id": session_id,
                                    "total_time_seconds": total_response_time,
                                    "message_count": message_count,
                                    "note": "完成但未收到正式结束消息"
                                }
                            }
                        
                    except Exception as receive_error:
                        receive_time = time.time() - response_start_time
                        logger.error(f"❌ 接收消息时发生错误 (用时 {receive_time:.2f}s): {str(receive_error)}")
                        logger.error(f"📋 错误详情: {traceback.format_exc()}")
                        yield {
                            "type": "error",
                            "content": f"接收消息时发生错误: {str(receive_error)}"
                        }
            
            except asyncio.CancelledError:
                # 捕获取消错误，优雅结束
                sdk_time = time.time() - client_start_time
                logger.warning(f"⚠️ 请求被取消 (用时 {sdk_time:.2f}s)")
                yield {
                    "type": "error",
                    "content": "请求被取消，可能是由于连接超时或服务中断"
                }
            except RuntimeError as runtime_err:
                # 特殊处理异步作用域错误
                sdk_time = time.time() - client_start_time
                if "cancel scope" in str(runtime_err):
                    logger.warning(f"⚠️ 异步作用域错误 (用时 {sdk_time:.2f}s): {str(runtime_err)}")
                    if generated_code_chunks:
                        # 尽管有错误，仍然尝试返回收集到的代码
                        logger.info("尝试从已收集的代码片段生成结果...")
                        final_code = self._extract_and_clean_code(generated_code_chunks)
                        yield {
                            "type": "complete",
                            "final_code": final_code,
                            "metadata": {
                                "model_used": target_model,
                                "session_id": session_id,
                                "note": "尽管有异步错误，但仍完成了代码生成"
                            }
                        }
                    else:
                        yield {
                            "type": "error",
                            "content": "请求处理过程中发生异步错误"
                        }
                else:
                    logger.error(f"❌ 运行时错误 (用时 {sdk_time:.2f}s): {str(runtime_err)}")
                    logger.error(f"📋 错误详情: {traceback.format_exc()}")
                    yield {
                        "type": "error",
                        "content": f"运行时错误: {str(runtime_err)}"
                    }
            except Exception as sdk_error:
                sdk_time = time.time() - client_start_time
                logger.error(f"❌ ClaudeSDKClient 错误 (用时 {sdk_time:.2f}s): {str(sdk_error)}")
                logger.error(f"📋 SDK 错误详情: {traceback.format_exc()}")
                yield {
                    "type": "error",
                    "content": f"Claude SDK 连接错误: {str(sdk_error)}"
                }
        
        except Exception as e:
            total_generation_time = time.time() - generation_start_time
            logger.error(f"❌ 代码生成过程发生错误 (总用时 {total_generation_time:.2f}s): {str(e)}")
            logger.error(f"📋 完整错误追踪: {traceback.format_exc()}")
            yield {
                "type": "error", 
                "content": f"代码生成过程中发生错误: {str(e)}"
            }
        finally:
            total_generation_time = time.time() - generation_start_time
            logger.info(f"🏁 === 代码生成会话结束: {session_id} ===")
            logger.info(f"⏱️  总耗时: {total_generation_time:.2f}s")
            logger.info(f"⏰ 结束时间: {time.strftime('%H:%M:%S')}")
    
    def _build_system_prompt(self) -> str:
        """构建专门用于前端代码生成的系统提示"""
        return """你是一个专业的前端开发工程师和UI/UX设计师。你的任务是根据用户的描述，生成完整的、可以直接在浏览器中运行的前端代码。

要求：
1. 生成的代码必须是完整的HTML文件，包含HTML、CSS和JavaScript
2. 代码应该是自包含的，不依赖任何外部库或资源
3. 注重视觉效果和用户体验，创建美观、现代的界面
4. 包含合适的动画效果和交互元素
5. 确保代码在现代浏览器中能正常运行
6. 使用响应式设计，适配不同屏幕尺寸

请按照以下格式生成代码：
1. 首先简述你的设计思路
2. 然后提供完整的HTML代码
3. 最后说明关键功能和特性"""
    
    def _build_coding_prompt(self, user_prompt: str) -> str:
        """构建完整的编码提示"""
        return f"""请根据以下需求生成前端代码：

{user_prompt}

请创建一个完整的HTML页面，包含所有必要的HTML、CSS和JavaScript代码。
代码应该能够直接在浏览器中打开并正常工作。"""
    
    def _validate_api_endpoint(self):
        """
        验证API端点是否有效，确保不是HTML页面
        
        Raises:
            ValueError: 如果API端点无效或返回HTML内容
        """
        import requests
        
        # 获取API配置
        api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_AUTH_TOKEN")
        base_url = settings.ANTHROPIC_BASE_URL or "https://api.anthropic.com"
        
        if not api_key:
            raise ValueError("未设置API密钥")
        
        logger.debug(f"🔍 验证API端点: {base_url}")
        
        # 构造测试请求
        test_url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        test_data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "test"}]
        }
        
        try:
            logger.debug("📤 发送API验证请求...")
            response = requests.post(test_url, headers=headers, json=test_data, timeout=10)
            
            # 检查响应内容类型
            content_type = response.headers.get('content-type', '').lower()
            logger.debug(f"📥 响应类型: {content_type}")
            
            # 如果返回HTML，说明不是有效的API端点
            if 'text/html' in content_type:
                raise ValueError(f"API端点 {base_url} 返回HTML页面，不是有效的API服务")
            
            # 检查响应内容是否包含HTML标签
            if '<html' in response.text.lower():
                logger.warning(f"⚠️ 检测到HTML响应: {response.text[:100]}...")
                raise ValueError(f"API端点 {base_url} 返回HTML内容，可能是代理页面而非API服务")
            
            # 尝试解析JSON响应
            try:
                response.json()
                logger.debug("✅ API端点返回有效JSON响应")
            except ValueError:
                logger.warning(f"⚠️ 无法解析JSON响应: {response.text[:100]}...")
                raise ValueError(f"API端点 {base_url} 未返回有效JSON响应")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"无法连接到API端点 {base_url}: {str(e)}")
    
    def _contains_code(self, text: str) -> bool:
        """检查文本是否包含代码块"""
        code_indicators = [
            "```html", "```css", "```javascript", "```js",
            "<!DOCTYPE", "<html", "<head", "<body",
            "<script", "<style", "function ", "const ", "let ", "var "
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in code_indicators)
    
    def _extract_and_clean_code(self, code_chunks: list[str]) -> str:
        """从代码片段中提取并清理完整的代码"""
        if not code_chunks:
            logger.warning("No code chunks found, returning default HTML")
            return "<html><body><h1>抱歉，未能生成有效的代码</h1></body></html>"
        
        logger.info(f"Extracting and cleaning {len(code_chunks)} code chunks")
        
        # 合并所有代码片段
        combined_code = "\n".join(code_chunks)
        
        # 尝试提取HTML代码块
        if "```html" in combined_code:
            # 提取HTML代码块
            start = combined_code.find("```html") + 7
            end = combined_code.find("```", start)
            if end > start:
                extracted = combined_code[start:end].strip()
                logger.info(f"Extracted HTML code block: {len(extracted)} characters")
                return extracted
        
        # 如果没有明确的代码块标记，但包含HTML标签，直接返回
        if "<!DOCTYPE" in combined_code or "<html" in combined_code:
            logger.info("Found complete HTML document without code block markers")
            return combined_code.strip()
        
        # 作为后备，包装成完整的HTML文档
        logger.warning("No complete HTML found, wrapping content in HTML document")
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI生成的页面</title>
</head>
<body>
    {combined_code}
</body>
</html>"""
    
    def _analyze_phase(self, text: str) -> str:
        """分析当前文本内容，判断AI处于哪个工作阶段"""
        text_lower = text.lower()
        
        # 编码阶段的关键词
        coding_indicators = [
            "```", "html", "css", "javascript", "function", "class", 
            "<!doctype", "<html", "<head", "<body", "<script", "<style"
        ]
        
        # 分析阶段的关键词  
        analysis_indicators = [
            "分析", "思考", "设计", "计划", "考虑", "需要", "应该", "可以",
            "理解", "要求", "功能", "特性", "布局", "样式", "交互"
        ]
        
        # 审查阶段的关键词
        reviewing_indicators = [
            "检查", "确保", "验证", "测试", "优化", "完善", "修改", "调整"
        ]
        
        if any(indicator in text_lower for indicator in coding_indicators):
            return "coding"
        elif any(indicator in text_lower for indicator in reviewing_indicators):
            return "reviewing"  
        elif any(indicator in text_lower for indicator in analysis_indicators):
            return "thinking"
        else:
            return "thinking"  # 默认为思考阶段
    
    def _get_phase_description(self, phase: str) -> str:
        """获取阶段的描述信息"""
        phase_descriptions = {
            "thinking": "🤔 分析阶段 - Claude 正在理解需求并制定方案...",
            "coding": "⚡ 编码阶段 - Claude 正在生成代码...",
            "reviewing": "🔍 优化阶段 - Claude 正在检查和优化代码..."
        }
        return phase_descriptions.get(phase, "🔄 处理中...")