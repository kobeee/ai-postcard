import logging
import json
from ...providers.provider_factory import ProviderFactory
from ...services.html_to_image import HTMLToImageService

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
        
        # 构建独立明信片卡片组件生成提示词（强调移动端/小程序环境与图片参考）
        coding_prompt = self._build_standalone_card_prompt(
            task, concept, content_data, image_url
        )
        
        try:
            # 使用Claude Code SDK生成前端代码
            # 注意：这里需要适配现有的Claude Code Provider
            from ...coding_service.providers.claude_provider import ClaudeCodeProvider
            import asyncio
            
            # 创建一个会话ID
            session_id = f"postcard_{task.get('task_id', 'unknown')}"
            
            # 创建Claude提供商实例
            claude_provider = ClaudeCodeProvider()
            
            # 生成代码，使用正确的超时保护机制
            frontend_code = ""
            try:
                async def consume_claude_generator():
                    """消费Claude生成器并返回结果"""
                    async_generator = claude_provider.generate(coding_prompt, session_id, image_url=image_url)
                    async for message in async_generator:
                        if message.get("type") == "complete":
                            return message.get("final_code", "")
                        elif message.get("type") == "error":
                            self.logger.error(f"❌ Claude 代码生成错误: {message.get('content', 'Unknown error')}")
                            return None
                    return None
                
                # 使用asyncio.wait_for实现正确的超时处理 - 设置5分钟超时适合复杂代码生成
                self.logger.info("🚀 开始Claude代码生成，超时设置：5分钟")
                frontend_code = await asyncio.wait_for(
                    consume_claude_generator(), 
                    timeout=300.0  # 5分钟超时，适合复杂AI代码生成任务
                )
                
                if frontend_code:
                    self.logger.info("✅ Claude代码生成成功")
                else:
                    self.logger.warning("⚠️ Claude代码生成完成但无有效代码，使用默认代码")
                            
            except asyncio.TimeoutError:
                self.logger.warning("⚠️ Claude代码生成超时（5分钟），使用默认代码")
                # 超时后优雅降级，不抛出异常
                frontend_code = None
            except asyncio.CancelledError:
                self.logger.warning("⚠️ Claude代码生成被取消，使用默认代码")
                # 正确处理取消：不重新抛出，而是优雅降级
                frontend_code = None
            except Exception as e:
                self.logger.error(f"❌ Claude代码生成异常: {str(e)}")
                frontend_code = None
            
            if not frontend_code:
                frontend_code = self._get_default_frontend_code(content_data, image_url)
            
            # 保存HTML源码（用于持久化）
            context["results"]["frontend_code"] = frontend_code
            context["results"]["card_html"] = frontend_code
            context["results"]["preview_url"] = f"/generated/postcard_{task.get('task_id')}.html"

            # 将HTML转换为图片，供小程序直接展示
            try:
                html2img = HTMLToImageService()
                convert_result = await html2img.convert_html_to_image(
                    html_content=frontend_code,
                    output_filename=f"postcard_{task.get('task_id')}.png",
                    width=375,
                    height=600,
                    format="png"
                )
                if convert_result and convert_result.get("success"):
                    context["results"]["card_image_url"] = convert_result.get("image_url")
                    self.logger.info(f"✅ 卡片图片生成成功: {convert_result.get('image_url')}")
                else:
                    self.logger.warning("⚠️ 卡片图片生成失败，使用原始背景图降级")
                    # 降级：不设置card_image_url，让前端使用image_url
            except Exception as e:
                self.logger.warning(f"⚠️ HTML转图片异常: {e}")
            
            self.logger.info(f"✅ 前端代码生成完成: {len(frontend_code)} 字符")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 前端代码生成失败: {e}")
            # 返回默认前端代码
            default_html = self._get_default_frontend_code(content_data, image_url)
            context["results"]["frontend_code"] = default_html
            context["results"]["card_html"] = default_html
            context["results"]["preview_url"] = f"/generated/postcard_default_{task.get('task_id')}.html"
            # 兜底尝试转图片
            try:
                html2img = HTMLToImageService()
                convert_result = await html2img.convert_html_to_image(
                    html_content=default_html,
                    output_filename=f"postcard_{task.get('task_id')}.png",
                    width=375,
                    height=600,
                    format="png"
                )
                if convert_result and convert_result.get("success"):
                    context["results"]["card_image_url"] = convert_result.get("image_url")
            except Exception:
                pass
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
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            width: 375px;
            height: 600px;
            max-width: 100vw;
            overflow: hidden;
            transform: scale(0.95);
            animation: cardAppear 1s ease forwards;
            margin: 0 auto;
        }}
        
        @keyframes cardAppear {{
            to {{
                transform: scale(1);
            }}
        }}
        
        .postcard-header {{
            height: 350px;
            background: url('{image_url}') center/cover;
            position: relative;
            border-radius: 20px 20px 0 0;
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
            padding: 30px 25px;
            text-align: center;
            height: 250px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
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
    
    def _build_standalone_card_prompt(self, task, concept, content_data, image_url):
        """构建独立明信片卡片组件生成提示"""
        
        # 解析环境信息和情绪信息
        environment_info = self._parse_environment_info(task)
        emotion_info = self._parse_emotion_info(task) 
        
        # 构建基础内容信息
        concept_info = ""
        if concept:
            try:
                if isinstance(concept, str) and concept.strip().startswith('{'):
                    concept_data = json.loads(concept)
                    concept_info = f"\n- 设计概念：{concept_data.get('视觉风格', '现代简约')}"
            except:
                pass
                
        base_content = f"""
明信片内容：
- 主标题：{content_data.get('主标题', '温馨祝福')}
- 副标题：{content_data.get('副标题', '来自心底的真诚')}
- 正文：{content_data.get('正文内容', '愿美好与你同在')}
- 署名：{content_data.get('署名建议', '致亲爱的你')}{concept_info}
- 参考图片：{image_url}"""
        
        # 构建个性化设计指导
        personalized_design = self._build_design_guidance(environment_info, emotion_info)
        
        # 构建专注于独立卡片组件的提示
        prompt = f"""
请生成一个独立的明信片卡片组件，要求：

{base_content}

🌍 环境背景：{environment_info.get('context_description', '温馨的日常时刻')}
💫 用户情绪：{emotion_info.get('emotion_description', '平静温和的心境')}

**卡片特性**：
- 这是一个独立的卡片组件，不是完整网页应用
- 卡片采用竖屏友好的长条形设计，宽度375px，高度600px（手机屏幕适配）
- 适合微信小程序webview展示，支持手机竖屏浏览
- 使用提供的参考图片作为卡片背景元素

**设计要求**：
- 精美的明信片样式设计，体现用户当前的环境和心境
- 包含上述内容信息的优雅展示
- 优雅的卡片边框、阴影和圆角效果
- 文字要有适当的背景确保可读性
- 融入环境特色：{personalized_design}

**技术要求**：
- 只生成一个HTML文件，包含内联CSS
- 使用提供的参考图片作为背景（通过image_url参数）
- 卡片要有固定尺寸，可以嵌入任何容器
- 移动端友好设计，适配微信小程序webview
- 悬停和触摸交互效果

**重要约束**：
- 只生成卡片组件本身，不要导航栏、按钮等额外元素
- 不要生成完整的网页结构（head、body等），只要卡片的核心div
- 专注于创造一个精美的、可嵌入的明信片卡片

请将参考图片融入卡片设计中，创造一张独特的个性化明信片卡片组件。
"""
        
        return prompt
    
    def _parse_environment_info(self, task):
        """解析环境信息"""
        try:
            # 从task中获取原始用户输入，通常包含环境信息
            user_input = task.get('user_input', '')
            
            environment_info = {
                'city': '未知城市',
                'weather': '温和',
                'time_period': 'day',
                'season': 'spring',
                'trending': '生活美好',
                'context_description': '在这个美好的时刻'
            }
            
            # 从用户输入中提取环境信息 - 更智能的解析
            import re
            
            # 提取城市信息 - 匹配更多城市名格式
            city_patterns = [
                r'城市[：:]\s*([^，,。\s]+)',
                r'(?:在|位于)\s*([^，,。\s]{2,6}(?:市|县|区|镇)?)(?:[，,。\s]|$)',
                r'(北京|上海|广州|深圳|杭州|南京|武汉|成都|重庆|西安|天津|苏州|青岛|大连|厦门|宁波|无锡|长沙|郑州|沈阳|哈尔滨)'
            ]
            
            for pattern in city_patterns:
                city_match = re.search(pattern, user_input)
                if city_match:
                    environment_info['city'] = city_match.group(1)
                    break
            
            # 提取天气信息 - 匹配温度和天气描述
            temp_match = re.search(r'(\d+)°?[CcFf]?', user_input)
            if temp_match:
                temp = int(temp_match.group(1))
                if temp > 28:
                    environment_info['weather'] = '炎热'
                elif temp > 20:
                    environment_info['weather'] = '温暖'
                else:
                    environment_info['weather'] = '凉爽'
            
            # 提取天气描述词
            weather_patterns = [
                r'天气[：:]\s*([^，,。\s]+)',
                r'(晴朗|多云|阴天|雨天|雪天|雾霾|微风|大风|炎热|温暖|凉爽|寒冷)'
            ]
            
            for pattern in weather_patterns:
                weather_match = re.search(pattern, user_input)
                if weather_match:
                    environment_info['weather'] = weather_match.group(1)
                    break
            
            # 判断时间段
            import datetime
            hour = datetime.datetime.now().hour
            if 5 <= hour < 12:
                environment_info['time_period'] = 'morning'
            elif 12 <= hour < 18:
                environment_info['time_period'] = 'afternoon'  
            elif 18 <= hour < 22:
                environment_info['time_period'] = 'evening'
            else:
                environment_info['time_period'] = 'night'
            
            # 判断季节
            month = datetime.datetime.now().month
            if 3 <= month <= 5:
                environment_info['season'] = 'spring'
            elif 6 <= month <= 8:
                environment_info['season'] = 'summer'
            elif 9 <= month <= 11:
                environment_info['season'] = 'autumn'
            else:
                environment_info['season'] = 'winter'
            
            # 构建上下文描述
            city_desc = f"在{environment_info['city']}"
            weather_desc = f"这个{environment_info['weather']}的{self._get_time_description(environment_info['time_period'])}"
            season_desc = f"正值{self._get_season_description(environment_info['season'])}"
            
            environment_info['context_description'] = f"{city_desc}，{weather_desc}，{season_desc}，这是一个值得纪念的时刻"
            
            return environment_info
            
        except Exception as e:
            self.logger.warning(f"解析环境信息失败: {e}")
            return {
                'context_description': '在这个温馨的时刻',
                'city': '本地',
                'weather': '宜人',
                'time_period': 'day',
                'season': 'spring'
            }
    
    def _parse_emotion_info(self, task):
        """解析情绪信息"""
        try:
            user_input = task.get('user_input', '')
            
            emotion_info = {
                'type': 'calm',
                'intensity': 'medium',
                'pattern': 'flowing',
                'emotion_description': '平静而温和的心境'
            }
            
            # 从用户输入中分析情绪
            if '活跃' in user_input or 'energetic' in user_input:
                emotion_info['type'] = 'energetic'
                emotion_info['emotion_description'] = '充满活力和激情的状态'
            elif '深思' in user_input or 'thoughtful' in user_input:
                emotion_info['type'] = 'thoughtful'
                emotion_info['emotion_description'] = '深思熟虑、内省的心境'
            else:
                emotion_info['type'] = 'calm'
                emotion_info['emotion_description'] = '平静安详、温和的情绪'
            
            # 分析强度
            if 'high' in user_input or '强烈' in user_input:
                emotion_info['intensity'] = 'high'
            elif 'low' in user_input or '轻微' in user_input:
                emotion_info['intensity'] = 'low'
            else:
                emotion_info['intensity'] = 'medium'
            
            return emotion_info
            
        except Exception as e:
            self.logger.warning(f"解析情绪信息失败: {e}")
            return {
                'emotion_description': '平静温和的心境',
                'type': 'calm',
                'intensity': 'medium'
            }
    
    def _build_design_guidance(self, environment_info, emotion_info):
        """构建个性化设计指导"""
        
        # 基于情绪类型选择设计风格
        emotion_styles = {
            'energetic': {
                'colors': '充满活力的橙红色调、动感的黄色点缀',
                'animations': '快节奏的动画、跳跃式的过渡效果',
                'interactions': '响应迅速的点击反馈、震动效果'
            },
            'calm': {
                'colors': '宁静的蓝绿色调、柔和的紫色渐变',
                'animations': '缓慢流畅的动画、渐现的过渡效果',
                'interactions': '温和的悬停效果、平滑的切换'
            },
            'thoughtful': {
                'colors': '深沉的蓝色、哲思的灰色调',
                'animations': '深度的层次动画、思考式的停顿',
                'interactions': '需要用户深度参与的交互'
            }
        }
        
        # 基于环境选择设计元素
        weather_elements = {
            '炎热': '太阳光芒、热浪波纹、橙红色背景',
            '温暖': '温润的光晕、舒适的渐变',
            '凉爽': '清新的微风效果、蓝绿色调'
        }
        
        time_elements = {
            'morning': '晨光效果、渐亮的动画',
            'afternoon': '温暖的日光、稳定的光影',
            'evening': '夕阳色调、温暖的橙色',
            'night': '星光粒子、深蓝夜空'
        }
        
        # 获取对应的设计元素
        emotion_style = emotion_styles.get(emotion_info['type'], emotion_styles['calm'])
        weather_element = weather_elements.get(environment_info.get('weather', '温和'), '舒适的光影效果')
        time_element = time_elements.get(environment_info.get('time_period', 'day'), '温和的光线')
        
        design_guidance = f"""
1. 色彩方案：{emotion_style['colors']}，融入{weather_element}
2. 动画风格：{emotion_style['animations']}，体现{time_element}
3. 交互设计：{emotion_style['interactions']}
4. 环境融合：体现{environment_info.get('city', '本地')}特色，展现{environment_info.get('season', '春天')}的季节感
5. 情绪表达：通过视觉元素传达{emotion_info['emotion_description']}
6. 创意元素：添加与当前时刻相关的独特视觉彩蛋和惊喜效果"""
        
        return design_guidance
    
    def _get_time_description(self, time_period):
        """获取时间段描述"""
        descriptions = {
            'morning': '清晨',
            'afternoon': '午后',
            'evening': '傍晚',
            'night': '夜晚'
        }
        return descriptions.get(time_period, '时刻')
    
    def _get_season_description(self, season):
        """获取季节描述"""
        descriptions = {
            'spring': '万物复苏的春天',
            'summer': '生机勃勃的夏日',
            'autumn': '收获满满的秋天',
            'winter': '宁静致远的冬日'
        }
        return descriptions.get(season, '美好的季节')