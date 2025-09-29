import logging
import json
import asyncio
import datetime
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class TwoStageGenerator:
    """阶段2：心象签生成器 - 基于分析生成内容"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载签体配置
        self.charm_configs = self._load_charm_configs()
        
        # 重试配置
        self.max_retries = 3
        self.retry_delays = [2, 4, 8]  # 指数退避
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行心象签生成"""
        task = context["task"]
        analysis = context["results"]["analysis"]
        task_id = task.get("task_id")
        
        self.logger.info(f"🎨 开始心象签生成: {task_id}")
        
        # 带重试的生成执行
        oracle_content = await self._generate_with_retry(analysis, task)
        
        # 将生成结果保存到context
        context["results"]["structured_data"] = oracle_content
        
        self.logger.info(f"✅ 心象签生成完成: {task_id}")
        return context
    
    async def _generate_with_retry(self, analysis: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """带重试机制的生成执行"""
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"📝 第{attempt+1}次生成尝试")
                
                # 签体推荐
                recommended_charms = self._recommend_charms(analysis)
                
                # 构建生成prompt
                prompt = self._build_generation_prompt(analysis, task, recommended_charms)
                
                # 调用Gemini
                response = await self.provider.generate_text(
                    prompt=prompt,
                    max_tokens=1200,
                    temperature=0.8 + attempt * 0.1  # 逐步提高创造性
                )
                
                # 解析响应
                oracle_content = self._parse_generation_response(response)
                
                # 后处理和验证
                oracle_content = self._post_process_oracle_content(oracle_content, analysis, task)
                
                if self._validate_oracle_content(oracle_content):
                    return oracle_content
                else:
                    raise ValueError("生成内容验证失败")
                    
            except Exception as e:
                self.logger.error(f"❌ 第{attempt+1}次生成失败: {e}")
                
                if attempt < self.max_retries - 1:
                    # 还有重试机会
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # 最后一次失败，使用模板降级
                    self.logger.warning(f"⚠️ 所有重试失败，使用模板降级")
                    return self._get_template_oracle(analysis, task)
    
    def _recommend_charms(self, analysis: Dict[str, Any]) -> list:
        """基于分析推荐签体"""
        five_elements = analysis.get("five_elements", {})
        emotion_state = analysis.get("psychological_profile", {}).get("emotion_state", "calm")
        
        # 获取主导五行
        dominant_element = max(five_elements.keys(), key=lambda k: five_elements[k]) if five_elements else "earth"
        
        # 签体分类映射
        charm_categories = {
            "wood": ["竹节长条", "银杏叶", "莲花圆牌"],  # 木系：成长、自然
            "fire": ["祥云流彩", "朱漆长牌", "六角灯笼面"],  # 火系：活力、光明
            "earth": ["方胜结", "长命锁", "海棠木窗"],  # 土系：稳重、传统
            "metal": ["金边墨玉璧", "八角锦囊", "如意结"],  # 金系：坚韧、精致
            "water": ["青玉团扇", "青花瓷扇", "双鱼锦囊"]  # 水系：流动、智慧
        }
        
        # 根据情绪调整推荐
        if emotion_state in ["energetic", "positive"]:
            preferred_charms = charm_categories.get("fire", []) + charm_categories.get("wood", [])
        elif emotion_state in ["calm", "thoughtful"]:
            preferred_charms = charm_categories.get("water", []) + charm_categories.get("metal", [])
        else:
            preferred_charms = charm_categories.get(dominant_element, [])
        
        # 匹配实际配置中的签体
        recommended = []
        for charm_config in self.charm_configs:
            charm_name = charm_config.get("name", "")
            for preferred in preferred_charms:
                if preferred in charm_name:
                    recommended.append(charm_config)
                    break
        
        # 如果没有匹配，返回前3个作为默认
        return recommended[:3] if recommended else self.charm_configs[:3]
    
    def _build_generation_prompt(self, analysis: Dict[str, Any], task: Dict[str, Any], recommended_charms: list) -> str:
        """构建生成prompt"""
        
        # 提取分析结果
        psychological_profile = analysis.get("psychological_profile", {})
        five_elements = analysis.get("five_elements", {})
        hexagram_match = analysis.get("hexagram_match", {})
        key_insights = analysis.get("key_insights", [])
        
        # 构建推荐签体信息
        charm_info = ""
        for i, charm in enumerate(recommended_charms, 1):
            charm_info += f"  {i}. {charm.get('name', '')} (ID: {charm.get('id', '')}) - {charm.get('note', '')}\n"
        
        # 获取绘画数据
        drawing_data = task.get("drawing_data", {}).get("analysis", {})
        
        prompt = f"""你是心象签创作大师，基于心理分析报告创作个性化心象签内容。

## 创作任务
根据分析报告生成完整心象签，体现东方美学和个性化表达。

## 分析报告
**心理档案**:
- 情绪状态: {psychological_profile.get('emotion_state', '未知')}
- 核心需求: {', '.join(psychological_profile.get('core_needs', []))}
- 能量类型: {psychological_profile.get('energy_type', '平衡')}
- 主导特质: {', '.join(psychological_profile.get('dominant_traits', []))}

**五行能量**:
- 木: {five_elements.get('wood', 0.5)}  火: {five_elements.get('fire', 0.5)}  土: {five_elements.get('earth', 0.5)}
- 金: {five_elements.get('metal', 0.5)}  水: {five_elements.get('water', 0.5)}

**卦象匹配**:
- 卦象: {hexagram_match.get('name', '未知')} ({hexagram_match.get('modern_name', '未知')})
- 启示: {hexagram_match.get('insight', '未知')}

**核心洞察**: {', '.join(key_insights)}

## 可选签体
{charm_info}

## 创作要求
1. **个性化表达**：基于分析结果体现用户独特性，避免通用模板
2. **文化融入**：结合卦象智慧和五行调和理念
3. **现代表达**：传统文化的现代化演绎
4. **色彩心理**：main_color和accent_color体现用户心理需求
5. **签体匹配**：从推荐列表选择最符合用户特质的签体

## 输出格式
严格按以下JSON格式返回，所有字段必填：

```json
{{
  "oracle_theme": {{
    "title": "基于分析的自然意象(4-6字)",
    "subtitle": "今日心象签"
  }},
  "charm_identity": {{
    "charm_name": "XX签(必须以'签'结尾)",
    "charm_description": "体现用户特质的签体描述",
    "charm_blessing": "个性化祝福(8字以内)",
    "main_color": "#hex颜色值",
    "accent_color": "#hex颜色值"
  }},
  "affirmation": "直击用户内心的祝福语(8-14字)",
  "oracle_manifest": {{
    "hexagram": {{
      "name": "{hexagram_match.get('modern_name', '内心和谐')}",
      "insight": "结合卦象的人生指引(不超过30字)"
    }},
    "daily_guide": [
      "基于五行的平衡建议(15-25字)",
      "针对心理状态的实用指引(15-25字)"
    ],
    "fengshui_focus": "结合用户状态的环境建议",
    "ritual_hint": "简单易行的调和仪式",
    "element_balance": {{
      "wood": {five_elements.get('wood', 0.5)},
      "fire": {five_elements.get('fire', 0.5)},
      "earth": {five_elements.get('earth', 0.5)},
      "metal": {five_elements.get('metal', 0.5)},
      "water": {five_elements.get('water', 0.5)}
    }}
  }},
  "ink_reading": {{
    "stroke_impression": "基于绘画数据的心理解读(25-40字)",
    "symbolic_keywords": ["核心关键词1", "关键词2", "关键词3"],
    "ink_metrics": {{
      "stroke_count": {drawing_data.get('stroke_count', 0)},
      "dominant_quadrant": "{drawing_data.get('dominant_quadrant', 'center')}",
      "pressure_tendency": "{drawing_data.get('pressure_tendency', 'steady')}"
    }}
  }},
  "context_insights": {{
    "session_time": "时间段描述",
    "season_hint": "季节时分",
    "visit_pattern": "基于用户特征的访问模式",
    "historical_keywords": []
  }},
  "blessing_stream": [
    "与意象呼应的祝福1(4-6字)",
    "体现需求的祝福2(4-6字)", 
    "五行调和的祝福3(4-6字)",
    "未来希冀的祝福4(4-6字)"
  ],
  "art_direction": {{
    "image_prompt": "基于意象的具体画面描述，水彩风格",
    "palette": ["主色调hex", "辅助色1hex", "辅助色2hex"],
    "animation_hint": "符合意境的动画效果"
  }},
  "ai_selected_charm": {{
    "charm_id": "选择的签体ID",
    "charm_name": "签体名称",
    "ai_reasoning": "基于分析选择此签体的原因"
  }},
  "culture_note": "灵感源于易经与五行智慧，不作吉凶断言，请以现代视角理解。"
}}
```

专注创作，体现深度个性化，避免套话模板。"""
        
        return prompt
    
    def _parse_generation_response(self, response: str) -> Dict[str, Any]:
        """解析生成响应"""
        try:
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("响应中未找到JSON数据")
            
            json_str = response[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON解析失败: {e}")
            self.logger.error(f"🐛 原始响应: {response[:300]}...")
            raise
    
    def _post_process_oracle_content(self, oracle_content: Dict[str, Any], analysis: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """后处理oracle内容"""
        
        # 确保所有必需字段存在
        required_fields = [
            "oracle_theme", "charm_identity", "affirmation", 
            "oracle_manifest", "ink_reading", "blessing_stream",
            "art_direction", "ai_selected_charm", "culture_note"
        ]
        
        for field in required_fields:
            if field not in oracle_content:
                self.logger.warning(f"⚠️ 缺少必需字段: {field}")
                oracle_content[field] = self._get_default_field_value(field, analysis)
        
        # 验证和修复oracle_theme
        if not isinstance(oracle_content.get("oracle_theme"), dict):
            oracle_content["oracle_theme"] = {
                "title": "心象如画",
                "subtitle": "今日心象签"
            }
        
        # 验证和修复charm_identity
        if not isinstance(oracle_content.get("charm_identity"), dict):
            oracle_content["charm_identity"] = {
                "charm_name": "安心签",
                "charm_description": "内心平静，万事顺遂",
                "charm_blessing": "愿你心安，诸事顺遂",
                "main_color": "#8B7355",
                "accent_color": "#D4AF37"
            }
        
        # 确保charm_name是XX签格式
        charm_name = oracle_content["charm_identity"].get("charm_name", "")
        if not charm_name.endswith("签"):
            oracle_title = oracle_content["oracle_theme"].get("title", "安心")
            if len(oracle_title) >= 2:
                oracle_content["charm_identity"]["charm_name"] = oracle_title[:2] + "签"
            else:
                oracle_content["charm_identity"]["charm_name"] = "安心签"
        
        # 验证五行数据
        element_balance = oracle_content.get("oracle_manifest", {}).get("element_balance", {})
        if not isinstance(element_balance, dict) or len(element_balance) != 5:
            oracle_content.setdefault("oracle_manifest", {})["element_balance"] = analysis.get("five_elements", {
                "wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5
            })
        
        # 确保context_insights存在
        if "context_insights" not in oracle_content:
            temporal_info = self._get_temporal_info()
            oracle_content["context_insights"] = {
                "session_time": temporal_info["time_period"],
                "season_hint": temporal_info["season_hint"],
                "visit_pattern": "心象之旅",
                "historical_keywords": []
            }
        
        return oracle_content
    
    def _validate_oracle_content(self, oracle_content: Dict[str, Any]) -> bool:
        """验证oracle内容"""
        try:
            # 检查必需字段
            required_fields = [
                "oracle_theme", "charm_identity", "affirmation",
                "oracle_manifest", "ink_reading", "blessing_stream"
            ]
            
            for field in required_fields:
                if field not in oracle_content:
                    self.logger.error(f"❌ 缺少必需字段: {field}")
                    return False
            
            # 检查oracle_theme结构
            oracle_theme = oracle_content.get("oracle_theme")
            if not isinstance(oracle_theme, dict) or "title" not in oracle_theme:
                self.logger.error("❌ oracle_theme结构错误")
                return False
            
            # 检查charm_identity结构
            charm_identity = oracle_content.get("charm_identity")
            if not isinstance(charm_identity, dict) or "charm_name" not in charm_identity:
                self.logger.error("❌ charm_identity结构错误")
                return False
            
            # 检查blessing_stream是数组
            blessing_stream = oracle_content.get("blessing_stream")
            if not isinstance(blessing_stream, list) or len(blessing_stream) < 3:
                self.logger.error("❌ blessing_stream结构错误")
                return False
            
            self.logger.info("✅ oracle内容验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 验证异常: {e}")
            return False
    
    def _get_template_oracle(self, analysis: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """模板降级生成"""
        from .template_oracle_generator import TemplateOracleGenerator
        
        generator = TemplateOracleGenerator()
        return generator.generate(analysis, task)
    
    def _get_temporal_info(self) -> Dict[str, str]:
        """获取时间信息"""
        try:
            now = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
        except:
            now = datetime.datetime.now()
            
        hour = now.hour
        month = now.month
        
        # 时间段判断
        if 6 <= hour < 12:
            time_period = "清晨时光"
        elif 12 <= hour < 18:
            time_period = "午后时分"
        elif 18 <= hour < 22:
            time_period = "黄昏时刻"
        else:
            time_period = "夜深人静"
        
        # 季节判断
        if 3 <= month <= 5:
            season_hint = "春季时分"
        elif 6 <= month <= 8:
            season_hint = "夏日时光"
        elif 9 <= month <= 11:
            season_hint = "秋季时节"
        else:
            season_hint = "冬日暖阳"
        
        return {
            "time_period": time_period,
            "season_hint": season_hint
        }
    
    def _load_charm_configs(self):
        """加载签体配置"""
        import os
        import json
        
        potential_paths = [
            os.environ.get('CHARM_CONFIG_PATH'),
            '/app/resources/签体/charm-config.json',
            os.path.join(os.path.dirname(__file__), '../../../../resources/签体/charm-config.json'),
            os.path.join(os.getcwd(), 'resources/签体/charm-config.json'),
        ]
        
        potential_paths = [p for p in potential_paths if p is not None]
        
        for config_path in potential_paths:
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        configs = json.load(f)
                        if isinstance(configs, list) and len(configs) > 0:
                            self.logger.info(f"✅ 成功加载 {len(configs)} 个签体配置")
                            return configs
            except Exception:
                continue
        
        self.logger.warning("⚠️ 使用默认签体配置")
        return self._get_default_charm_configs()
    
    def _get_default_charm_configs(self):
        """默认签体配置"""
        return [
            {"id": "lianhua-yuanpai", "name": "莲花圆牌 (平和雅致)", "note": "圆牌留白充足"},
            {"id": "jinbian-moyu", "name": "金边墨玉璧 (沉稳庄重)", "note": "墨玉色调沉稳"},
            {"id": "qinghua-cishan", "name": "青花瓷扇 (文化底蕴)", "note": "青花纹路典雅"}
        ]
    
    def _get_default_field_value(self, field: str, analysis: Dict[str, Any]) -> Any:
        """获取字段的默认值"""
        defaults = {
            "oracle_theme": {"title": "心象如画", "subtitle": "今日心象签"},
            "charm_identity": {
                "charm_name": "安心签",
                "charm_description": "内心平静，万事顺遂", 
                "charm_blessing": "愿你心安，诸事顺遂",
                "main_color": "#8B7355",
                "accent_color": "#D4AF37"
            },
            "affirmation": "愿你被这个世界温柔以待",
            "oracle_manifest": {
                "hexagram": {"name": "内心和谐", "insight": "在变化中寻找内心的平衡"},
                "daily_guide": ["宜保持内心平静", "宜感恩生活中的美好"],
                "fengshui_focus": "面向光明的方向",
                "ritual_hint": "深呼吸三次，感受内心的平静",
                "element_balance": {"wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5}
            },
            "ink_reading": {
                "stroke_impression": "笔触体现了内心的平和状态，显示着心境的美好",
                "symbolic_keywords": ["平和", "美好", "和谐"],
                "ink_metrics": {"stroke_count": 0, "dominant_quadrant": "center", "pressure_tendency": "steady"}
            },
            "blessing_stream": ["心想事成", "平安喜乐", "一路顺风", "万事如意"],
            "art_direction": {
                "image_prompt": "心象如画的自然意象，水彩风格",
                "palette": ["#8B7355", "#D4AF37", "#F0F8FF"],
                "animation_hint": "温和的光影变化"
            },
            "ai_selected_charm": {
                "charm_id": "lianhua-yuanpai",
                "charm_name": "莲花圆牌 (平和雅致)",
                "ai_reasoning": "基于用户心境特征选择"
            },
            "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
        }
        return defaults.get(field, {})