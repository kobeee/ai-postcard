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
        
        logger.info(f"✅ 环境变量配置完成 - Token: {auth_token[:8]}...{auth_token[-4:]}")
        if base_url:
            logger.info(f"✅ 使用自定义Base URL: {base_url}")

    async def generate(self, prompt: str, session_id: str, model: str | None = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成代码 - 简化版本，基于acceptEdits模式
        """
        # 使用传入的model参数，如果没有则使用默认模型
        target_model = model or self.model
        
        try:
            yield {"type": "status", "content": "🚀 初始化AI代码生成器..."}
            logger.info(f"📤 开始代码生成任务 - 会话ID: {session_id}, 模型: {target_model}")

            # 构建系统提示 - 非交互式模式
            system_prompt = self._build_system_prompt()
            
            # Claude Code SDK配置 - 基于官方文档最佳实践
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=3,
                allowed_tools=["Read", "WebSearch", "Bash"],
                permission_mode="bypassPermissions",  # 绕过权限检查，直接生成代码
                cwd="/app"  # 设置工作目录
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
                async for message in client.receive_response():
                    logger.debug(f"📨 收到消息: {type(message).__name__}")
                    
                    # 🔍 DEBUG: 打印完整消息结构
                    logger.info(f"🔍 DEBUG - 消息类型: {type(message).__name__}")
                    logger.info(f"🔍 DEBUG - 消息属性: {dir(message)}")
                    if hasattr(message, '__dict__'):
                        logger.info(f"🔍 DEBUG - 消息内容: {message.__dict__}")
                    
                    # 处理消息内容
                    if hasattr(message, 'content') and message.content:
                        logger.info(f"🔍 DEBUG - content类型: {type(message.content)}, 长度: {len(message.content) if hasattr(message.content, '__len__') else 'N/A'}")
                        
                        for i, block in enumerate(message.content):
                            logger.info(f"🔍 DEBUG - Block {i}: 类型={type(block).__name__}, 属性={dir(block)}")
                            if hasattr(block, '__dict__'):
                                logger.info(f"🔍 DEBUG - Block {i} 内容: {block.__dict__}")
                            
                            if hasattr(block, 'text') and block.text:
                                text = block.text
                                logger.info(f"🔍 DEBUG - Block {i} text长度: {len(text)}")
                                logger.info(f"🔍 DEBUG - Block {i} text内容: {text[:500]}...")  # 只显示前500字符
                                
                                # 判断是否为代码块
                                if self._contains_code(text):
                                    generated_code_chunks.append(text)
                                    logger.info(f"✅ 发现代码块 {len(generated_code_chunks)}，内容: {text[:200]}...")
                                    yield {"type": "code", "content": text, "phase": "coding"}
                                else:
                                    markdown_content.append(text)
                                    logger.info(f"📝 发现markdown内容: {text[:200]}...")
                                    yield {"type": "markdown", "content": text, "phase": "thinking"}
                    
                # 处理工具调用 - 提取文件名信息
                if hasattr(message, 'content') and message.content:
                    for block in message.content:
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
                    
                    # 处理结果消息
                    if type(message).__name__ == "ResultMessage":
                        logger.info("✅ 收到结果消息，生成完成")
                        
                        # 🔍 DEBUG: 分析收集到的代码块
                        logger.info(f"🔍 DEBUG - 总共收集到 {len(generated_code_chunks)} 个代码块")
                        for i, chunk in enumerate(generated_code_chunks):
                            logger.info(f"🔍 DEBUG - 代码块 {i+1}: 长度={len(chunk)}, 内容前200字符: {chunk[:200]}...")
                        
                        logger.info(f"🔍 DEBUG - 总共收集到 {len(markdown_content)} 个markdown块")
                        for i, md in enumerate(markdown_content):
                            logger.info(f"🔍 DEBUG - Markdown块 {i+1}: 长度={len(md)}, 内容前200字符: {md[:200]}...")
                        
                        # 提取最终代码
                        final_code = self._extract_and_clean_code(generated_code_chunks)
                        logger.info(f"🔍 DEBUG - 最终代码长度: {len(final_code)}")
                        logger.info(f"🔍 DEBUG - 最终代码内容: {final_code[:500]}...")
                        
                        yield {"type": "status", "content": "✅ 代码生成完成！"}
                        
                        # 🔍 DEBUG: 提取并返回文件信息
                        extracted_files = self._extract_files_info(generated_code_chunks)
                        logger.info(f"🔍 DEBUG - 提取到的文件: {list(extracted_files.keys())}")
                        
                        yield {
                            "type": "complete",
                            "final_code": final_code,
                            "files": extracted_files,  # 新增：文件信息
                            "metadata": {
                                "model_used": target_model,
                                "session_id": session_id,
                                "cost_usd": getattr(message, 'total_cost_usd', 0),
                                "duration_ms": getattr(message, 'duration_ms', 0),
                                "total_tokens": getattr(message, 'total_tokens', 0)
                            }
                        }
                        logger.info("🎉 代码生成任务完成")
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
        """构建系统提示 - 非交互式模式"""
        return """
你是一个专业的前端代码生成助手。

**工作模式**：
- 直接根据用户需求生成完整可运行的前端代码
- 必须在需要时调用工具（如Write）将代码写入对应文件，而不是只输出代码文本
- 代码和文件创建要同步进行，确保每个文件都通过工具创建
- 不要添加无关的解释性文字
- 遇到多文件项目时，自动拆分并分别创建

**输出要求**：
- 使用标准的代码块格式（```html、```css、```javascript等）包裹代码
- 生成的代码必须能在浏览器中直接运行
- 包含完整的HTML结构、CSS样式和JavaScript逻辑
- 代码风格现代化，用户体验友好
- 适当的注释说明关键功能
- 不要输出“我来为你创建...”等说明性文字

请根据用户需求直接生成代码，并通过工具创建文件，无需询问确认。"""

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
        """提取文件信息，返回文件名和内容的映射，自动去除代码块标记"""
        if not code_chunks:
            return {}
        import re
        full_content = '\n'.join(code_chunks)
        extracted_files = {}
        # 提取带文件名的代码块
        file_patterns = [
            r'```([\w\-_.]+\.[\w]+)\s*\n(.*?)```',  # ```filename.ext
            r'```\s*\n([\w\-_.]+\.[\w]+)\s*\n(.*?)```'  # ```\nfilename.ext
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, full_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    filename, content = match
                    if filename and content.strip():
                        # 去除所有代码块标记
                        clean_content = re.sub(r'^```[\w\-_.]*\n?', '', content.strip())
                        clean_content = re.sub(r'```$', '', clean_content.strip())
                        extracted_files[filename] = clean_content.strip()
                        logger.info(f"🔍 提取文件: {filename} ({len(clean_content)} 字符)")
        # 如果没有找到带文件名的代码块，使用默认文件名
        if not extracted_files:
            detected_filename = None
            if hasattr(self, '_detected_filenames') and self._detected_filenames:
                detected_filename = self._detected_filenames[0]
                logger.info(f"🔍 使用检测到的文件名: {detected_filename}")
            html_match = re.search(r'```(?:html)?\s*\n(.*?)```', full_content, re.DOTALL)
            if html_match:
                filename = detected_filename if detected_filename and detected_filename.endswith('.html') else 'index.html'
                clean_content = re.sub(r'^```[\w\-_.]*\n?', '', html_match.group(1).strip())
                clean_content = re.sub(r'```$', '', clean_content.strip())
                extracted_files[filename] = clean_content.strip()
            css_match = re.search(r'```css\s*\n(.*?)```', full_content, re.DOTALL)
            if css_match:
                filename = detected_filename if detected_filename and detected_filename.endswith('.css') else 'style.css'
                clean_content = re.sub(r'^```[\w\-_.]*\n?', '', css_match.group(1).strip())
                clean_content = re.sub(r'```$', '', clean_content.strip())
                extracted_files[filename] = clean_content.strip()
            js_match = re.search(r'```(?:javascript|js)\s*\n(.*?)```', full_content, re.DOTALL)
            if js_match:
                filename = detected_filename if detected_filename and detected_filename.endswith('.js') else 'script.js'
                clean_content = re.sub(r'^```[\w\-_.]*\n?', '', js_match.group(1).strip())
                clean_content = re.sub(r'```$', '', clean_content.strip())
                extracted_files[filename] = clean_content.strip()
        return extracted_files

    def _extract_and_clean_code(self, code_chunks: list) -> str:
        """提取和清理代码，自动去除代码块标记"""
        logger.info(f"🔍 DEBUG - _extract_and_clean_code: 输入 {len(code_chunks)} 个代码块")
        if not code_chunks:
            logger.warning("⚠️ 没有代码块，返回默认HTML")
            return "<html><head><title>生成失败</title></head><body><h1>未能生成有效代码</h1></body></html>"
        import re
        # 合并所有代码块
        full_content = '\n'.join(code_chunks)
        logger.info(f"🔍 DEBUG - 合并后内容长度: {len(full_content)}")
        logger.info(f"🔍 DEBUG - 合并后内容前1000字符: {full_content[:1000]}...")
        # 检查是否包含HTML结构，但需要精确提取
        if '<!DOCTYPE' in full_content or '<html' in full_content:
            logger.info("✅ 发现完整HTML结构，开始精确提取")
            html_start = full_content.find('<!DOCTYPE')
            if html_start == -1:
                html_start = full_content.find('<html')
            if html_start != -1:
                clean_html = full_content[html_start:].strip()
                # 移除markdown代码块标记
                clean_html = re.sub(r'^```[\w\-_.]*\n?', '', clean_html)
                clean_html = re.sub(r'```$', '', clean_html)
                logger.info(f"🔍 精确提取HTML，长度: {len(clean_html)}")
                logger.info(f"🔍 HTML开头: {clean_html[:200]}...")
                return clean_html
        
        # 否则尝试提取代码块
        import re
        
        logger.info("🔍 尝试从代码块中提取HTML/CSS/JS...")
        
        # 🔍 更强大的代码块提取逻辑
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
            logger.info(f"🔍 代码块模式 '{pattern}' 匹配到 {len(matches)} 个结果")
            
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    first_part, content = match
                    content = content.strip()
                    
                    if not content:  # 跳过空内容
                        continue
                    
                    # 判断第一部分是语言还是文件名
                    if '.' in first_part:  # 包含点号，可能是文件名
                        filename = first_part
                        logger.info(f"🔍 发现文件: {filename}")
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
                            logger.info(f"🔍 HTML代码块: {content[:100]}...")
                        elif language in ['css']:
                            css_matches.append(content)
                            logger.info(f"🔍 CSS代码块: {content[:100]}...")
                        elif language in ['javascript', 'js']:
                            js_matches.append(content)
                            logger.info(f"🔍 JS代码块: {content[:100]}...")
                        else:
                            # 未知语言，尝试根据内容判断
                            if any(tag in content for tag in ['<html', '<body', '<div', '<!DOCTYPE']):
                                html_matches.append(content)
                                logger.info(f"🔍 根据内容判断为HTML: {content[:100]}...")
                            elif any(prop in content for prop in ['background:', 'color:', 'font-size:']):
                                css_matches.append(content)
                                logger.info(f"🔍 根据内容判断为CSS: {content[:100]}...")
                            elif any(keyword in content for keyword in ['function', 'const', 'let', 'document.']):
                                js_matches.append(content)
                                logger.info(f"🔍 根据内容判断为JS: {content[:100]}...")
                elif isinstance(match, str):  # 简单代码块，没有语言标识
                    content = match.strip()
                    if content:
                        # 根据内容特征判断类型
                        if any(tag in content for tag in ['<html', '<body', '<div', '<!DOCTYPE']):
                            html_matches.append(content)
                            logger.info(f"🔍 无标识HTML代码块: {content[:100]}...")
                        elif any(prop in content for prop in ['background:', 'color:', 'font-size:']):
                            css_matches.append(content)
                            logger.info(f"🔍 无标识CSS代码块: {content[:100]}...")
                        elif any(keyword in content for keyword in ['function', 'const', 'let', 'document.']):
                            js_matches.append(content)
                            logger.info(f"🔍 无标识JS代码块: {content[:100]}...")
                        else:
                            # 默认当作HTML处理
                            html_matches.append(content)
                            logger.info(f"🔍 默认HTML代码块: {content[:100]}...")
        
        logger.info(f"🔍 提取结果: HTML={len(html_matches)}, CSS={len(css_matches)}, JS={len(js_matches)}")
        
        # 打印提取到的内容
        for i, html in enumerate(html_matches):
            logger.info(f"🔍 HTML块 {i+1} 前200字符: {html[:200]}...")
        for i, css in enumerate(css_matches):
            logger.info(f"🔍 CSS块 {i+1} 前200字符: {css[:200]}...")
        for i, js in enumerate(js_matches):
            logger.info(f"🔍 JS块 {i+1} 前200字符: {js[:200]}...")
        
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

    def _build_coding_prompt(self, user_prompt: str) -> str:
        """构建编码提示"""
        return f"""请根据以下需求生成前端代码：

{user_prompt}

请直接生成完整可运行的HTML代码，包含必要的CSS和JavaScript。
"""