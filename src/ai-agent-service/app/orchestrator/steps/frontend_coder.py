import logging
import json
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class FrontendCoder:
    """前端代码生成器 - 第4步：生成最终的前端HTML/CSS/JS代码"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_code_provider("claude")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context):
        """生成前端HTML/CSS/JS代码"""
        task = context["task"]
        concept = context["results"]["concept"]
        content = context["results"]["content"]
        image_url = context["results"]["image_url"]
        
        self.logger.info(f"💻 开始生成前端代码: {task.get('task_id')}")
        
        # 解析内容结构
        try:
            if isinstance(content, str) and content.strip().startswith('{'):
                content_data = json.loads(content)
            else:
                content_data = {
                    "主标题": "温馨祝福",
                    "副标题": "来自心底的真诚",
                    "正文内容": content,
                    "署名建议": "致亲爱的你"
                }
        except json.JSONDecodeError:
            content_data = {
                "主标题": "温馨祝福",
                "副标题": "来自心底的真诚", 
                "正文内容": content,
                "署名建议": "致亲爱的你"
            }
        
        # 构建前端代码生成提示词
        coding_prompt = f"""
请生成一个交互式明信片的完整前端代码，要求：

明信片内容：
- 主标题：{content_data.get('主标题', '温馨祝福')}
- 副标题：{content_data.get('副标题', '来自心底的真诚')}
- 正文：{content_data.get('正文内容', '愿美好与你同在')}
- 署名：{content_data.get('署名建议', '致亲爱的你')}
- 背景图片：{image_url}

技术要求：
1. 纯HTML/CSS/JS实现，无需外部框架
2. 适配移动端（微信小程序webview）
3. 添加精美的CSS动画效果
4. 实现交互功能（点击、滑动等）
5. 响应式设计，适应不同屏幕尺寸

设计要求：
1. 明信片风格的卡片设计
2. 背景图片作为卡片背景或装饰元素
3. 文字层次分明，易于阅读
4. 色彩搭配和谐，符合明信片的温馨感
5. 考虑文字与背景的对比度

动画效果建议：
- 页面加载时的渐入动画
- 文字逐层显示动画
- 背景图片的轻微缩放或移动效果
- 鼠标悬停或点击的交互反馈
- 卡片翻转或3D效果

互动功能：
- 点击卡片可以翻转或展开更多内容
- 简单的粒子效果或背景动效
- 音效提示（可选）

请生成完整可运行的HTML代码，包含内联的CSS和JavaScript。
确保代码在移动设备上运行流畅，并且具有良好的用户体验。
"""
        
        try:
            # 使用Claude Code SDK生成前端代码
            # 注意：这里需要适配现有的Claude Code Provider
            from ...coding_service.providers.claude_provider import ClaudeCodeProvider
            import asyncio
            
            # 创建一个会话ID
            session_id = f"postcard_{task.get('task_id', 'unknown')}"
            
            # 创建Claude提供商实例
            claude_provider = ClaudeCodeProvider()
            
            # 生成代码，添加超时保护
            frontend_code = ""
            try:
                # 设置60秒超时，防止无限等待
                async_generator = claude_provider.generate(coding_prompt, session_id)
                timeout_task = asyncio.create_task(asyncio.sleep(60))
                
                async for message in async_generator:
                    if timeout_task.done():
                        self.logger.warning("⚠️ Claude 代码生成超时，使用默认代码")
                        break
                    if message.get("type") == "complete":
                        frontend_code = message.get("final_code", "")
                        timeout_task.cancel()
                        break
                    elif message.get("type") == "error":
                        self.logger.error(f"❌ Claude 代码生成错误: {message.get('error', 'Unknown error')}")
                        timeout_task.cancel()
                        break
                        
                if not timeout_task.cancelled():
                    timeout_task.cancel()
                            
            except asyncio.CancelledError:
                self.logger.warning("⚠️ Claude 代码生成被取消，使用默认代码")
                # 重要：不要重新抛出 CancelledError，而是优雅降级
                pass
            
            if not frontend_code:
                frontend_code = self._get_default_frontend_code(content_data, image_url)
            
            context["results"]["frontend_code"] = frontend_code
            context["results"]["preview_url"] = f"/generated/postcard_{task.get('task_id')}.html"
            
            self.logger.info(f"✅ 前端代码生成完成: {len(frontend_code)} 字符")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 前端代码生成失败: {e}")
            # 返回默认前端代码
            context["results"]["frontend_code"] = self._get_default_frontend_code(content_data, image_url)
            context["results"]["preview_url"] = f"/generated/postcard_default_{task.get('task_id')}.html"
            return context
    
    def _get_default_frontend_code(self, content_data, image_url):
        """获取默认前端代码（兜底方案）"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI生成明信片</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        
        .postcard {{
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            max-width: 400px;
            width: 100%;
            overflow: hidden;
            transform: scale(0.9);
            animation: cardAppear 1s ease forwards;
        }}
        
        @keyframes cardAppear {{
            to {{
                transform: scale(1);
            }}
        }}
        
        .postcard-header {{
            height: 200px;
            background: url('{image_url}') center/cover;
            position: relative;
        }}
        
        .postcard-header::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.3));
        }}
        
        .postcard-content {{
            padding: 30px;
            text-align: center;
        }}
        
        .main-title {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            opacity: 0;
            animation: fadeInUp 1s ease 0.5s forwards;
        }}
        
        .sub-title {{
            font-size: 16px;
            color: #666;
            margin-bottom: 20px;
            opacity: 0;
            animation: fadeInUp 1s ease 0.7s forwards;
        }}
        
        .main-content {{
            font-size: 18px;
            line-height: 1.6;
            color: #444;
            margin-bottom: 25px;
            opacity: 0;
            animation: fadeInUp 1s ease 0.9s forwards;
        }}
        
        .signature {{
            font-size: 14px;
            color: #888;
            font-style: italic;
            opacity: 0;
            animation: fadeInUp 1s ease 1.1s forwards;
        }}
        
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .postcard:hover {{
            transform: scale(1.02);
            transition: transform 0.3s ease;
        }}
        
        @media (max-width: 480px) {{
            .postcard {{
                margin: 10px;
            }}
            
            .main-title {{
                font-size: 24px;
            }}
            
            .main-content {{
                font-size: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="postcard">
        <div class="postcard-header"></div>
        <div class="postcard-content">
            <h1 class="main-title">{content_data.get('主标题', '温馨祝福')}</h1>
            <p class="sub-title">{content_data.get('副标题', '来自心底的真诚')}</p>
            <p class="main-content">{content_data.get('正文内容', '愿美好与你同在')}</p>
            <p class="signature">{content_data.get('署名建议', '致亲爱的你')}</p>
        </div>
    </div>
    
    <script>
        // 添加点击交互
        document.querySelector('.postcard').addEventListener('click', function() {{
            this.style.transform = 'scale(1.05)';
            setTimeout(() => {{
                this.style.transform = 'scale(1)';
            }}, 200);
        }});
        
        // 页面加载完成后的效果
        window.addEventListener('load', function() {{
            console.log('AI生成的明信片加载完成');
        }});
    </script>
</body>
</html>"""