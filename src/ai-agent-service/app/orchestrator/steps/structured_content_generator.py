import logging
import json
import random
from typing import Dict, Any, Optional
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class StructuredContentGenerator:
    """结构化内容生成器 - 生成心象签完整数据结构，支持挂件体验"""
    
    def __init__(self):
        # 文本生成使用 Gemini
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成结构化的卡片内容"""
        try:
            task = context["task"]
            results = context["results"]
            
            # 获取之前步骤的结果
            concept = results.get("concept", "")
            content = results.get("content", "")
            image_url = results.get("image_url", "")
            selected_charm = results.get("selected_charm_style", {})
            quiz_insights = results.get("quiz_insights", {})
            
            self.logger.info("🎨 开始生成结构化内容...")
            
            # 构建增强的Prompt
            enhanced_prompt = self._build_structured_prompt(task, concept, content, selected_charm, quiz_insights)
            
            # 调用Gemini生成结构化数据
            structured_content = await self.provider.generate_text(enhanced_prompt)
            
            # 解析并验证结构化数据
            parsed_data = self._parse_and_validate(structured_content)
            
            # 添加背景图片URL
            if image_url:
                if "visual" not in parsed_data:
                    parsed_data["visual"] = {}
                # 🔧 修复：再次确保visual字段是字典类型
                if not isinstance(parsed_data["visual"], dict):
                    parsed_data["visual"] = {}
                parsed_data["visual"]["background_image_url"] = image_url
            
            # 🔮 添加AI选择的签体信息
            if selected_charm and isinstance(selected_charm, dict):
                if "ai_selected_charm" not in parsed_data:
                    parsed_data["ai_selected_charm"] = {}
                
                # 从parsed_data中提取自然意象和情绪信息用于推理说明
                natural_scene = "自然意象"
                emotion_tone = "情绪基调"
                if "oracle_theme" in parsed_data and isinstance(parsed_data["oracle_theme"], dict):
                    natural_scene = parsed_data["oracle_theme"].get("title", "自然意象")
                if "charm_identity" in parsed_data and isinstance(parsed_data["charm_identity"], dict):
                    emotion_tone = parsed_data["charm_identity"].get("charm_description", "情绪基调")
                
                parsed_data["ai_selected_charm"] = {
                    "charm_id": selected_charm.get("id", "lianhua-yuanpai"),
                    "charm_name": selected_charm.get("name", "莲花圆牌 (平和雅致)"),
                    "ai_reasoning": f"基于'{natural_scene}'的自然意象和'{emotion_tone}'选择的签体"
                }
                self.logger.info(f"✅ 添加AI选择签体信息: {parsed_data['ai_selected_charm']['charm_id']}")
            
            # 保存结构化数据到结果中
            results["structured_data"] = parsed_data
            
            self.logger.info("✅ 结构化内容生成完成")
            self.logger.info(f"📊 生成内容包含：{list(parsed_data.keys())}")
            
            context["results"] = results
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 结构化内容生成失败: {e}")
            # 🔧 使用fallback数据，但确保包含签体信息
            fallback_data = self._get_fallback_structure()
            
            # 🔮 即使生成失败，也要添加AI选择的签体信息
            if selected_charm and isinstance(selected_charm, dict):
                if "ai_selected_charm" not in fallback_data:
                    fallback_data["ai_selected_charm"] = {}
                
                natural_scene = "自然意象"
                emotion_tone = "情绪基调"
                if "oracle_theme" in fallback_data and isinstance(fallback_data["oracle_theme"], dict):
                    natural_scene = fallback_data["oracle_theme"].get("title", "自然意象")
                if "charm_identity" in fallback_data and isinstance(fallback_data["charm_identity"], dict):
                    emotion_tone = fallback_data["charm_identity"].get("charm_description", "情绪基调")
                
                fallback_data["ai_selected_charm"] = {
                    "charm_id": selected_charm.get("id", "lianhua-yuanpai"),
                    "charm_name": selected_charm.get("name", "莲花圆牌 (平和雅致)"),
                    "ai_reasoning": f"基于'{natural_scene}'的自然意象和'{emotion_tone}'选择的签体"
                }
                self.logger.info(f"✅ Fallback中添加AI选择签体信息: {fallback_data['ai_selected_charm']['charm_id']}")
            
            # 🔧 添加背景图片URL到fallback数据
            if image_url:
                if "visual" not in fallback_data:
                    fallback_data["visual"] = {}
                if not isinstance(fallback_data["visual"], dict):
                    fallback_data["visual"] = {}
                fallback_data["visual"]["background_image_url"] = image_url
            
            # 保存fallback结构化数据到结果中
            results["structured_data"] = fallback_data
            
            self.logger.warning("⚠️ 使用fallback结构化数据")
            self.logger.info(f"📊 Fallback内容包含：{list(fallback_data.keys())}")
            
            context["results"] = results
            return context
    
    def _build_structured_prompt(self, task: Dict[str, Any], concept: str, content: str, selected_charm: Dict[str, Any], quiz_insights: Dict[str, Any]) -> str:
        """构建心象签结构化内容生成的Prompt，支持挂件体验"""
        user_input = task.get("user_input", "")
        ink_metrics = task.get('drawing_data', {}).get('analysis', {})
        
        # 解析概念和文案数据
        concept_data = {}
        content_data = {}
        try:
            if isinstance(concept, str) and concept.strip().startswith('{'):
                concept_data = json.loads(concept)
            if isinstance(content, str) and content.strip().startswith('{'):
                content_data = json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 提取关键信息
        natural_scene = concept_data.get('natural_scene', '晨光照进窗')
        emotion_tone = concept_data.get('emotion_tone', '平静')
        affirmation = content_data.get('affirmation', '愿所盼皆有回应')
        stroke_impression = content_data.get('stroke_impression', '笔触柔软，心境平和')
        symbolic_keywords = content_data.get('symbolic_keywords', ['流动', '平和'])
        daily_guide = content_data.get('daily_guide', ['宜静心思考', '宜关怀自己'])
        
        # 获取当前时间信息 (使用中国时区)
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
        try:
            from common.timezone_utils import china_now
            now = china_now()
        except ImportError:
            import datetime
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
        
        hour = now.hour
        month = now.month
        weekday = now.strftime('%A')
        
        # 确定时段和季节
        if hour < 6:
            session_time = "凌晨"
        elif hour < 12:
            session_time = "上午"
        elif hour < 18:
            session_time = "下午"
        elif hour < 22:
            session_time = "傍晚"
        else:
            session_time = "夜晚"
            
        if 3 <= month <= 5:
            season_hint = "春"
        elif 6 <= month <= 8:
            season_hint = "夏"
        elif 9 <= month <= 11:
            season_hint = "秋"
        else:
            season_hint = "冬"
        
        # 提取挂件和问答洞察信息
        charm_name = selected_charm.get('name', '莲花圆牌 (平和雅致)')
        charm_note = selected_charm.get('note', '平和雅致的挂件风格')
        quiz_summary = quiz_insights.get('summary', '心境平和，内心安宁')
        emotion_vector = quiz_insights.get('emotion_vector', {})
        action_focus = quiz_insights.get('action_focus', ['保持平静'])
        
        prompt = f"""
