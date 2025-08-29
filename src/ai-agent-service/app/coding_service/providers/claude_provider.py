import asyncio
import logging
import os
import time
import traceback
from typing import AsyncGenerator, Dict, Any
import urllib.request
import urllib.parse
import mimetypes
from .base import BaseCodeProvider
from ..config import settings

# 导入Claude Code SDK
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

# 设置日志记录器
logger = logging.getLogger(__name__)

class ClaudeCodeProvider(BaseCodeProvider):
    """
    Claude Code SDK提供者 - 重构优化版本
    
    基于Claude Code SDK官方文档最佳实践：
    - 使用acceptEdits模式自动接受编辑
    - 非交互式执行，无需用户确认
    - 简化的流式处理逻辑
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Claude Code SDK"
        self.model = "claude-sonnet-4-20250514"
        
        # 验证环境变量
        auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        
        if not auth_token:
            logger.error("❌ ANTHROPIC_AUTH_TOKEN 环境变量未设置")
            raise ValueError("ANTHROPIC_AUTH_TOKEN 环境变量未设置")
        
        if base_url:
            logger.info(f"✅ 使用自定义Base URL: {base_url}")

    async def generate(self, prompt: str, session_id: str, model: str | None = None, image_url: str | None = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成代码 - 优化版本，基于Claude Code SDK最佳实践
        
        **重要修复**: 基于官方文档优化图片处理流程，避免超时和无响应问题
        """
        # 使用传入的model参数，如果没有则使用默认模型
        target_model = model or self.model
        
        # 【性能优化】记录开始时间用于性能监控
        generation_start_time = time.time()
        
        try:
            yield {"type": "status", "content": "🚀 初始化AI代码生成器（优化模式）..."}
            logger.info(f"📤 开始优化代码生成任务 - 会话ID: {session_id}, 模型: {target_model}")
            if image_url:
                logger.info(f"🖼️ 包含图片处理: {image_url[:50]}...")

            # 构建系统提示 - 非交互式模式
            system_prompt = self._build_system_prompt()
            
            # Claude Code SDK配置 - 基于官方文档最佳实践
            # 设置工作目录为AI生成文件的专用目录，避免与前端文件冲突
            # 与main.py中的static_dir保持一致：/app/app/static/generated
            generated_dir = "/app/app/static/generated"
            os.makedirs(generated_dir, exist_ok=True)  # 确保目录存在
            
            # 【修复】添加超时处理和更合理的工具配置
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=3,  # 降低轮次以避免超时，图片处理复杂度较高
                allowed_tools=["Write", "Read", "Edit"],  # 使用Write、Read、Edit工具用于文件生成
                permission_mode="bypassPermissions",  # 允许所有工具而不提示，实现完全自动化
                cwd=generated_dir,  # 设置为AI生成文件专用目录
                max_thinking_tokens=4000  # 【修复】限制思考tokens，避免过度分析
            )
            
            logger.info("🔧 创建Claude SDK客户端...")
            
            # 使用Claude SDK进行代码生成
            async with ClaudeSDKClient(options=options) as client:
                logger.info("✅ Claude SDK客户端初始化成功")
                
                # 【修复】优化图片处理：按照官方文档建议，直接在提示中引用图片
                combined_prompt = self._build_optimized_prompt(prompt, image_url, generated_dir)
                
                # 发送查询
                yield {"type": "status", "content": "🧠 分析需求并生成代码..."}
                logger.info(f"📨 发送查询, 长度: {len(combined_prompt)} 字符")
                
                # 【修复】添加超时保护的异步任务
                try:
                    await asyncio.wait_for(client.query(combined_prompt), timeout=30.0)  # 30秒查询超时
                    logger.info("📨 查询发送成功，开始接收响应...")
                except asyncio.TimeoutError:
                    logger.error("❌ 查询发送超时")
                    yield {"type": "error", "content": "查询发送超时，请重试"}
                    return
                
                # 收集生成的代码和分析内容
                generated_code_chunks = []
                markdown_content = []
                
                # 流式接收响应
                current_stream_buffer = ""  # 用于累积流式内容
                response_start_time = time.time()  # 响应处理开始时间
                
                # 【修复】添加响应超时处理和更详细的调试信息
                response_count = 0
                last_activity_time = time.time()
                
                try:
                    # 【修复】响应循环处理
                    async for message in client.receive_response():
                        response_count += 1
                        current_time = time.time()
                        last_activity_time = current_time
                        
                        logger.info(f"📨 收到响应 #{response_count}: {type(message).__name__} (耗时: {current_time - response_start_time:.1f}s)")
                        
                        # 【修复】增强的DEBUG模式和超时检测
                        if current_time - response_start_time > 300:  # 5分钟超时检测
                            logger.error("❌ 响应处理超时，主动终止")
                            yield {"type": "error", "content": "响应处理超时，请重试"}
                            return
                        
                        # 🔍 DEBUG模式 - 详细消息分析
                        debug_mode = logger.isEnabledFor(logging.DEBUG)
                        if debug_mode or response_count <= 3:  # 前3个消息总是记录详细信息
                            logger.info(f"🔍 消息详情 #{response_count}:")
                            logger.info(f"   - 类型: {type(message).__name__}")
                            logger.info(f"   - 属性: {[attr for attr in dir(message) if not attr.startswith('_')]}")
                            if hasattr(message, 'content') and message.content:
                                logger.info(f"   - 内容块数量: {len(message.content)}")
                                for j, block in enumerate(message.content):
                                    logger.info(f"   - 块 {j}: {type(block).__name__}")
                                    if hasattr(block, 'text') and block.text:
                                        logger.info(f"   - 文本长度: {len(block.text)}")
                        
                        # 处理消息内容
                        if hasattr(message, 'content') and message.content:
                            for i, block in enumerate(message.content):
                                if hasattr(block, 'text') and block.text:
                                    text = block.text
                                    current_stream_buffer += text
                                    
                                    # 实时流式输出文本内容
                                    if self._contains_code(text):
                                        generated_code_chunks.append(text)
                                        logger.info(f"✅ 代码块 #{len(generated_code_chunks)}: {text[:100]}...")
                                        
                                        # 尝试实时提取和更新文件
                                        partial_files = self._extract_files_info([current_stream_buffer])
                                        
                                        yield {
                                            "type": "code_stream", 
                                            "content": text, 
                                            "phase": "coding",
                                            "partial_files": partial_files,
                                            "buffer_length": len(current_stream_buffer)
                                        }
                                    else:
                                        markdown_content.append(text)
                                        logger.info(f"📝 文本块 #{len(markdown_content)}: {text[:100]}...")
                                        yield {"type": "markdown_stream", "content": text, "phase": "thinking"}
                    
                    # 处理工具调用和工具结果 - 提取文件名信息
                    if hasattr(message, 'content') and message.content:
                        for block in message.content:
                            # 处理工具调用 (ToolUseBlock)
                            if hasattr(block, 'name') and block.name == 'Write':
                                # 从Write工具调用中提取文件名
                                if hasattr(block, 'input') and 'file_path' in block.input:
                                    file_path = block.input['file_path']
                                    file_name = file_path.split('/')[-1]  # 提取文件名
                                    logger.info(f"🔧 Claude尝试写入文件: {file_name}")
                                    
                                    # 记录文件名信息，供后续使用
                                    if not hasattr(self, '_detected_filenames'):
                                        self._detected_filenames = []
                                    self._detected_filenames.append(file_name)
                                    
                                    yield {
                                        "type": "tool_use", 
                                        "content": f"🔧 生成文件: {file_name}",
                                        "tool_name": "Write",
                                        "file_name": file_name
                                    }
                            
                            # 处理工具结果 (ToolResultBlock) - 可能包含文件创建的反馈
                            elif hasattr(block, 'content') and hasattr(block, 'tool_use_id'):
                                tool_result_content = block.content
                                logger.info(f"🔧 工具执行结果: {tool_result_content}")
                                
                                # 从工具结果中提取文件信息
                                if "File created successfully at:" in tool_result_content:
                                    import re
                                    file_path_match = re.search(r"File created successfully at:\s*(.+)", tool_result_content)
                                    if file_path_match:
                                        raw_file_path = file_path_match.group(1).strip()
                                        
                                        # 处理相对路径：如果Claude返回相对路径，需要基于generated_dir构建完整路径
                                        if not os.path.isabs(raw_file_path):
                                            # 相对路径，基于工作目录构建完整路径
                                            full_file_path = os.path.join(generated_dir, raw_file_path)
                                        else:
                                            # 绝对路径直接使用
                                            full_file_path = raw_file_path
                                        
                                        file_name = os.path.basename(full_file_path)
                                        logger.info(f"✅ 文件创建成功: {file_name}")
                                        logger.info(f"📁 原始路径: {raw_file_path}")
                                        logger.info(f"📁 完整路径: {full_file_path}")
                                        
                                        # 读取文件内容并确保复制到预期路径
                                        try:
                                            if os.path.exists(full_file_path):
                                                # 仅对文本类型按utf-8读取，二进制文件跳过内容读取
                                                is_text = any(full_file_path.lower().endswith(ext) for ext in ['.html', '.css', '.js', '.json', '.txt', '.md', '.wxml', '.wxss'])
                                                if is_text:
                                                    with open(full_file_path, 'r', encoding='utf-8') as f:
                                                        file_content = f.read()
                                                else:
                                                    file_content = None
                                                    logger.info(f"📄 成功读取文件内容: {file_name} ({len(file_content)} 字符)")
                                                    
                                                    # 🔧 强制确保文件在预期路径下存在
                                                    if file_content is not None:
                                                        self._ensure_file_in_target_path(file_name, file_content, generated_dir)
                                                    
                                                    yield {
                                                        "type": "file_created",
                                                        "file_name": file_name,
                                                        "file_content": file_content,
                                                        "content": f"✅ 文件创建完成: {file_name}"
                                                    }
                                            else:
                                                logger.warning(f"⚠️ 文件不存在: {full_file_path}")
                                                # 尝试在当前工作目录查找
                                                alt_paths = [
                                                    os.path.join(os.getcwd(), file_name),
                                                    os.path.join("/app", file_name),
                                                    file_name  # 直接使用文件名
                                                ]
                                                
                                                file_found = False
                                                for alt_path in alt_paths:
                                                    if os.path.exists(alt_path):
                                                        logger.info(f"🔍 在备用路径找到文件: {alt_path}")
                                                        with open(alt_path, 'r', encoding='utf-8') as f:
                                                            file_content = f.read()
                                                            yield {
                                                                "type": "file_created",
                                                                "file_name": file_name,
                                                                "file_content": file_content,
                                                                "content": f"✅ 文件创建完成: {file_name}"
                                                            }
                                                        file_found = True
                                                        break
                                                
                                                if not file_found:
                                                    yield {
                                                        "type": "tool_result", 
                                                        "content": f"⚠️ 文件创建完成但无法读取: {file_name}",
                                                        "file_name": file_name,
                                                        "file_path": full_file_path
                                                    }
                                        except Exception as e:
                                            logger.error(f"❌ 读取文件失败: {file_name} - {str(e)}")
                                            yield {
                                                "type": "tool_result", 
                                                "content": f"⚠️ 文件创建完成但读取失败: {file_name}",
                                                "file_name": file_name,
                                                "file_path": full_file_path
                                            }
                    
                    # 处理结果消息
                    if type(message).__name__ == "ResultMessage":
                        logger.info("✅ 收到结果消息，生成完成")
                        
                        # 提取最终代码
                        final_code = self._extract_and_clean_code(generated_code_chunks)
                        logger.info(f"✅ 最终代码生成完成，长度: {len(final_code)} 字符")
                        
                        yield {"type": "status", "content": "✅ 代码生成完成！"}
                        
                        # 提取并返回文件信息
                        extracted_files = self._extract_files_info(generated_code_chunks)
                        
                        # 🔍 扫描generated目录中实际存在的文件（兜底方案）
                        actual_files = self._scan_generated_files(generated_dir)
                        if actual_files:
                            # 合并实际文件和提取的文件
                            for filename, content in actual_files.items():
                                if filename not in extracted_files:
                                    extracted_files[filename] = content
                                    logger.info(f"📁 从目录扫描到新文件: {filename}")
                        
                        # 🔧 确保所有文件都在正确的位置（关键步骤）
                        for filename, content in extracted_files.items():
                            self._ensure_file_in_target_path(filename, content, generated_dir)
                        
                        logger.info(f"📁 最终文件列表: {list(extracted_files.keys())}")
                        
                        # 【性能监控】计算总耗时
                        total_generation_time = time.time() - generation_start_time
                        
                        yield {
                            "type": "complete",
                            "final_code": final_code,
                            "files": extracted_files,  # 新增：文件信息
                            "metadata": {
                                "model_used": target_model,
                                "session_id": session_id,
                                "cost_usd": getattr(message, 'total_cost_usd', 0),
                                "duration_ms": getattr(message, 'duration_ms', 0),
                                "total_tokens": getattr(message, 'total_tokens', 0),
                                # 【优化监控】性能指标
                                "total_generation_time": round(total_generation_time, 2),
                                "files_generated": len(extracted_files),
                                "code_length": len(final_code),
                                "optimization_enabled": True
                            }
                        }
                        logger.info(f"🎉 优化代码生成完成 - 耗时: {total_generation_time:.2f}s, 文件: {len(extracted_files)}, 代码: {len(final_code)} 字符")
                        return
                        
                except asyncio.TimeoutError:
                    logger.error("❌ 响应接收超时")
                    yield {"type": "error", "content": "响应接收超时，请重试"}
                    return
                except Exception as resp_e:
                    logger.error(f"❌ 响应处理异常: {str(resp_e)}")
                    logger.error(f"📋 响应异常详情: {traceback.format_exc()}")
                    yield {"type": "error", "content": f"响应处理失败: {str(resp_e)}"}
                    return
                        
        except asyncio.CancelledError:
            # 任务已完成或上层取消，视为正常结束，避免进程异常退出
            logger.warning("⚠️ 生成过程被取消（CancelledError），已安全忽略")
            return
        except GeneratorExit:
            # WebSocket连接断开时的正常清理，不是错误
            logger.info("🔌 WebSocket连接已断开，停止代码生成")
            raise  # 重新抛出，让异步生成器正常退出
        except RuntimeError as e:
            if "cancel scope" in str(e) or "GeneratorExit" in str(e):
                # 异步作用域错误，通常发生在连接断开时，不影响功能
                logger.warning(f"⚠️ 异步清理警告: {str(e)}")
                # 不yield错误消息，因为这不是真正的错误
            else:
                logger.error(f"❌ 运行时错误: {str(e)}")
                yield {"type": "error", "content": f"运行时错误: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ 代码生成失败: {str(e)}")
            logger.error(f"📋 异常详情: {traceback.format_exc()}")
            yield {"type": "error", "content": f"代码生成失败: {str(e)}"}
    
    def _build_optimized_prompt(self, prompt: str, image_url: str | None = None, generated_dir: str = None) -> str:
        """
        构建优化的提示，基于官方Claude Code SDK最佳实践处理图片
        
        **关键修复**: 不下载图片，直接在提示中引用图片URL，让Claude自动处理
        """
        # 基础提示构建
        base_prompt = f"{prompt}\n\n"
        
        # 添加运行时约束
        runtime_constraints = (
            "[Runtime Constraints]\n"
            "- 本项目运行于微信小程序的 webview 中，要求移动端优先与完全自适应\n"
            "- 所有产物须为纯 HTML/CSS/JS，不依赖外部框架\n"
            "- 动画和交互需在移动端流畅，注意性能与可用性\n"
        )
        
        # 【修复】图片处理：按照官方文档，直接引用图片，让Claude自动使用Read工具
        if image_url:
            # 下载图片到本地作为参考（为了稳定性）
            image_filename = None
            if generated_dir:
                try:
                    image_filename = self._download_image(image_url, generated_dir)
                    if image_filename:
                        logger.info(f"🖼️ 图片已下载供参考: {image_filename}")
                except Exception as e:
                    logger.warning(f"⚠️ 图片下载失败: {str(e)}")
            
            # 【关键修复】简化图片引用，让Claude自动处理
            if image_filename:
                image_reference = (
                    f"\n[Visual Reference]\n"
                    f"参考图片: {image_filename}\n"
                    f"请分析图片的配色方案、布局风格和视觉元素，创建风格一致的交互页面。\n"
                )
            else:
                # 如果下载失败，直接引用URL
                image_reference = (
                    f"\n[Visual Reference]\n" 
                    f"参考图片: {image_url}\n"
                    f"请分析图片的配色方案、布局风格和视觉元素，创建风格一致的交互页面。\n"
                )
        else:
            image_reference = ""
        
        # 组合最终提示
        combined_prompt = base_prompt + runtime_constraints + image_reference
        
        logger.info(f"📝 构建优化提示完成, 总长度: {len(combined_prompt)} 字符")
        if image_url:
            logger.info(f"🖼️ 包含图片引用: {'本地文件' if image_filename else 'URL引用'}")
            
        return combined_prompt

    def _build_system_prompt(self) -> str:
        """构建系统提示 - 生成移动端优先的HTML/CSS/JS单页明信片"""
        return """
You are an expert mobile web UI developer. Your task is to generate a beautiful, animated postcard as a single mobile-friendly web page.

# Requirements
- Generate production-ready HTML/CSS/JS for a postcard card sized 375x600px (mobile portrait)
- Prefer a single HTML file with inline CSS. If you split files, use exactly: index.html, style.css, script.js
- No external frameworks or CDNs. Pure HTML5/CSS3/vanilla JS only
- Smooth animations and delightful micro-interactions suitable for mobile
- Embed provided background image URL elegantly with overlays for text readability

# File rules
- Use the Write tool to create files in the working directory
- Allowed filenames: index.html, style.css, script.js (no subdirectories)
- Keep CSS concise; inline CSS inside index.html is preferred

# Mobile-first constraints
- The card must be centered with fixed size 375x600 and max-width: 100vw
- Use modern CSS (flex, transform, transition, keyframes)
- Avoid heavy computations; ensure 60fps on mobile

# Output
- Create index.html with a complete <!DOCTYPE html> document including meta viewport
- Optionally create style.css and script.js; link them properly if created
        """

    def _download_image(self, image_url: str, target_dir: str) -> str | None:
        """下载图片到目标目录，返回文件名；失败返回None"""
        try:
            os.makedirs(target_dir, exist_ok=True)

            parsed = urllib.parse.urlparse(image_url)
            url_path = parsed.path or ""
            # 从URL推断扩展名
            ext = os.path.splitext(url_path)[1].lower()

            req = urllib.request.Request(image_url, headers={"User-Agent": "ai-postcard-bot/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if not ext:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "png" in content_type:
                        ext = ".png"
                    elif "jpeg" in content_type or "jpg" in content_type:
                        ext = ".jpg"
                    elif "webp" in content_type:
                        ext = ".webp"
                    elif "gif" in content_type:
                        ext = ".gif"
                    else:
                        # 兜底
                        guessed = mimetypes.guess_extension(content_type.split(";")[0]) if content_type else None
                        ext = guessed or ".jpg"

            filename = f"postcard_image{ext}"
            file_path = os.path.join(target_dir, filename)
            with open(file_path, "wb") as f:
                f.write(data)
            return filename
        except Exception as e:
            logger.warning(f"下载图片失败: {image_url} - {str(e)}")
            return None

    def _contains_code(self, text: str) -> bool:
        """判断文本是否包含代码块"""
        if not text:
            return False
        
        # 更宽松的代码块判断条件
        code_indicators = [
            # 代码块标记
            '```',
            # 微信小程序WXML标签
            '<view', '<text', '<image', '<button', '<input', '<form', 
            '<scroll-view', '<swiper', '<picker', '<switch', '<slider',
            # 微信小程序指令
            'wx:for', 'wx:if', 'wx:key', 'wx:elif', 'wx:else',
            'bindtap', 'bindinput', 'bindchange', 'catchtap',
            # 微信小程序数据绑定
            '{{', '}}',
            # HTML相关
            '<!DOCTYPE', '<html', '<body', '<div', '<script', '<style',
            '<canvas', '<svg',
            # JavaScript相关
            'function ', 'const ', 'let ', 'var ', '=>',
            'document.', 'window.', 'addEventListener',
            'console.log', 'querySelector',
            # 微信小程序JavaScript
            'Component({', 'this.setData', 'this.data', 'wx.', 
            'properties:', 'methods:', 'lifetimes:', 'attached():', 'ready():',
            # CSS相关
            'background:', 'color:', 'font-size:', 'margin:', 'padding:',
            'display:', 'position:', 'width:', 'height:',
            # 微信小程序WXSS
            'rpx', 'view {', '.container {', '.page {',
            # 其他代码特征
            '{', '}', ';', '//', '/*', '*/',
        ]
        
        # 如果包含代码块标记，直接返回True
        if '```' in text:
            return True
            
        # 否则检查其他代码特征，需要满足多个条件
        matches = sum(1 for indicator in code_indicators if indicator in text)
        return matches >= 3  # 至少包含3个代码特征才认为是代码

    def _extract_files_info(self, code_chunks: list) -> dict:
        """改进的文件提取逻辑，专门处理微信小程序组件代码"""
        if not code_chunks:
            return {}
        
        import re
        full_content = '\n'.join(code_chunks)
        extracted_files = {}
        
        # 🔍 微信小程序文件模式匹配
        file_patterns = [
            # 标准文件名格式，支持小程序文件扩展名
            r'```([\w\-_.]+\.(?:wxml|wxss|js|json))\s*\n(.*?)```',
            # 兼容HTML/CSS格式，转换为小程序格式
            r'```([\w\-_.]+\.(?:html|css|js|json|md|txt))\s*\n(.*?)```',
            # 带语言标识
            r'```(\w+)\s*\n(?:\/\*.*?([\w\-_.]+\.(?:wxml|wxss|js)).*?\*\/\s*)?(.*?)```',
            # Write工具调用模式
            r'file_path["\']:\s*["\']([^"\']+)["\'].*?content["\']:\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, full_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:  # 标准格式 (filename, content)
                        filename, content = match
                    elif len(match) == 3:  # 带语言标识 (lang, filename, content)
                        lang, filename, content = match
                        if not filename:  # 如果没有文件名，根据语言推断
                            filename = self._get_default_miniprogram_filename(lang)
                    else:
                        continue
                    
                    if filename and content and content.strip():
                        # 🧹 深度清理代码内容
                        clean_content = self._deep_clean_miniprogram_code(content, filename)
                        if clean_content:
                            extracted_files[filename] = clean_content
                            logger.info(f"✅ 提取小程序文件: {filename} ({len(clean_content)} 字符)")
        
        # 🎯 智能默认文件检测
        if not extracted_files:
            extracted_files = self._extract_miniprogram_by_content_analysis(full_content)
        
        return extracted_files
    
    def _deep_clean_code(self, content: str, filename: str) -> str:
        """深度清理代码内容，确保高质量输出"""
        import re
        
        # 基础清理
        clean_content = content.strip()
        
        # 移除代码块标记
        clean_content = re.sub(r'^```[\w\-_.]*\s*\n?', '', clean_content)
        clean_content = re.sub(r'\n?```\s*$', '', clean_content)
        
        # 移除多余的注释和说明性文字
        clean_content = re.sub(r'^//\s*文件名?[:：]\s*.*$', '', clean_content, flags=re.MULTILINE)
        clean_content = re.sub(r'^<!--\s*文件名?[:：]\s*.*?-->', '', clean_content, flags=re.MULTILINE)
        
        # 根据文件类型进行特定清理
        if filename.endswith('.html'):
            clean_content = self._clean_html_content(clean_content)
        elif filename.endswith('.css'):
            clean_content = self._clean_css_content(clean_content)
        elif filename.endswith('.js'):
            clean_content = self._clean_js_content(clean_content)
        
        return clean_content.strip()
    
    def _clean_html_content(self, content: str) -> str:
        """清理HTML内容"""
        import re
        
        # 确保有完整的HTML结构
        if not content.startswith('<!DOCTYPE') and not content.startswith('<html'):
            if '<head>' not in content and '<body>' not in content:
                # 简单HTML片段，包装为完整结构
                content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI生成应用</title>
</head>
<body>
    {content}
</body>
</html>"""
        
        # 移除重复的DOCTYPE声明
        content = re.sub(r'(<!DOCTYPE[^>]*>\s*)+', '<!DOCTYPE html>\n', content, flags=re.IGNORECASE)
        
        return content
    
    def _clean_css_content(self, content: str) -> str:
        """清理CSS内容"""
        import re
        
        # 移除重复的样式声明
        content = re.sub(r'(\s*([^{]+\{[^}]*\})\s*)+', r'\2', content)
        
        # 格式化CSS
        content = re.sub(r'\s*{\s*', ' {\n    ', content)
        content = re.sub(r';\s*', ';\n    ', content)
        content = re.sub(r'\s*}\s*', '\n}\n\n', content)
        
        return content.strip()
    
    def _clean_js_content(self, content: str) -> str:
        """清理JavaScript内容"""
        import re
        
        # 移除重复的函数声明
        content = re.sub(r'(function\s+(\w+)[^{]*\{[^}]*\})\s*\1+', r'\1', content)
        
        # 确保正确的分号使用
        content = re.sub(r'([^;])\n', r'\1;\n', content)
        
        return content
    
    def _get_default_filename(self, lang: str) -> str:
        """根据语言获取默认文件名"""
        lang_map = {
            'html': 'index.html',
            'css': 'style.css', 
            'javascript': 'script.js',
            'js': 'script.js',
            'json': 'data.json'
        }
        return lang_map.get(lang.lower(), 'file.txt')
    
    def _extract_by_content_analysis(self, content: str) -> dict:
        """基于内容分析提取文件"""
        import re
        extracted_files = {}
        
        # HTML内容检测
        html_patterns = [
            r'```(?:html)?\s*\n(.*?)```',
            r'(<!DOCTYPE.*?</html>)',
            r'(<html.*?</html>)'
        ]
        
        for pattern in html_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                html_content = self._deep_clean_code(match.group(1), 'index.html')
                if html_content:
                    extracted_files['index.html'] = html_content
                    break
        
        # CSS内容检测
        css_match = re.search(r'```css\s*\n(.*?)```', content, re.DOTALL)
        if css_match:
            css_content = self._deep_clean_code(css_match.group(1), 'style.css')
            if css_content:
                extracted_files['style.css'] = css_content
        
        # JavaScript内容检测
        js_match = re.search(r'```(?:javascript|js)\s*\n(.*?)```', content, re.DOTALL)
        if js_match:
            js_content = self._deep_clean_code(js_match.group(1), 'script.js')
            if js_content:
                extracted_files['script.js'] = js_content
        
        return extracted_files
    
    def _resolve_file_dependencies(self, files: dict) -> dict:
        """解析和处理文件依赖关系"""
        if 'index.html' in files:
            html_content = files['index.html']
            
            # 如果HTML中没有引用CSS和JS，但存在这些文件，自动添加引用
            if 'style.css' in files and '<link' not in html_content and '<style>' not in html_content:
                # 在head中添加CSS链接
                if '<head>' in html_content:
                    html_content = html_content.replace('<head>', '<head>\n    <link rel="stylesheet" href="style.css">')
                files['index.html'] = html_content
            
            if 'script.js' in files and '<script' not in html_content:
                # 在body结束前添加JS引用
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', '    <script src="script.js"></script>\n</body>')
                files['index.html'] = html_content
        
        return files
    
    def _scan_generated_files(self, generated_dir: str) -> dict:
        """扫描生成目录中的实际文件（兜底方案）"""
        files = {}
        try:
            if os.path.exists(generated_dir):
                for filename in os.listdir(generated_dir):
                    file_path = os.path.join(generated_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                files[filename] = content
                                logger.info(f"📄 扫描到文件: {filename} ({len(content)} 字符)")
                        except Exception as e:
                            logger.warning(f"⚠️ 读取文件失败: {filename} - {str(e)}")
        except Exception as e:
            logger.error(f"❌ 扫描目录失败: {generated_dir} - {str(e)}")
        
        return files

    def _extract_and_clean_code(self, code_chunks: list) -> str:
        """提取并返回最终HTML字符串（优先index.html）"""
        logger.info(f"📝 处理 {len(code_chunks)} 个代码块（HTML模式）")
        if not code_chunks:
            logger.warning("⚠️ 没有代码块，返回默认HTML页面")
            return "<!DOCTYPE html>\n<html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>AI明信片</title></head><body><div style=\"width:375px;height:600px;margin:20px auto;background:#fafafa;border-radius:20px;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(0,0,0,.1)\">生成中...</div></body></html>"

        full_content = '\n'.join(code_chunks)
        logger.info(f"📝 合并后内容长度: {len(full_content)} 字符")
        
        # 先用通用HTML提取
        extracted_files = self._extract_by_content_analysis(full_content)

        # 再合并扫描到的生成目录文件（如有）
        generated_dir = "/app/app/static/generated"
        actual_files = self._scan_generated_files(generated_dir)
        for filename, content in actual_files.items():
            if filename not in extracted_files:
                extracted_files[filename] = content

        # 解析依赖，确保index.html正确引用
        if extracted_files:
            files_resolved = self._resolve_file_dependencies(extracted_files)
            if 'index.html' in files_resolved:
                html = files_resolved['index.html']
                logger.info("✅ 返回提取到的 index.html 内容")
                return html

        # 兜底：在流里直接找<html>…</html>片段
        import re
        match = re.search(r'(<!DOCTYPE[\s\S]*?</html>)', full_content, re.IGNORECASE)
        if match:
            logger.info("✅ 直接从流式内容中提取完整HTML")
            return self._clean_html_content(match.group(1))

        # 最后兜底：构造简单HTML骨架
        logger.info("⚠️ 未找到明确的HTML，返回兜底页面")
        return "<!DOCTYPE html>\n<html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>AI明信片</title></head><body><div style=\"width:375px;height:600px;margin:20px auto;background:#fff;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,.1);display:flex;align-items:center;justify-content:center;font-family:Arial,Helvetica,PingFang SC\">AI Postcard</div></body></html>"

    def _ensure_file_in_target_path(self, filename: str, content: str, target_dir: str):
        """
        强制确保文件在目标路径存在，支持网页预览
        这是确保文件正确放置的关键方法
        """
        
        target_file_path = os.path.join(target_dir, filename)
        
        try:
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 强制写入文件内容到目标路径
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 验证文件存在和内容正确
            if os.path.exists(target_file_path):
                with open(target_file_path, 'r', encoding='utf-8') as f:
                    verify_content = f.read()
                    if len(verify_content) == len(content):
                        logger.info(f"✅ 文件确保成功: {target_file_path} ({len(content)} 字符)")
                        
                        # 设置文件权限确保可读
                        os.chmod(target_file_path, 0o644)
                        
                        return True
                    else:
                        logger.error(f"❌ 文件内容验证失败: {target_file_path}")
            else:
                logger.error(f"❌ 文件创建失败: {target_file_path}")
                
        except Exception as e:
            logger.error(f"❌ 确保文件存在时出错: {filename} -> {target_file_path} - {str(e)}")
            
        return False

    def _get_default_miniprogram_filename(self, lang: str) -> str:
        """根据语言获取默认的小程序文件名"""
        lang_map = {
            'wxml': 'postcard-component.wxml',
            'wxss': 'postcard-component.wxss',
            'javascript': 'postcard-component.js',
            'js': 'postcard-component.js',
            'html': 'postcard-component.wxml',  # 转换HTML为WXML
            'css': 'postcard-component.wxss',   # 转换CSS为WXSS
            'json': 'postcard-component.json'
        }
        return lang_map.get(lang.lower(), 'postcard-component.js')
    
    def _deep_clean_miniprogram_code(self, content: str, filename: str) -> str:
        """深度清理小程序代码内容"""
        import re
        
        # 基础清理
        clean_content = content.strip()
        
        # 移除代码块标记
        clean_content = re.sub(r'^```[\w\-_.]*\s*\n?', '', clean_content)
        clean_content = re.sub(r'\n?```\s*$', '', clean_content)
        
        # 移除多余的注释和说明性文字
        clean_content = re.sub(r'^//\s*文件名?[:：]\s*.*$', '', clean_content, flags=re.MULTILINE)
        clean_content = re.sub(r'^<!--\s*文件名?[:：]\s*.*?-->', '', clean_content, flags=re.MULTILINE)
        
        # 根据文件类型进行特定清理
        if filename.endswith('.wxml'):
            clean_content = self._clean_wxml_content(clean_content)
        elif filename.endswith('.wxss'):
            clean_content = self._clean_wxss_content(clean_content)
        elif filename.endswith('.js'):
            clean_content = self._clean_miniprogram_js_content(clean_content)
        
        return clean_content.strip()
    
    def _clean_wxml_content(self, content: str) -> str:
        """清理WXML内容"""
        import re
        
        # 如果包含HTML标签，转换为小程序标签
        content = re.sub(r'<div', '<view', content)
        content = re.sub(r'</div>', '</view>', content)
        content = re.sub(r'<span', '<text', content)
        content = re.sub(r'</span>', '</text>', content)
        content = re.sub(r'<p', '<text', content)
        content = re.sub(r'</p>', '</text>', content)
        content = re.sub(r'onclick=', 'bindtap=', content)
        
        # 确保有根节点
        if not content.startswith('<view') and not content.startswith('<!--'):
            content = f'<view class="postcard-container">\n{content}\n</view>'
        
        return content
    
    def _clean_wxss_content(self, content: str) -> str:
        """清理WXSS内容"""
        import re
        
        # 转换px单位为rpx（如果需要）
        # 这里先保持原样，因为生成时已经使用了rpx
        
        # 格式化WXSS
        content = re.sub(r'\s*{\s*', ' {\n  ', content)
        content = re.sub(r';\s*', ';\n  ', content)
        content = re.sub(r'\s*}\s*', '\n}\n\n', content)
        
        return content.strip()
    
    def _clean_miniprogram_js_content(self, content: str) -> str:
        """清理小程序JavaScript内容"""
        import re
        
        # 确保使用Component构造器
        if not content.strip().startswith('Component('):
            if 'Component(' not in content:
                content = f"""Component({{
  properties: {{}},
  data: {{}},
  methods: {{
    {content}
  }}
}})"""
        
        return content
    
    def _extract_miniprogram_by_content_analysis(self, content: str) -> dict:
        """基于内容分析提取小程序文件"""
        import re
        extracted_files = {}
        
        # WXML内容检测
        wxml_patterns = [
            r'```(?:wxml|html)?\s*\n(.*?)```',
            r'(<view.*?</view>)',
            r'(<text.*?</text>)'
        ]
        
        for pattern in wxml_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                wxml_content = self._deep_clean_miniprogram_code(match.group(1), 'postcard-component.wxml')
                if wxml_content:
                    extracted_files['postcard-component.wxml'] = wxml_content
                    break
        
        # WXSS内容检测
        wxss_match = re.search(r'```(?:wxss|css)\s*\n(.*?)```', content, re.DOTALL)
        if wxss_match:
            wxss_content = self._deep_clean_miniprogram_code(wxss_match.group(1), 'postcard-component.wxss')
            if wxss_content:
                extracted_files['postcard-component.wxss'] = wxss_content
        
        # JavaScript内容检测
        js_match = re.search(r'```(?:javascript|js)\s*\n(.*?)```', content, re.DOTALL)
        if js_match:
            js_content = self._deep_clean_miniprogram_code(js_match.group(1), 'postcard-component.js')
            if js_content:
                extracted_files['postcard-component.js'] = js_content
        
        return extracted_files

    def _build_coding_prompt(self, user_prompt: str) -> str:
        """构建编码提示"""
        return f"""请根据以下需求生成微信小程序明信片组件：

{user_prompt}

请生成完整的小程序组件代码，包含WXML模板、WXSS样式和JavaScript逻辑。
"""