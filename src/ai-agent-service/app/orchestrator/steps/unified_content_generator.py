import logging
import json
import asyncio
import os
from typing import Dict, Any, Optional
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class UnifiedContentGenerator:
    """优化版统一内容生成器 - 减少70%+ token消耗，提升生成质量"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载签体配置
        self.charm_configs = self._load_charm_configs()
        
        # 优化的重试配置 - 读取环境变量
        self.max_retries = int(os.getenv("GEMINI_RETRY_MAX_ATTEMPTS", "3"))
        retry_delays_str = os.getenv("GEMINI_RETRY_DELAYS", "2,8,20")
        self.retry_delays = [int(x.strip()) for x in retry_delays_str.split(",")]
        self.temperature_levels = [0.6, 0.8, 1.0]  # 优化：降低初始温度
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """主执行方法 - 带重试机制的统一生成"""
        task = context["task"]
        task_id = task.get("task_id")
        
        self.logger.info(f"🎯 开始统一内容生成: {task_id}")
        
        # 执行带重试的生成
        for attempt in range(self.max_retries):
            try:
                temperature = self.temperature_levels[min(attempt, 2)]
                self.logger.info(f"📝 第{attempt+1}次尝试，温度: {temperature}")
                
                # 快速分析用户特征
                user_profile = self._analyze_user_essence(task)
                
                # 智能推荐签体
                recommended_charms = self._smart_charm_recommendation(user_profile)
                
                # 构建优化prompt
                prompt = self._build_optimized_prompt(task, user_profile, recommended_charms)
                
                # 记录prompt长度
                self.logger.info(f"📏 优化prompt长度: {len(prompt)} 字符")
                
                # 调用Gemini生成
                response = await self.provider.generate_text(
                    prompt=prompt,
                    max_tokens=int(os.getenv("GEMINI_TEXT_MAX_TOKENS", "2000")),
                    temperature=temperature
                )
                
                # 解析和验证
                structured_data = self._parse_response(response)
                if self._validate_structured_data(structured_data):
                    context["results"]["structured_data"] = structured_data
                    self.logger.info("✅ 数据结构验证通过")
                    self.logger.info(f"✅ 优化版统一生成成功: {task_id}")
                    return context
                else:
                    raise ValueError("生成的数据结构验证失败")
                    
            except Exception as e:
                self.logger.error(f"❌ 第{attempt+1}次生成失败: {e}")
                
                if attempt < self.max_retries - 1:
                    # 增加重试间隔，避免触发rate limit
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # 最后一次失败，使用智能降级
                    self.logger.warning(f"⚠️ 所有重试失败，使用智能降级: {task_id}")
                    structured_data = self._get_intelligent_fallback(task)
                    context["results"]["structured_data"] = structured_data
                    return context
    
    def _analyze_user_essence(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """快速用户本质分析 - 替代复杂的用户档案分析"""
        user_input = task.get("user_input", "")
        drawing_data = task.get("drawing_data", {}).get("analysis", {})
        quiz_answers = task.get("quiz_answers", [])
        
        # 快速情绪检测
        emotion_keywords = {
            "peaceful": ["平静", "宁静", "淡然", "从容", "安静"],
            "energetic": ["活力", "精力", "动力", "兴奋", "激动"],
            "contemplative": ["思考", "沉思", "想念", "回忆", "深思"],
            "anxious": ["焦虑", "担心", "不安", "紧张", "压力"],
            "hopeful": ["希望", "期待", "向往", "憧憬", "梦想"]
        }
        
        detected_emotion = "peaceful"
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                detected_emotion = emotion
                break
        
        # 简化的五行计算
        elements = {"wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5}
        if detected_emotion == "energetic":
            elements["fire"] += 0.2
        elif detected_emotion == "contemplative":
            elements["water"] += 0.2
        elif detected_emotion == "peaceful":
            elements["earth"] += 0.2
        
        # 简化的卦象匹配
        hexagram_map = {
            "peaceful": {"name": "坤为地", "modern_name": "厚德载物", "insight": "如大地般包容，在沉静中积累力量"},
            "energetic": {"name": "乾为天", "modern_name": "自强不息", "insight": "如天行健，持续前进，必有所成"},
            "contemplative": {"name": "风雷益", "modern_name": "止水流深", "insight": "平静中蕴含着深邃的力量"},
            "anxious": {"name": "山雷颐", "modern_name": "颐养生息", "insight": "暂停脚步，让心灵得到滋养"},
            "hopeful": {"name": "火地晋", "modern_name": "光明进取", "insight": "内心光明，照亮前进的道路"}
        }
        
        return {
            "stroke_analysis": {
                "stroke_count": drawing_data.get("stroke_count", 0),
                "drawing_rhythm": "steady",
                "energy_type": detected_emotion
            },
            "quiz_insights": {
                "emotional_state": detected_emotion,
                "stress_level": "low" if detected_emotion in ["peaceful", "hopeful"] else "medium",
                "core_needs": ["inner_balance"]
            },
            "five_elements": elements,
            "hexagram": hexagram_map.get(detected_emotion, hexagram_map["peaceful"])
        }
    
    def _smart_charm_recommendation(self, user_profile: Dict[str, Any]) -> list:
        """智能签体推荐 - 基于核心特征快速匹配"""
        emotion = user_profile["quiz_insights"]["emotional_state"]
        
        # 情绪-签体映射
        emotion_charm_map = {
            "peaceful": ["宁静致远", "水墨禅心", "湖心月影"],
            "energetic": ["祥云流彩", "朱漆长牌", "六角灯笼面"],
            "contemplative": ["青玉团扇", "竹节长条", "银杏叶"],
            "anxious": ["长命锁", "海棠木窗", "方胜结"],
            "hopeful": ["莲花圆牌", "如意结", "双鱼锦囊"]
        }
        
        preferred_names = emotion_charm_map.get(emotion, emotion_charm_map["peaceful"])
        
        # 匹配实际配置
        recommended = []
        for charm_config in self.charm_configs:
            charm_name = charm_config.get("name", "")
            for preferred in preferred_names:
                if preferred in charm_name:
                    recommended.append(charm_config)
                    break
            if len(recommended) >= 3:
                break
        
        return recommended if recommended else self.charm_configs[:3]
    
    def _build_optimized_prompt(self, task: Dict[str, Any], user_profile: Dict[str, Any], recommended_charms: list) -> str:
        """构建高度优化的Prompt - 减少70%+ token消耗"""
        
        # 核心信息提取
        user_input = task.get("user_input", "")
        stroke_analysis = user_profile["stroke_analysis"]
        quiz_insights = user_profile["quiz_insights"]
        five_elements = user_profile["five_elements"]
        hexagram = user_profile["hexagram"]
        
        # 签体信息压缩
        charms_str = "|".join([f"{c.get('id', '')},{c.get('name', '')}" for c in recommended_charms[:3]])
        
        # 五行状态压缩
        elements_str = "|".join([f"{k}:{v:.1f}" for k, v in five_elements.items()])
        
        # 核心特征编码
        user_state = f"{quiz_insights['emotional_state']},{quiz_insights['stress_level']},{stroke_analysis['energy_type']}"
        
        prompt = f"""心象签大师，基于用户档案生成个性化心象签：