你是心象签系统的最终编撰师，负责整合所有信息生成完整的心象签体验。

已生成信息：
- 自然意象：{natural_scene}
- 情绪基调：{emotion_tone} 
- 祝福短句：{affirmation}
- 笔触印象：{stroke_impression}
- 象征关键词：{symbolic_keywords}
- 生活指引：{daily_guide}
- 用户输入：{user_input}
- 绘画特征：{ink_metrics.get('drawing_description', '平和的笔触')}

挂件信息：
- 选择签体：{charm_name}
- 签体特色：{charm_note}

问答洞察：
- 心境解读：{quiz_summary}
- 情绪倾向：{emotion_vector}
- 行动偏好：{action_focus}

当前时空背景：
- 时段：{session_time}
- 季节：{season_hint}季时分

请基于心象签理念，结合挂件风格和问答洞察，生成完整的JSON结构：

```json
{{
  "oracle_theme": {{
    "title": "{natural_scene}",
    "subtitle": "今日心象签"
  }},
  "charm_identity": {{
    "charm_name": "根据自然意象生成的2-4字签名，格式必须为'XX签'，与'{natural_scene}'高度呼应。如：晨光→晨露签，微风→清风签，花开→花语签，雨后→新生签，山水→静心签",
    "charm_description": "描述这个签的特质和寓意，要与自然意象完美呼应，体现心境与自然的共鸣",
    "charm_blessing": "与签名意境一致的8字内祝福，如：心如止水事事顺，或：愿你如花般绽放",
    "main_color": "符合'{natural_scene}'主色调的hex值（晨光用#FFD700，微风用#87CEEB，花开用#FFB6C1）",
    "accent_color": "与主色调和谐的辅助色hex值，形成完整配色方案"
  }},
  "affirmation": "{affirmation}",
  "oracle_manifest": {{
    "hexagram": {{
      "name": "基于'{natural_scene}'的具体卦象名称，要与心境和自然意象高度相关（如晨光对应'晨曦初露'、微风对应'清风徐来'等）",
      "symbol": "可为空或简短解释",
      "insight": "针对用户当前心境的1-2句具体解读，要与'{natural_scene}'和用户输入'{user_input}'相关"
    }},
    "daily_guide": {daily_guide},
    "fengshui_focus": "一句方位或环境建议（如'面向南方时更易聚焦'）",
    "ritual_hint": "一个简单的仪式建议（如'闭眼深呼吸三次'）",
    "element_balance": {{
      "wood": 0.6,
      "fire": 0.7, 
      "earth": 0.3,
      "metal": 0.4,
      "water": 0.5
    }}
  }},
  "ink_reading": {{
    "stroke_impression": "{stroke_impression}",
    "symbolic_keywords": {symbolic_keywords},
    "ink_metrics": {{
      "stroke_count": {ink_metrics.get('stroke_count', 0)},
      "dominant_quadrant": "{ink_metrics.get('dominant_quadrant', 'center')}",
      "pressure_tendency": "{ink_metrics.get('pressure_tendency', 'steady')}"
    }}
  }},
  "context_insights": {{
    "session_time": "{session_time}",
    "season_hint": "{season_hint}季时分",
    "visit_pattern": "今日心象之旅",
    "historical_keywords": []
  }},
  "blessing_stream": [
    "与自然意象呼应的祝福短语1（4-6字）",
    "与自然意象呼应的祝福短语2（4-6字）",  
    "与自然意象呼应的祝福短语3（4-6字）",
    "与自然意象呼应的祝福短语4（4-6字）"
  ],
  "art_direction": {{
    "image_prompt": "基于'{natural_scene}'的自然现象抽象图，{concept_data.get('color_inspiration', '暖色调')}水彩风格",
    "palette": ["{concept_data.get('color_inspiration', '#f5cba7')}", "#d4a3e3", "#4b3f72"],
    "animation_hint": "从模糊到清晰的光晕扩散"
  }},
  "culture_note": "灵感源于易经与民俗智慧，不作吉凶断言，请以现代视角理解。"
}}
```

