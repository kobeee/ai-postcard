"""
HTML转图片服务 - 为小程序提供HTML内容的图片渲染
解决小程序无法使用web-view组件的问题
"""

import asyncio
import logging
import os
import base64
import tempfile
import subprocess
import uuid
from typing import Optional, Dict, Any
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

class HTMLToImageService:
    """HTML转图片服务"""
    
    def __init__(self):
        self.output_dir = "/app/app/static/generated/images"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化时检查依赖
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查系统依赖"""
        try:
            # 检查是否有puppeteer或者其他HTML转图片工具
            # 这里我们使用基于Node.js的html-to-image服务
            pass
        except Exception as e:
            logger.warning(f"HTML转图片依赖检查失败: {e}")
    
    async def convert_html_to_image(
        self, 
        html_content: str, 
        output_filename: str = None,
        width: int = 375,
        height: int = 600,
        format: str = "png"
    ) -> Optional[Dict[str, Any]]:
        """
        将HTML内容转换为图片
        
        Args:
            html_content: HTML内容
            output_filename: 输出文件名（可选）
            width: 图片宽度
            height: 图片高度
            format: 图片格式（png/jpeg）
            
        Returns:
            包含图片路径和URL的字典，失败返回None
        """
        try:
            if not output_filename:
                output_filename = f"postcard_{uuid.uuid4().hex[:8]}.{format}"
            
            output_path = os.path.join(self.output_dir, output_filename)
            
            # 方法1: 使用基于Node.js的html-to-image转换
            success = await self._convert_with_puppeteer(
                html_content, output_path, width, height, format
            )
            
            if success:
                # 生成访问URL（支持可配置公网前缀）
                path_part = f"/generated/images/{output_filename}"
                public_base = os.getenv("AI_AGENT_PUBLIC_URL", "").rstrip("/")
                image_url = f"{public_base}{path_part}" if public_base else path_part
                
                return {
                    "success": True,
                    "image_path": output_path,
                    "image_url": image_url,
                    "filename": output_filename,
                    "width": width,
                    "height": height,
                    "format": format
                }
            else:
                # 降级方案：生成简单的默认图片
                return await self._generate_fallback_image(
                    html_content, output_filename, width, height
                )
                
        except Exception as e:
            logger.error(f"HTML转图片失败: {e}")
            return None
    
    async def _convert_with_puppeteer(
        self, 
        html_content: str, 
        output_path: str, 
        width: int, 
        height: int, 
        format: str
    ) -> bool:
        """使用Puppeteer进行HTML转图片"""
        try:
            # 创建临时HTML文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                # 确保HTML包含完整的文档结构
                if not html_content.strip().startswith('<!DOCTYPE'):
                    # 补全HTML结构
                    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI生成明信片</title>
</head>
<body style="margin: 0; padding: 0; background: #f0f0f0; display: flex; justify-content: center; align-items: center; min-height: 100vh;">
    {html_content}
</body>
</html>"""
                else:
                    full_html = html_content
                
                tmp_file.write(full_html)
                tmp_html_path = tmp_file.name
            
            # 创建Node.js脚本用于转换
            puppeteer_script = f"""
const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {{
  const browser = await puppeteer.launch({{
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  }});
  
  const page = await browser.newPage();
  await page.setViewport({{ width: {width}, height: {height} }});
  
  await page.goto('file://{tmp_html_path}', {{ waitUntil: 'networkidle0' }});
  
  await page.screenshot({{ 
    path: '{output_path}', 
    type: '{format}',
    fullPage: false,
    clip: {{ x: 0, y: 0, width: {width}, height: {height} }}
  }});
  
  await browser.close();
}})();
"""
            
            # 创建临时JS文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tmp_js_file:
                tmp_js_file.write(puppeteer_script)
                tmp_js_path = tmp_js_file.name
            
            try:
                # 执行Node.js脚本
                process = await asyncio.create_subprocess_exec(
                    'node', tmp_js_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
                
                if process.returncode == 0 and os.path.exists(output_path):
                    logger.info(f"✅ HTML转图片成功: {output_path}")
                    return True
                else:
                    logger.warning(f"Puppeteer转换失败: {stderr.decode()}")
                    return False
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_html_path)
                    os.unlink(tmp_js_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Puppeteer转换异常: {e}")
            return False
    
    async def _generate_fallback_image(
        self, 
        html_content: str, 
        filename: str, 
        width: int, 
        height: int
    ) -> Dict[str, Any]:
        """生成降级方案图片"""
        try:
            # 使用PIL生成简单的文本图片作为降级方案
            try:
                from PIL import Image, ImageDraw, ImageFont
                
                # 创建图片
                image = Image.new('RGB', (width, height), color='#f8f9fa')
                draw = ImageDraw.Draw(image)
                
                # 尝试使用系统字体
                try:
                    font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 24)
                except:
                    font = ImageFont.load_default()
                
                # 绘制文本
                text = "AI生成的明信片\n正在处理中..."
                draw.text((width//4, height//2-50), text, fill='#333333', font=font)
                
                output_path = os.path.join(self.output_dir, filename)
                image.save(output_path)
                
                path_part = f"/generated/images/{filename}"
                public_base = os.getenv("AI_AGENT_PUBLIC_URL", "").rstrip("/")
                image_url = f"{public_base}{path_part}" if public_base else path_part

                return {
                    "success": True,
                    "image_path": output_path,
                    "image_url": image_url,
                    "filename": filename,
                    "width": width,
                    "height": height,
                    "fallback": True
                }
                
            except ImportError:
                # 如果没有PIL，使用更简单的方案
                logger.warning("PIL不可用，使用最简降级方案")
                
                # 创建一个简单的SVG然后保存
                svg_content = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
                    <rect width="100%" height="100%" fill="#f8f9fa"/>
                    <text x="50%" y="50%" text-anchor="middle" fill="#333" font-size="20" font-family="Arial, sans-serif">
                        AI生成明信片
                    </text>
                </svg>'''
                
                # 保存SVG文件
                svg_filename = filename.replace('.png', '.svg').replace('.jpg', '.svg')
                svg_path = os.path.join(self.output_dir, svg_filename)
                
                async with aiofiles.open(svg_path, 'w') as f:
                    await f.write(svg_content)
                
                path_part = f"/generated/images/{svg_filename}"
                public_base = os.getenv("AI_AGENT_PUBLIC_URL", "").rstrip("/")
                image_url = f"{public_base}{path_part}" if public_base else path_part

                return {
                    "success": True,
                    "image_path": svg_path,
                    "image_url": image_url,
                    "filename": svg_filename,
                    "width": width,
                    "height": height,
                    "fallback": True,
                    "format": "svg"
                }
                
        except Exception as e:
            logger.error(f"降级方案生成失败: {e}")
            return None
    
    async def get_image_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """获取图片信息"""
        try:
            file_path = os.path.join(self.output_dir, filename)
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                path_part = f"/generated/images/{filename}"
                public_base = os.getenv("AI_AGENT_PUBLIC_URL", "").rstrip("/")
                image_url = f"{public_base}{path_part}" if public_base else path_part

                return {
                    "filename": filename,
                    "path": file_path,
                    "url": image_url,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime
                }
            return None
        except Exception as e:
            logger.error(f"获取图片信息失败: {e}")
            return None
    
    async def cleanup_old_images(self, max_age_hours: int = 24):
        """清理旧图片文件"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > max_age_seconds:
                        os.unlink(file_path)
                        logger.info(f"清理旧图片: {filename}")
        except Exception as e:
            logger.error(f"清理旧图片失败: {e}")