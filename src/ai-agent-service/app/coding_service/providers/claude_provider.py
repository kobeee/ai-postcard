import asyncio
import logging
import os
import time
import traceback
from typing import AsyncGenerator, Dict, Any
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

    async def generate(self, prompt: str, session_id: str, model: str | None = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成代码 - 优化版本，基于Claude Code SDK最佳实践
        """
        # 使用传入的model参数，如果没有则使用默认模型
        target_model = model or self.model
        
        # 【性能优化】记录开始时间用于性能监控
        generation_start_time = time.time()
        
        try:
            yield {"type": "status", "content": "🚀 初始化AI代码生成器（优化模式）..."}
            logger.info(f"📤 开始优化代码生成任务 - 会话ID: {session_id}, 模型: {target_model}")
            logger.info(f"🔧 启用优化特性: skip_permissions=True, max_turns=5")

            # 构建系统提示 - 非交互式模式
            system_prompt = self._build_system_prompt()
            
            # Claude Code SDK配置 - 基于官方文档最佳实践
            # 设置工作目录为AI生成文件的专用目录，避免与前端文件冲突
            # 与main.py中的static_dir保持一致：/app/app/static/generated
            generated_dir = "/app/app/static/generated"
            os.makedirs(generated_dir, exist_ok=True)  # 确保目录存在
            
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=5,  # 增加轮次以获得更好的结果
                allowed_tools=["Write", "Read", "Edit"],  # 使用Write、Read、Edit工具用于文件生成
                permission_mode="bypassPermissions",  # 允许所有工具而不提示，实现完全自动化
                cwd=generated_dir  # 设置为AI生成文件专用目录
            )
            
            logger.info("🔧 创建Claude SDK客户端...")
            
            # 使用Claude SDK进行代码生成
            async with ClaudeSDKClient(options=options) as client:
                logger.info("✅ Claude SDK客户端初始化成功")
                
                # 发送查询
                yield {"type": "status", "content": "🧠 分析需求并生成代码..."}
                await client.query(prompt)
                logger.info("📨 查询发送成功，开始接收响应...")
                
                # 收集生成的代码和分析内容
                generated_code_chunks = []
                markdown_content = []
                
                # 流式接收响应
                current_stream_buffer = ""  # 用于累积流式内容
                
                async for message in client.receive_response():
                    logger.debug(f"📨 收到消息: {type(message).__name__}")
                    
                    # 🔍 DEBUG模式 - 详细消息分析（仅在需要时启用）
                    debug_mode = logger.isEnabledFor(logging.DEBUG)
                    if debug_mode:
                        logger.info(f"🔍 DEBUG - 消息类型: {type(message).__name__}")
                        logger.info(f"🔍 DEBUG - 消息属性: {[attr for attr in dir(message) if not attr.startswith('_')]}")
                        if hasattr(message, 'content'):
                            logger.info(f"🔍 DEBUG - 消息内容: {getattr(message, '__dict__', 'No dict available')}")
                    
                    # 处理消息内容
                    if hasattr(message, 'content') and message.content:
                        for i, block in enumerate(message.content):
                            if hasattr(block, 'text') and block.text:
                                text = block.text
                                current_stream_buffer += text
                                
                                # 实时流式输出文本内容
                                if self._contains_code(text):
                                    generated_code_chunks.append(text)
                                    logger.info(f"✅ 流式代码块: {text[:100]}...")
                                    
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
                                    logger.info(f"📝 流式markdown: {text[:100]}...")
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
                                                with open(full_file_path, 'r', encoding='utf-8') as f:
                                                    file_content = f.read()
                                                    logger.info(f"📄 成功读取文件内容: {file_name} ({len(file_content)} 字符)")
                                                    
                                                    # 🔧 强制确保文件在预期路径下存在
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
    
    def _build_system_prompt(self) -> str:
        """构建优化的系统提示 - 基于Claude Code最佳实践"""
        return """
You are an expert frontend code generator specializing in creating interactive web applications. Your workspace is set to /app/static/generated.

# Your Mission
Create complete, functional, interactive web applications that users can immediately run and enjoy. Focus on building working software, not just code examples.

# Core Workflow
1. **Analyze the requirements** thoroughly to understand all needed features
2. **Design the application architecture** ensuring all components work together
3. **Generate working files** using the Write tool for each file (critical step)
4. **Create polished, production-ready code** that users will love

# File Creation Rules
- **Always use Write tool** to create actual files - this is mandatory
- **Use simple filenames only**: index.html, style.css, script.js
- **Never use paths**: avoid /tmp/, ./files/, or /app/static/generated/ prefixes
- **Create multiple files** when the project needs them

# Code Quality Standards
Your generated applications must be:
- **Completely functional**: Every button, input, and feature works perfectly
- **Fully interactive**: All user actions produce appropriate responses  
- **Visually polished**: Modern, attractive CSS styling
- **Well-structured**: Clean, organized, maintainable code
- **Error-resistant**: Proper input validation and error handling

# Technical Requirements
- Generate complete HTML documents with proper structure
- Use modern CSS for styling (flexbox, grid, animations where appropriate)
- Write complete JavaScript with all functions implemented
- Ensure all event listeners are properly bound
- Include responsive design considerations
- Add helpful comments for complex logic

# Application Types
For any type of application (games, tools, forms, etc.):
- Implement ALL required logic completely
- Test critical user interaction paths mentally
- Ensure the user experience is smooth and intuitive
- Make it something users will actually want to use

Remember: You're not just generating code - you're building working applications that should delight users. Focus on creating something genuinely useful and enjoyable.

Start generating the application files now using the Write tool."""

    def _contains_code(self, text: str) -> bool:
        """判断文本是否包含代码块"""
        if not text:
            return False
        
        # 更宽松的代码块判断条件
        code_indicators = [
            # 代码块标记
            '```',
            # HTML相关
            '<!DOCTYPE', '<html', '<body', '<div', '<script', '<style',
            '<button', '<input', '<form', '<canvas', '<svg',
            # JavaScript相关
            'function ', 'const ', 'let ', 'var ', '=>',
            'document.', 'window.', 'addEventListener',
            'console.log', 'querySelector',
            # CSS相关
            'background:', 'color:', 'font-size:', 'margin:', 'padding:',
            'display:', 'position:', 'width:', 'height:',
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
        """改进的文件提取逻辑，支持更好的代码质量和准确提取"""
        if not code_chunks:
            return {}
        
        import re
        full_content = '\n'.join(code_chunks)
        extracted_files = {}
        
        # 🔍 增强的文件模式匹配
        file_patterns = [
            # 标准文件名格式
            r'```([\w\-_.]+\.(?:html|css|js|json|md|txt))\s*\n(.*?)```',
            # 带语言标识但在注释中含文件名
            r'```(\w+)\s*\n(?:\/\*.*?([\w\-_.]+\.(?:html|css|js)).*?\*\/\s*)?(.*?)```',
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
                            filename = self._get_default_filename(lang)
                    else:
                        continue
                    
                    if filename and content and content.strip():
                        # 🧹 深度清理代码内容
                        clean_content = self._deep_clean_code(content, filename)
                        if clean_content:
                            extracted_files[filename] = clean_content
                            logger.info(f"✅ 提取高质量文件: {filename} ({len(clean_content)} 字符)")
        
        # 🎯 智能默认文件检测
        if not extracted_files:
            extracted_files = self._extract_by_content_analysis(full_content)
        
        # 🔧 文件关联和依赖处理
        extracted_files = self._resolve_file_dependencies(extracted_files)
        
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
        """提取和清理代码，自动去除代码块标记"""
        logger.info(f"📝 处理 {len(code_chunks)} 个代码块")
        if not code_chunks:
            logger.warning("⚠️ 没有代码块，返回默认HTML")
            return "<html><head><title>生成失败</title></head><body><h1>未能生成有效代码</h1></body></html>"
        import re
        # 合并所有代码块
        full_content = '\n'.join(code_chunks)
        logger.info(f"📝 合并后内容长度: {len(full_content)} 字符")
        
        # 检查是否包含HTML结构，但需要精确提取
        if '<!DOCTYPE' in full_content or '<html' in full_content:
            logger.info("✅ 发现完整HTML结构，开始提取")
            html_start = full_content.find('<!DOCTYPE')
            if html_start == -1:
                html_start = full_content.find('<html')
            if html_start != -1:
                clean_html = full_content[html_start:].strip()
                # 移除markdown代码块标记
                clean_html = re.sub(r'^```[\w\-_.]*\n?', '', clean_html)
                clean_html = re.sub(r'```$', '', clean_html)
                logger.info(f"✅ HTML提取完成，长度: {len(clean_html)} 字符")
                return clean_html
        
        # 否则尝试提取代码块
        import re
        
        logger.info("📝 尝试从代码块中提取HTML/CSS/JS...")
        
        # 更强大的代码块提取逻辑
        html_matches = []
        css_matches = []
        js_matches = []
        extracted_files = {}  # 存储文件名和内容的映射
        
        # 通用代码块模式 - 支持各种格式
        code_block_patterns = [
            # 标准格式: ```language\ncode```
            r'```(\w+)\s*\n(.*?)```',
            # 带文件名: ```filename.ext\ncode```
            r'```([\w\-_.]+\.[\w]+)\s*\n(.*?)```',
            # 文件名在第一行: ```\nfilename.ext\ncode```
            r'```\s*\n([\w\-_.]+\.[\w]+)\s*\n(.*?)```',
            # 简单代码块: ```\ncode```
            r'```\s*\n(.*?)```'
        ]
        
        for pattern in code_block_patterns:
            matches = re.findall(pattern, full_content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    first_part, content = match
                    content = content.strip()
                    
                    if not content:  # 跳过空内容
                        continue
                    
                    # 判断第一部分是语言还是文件名
                    if '.' in first_part:  # 包含点号，可能是文件名
                        filename = first_part
                        logger.info(f"📁 发现文件: {filename}")
                        extracted_files[filename] = content
                        
                        # 根据文件扩展名分类
                        if filename.endswith('.html'):
                            html_matches.append(content)
                        elif filename.endswith('.css'):
                            css_matches.append(content)
                        elif filename.endswith('.js'):
                            js_matches.append(content)
                    else:  # 是语言标识符
                        language = first_part.lower()
                        if language in ['html', 'htm']:
                            html_matches.append(content)
                        elif language in ['css']:
                            css_matches.append(content)
                        elif language in ['javascript', 'js']:
                            js_matches.append(content)
                        else:
                            # 未知语言，尝试根据内容判断
                            if any(tag in content for tag in ['<html', '<body', '<div', '<!DOCTYPE']):
                                html_matches.append(content)
                            elif any(prop in content for prop in ['background:', 'color:', 'font-size:']):
                                css_matches.append(content)
                            elif any(keyword in content for keyword in ['function', 'const', 'let', 'document.']):
                                js_matches.append(content)
                elif isinstance(match, str):  # 简单代码块，没有语言标识
                    content = match.strip()
                    if content:
                        # 根据内容特征判断类型
                        if any(tag in content for tag in ['<html', '<body', '<div', '<!DOCTYPE']):
                            html_matches.append(content)
                        elif any(prop in content for prop in ['background:', 'color:', 'font-size:']):
                            css_matches.append(content)
                        elif any(keyword in content for keyword in ['function', 'const', 'let', 'document.']):
                            js_matches.append(content)
                        else:
                            # 默认当作HTML处理
                            html_matches.append(content)
        
        logger.info(f"📊 提取结果: HTML={len(html_matches)}, CSS={len(css_matches)}, JS={len(js_matches)}")
        
        # 组装完整的HTML文档
        html_content = html_matches[0] if html_matches else ""
        css_content = css_matches[0] if css_matches else ""
        js_content = js_matches[0] if js_matches else ""
        
        if html_content:
            # 如果HTML内容不完整，补充基本结构
            if not html_content.strip().startswith('<!DOCTYPE'):
                if '<style>' not in html_content and css_content:
                    html_content = html_content.replace('<head>', f'<head>\n<style>\n{css_content}\n</style>')
                if '<script>' not in html_content and js_content:
                    html_content = html_content.replace('</body>', f'<script>\n{js_content}\n</script>\n</body>')
            
            return html_content
        
        # 如果没有明确的HTML结构，创建一个基本模板
        if css_content or js_content:
            return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI生成的应用</title>
    <style>
{css_content}
    </style>
</head>
<body>
    <div id="app">
        <h1>AI生成的应用</h1>
    </div>
    <script>
{js_content}
    </script>
</body>
</html>"""
        
        # 兜底：返回原始内容
        return full_content

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

    def _build_coding_prompt(self, user_prompt: str) -> str:
        """构建编码提示"""
        return f"""请根据以下需求生成前端代码：

{user_prompt}

请直接生成完整可运行的HTML代码，包含必要的CSS和JavaScript。
"""