关键要求：
1. **🔥 签名格式严格要求**：charm_identity.charm_name必须是"XX签"格式，不能是其他形式！如：晨露签、清风签、花语签、静心签、新生签等
2. **自然意象呼应**：签名与'{natural_scene}'意境完美匹配，体现人与自然的共鸣
3. **色彩和谐设计**：main_color反映自然意象的主色调，accent_color形成和谐配色
4. **卦象现代化表达**：基于自然意象的诗意卦象名，避免古老玄学术语
5. **祝福情感共鸣**：blessing_stream与自然意象深度呼应，如彩虹→"雨过天晴心更明"
6. **生活实用指引**：daily_guide要温和实用，oracle_manifest的insight要现代表达
7. **挂件风格融合**：整体内容风格与选择的{charm_name}挂件特色一致
8. **问答洞察融入**：daily_guide体现{action_focus}，hexagram的insight体现{quiz_summary}
9. **笔触数据运用**：stroke_impression结合ink_metrics真实数据，增强可信度
10. **色彩方案统一**：art_direction的palette与charm_identity的颜色形成统一视觉方案

注意：
- 所有字段都必须填写，不能为空
- blessing_stream数组需要4-6个短语
- daily_guide数组需要2-3条建议
- 避免命令式/玄学口吻，保持温柔日常风格
- 免责声明固定使用提供的文案