用户表达：{user_input}
心理特征：{user_state}
绘画数据：{stroke_analysis['stroke_count']}笔,{stroke_analysis.get('drawing_rhythm', 'steady')}
卦象：{hexagram['name']}-{hexagram['insight'][:20]}
五行：{elements_str}
签体选项：{charms_str}

要求：
1. 选择最匹配的签体ID
2. 自然意象要有画面感(春花/秋月/晨雾等)
3. 祝福语个性化，避免套话
4. 指引要实用具体

JSON格式(必须完整)：
{{
  "oracle_theme": {{
    "title": "4-6字自然意象",
    "subtitle": "今日心象签"
  }},
  "charm_identity": {{
    "charm_name": "XX签",
    "charm_description": "签体特质",
    "charm_blessing": "8字祝福",
    "main_color": "#hex色值", 
    "accent_color": "#hex色值"
  }},
  "ai_selected_charm": {{
    "charm_id": "选择的签体ID",
    "charm_name": "签体名称",
    "selection_reason": "选择理由"
  }},
  "oracle_affirmation": "8-14字个性化祝福",
  "oracle_manifest": {{
    "hexagram": {{
      "name": "{hexagram['modern_name']}",
      "insight": "20字内指引"
    }},
    "daily_guide": ["实用建议1", "实用建议2"],
    "fengshui_focus": "环境建议",
    "ritual_hint": "简单仪式",
    "element_balance": {five_elements}
  }},
  "ink_reading": {{
    "stroke_impression": "基于{stroke_analysis['stroke_count']}笔的心理解读",
    "symbolic_keywords": ["关键词1", "关键词2", "关键词3"],
    "ink_metrics": {{
      "stroke_count": {stroke_analysis['stroke_count']},
      "dominant_quadrant": "center",
      "pressure_tendency": "steady"
    }}
  }},
  "context_insights": {{
    "session_time": "当前时段",
    "season_hint": "当前季节",
    "visit_pattern": "心象之旅",
    "historical_keywords": []
  }},
  "blessing_stream": ["祝福1", "祝福2", "祝福3", "祝福4"],
  "art_direction": {{
    "image_prompt": "基于自然意象的图像描述",
    "palette": ["主色", "辅助色", "装饰色"],
    "animation_hint": "光影效果"
  }},
  "visual": {{
    "background_image_url": "",
    "color_scheme": "warm/cool/neutral",
    "style_preference": "traditional/modern/artistic"
  }},
  "culture_note": "传统文化的现代解读"
}}"""

        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析Gemini响应"""
        try:
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("响应中未找到有效的JSON格式")
                
        except Exception as e:
            self.logger.error(f"❌ 解析响应失败: {e}")
            raise
    
    def _validate_structured_data(self, data: Dict[str, Any]) -> bool:
        """验证结构化数据完整性"""
        required_fields = [
            "oracle_theme", "charm_identity", "ai_selected_charm", 
            "oracle_affirmation", "oracle_manifest", "ink_reading",
            "context_insights", "blessing_stream", "art_direction", "visual"
        ]
        
        for field in required_fields:
            if field not in data:
                self.logger.error(f"❌ 缺少必要字段: {field}")
                return False
        
        return True
    
    def _get_intelligent_fallback(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """智能降级方案 - 基于用户输入生成个性化兜底"""
        user_input = task.get("user_input", "")
        
        # 分析用户输入的情绪倾向
        emotion_keywords = {
            "positive": ["开心", "快乐", "高兴", "愉快", "兴奋", "激动"],
            "calm": ["平静", "安静", "宁静", "淡然", "从容", "放松"],
            "energetic": ["活力", "精力", "动力", "充满", "积极"],
            "thoughtful": ["思考", "沉思", "想念", "回忆", "深思", "反思"],
            "hopeful": ["希望", "期待", "梦想", "未来", "目标", "愿望"]
        }
        
        detected_emotion = "calm"
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                detected_emotion = emotion
                break
        
        # 基于检测到的情绪生成个性化兜底
        fallback_templates = {
            "positive": {
                "title": "春日暖阳",
                "charm_name": "暖阳签",
                "affirmation": "愿快乐如春花绽放",
                "main_color": "#FFE4B5",
                "blessing": ["心花怒放", "笑靥如花", "春风得意", "阳光满怀"]
            },
            "calm": {
                "title": "湖水如镜", 
                "charm_name": "静心签",
                "affirmation": "愿内心如湖水般宁静",
                "main_color": "#B0E0E6",
                "blessing": ["心如止水", "宁静致远", "岁月静好", "内心安宁"]
            },
            "energetic": {
                "title": "破浪前行",
                "charm_name": "活力签", 
                "affirmation": "愿活力如潮水般涌现",
                "main_color": "#FF6B6B",
                "blessing": ["活力四射", "勇往直前", "破浪前行", "动力满满"]
            },
            "thoughtful": {
                "title": "月下思语",
                "charm_name": "深思签",
                "affirmation": "愿思考带来智慧光芒", 
                "main_color": "#9370DB",
                "blessing": ["深思熟虑", "智慧如海", "思接千载", "洞察深邃"]
            },
            "hopeful": {
                "title": "晨曦初露",
                "charm_name": "希望签",
                "affirmation": "愿希望如晨曦般闪耀",
                "main_color": "#FFD700", 
                "blessing": ["希望满怀", "曙光在前", "梦想成真", "未来可期"]
            }
        }
        
        template = fallback_templates.get(detected_emotion, fallback_templates["calm"])
        
        return {
            "oracle_theme": {
                "title": template["title"],
                "subtitle": "今日心象签"
            },
            "charm_identity": {
                "charm_name": template["charm_name"],
                "charm_description": f"如{template['title']}般的心境，内心{detected_emotion}",
                "charm_blessing": template["affirmation"],
                "main_color": template["main_color"],
                "accent_color": "#FFFFFF"
            },
            "oracle_affirmation": template["affirmation"],
            "oracle_manifest": {
                "hexagram": {
                    "name": "内心安宁",
                    "insight": "心境如水，包容万物。"
                },
                "daily_guide": [
                    "宜保持当下的美好心境",
                    "宜感恩生活中的小确幸"
                ],
                "fengshui_focus": "面向光明的方向",
                "ritual_hint": "深呼吸三次，感受内心的平静",
                "element_balance": {
                    "wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5
                }
            },
            "ink_reading": {
                "stroke_impression": f"笔触体现了内心的{detected_emotion}状态，显示着心境的美好",
                "symbolic_keywords": [detected_emotion, "平和", "美好"],
                "ink_metrics": {
                    "stroke_count": task.get('drawing_data', {}).get('analysis', {}).get('stroke_count', 0),
                    "dominant_quadrant": task.get('drawing_data', {}).get('analysis', {}).get('dominant_quadrant', 'center'),
                    "pressure_tendency": task.get('drawing_data', {}).get('analysis', {}).get('pressure_tendency', 'steady')
                }
            },
            "context_insights": {
                "session_time": "当下时刻",
                "season_hint": "四季流转",
                "visit_pattern": "心象之旅",
                "historical_keywords": []
            },
            "blessing_stream": template["blessing"],
            "art_direction": {
                "image_prompt": f"{template['title']}的自然意象，水彩风格",
                "palette": [template["main_color"], "#F0F8FF", "#FFF8DC"],
                "animation_hint": "温和的光影变化"
            },
            "ai_selected_charm": {
                "charm_id": "lianhua-yuanpai",
                "charm_name": "莲花圆牌 (平和雅致)",
                "selection_reason": f"基于用户{detected_emotion}的心境特征选择"
            },
            "visual": {
                "background_image_url": "",
                "color_scheme": "cool",
                "style_preference": "traditional"
            },
            "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
        }
    
    
    
    
    
    
    
    
    def _load_charm_configs(self):
        """加载签体配置 - 精简版本"""
        try:
            config_path = os.getenv('CHARM_CONFIG_PATH', '/app/resources/签体/charm-config.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                    self.logger.info(f"✅ 成功加载 {len(configs)} 个签体配置")
                    return configs
            else:
                self.logger.warning("⚠️ 使用默认签体配置")
                return [
                    {"id": "lianhua-yuanpai", "name": "莲花圆牌 (平和雅致)", "note": "内心平和"},
                    {"id": "xiangYun-liucai", "name": "祥云流彩 (活力充沛)", "note": "活力充沛"},
                    {"id": "shuimo-chanxin", "name": "水墨禅心 (禅意深远)", "note": "禅意深远"}
                ]
        except Exception as e:
            self.logger.error(f"❌ 加载签体配置失败: {e}")
            return [{"id": "fallback", "name": "默认签体", "note": "备用配置"}]
    