请直接返回JSON格式数据，不要添加其他文字说明。
"""
        
        return prompt
    
    def _extract_location_info(self, user_input: str) -> Dict[str, Any]:
        """从用户输入中提取位置信息"""
        location_info = {}
        
        # 简单的城市名提取（这里可以使用更复杂的NLP处理）
        import re
        
        # 常见城市名模式
        city_patterns = [
            r'地理位置：([^（）]*?)（',
            r'城市：([^，。]*)',
            r'位置.*?([^，。]*?)市',
            r'([^，。]*?)的天气',
            r'在([^，。]*?)，',
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, user_input)
            if match:
                city = match.group(1).strip()
                if len(city) > 1 and len(city) < 10:  # 合理的城市名长度
                    location_info['city'] = city
                    break
        
        # 提取天气信息
        weather_patterns = [
            r'天气[：:](.*?)(?:[，。]|$)',
            r'天气状况[：:](.*?)(?:[，。]|$)', 
            r'今天(.*?)(?:°C|度)',
        ]
        
        for pattern in weather_patterns:
            match = re.search(pattern, user_input)
            if match:
                weather = match.group(1).strip()
                location_info['weather'] = weather
                break
        
        return location_info
    
    def _parse_and_validate(self, response: str) -> Dict[str, Any]:
        """解析并验证心象签结构化数据"""
        try:
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("响应中未找到JSON数据")
            
            json_str = response[json_start:json_end]
            raw_parsed_data = json.loads(json_str)
            
            # 处理AI返回列表而非字典的情况
            if isinstance(raw_parsed_data, list):
                if len(raw_parsed_data) > 0 and isinstance(raw_parsed_data[0], dict):
                    parsed_data = raw_parsed_data[0]
                    self.logger.warning("⚠️ AI返回了数组格式，已自动提取第一个对象")
                else:
                    raise ValueError("AI返回的数组中没有有效的字典对象")
            elif isinstance(raw_parsed_data, dict):
                parsed_data = raw_parsed_data
            else:
                raise ValueError(f"AI返回了不支持的数据类型: {type(raw_parsed_data)}")
            
            # 验证心象签必需字段
            required_fields = ["oracle_theme", "charm_identity", "affirmation", "oracle_manifest", "ink_reading", "blessing_stream"]
            for field in required_fields:
                if field not in parsed_data:
                    self.logger.warning(f"⚠️ 缺少心象签必需字段：{field}")
            
            # 确保oracle_theme结构完整
            if "oracle_theme" not in parsed_data or not isinstance(parsed_data["oracle_theme"], dict):
                parsed_data["oracle_theme"] = {
                    "title": "晨光照进窗",
                    "subtitle": "今日心象签"
                }
            
            # 确保charm_identity结构完整
            if "charm_identity" not in parsed_data or not isinstance(parsed_data["charm_identity"], dict):
                parsed_data["charm_identity"] = {
                    "charm_name": "安心签",
                    "charm_description": "内心平静，万事顺遂",
                    "charm_blessing": "愿你心安，诸事顺遂",
                    "main_color": "#8B7355",
                    "accent_color": "#D4AF37"
                }
            
            # 确保oracle_manifest结构完整
            if "oracle_manifest" not in parsed_data or not isinstance(parsed_data["oracle_manifest"], dict):
                parsed_data["oracle_manifest"] = {
                    "hexagram": {
                        "name": "和风细雨",
                        "insight": "慢一点，你在好转的路上。"
                    },
                    "daily_guide": ["宜整理桌面，给心绪留白"],
                    "fengshui_focus": "面向阳光的方向",
                    "ritual_hint": "深呼吸三次",
                    "element_balance": {
                        "wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5
                    }
                }
            
            # 确保ink_reading结构完整
            if "ink_reading" not in parsed_data or not isinstance(parsed_data["ink_reading"], dict):
                parsed_data["ink_reading"] = {
                    "stroke_impression": "笔触柔软，心境平和",
                    "symbolic_keywords": ["流动", "平和"],
                    "ink_metrics": {
                        "stroke_count": 0,
                        "dominant_quadrant": "center",
                        "pressure_tendency": "steady"
                    }
                }
            
            # 确保blessing_stream是数组
            if "blessing_stream" not in parsed_data or not isinstance(parsed_data["blessing_stream"], list):
                parsed_data["blessing_stream"] = ["心想事成", "平安喜乐", "一路顺风", "万事如意"]
            
            # 确保context_insights结构完整
            if "context_insights" not in parsed_data or not isinstance(parsed_data["context_insights"], dict):
                parsed_data["context_insights"] = {
                    "session_time": "今日",
                    "season_hint": "当下",
                    "visit_pattern": "心象之旅",
                    "historical_keywords": []
                }
            
            # 确保art_direction结构完整
            if "art_direction" not in parsed_data or not isinstance(parsed_data["art_direction"], dict):
                parsed_data["art_direction"] = {
                    "image_prompt": "晨曦与薄雾的抽象水彩",
                    "palette": ["#f5e6cc", "#d9c4f2"],
                    "animation_hint": "从模糊到清晰的光晕扩散"
                }
            
            # 确保culture_note存在
            if "culture_note" not in parsed_data:
                parsed_data["culture_note"] = "灵感源于易经与民俗智慧，不作吉凶断言，请以现代视角理解。"

            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON解析失败: {e}")
            self.logger.error(f"🐛 AI原始响应内容: {response[:1000]}...")
            return self._get_fallback_structure()
        except Exception as e:
            import traceback
            self.logger.error(f"❌ 数据验证失败: {e}")
            self.logger.error(f"🐛 详细错误堆栈: {traceback.format_exc()}")
            return self._get_fallback_structure()
    
    def _get_fallback_structure(self) -> Dict[str, Any]:
        """获取心象签降级数据结构"""
        # 随机选择降级内容，避免每次都一样
        fallback_options = [
            {
                "oracle_theme": {
                    "title": "晨光照进窗",
                    "subtitle": "今日心象签"
                },
                "charm_identity": {
                    "charm_name": "安心签",
                    "charm_description": "内心平静，万事顺遂",
                    "charm_blessing": "愿你心安，诸事顺遂",
                    "main_color": "#8B7355",
                    "accent_color": "#D4AF37"
                },
                "affirmation": "愿你的努力皆被温柔回应",
                "oracle_manifest": {
                    "hexagram": {
                        "name": "和风细雨",
                        "insight": "慢一点，你在好转的路上。"
                    },
                    "daily_guide": [
                        "宜整理桌面，给心绪留白",
                        "宜尝试5分钟冥想"
                    ],
                    "fengshui_focus": "面向阳光的方向",
                    "ritual_hint": "深呼吸三次，感谢当下",
                    "element_balance": {
                        "wood": 0.7, "fire": 0.5, "earth": 0.6, "metal": 0.4, "water": 0.5
                    }
                },
                "ink_reading": {
                    "stroke_impression": "笔触柔软，说明心里有一块柔软区域被触碰",
                    "symbolic_keywords": ["柔和", "回环"],
                    "ink_metrics": {
                        "stroke_count": 90,
                        "dominant_quadrant": "upper_right",
                        "pressure_tendency": "light"
                    }
                },
                "context_insights": {
                    "session_time": "清晨",
                    "season_hint": "初春",
                    "visit_pattern": "久别重逢",
                    "historical_keywords": []
                },
                "blessing_stream": [
                    "心想事成",
                    "平安喜乐", 
                    "一路顺风"
                ],
                "art_direction": {
                    "image_prompt": "晨曦与薄雾的抽象水彩",
                    "palette": ["#f5e6cc", "#d9c4f2"],
                    "animation_hint": "从模糊到清晰的光晕扩散"
                },
                "culture_note": "灵感源自传统文化启迪，不作吉凶断言。"
            },
            {
                "oracle_theme": {
                    "title": "微风过竹林",
                    "subtitle": "今日心象签"
                },
                "charm_identity": {
                    "charm_name": "清心签",
                    "charm_description": "如竹般坚韧，如风般自由",
                    "charm_blessing": "愿你心如清风，身如劲竹",
                    "main_color": "#7C8471", 
                    "accent_color": "#A8E6CF"
                },
                "affirmation": "愿内心的宁静伴你前行",
                "oracle_manifest": {
                    "hexagram": {
                        "name": "风山渐",
                        "insight": "如竹般坚韧，在风中保持内心的宁静。"
                    },
                    "daily_guide": [
                        "宜到户外走走，感受自然的力量",
                        "宜听听音乐，让心情放松"
                    ],
                    "fengshui_focus": "在绿植旁工作更有灵感",
                    "ritual_hint": "摸摸植物的叶子，感受生命的力量",
                    "element_balance": {
                        "wood": 0.8, "fire": 0.3, "earth": 0.5, "metal": 0.6, "water": 0.4
                    }
                },
                "ink_reading": {
                    "stroke_impression": "线条流畅，内心有着清晰的方向感",
                    "symbolic_keywords": ["坚韧", "流动", "清晰"],
                    "ink_metrics": {
                        "stroke_count": 120,
                        "dominant_quadrant": "center",
                        "pressure_tendency": "steady"
                    }
                },
                "context_insights": {
                    "session_time": "午后",
                    "season_hint": "仲夏",
                    "visit_pattern": "心象探索",
                    "historical_keywords": []
                },
                "blessing_stream": [
                    "清风徐来",
                    "心如止水",
                    "步步生花",
                    "宁静致远"
                ],
                "art_direction": {
                    "image_prompt": "竹林中的阳光斑点，绿色清新水彩",
                    "palette": ["#9DE0AD", "#45B7D1", "#96CEB4"],
                    "animation_hint": "光影摇曳的自然律动"
                },
                "culture_note": "灵感源自传统文化启迪，不作吉凶断言。"
            }
        ]
        
        return random.choice(fallback_options)
