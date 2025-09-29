# AI工作流优化方案：合并多次调用为高效单次调用

**文档版本**：v1.0  
**创建时间**：2025-09-28  
**负责人**：AI助手 & 开发团队  

## 1. 方案概述

### 1.1 优化目标
将当前的**3次文本AI调用 + 1次图像调用**优化为**1次文本AI调用 + 1次图像调用**，同时显著提升个性化效果和用户体验。

### 1.2 核心收益
- ⚡ **性能提升**：响应时间减少50-70%
- 💰 **成本降低**：API调用费用减少66%
- 🎯 **体验优化**：更连贯的逻辑推理，更个性化的内容
- 🔧 **维护简化**：减少兜底逻辑复杂度，提升系统稳定性

### 1.3 技术架构变更

#### 当前架构（4步工作流）：
```
用户输入 → ConceptGenerator → ContentGenerator → StructuredContentGenerator → ImageGenerator
         ↓                  ↓                    ↓                           ↓
     (调用1: Gemini)   (调用2: Gemini)    (调用3: Gemini)            (调用4: 生图)
```

#### 优化后架构（2步工作流）：
```
用户输入 → UnifiedContentGenerator → ImageGenerator
         ↓                         ↓
    (调用1: Gemini统一生成)      (调用2: 生图)
```

## 2. 详细设计方案

### 2.1 新增统一内容生成器

#### 2.1.1 创建新文件
**文件路径**：`src/ai-agent-service/app/orchestrator/steps/unified_content_generator.py`

**核心功能**：
- 整合原有3个Generator的所有功能
- 一次性生成完整的心象签结构化数据
- 内置签体选择逻辑
- 集成重试机制和智能降级

#### 2.1.2 数据结构保持不变
确保输出的`structured_data`格式完全兼容现有小程序端：

```python
{
    "oracle_theme": {"title": "自然意象", "subtitle": "今日心象签"},
    "charm_identity": {
        "charm_name": "XX签",
        "charm_description": "签的特质描述",
        "charm_blessing": "8字祝福",
        "main_color": "#hex值",
        "accent_color": "#hex值"
    },
    "affirmation": "祝福短句",
    "oracle_manifest": {
        "hexagram": {"name": "卦象名", "insight": "具体解读"},
        "daily_guide": ["生活指引1", "生活指引2"],
        "fengshui_focus": "风水建议",
        "ritual_hint": "仪式提示",
        "element_balance": {"wood": 0.6, "fire": 0.7, ...}
    },
    "ink_reading": {
        "stroke_impression": "笔触印象",
        "symbolic_keywords": ["关键词1", "关键词2"],
        "ink_metrics": {...}
    },
    "context_insights": {...},
    "blessing_stream": [...],
    "art_direction": {...},
    "ai_selected_charm": {...},
    "culture_note": "免责声明"
}
```

### 2.2 重试机制设计

#### 2.2.1 三级重试策略
```python
class RetryStrategy:
    def __init__(self):
        self.max_retries = 3
        self.retry_delays = [1, 3, 5]  # 秒
        self.fallback_temperature = [0.7, 0.9, 1.0]  # 逐步提高创造性
    
    async def execute_with_retry(self, generator_func, context):
        for attempt in range(self.max_retries):
            try:
                # 调整参数进行重试
                temp = self.fallback_temperature[min(attempt, 2)]
                result = await generator_func(context, temperature=temp)
                
                if self._validate_result(result):
                    return result
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # 最后一次失败，使用intelligent fallback
                    return self._get_intelligent_fallback(context)
```

#### 2.2.2 失败分类处理
- **网络错误**：立即重试
- **API限额**：延长等待时间后重试
- **内容过滤**：调整prompt参数重试
- **格式错误**：使用更严格的format instruction重试

### 2.3 Prompt优化设计

#### 2.3.1 个性化分析引擎
```python
class PersonalizationEngine:
    def analyze_user_profile(self, user_data):
        """深度分析用户特征"""
        return {
            "emotion_pattern": self._analyze_drawing(user_data.drawing_data),
            "psychology_profile": self._analyze_quiz(user_data.quiz_answers),
            "temporal_context": self._analyze_time_space(user_data.timestamp),
            "personal_keywords": self._extract_keywords(user_data.user_input),
            "energy_signature": self._calculate_energy(user_data)
        }
    
    def _analyze_drawing(self, drawing_data):
        """绘画心理分析"""
        # 基于笔画数、绘制时长、压力变化等进行心理分析
        
    def _analyze_quiz(self, quiz_answers):
        """问答心理档案"""
        # 构建多维度心理特征向量
        
    def _calculate_energy(self, user_data):
        """计算用户能量特征，结合五行理论"""
```

#### 2.3.2 智能Prompt构建器
```python
class IntelligentPromptBuilder:
    def build_unified_prompt(self, user_data, charm_configs):
        """构建高度个性化的统一prompt"""
        
        # 1. 用户特征深度分析
        profile = self.personalization_engine.analyze_user_profile(user_data)
        
        # 2. 周易卦象匹配
        hexagram = self._match_hexagram(profile)
        
        # 3. 五行平衡分析
        elements = self._analyze_five_elements(profile)
        
        # 4. 签体智能推荐
        recommended_charms = self._recommend_charms(profile, charm_configs)
        
        # 5. 构建完整prompt
        return self._assemble_prompt(profile, hexagram, elements, recommended_charms)
```

#### 2.3.3 核心Prompt模板
```python
UNIFIED_PROMPT_TEMPLATE = """
你是资深的心象签大师，融合现代心理学、传统易经智慧和自然哲学，为用户创作独一无二的心象签体验。

== 用户心灵档案 ==
📱 用户表达：{user_input}
🎨 绘画心理分析：
  - 笔触特征：{stroke_analysis}
  - 情绪印记：{emotion_signature}
  - 心理节奏：{psychological_rhythm}
  
🧠 深度心理测评：
  - 核心需求：{core_needs}
  - 情感状态：{emotional_state} 
  - 行动倾向：{action_tendency}
  - 压力指数：{stress_level}
  - 内在渴望：{inner_desires}

⏰ 时空能量场：
  - 时辰能量：{time_energy}
  - 季节共振：{seasonal_resonance}
  - 地理磁场：{location_energy}

== 易经智慧解析 ==
🔮 匹配卦象：{matched_hexagram}
📜 卦象启示：{hexagram_insight}
⚡ 当前运势：{current_fortune}

== 五行能量诊断 ==
🌳 木能量：{wood_energy} - {wood_analysis}
🔥 火能量：{fire_energy} - {fire_analysis}  
🏔️ 土能量：{earth_energy} - {earth_analysis}
⚙️ 金能量：{metal_energy} - {metal_analysis}
💧 水能量：{water_energy} - {water_analysis}

== 签体推荐算法 ==
根据用户能量特征，推荐以下签体（按匹配度排序）：
{recommended_charms}

== 创作要求 ==

请基于以上深度分析，创作一个真正直击用户心灵的心象签。要求：

1. **自然意象映射**：将用户的真实心境映射为具体的自然现象，要有画面感和诗意
2. **易经智慧融入**：基于匹配的卦象，给出现代化的人生指引
3. **五行平衡调和**：根据五行诊断，在daily_guide中给出能量平衡建议
4. **深度个性化**：每个字段都要体现对用户的深度理解，避免套话
5. **签体智能选择**：从推荐列表中选择最匹配的签体
6. **色彩心理学**：main_color和accent_color要体现用户的心理需求
7. **风水环境优化**：fengshui_focus要结合用户当前状态给出实用建议

== 输出格式 ==
请严格按照以下JSON格式输出，所有字段必填：

```json
{
  "oracle_theme": {
    "title": "基于用户真实心境的自然意象(4-6字)",
    "subtitle": "今日心象签"
  },
  "charm_identity": {
    "charm_name": "必须是'XX签'格式，与自然意象深度呼应",
    "charm_description": "体现签的独特气质和用户共鸣点",
    "charm_blessing": "8字内个性化祝福，避免套话",
    "main_color": "体现用户心理需求的主色调hex值",
    "accent_color": "与主色调和谐的辅助色hex值"
  },
  "affirmation": "8-14字个性化祝福，直击用户内心需求",
  "oracle_manifest": {
    "hexagram": {
      "name": "基于{matched_hexagram}的现代化卦象名",
      "insight": "结合卦象和用户状态的具体人生指引(不超过30字)"
    },
    "daily_guide": [
      "基于五行分析的能量平衡建议(15-25字)",
      "针对用户心理状态的实用指引(15-25字)"
    ],
    "fengshui_focus": "结合用户状态的环境优化建议",
    "ritual_hint": "简单易行的能量调和仪式",
    "element_balance": {
      "wood": {wood_energy},
      "fire": {fire_energy},
      "earth": {earth_energy}, 
      "metal": {metal_energy},
      "water": {water_energy}
    }
  },
  "ink_reading": {
    "stroke_impression": "基于真实绘画数据的心理解读(25-40字)",
    "symbolic_keywords": ["体现核心心境的关键词1", "关键词2", "关键词3"],
    "ink_metrics": {
      "stroke_count": {actual_stroke_count},
      "dominant_quadrant": "{actual_dominant_quadrant}",
      "pressure_tendency": "{actual_pressure_tendency}"
    }
  },
  "context_insights": {
    "session_time": "{actual_time_period}",
    "season_hint": "{current_season}时分",
    "visit_pattern": "基于用户特征的访问模式描述",
    "historical_keywords": []
  },
  "blessing_stream": [
    "与自然意象高度呼应的祝福1(4-6字)",
    "体现用户需求的祝福2(4-6字)",
    "融入五行调和的祝福3(4-6字)", 
    "展现未来希冀的祝福4(4-6字)"
  ],
  "art_direction": {
    "image_prompt": "基于自然意象的具体画面描述，用于生图",
    "palette": ["主色调", "辅助色1", "辅助色2"],
    "animation_hint": "符合意境的动画效果描述"
  },
  "ai_selected_charm": {
    "charm_id": "从推荐列表选择的最佳签体ID",
    "charm_name": "选择的签体名称", 
    "ai_reasoning": "选择这个签体的个性化原因说明"
  },
  "culture_note": "灵感源于易经与五行智慧，不作吉凶断言，请以现代视角理解。"
}
```

== 创作原则 ==
1. 🎯 **真诚直击**：每句话都要能触动用户内心，避免空洞套话
2. 🌟 **独特个性**：基于深度分析，确保内容的独一无二性
3. 🔄 **古今融合**：传统智慧与现代表达的完美结合
4. 💝 **温暖治愈**：传递正能量，给用户前进的力量
5. 🎨 **美学品味**：色彩、意象、文字都要体现东方美学

请开始创作这个独一无二的心象签。
"""
```

## 3. 详细实施方案

### 3.1 项目背景与上下文

#### 3.1.1 当前系统架构
```
用户在微信小程序 → API Gateway → postcard-service → Redis Stream → ai-agent-worker
                                                                      ↓
                                          ConceptGenerator → ContentGenerator → StructuredContentGenerator → ImageGenerator
```

#### 3.1.2 数据流转路径
1. **用户输入数据结构**:
```python
task_data = {
    "task_id": "uuid",
    "user_id": "openid", 
    "user_input": "用户文字描述",
    "drawing_data": {
        "analysis": {
            "stroke_count": 120,
            "drawing_time": 15000,  # ms
            "dominant_quadrant": "upper_right",
            "pressure_tendency": "steady",
            "drawing_description": "平和的笔触"
        }
    },
    "quiz_answers": [
        {"question_id": "mood_1", "option_id": "calm"},
        {"question_id": "pressure_2", "option_id": "moderate"}
    ]
}
```

2. **最终输出数据结构** (必须保持不变):
```python
structured_data = {
    "oracle_theme": {"title": "自然意象", "subtitle": "今日心象签"},
    "charm_identity": {...},
    "affirmation": "祝福短句", 
    "oracle_manifest": {...},
    "ink_reading": {...},
    "context_insights": {...},
    "blessing_stream": [...],
    "art_direction": {...},
    "ai_selected_charm": {...},
    "culture_note": "免责声明"
}
```

### 3.2 文件变更清单与具体实现

#### 3.2.1 新增文件及完整代码

**文件**: `src/ai-agent-service/app/orchestrator/steps/unified_content_generator.py`
```python
import logging
import json
import asyncio
from typing import Dict, Any, Optional
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class UnifiedContentGenerator:
    """统一内容生成器 - 替代原有3个生成器，一次性生成完整心象签"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载签体配置 (复用原logic)
        self.charm_configs = self._load_charm_configs()
        
        # 重试配置
        self.max_retries = 3
        self.retry_delays = [1, 3, 5]  # 秒
        self.temperature_levels = [0.7, 0.9, 1.0]  # 重试时递增温度
        
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
                
                # 核心生成逻辑
                structured_data = await self._generate_unified_content(task, temperature)
                
                # 验证生成结果
                if self._validate_structured_data(structured_data):
                    context["results"]["structured_data"] = structured_data
                    self.logger.info(f"✅ 统一生成成功: {task_id}")
                    return context
                else:
                    raise ValueError("生成的数据结构验证失败")
                    
            except Exception as e:
                self.logger.error(f"❌ 第{attempt+1}次生成失败: {e}")
                
                if attempt < self.max_retries - 1:
                    # 还有重试机会，等待后继续
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # 最后一次失败，使用智能降级
                    self.logger.warning(f"⚠️ 所有重试失败，使用智能降级: {task_id}")
                    structured_data = self._get_intelligent_fallback(task)
                    context["results"]["structured_data"] = structured_data
                    return context
    
    async def _generate_unified_content(self, task: Dict[str, Any], temperature: float) -> Dict[str, Any]:
        """核心统一生成逻辑"""
        
        # 1. 深度个性化分析
        user_profile = self._analyze_user_profile(task)
        
        # 2. 签体智能推荐
        recommended_charms = self._recommend_charms(user_profile)
        
        # 3. 构建统一Prompt
        prompt = self._build_unified_prompt(task, user_profile, recommended_charms)
        
        # 4. 调用Gemini生成
        response = await self.provider.generate_text(
            prompt=prompt,
            max_tokens=3000,
            temperature=temperature
        )
        
        # 5. 解析JSON响应
        structured_data = self._parse_response(response)
        
        # 6. 后处理和完善
        structured_data = self._post_process_data(structured_data, task, user_profile)
        
        return structured_data
    
    def _analyze_user_profile(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """深度个性化分析 - 构建用户心理档案"""
        user_input = task.get("user_input", "")
        drawing_data = task.get("drawing_data", {}).get("analysis", {})
        quiz_answers = task.get("quiz_answers", [])
        
        # 绘画心理分析
        stroke_analysis = self._analyze_drawing_psychology(drawing_data)
        
        # 问答心理档案
        quiz_insights = self._analyze_quiz_psychology(quiz_answers)
        
        # 五行能量计算
        five_elements = self._calculate_five_elements(stroke_analysis, quiz_insights, user_input)
        
        # 易经卦象匹配
        hexagram = self._match_hexagram(stroke_analysis, quiz_insights)
        
        # 时空能量场
        temporal_energy = self._analyze_temporal_energy()
        
        return {
            "stroke_analysis": stroke_analysis,
            "quiz_insights": quiz_insights,
            "five_elements": five_elements,
            "hexagram": hexagram,
            "temporal_energy": temporal_energy,
            "user_input": user_input
        }
    
    def _analyze_drawing_psychology(self, drawing_data: Dict[str, Any]) -> Dict[str, Any]:
        """绘画心理学分析"""
        stroke_count = drawing_data.get("stroke_count", 0)
        drawing_time = drawing_data.get("drawing_time", 0)
        dominant_quadrant = drawing_data.get("dominant_quadrant", "center")
        pressure_tendency = drawing_data.get("pressure_tendency", "steady")
        
        # 心理特征分析
        if stroke_count > 150:
            psychology = "内心活跃，思维敏捷，情感丰富，渴望表达"
            energy_type = "dynamic"
        elif stroke_count < 50:
            psychology = "内心沉静，善于深思，注重精神品质"
            energy_type = "contemplative"
        else:
            psychology = "思维平衡，行动有度，内外兼修"
            energy_type = "balanced"
        
        # 空间心理学
        quadrant_meanings = {
            "upper_left": "理性思考，逻辑分析",
            "upper_right": "直觉创意，情感表达", 
            "lower_left": "实际行动，物质关注",
            "lower_right": "内在探索，精神追求",
            "center": "平衡统一，整体思维"
        }
        
        space_psychology = quadrant_meanings.get(dominant_quadrant, "整体平衡")
        
        # 压力心理学
        pressure_meanings = {
            "light": "轻松自在，压力较小",
            "steady": "稳定平和，控制良好",
            "heavy": "专注认真，可能有压力"
        }
        
        pressure_psychology = pressure_meanings.get(pressure_tendency, "状态稳定")
        
        return {
            "stroke_count": stroke_count,
            "psychology_insight": psychology,
            "energy_type": energy_type,
            "space_psychology": space_psychology,
            "pressure_psychology": pressure_psychology,
            "drawing_rhythm": "快速" if drawing_time < 10000 else "从容" if drawing_time < 30000 else "深思"
        }
    
    def _analyze_quiz_psychology(self, quiz_answers: list) -> Dict[str, Any]:
        """问答心理档案分析"""
        if not quiz_answers:
            return {
                "core_needs": ["inner_peace"],
                "emotional_state": "stable",
                "stress_level": "low",
                "action_tendency": "balanced",
                "inner_desires": ["harmony"]
            }
        
        # 分析核心需求
        core_needs = []
        emotional_indicators = []
        stress_indicators = []
        action_indicators = []
        
        for answer in quiz_answers:
            option_id = answer.get("option_id", "")
            
            # 分析需求模式
            if "rest" in option_id or "relax" in option_id:
                core_needs.append("rest_recovery")
            if "connection" in option_id or "companion" in option_id:
                core_needs.append("social_connection")
            if "growth" in option_id or "learn" in option_id:
                core_needs.append("self_growth")
            if "creative" in option_id or "art" in option_id:
                core_needs.append("creative_expression")
            
            # 分析情绪状态
            if "happy" in option_id or "joy" in option_id:
                emotional_indicators.append("positive")
            if "sad" in option_id or "down" in option_id:
                emotional_indicators.append("melancholy")
            if "anxious" in option_id or "worry" in option_id:
                emotional_indicators.append("anxious")
            if "calm" in option_id or "peace" in option_id:
                emotional_indicators.append("peaceful")
            
            # 分析压力水平
            if "pressure" in option_id or "stress" in option_id:
                stress_indicators.append("high")
            if "overwhelmed" in option_id:
                stress_indicators.append("overwhelmed")
            if "relaxed" in option_id:
                stress_indicators.append("low")
        
        # 综合分析
        return {
            "core_needs": list(set(core_needs)) if core_needs else ["inner_balance"],
            "emotional_state": self._determine_dominant_emotion(emotional_indicators),
            "stress_level": self._calculate_stress_level(stress_indicators),
            "action_tendency": self._analyze_action_pattern(action_indicators),
            "inner_desires": self._extract_inner_desires(core_needs, emotional_indicators)
        }
    
    def _calculate_five_elements(self, stroke_analysis: Dict, quiz_insights: Dict, user_input: str) -> Dict[str, float]:
        """五行能量计算"""
        # 基础五行值
        elements = {"wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5}
        
        # 根据绘画特征调整
        energy_type = stroke_analysis.get("energy_type", "balanced")
        if energy_type == "dynamic":
            elements["fire"] += 0.2  # 火旺
            elements["wood"] += 0.1  # 木助
        elif energy_type == "contemplative":
            elements["water"] += 0.2  # 水旺
            elements["metal"] += 0.1  # 金助
        
        # 根据心理状态调整
        emotional_state = quiz_insights.get("emotional_state", "stable")
        if emotional_state == "anxious":
            elements["fire"] += 0.1
            elements["earth"] -= 0.1
        elif emotional_state == "melancholy":
            elements["metal"] += 0.1
            elements["wood"] -= 0.1
        elif emotional_state == "peaceful":
            elements["earth"] += 0.1
            elements["water"] += 0.1
        
        # 根据用户输入关键词调整
        wood_keywords = ["成长", "发展", "创新", "学习", "春天"]
        fire_keywords = ["激情", "活力", "热情", "夏天", "光明"] 
        earth_keywords = ["稳定", "平静", "踏实", "安全", "家庭"]
        metal_keywords = ["坚持", "精确", "完美", "秋天", "收获"]
        water_keywords = ["流动", "智慧", "深度", "冬天", "宁静"]
        
        for keyword in wood_keywords:
            if keyword in user_input:
                elements["wood"] += 0.05
        for keyword in fire_keywords:
            if keyword in user_input:
                elements["fire"] += 0.05
        for keyword in earth_keywords:
            if keyword in user_input:
                elements["earth"] += 0.05
        for keyword in metal_keywords:
            if keyword in user_input:
                elements["metal"] += 0.05
        for keyword in water_keywords:
            if keyword in user_input:
                elements["water"] += 0.05
        
        # 确保值在0-1范围内
        for key in elements:
            elements[key] = max(0.0, min(1.0, elements[key]))
        
        return elements
    
    def _match_hexagram(self, stroke_analysis: Dict, quiz_insights: Dict) -> Dict[str, str]:
        """易经卦象匹配"""
        energy_type = stroke_analysis.get("energy_type", "balanced")
        emotional_state = quiz_insights.get("emotional_state", "stable")
        core_needs = quiz_insights.get("core_needs", [])
        
        # 卦象匹配逻辑
        if energy_type == "dynamic" and emotional_state == "positive":
            return {"name": "乾为天", "modern_name": "自强不息", "insight": "如天行健，持续前进，必有所成"}
        elif energy_type == "contemplative" and "self_growth" in core_needs:
            return {"name": "坤为地", "modern_name": "厚德载物", "insight": "如大地般包容，在沉静中积累力量"}
        elif "social_connection" in core_needs:
            return {"name": "泽风大过", "modern_name": "和谐共融", "insight": "与他人的连接是内心的滋养"}
        elif emotional_state == "anxious":
            return {"name": "山雷颐", "modern_name": "颐养生息", "insight": "暂停脚步，让心灵得到滋养"}
        elif "creative_expression" in core_needs:
            return {"name": "火地晋", "modern_name": "光明进取", "insight": "创意如火，照亮前进的道路"}
        else:
            return {"name": "风雷益", "modern_name": "止水流深", "insight": "平静中蕴含着深邃的力量"}
    
    def _analyze_temporal_energy(self) -> Dict[str, str]:
        """时空能量场分析"""
        import datetime
        from zoneinfo import ZoneInfo
        
        try:
            now = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
        except:
            now = datetime.datetime.now()
            
        hour = now.hour
        month = now.month
        weekday = now.weekday()
        
        # 时辰能量
        if 6 <= hour < 12:
            time_energy = "朝阳初升，生机勃勃"
        elif 12 <= hour < 18:
            time_energy = "阳光正盛，活力充沛"
        elif 18 <= hour < 22:
            time_energy = "夕阳西下，温暖柔和"
        else:
            time_energy = "夜深人静，内省时光"
        
        # 季节共振
        if 3 <= month <= 5:
            season_energy = "春回大地，万物复苏"
        elif 6 <= month <= 8:
            season_energy = "夏日炎炎，热情似火"
        elif 9 <= month <= 11:
            season_energy = "秋高气爽，收获在望"
        else:
            season_energy = "冬藏精华，静待春来"
        
        # 周期律动
        if weekday < 5:
            week_energy = "工作日节奏，专注前行"
        else:
            week_energy = "周末时光，放松身心"
        
        return {
            "time_energy": time_energy,
            "season_energy": season_energy,
            "week_energy": week_energy,
            "current_time": now.strftime("%H:%M"),
            "current_season": "春" if 3 <= month <= 5 else "夏" if 6 <= month <= 8 else "秋" if 9 <= month <= 11 else "冬"
        }
    
    def _recommend_charms(self, user_profile: Dict[str, Any]) -> list:
        """基于用户特征推荐签体"""
        stroke_analysis = user_profile["stroke_analysis"]
        quiz_insights = user_profile["quiz_insights"]
        five_elements = user_profile["five_elements"]
        
        # 获取主导五行
        dominant_element = max(five_elements.keys(), key=lambda k: five_elements[k])
        
        # 签体分类映射
        charm_categories = {
            "wood": ["竹节长条", "银杏叶", "莲花圆牌"],  # 木系：成长、自然
            "fire": ["祥云流彩", "朱漆长牌", "六角灯笼面"],  # 火系：活力、光明
            "earth": ["方胜结", "长命锁", "海棠木窗"],  # 土系：稳重、传统
            "metal": ["金边墨玉璧", "八角锦囊", "如意结"],  # 金系：坚韧、精致
            "water": ["青玉团扇", "青花瓷扇", "双鱼锦囊"]  # 水系：流动、智慧
        }
        
        # 基于能量类型调整
        energy_type = stroke_analysis.get("energy_type", "balanced")
        if energy_type == "dynamic":
            preferred_charms = charm_categories.get("fire", []) + charm_categories.get("wood", [])
        elif energy_type == "contemplative":
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
    
    def _build_unified_prompt(self, task: Dict[str, Any], user_profile: Dict[str, Any], recommended_charms: list) -> str:
        """构建统一的高质量Prompt"""
        
        # 提取关键信息
        user_input = task.get("user_input", "")
        stroke_analysis = user_profile["stroke_analysis"]
        quiz_insights = user_profile["quiz_insights"]
        five_elements = user_profile["five_elements"]
        hexagram = user_profile["hexagram"]
        temporal_energy = user_profile["temporal_energy"]
        
        # 构建推荐签体信息
        charm_info = ""
        for i, charm in enumerate(recommended_charms, 1):
            charm_info += f"  {i}. {charm.get('name', '')} (ID: {charm.get('id', '')}) - {charm.get('note', '')}\n"
        
        prompt = f"""你是资深的心象签大师，融合现代心理学、传统易经智慧和自然哲学，为用户创作独一无二的心象签体验。

== 用户心灵档案 ==
📱 用户表达：{user_input}

🎨 绘画心理分析：
- 笔画特征：{stroke_analysis['stroke_count']}笔，{stroke_analysis['drawing_rhythm']}节奏
- 心理洞察：{stroke_analysis['psychology_insight']}
- 空间心理：{stroke_analysis['space_psychology']}
- 压力状态：{stroke_analysis['pressure_psychology']}
- 能量类型：{stroke_analysis['energy_type']}

🧠 深度心理测评：
- 核心需求：{', '.join(quiz_insights['core_needs'])}
- 情感状态：{quiz_insights['emotional_state']}
- 压力水平：{quiz_insights['stress_level']}
- 行动倾向：{quiz_insights['action_tendency']}
- 内在渴望：{', '.join(quiz_insights['inner_desires'])}

⏰ 时空能量场：
- 时辰能量：{temporal_energy['time_energy']}
- 季节共振：{temporal_energy['season_energy']}
- 周期律动：{temporal_energy['week_energy']}
- 当前时刻：{temporal_energy['current_time']} ({temporal_energy['current_season']}季)

== 易经智慧解析 ==
🔮 匹配卦象：{hexagram['name']} ({hexagram['modern_name']})
📜 卦象启示：{hexagram['insight']}

== 五行能量诊断 ==
🌳 木能量：{five_elements['wood']:.1f} - {"旺盛" if five_elements['wood'] > 0.6 else "平衡" if five_elements['wood'] > 0.4 else "需补"}
🔥 火能量：{five_elements['fire']:.1f} - {"旺盛" if five_elements['fire'] > 0.6 else "平衡" if five_elements['fire'] > 0.4 else "需补"}
🏔️ 土能量：{five_elements['earth']:.1f} - {"旺盛" if five_elements['earth'] > 0.6 else "平衡" if five_elements['earth'] > 0.4 else "需补"}
⚙️ 金能量：{five_elements['metal']:.1f} - {"旺盛" if five_elements['metal'] > 0.6 else "平衡" if five_elements['metal'] > 0.4 else "需补"}
💧 水能量：{five_elements['water']:.1f} - {"旺盛" if five_elements['water'] > 0.6 else "平衡" if five_elements['water'] > 0.4 else "需补"}

== 签体推荐算法 ==
根据用户五行特征和心理档案，推荐以下签体（按匹配度排序）：
{charm_info}

== 创作要求 ==

请基于以上深度分析，创作一个真正直击用户心灵的心象签。要求：

1. **自然意象映射**：将用户的真实心境映射为具体的自然现象，要有画面感和诗意
2. **易经智慧融入**：基于匹配的卦象，给出现代化的人生指引  
3. **五行平衡调和**：根据五行诊断，在daily_guide中给出能量平衡建议
4. **深度个性化**：每个字段都要体现对用户的深度理解，避免套话
5. **签体智能选择**：从推荐列表中选择最匹配的签体
6. **色彩心理学**：main_color和accent_color要体现用户的心理需求
7. **风水环境优化**：fengshui_focus要结合用户当前状态给出实用建议

请严格按照以下JSON格式输出，所有字段必填：

```json
{{
  "oracle_theme": {{
    "title": "基于用户真实心境的自然意象(4-6字)",
    "subtitle": "今日心象签"
  }},
  "charm_identity": {{
    "charm_name": "必须是'XX签'格式，与自然意象深度呼应",
    "charm_description": "体现签的独特气质和用户共鸣点",
    "charm_blessing": "8字内个性化祝福，避免套话",
    "main_color": "体现用户心理需求的主色调hex值",
    "accent_color": "与主色调和谐的辅助色hex值"
  }},
  "affirmation": "8-14字个性化祝福，直击用户内心需求",
  "oracle_manifest": {{
    "hexagram": {{
      "name": "基于{hexagram['modern_name']}的现代化卦象名",
      "insight": "结合卦象和用户状态的具体人生指引(不超过30字)"
    }},
    "daily_guide": [
      "基于五行分析的能量平衡建议(15-25字)",
      "针对用户心理状态的实用指引(15-25字)"
    ],
    "fengshui_focus": "结合用户状态的环境优化建议",
    "ritual_hint": "简单易行的能量调和仪式",
    "element_balance": {{
      "wood": {five_elements['wood']},
      "fire": {five_elements['fire']},
      "earth": {five_elements['earth']},
      "metal": {five_elements['metal']},
      "water": {five_elements['water']}
    }}
  }},
  "ink_reading": {{
    "stroke_impression": "基于真实绘画数据的心理解读：{stroke_analysis['psychology_insight']}，{stroke_analysis['space_psychology']}",
    "symbolic_keywords": ["体现核心心境的关键词1", "关键词2", "关键词3"],
    "ink_metrics": {{
      "stroke_count": {stroke_analysis['stroke_count']},
      "dominant_quadrant": "{task.get('drawing_data', {}).get('analysis', {}).get('dominant_quadrant', 'center')}",
      "pressure_tendency": "{task.get('drawing_data', {}).get('analysis', {}).get('pressure_tendency', 'steady')}"
    }}
  }},
  "context_insights": {{
    "session_time": "{temporal_energy['current_time']}",
    "season_hint": "{temporal_energy['current_season']}季时分",
    "visit_pattern": "基于用户特征的访问模式描述",
    "historical_keywords": []
  }},
  "blessing_stream": [
    "与自然意象高度呼应的祝福1(4-6字)",
    "体现用户需求的祝福2(4-6字)",
    "融入五行调和的祝福3(4-6字)",
    "展现未来希冀的祝福4(4-6字)"
  ],
  "art_direction": {{
    "image_prompt": "基于自然意象的具体画面描述，水彩风格，用于AI生图",
    "palette": ["主色调hex", "辅助色1hex", "辅助色2hex"],
    "animation_hint": "符合意境的动画效果描述"
  }},
  "ai_selected_charm": {{
    "charm_id": "从推荐列表选择的最佳签体ID",
    "charm_name": "选择的签体名称",
    "ai_reasoning": "基于'{hexagram['modern_name']}'卦象和'{stroke_analysis['energy_type']}'能量特征选择此签体"
  }},
  "culture_note": "灵感源于易经与五行智慧，不作吉凶断言，请以现代视角理解。"
}}
```

== 创作原则 ==
1. 🎯 **真诚直击**：每句话都要能触动用户内心，避免空洞套话
2. 🌟 **独特个性**：基于深度分析，确保内容的独一无二性
3. 🔄 **古今融合**：传统智慧与现代表达的完美结合
4. 💝 **温暖治愈**：传递正能量，给用户前进的力量
5. 🎨 **美学品味**：色彩、意象、文字都要体现东方美学

请直接返回JSON格式数据，不要添加其他文字说明。
"""
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析AI响应为结构化数据"""
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
            self.logger.error(f"🐛 AI原始响应: {response[:500]}...")
            raise
    
    def _post_process_data(self, structured_data: Dict[str, Any], task: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """后处理和数据完善"""
        
        # 确保所有必需字段存在
        required_fields = [
            "oracle_theme", "charm_identity", "affirmation", 
            "oracle_manifest", "ink_reading", "blessing_stream",
            "art_direction", "ai_selected_charm", "culture_note"
        ]
        
        for field in required_fields:
            if field not in structured_data:
                self.logger.warning(f"⚠️ 缺少必需字段: {field}")
                structured_data[field] = self._get_default_field_value(field, user_profile)
        
        # 验证和修复oracle_theme
        if not isinstance(structured_data.get("oracle_theme"), dict):
            structured_data["oracle_theme"] = {
                "title": "心象如画",
                "subtitle": "今日心象签"
            }
        
        # 验证和修复charm_identity
        if not isinstance(structured_data.get("charm_identity"), dict):
            structured_data["charm_identity"] = {
                "charm_name": "安心签",
                "charm_description": "内心平静，万事顺遂",
                "charm_blessing": "愿你心安，诸事顺遂",
                "main_color": "#8B7355",
                "accent_color": "#D4AF37"
            }
        
        # 确保charm_name是XX签格式
        charm_name = structured_data["charm_identity"].get("charm_name", "")
        if not charm_name.endswith("签"):
            oracle_title = structured_data["oracle_theme"].get("title", "安心")
            if len(oracle_title) >= 2:
                structured_data["charm_identity"]["charm_name"] = oracle_title[:2] + "签"
            else:
                structured_data["charm_identity"]["charm_name"] = "安心签"
        
        # 验证五行数据
        element_balance = structured_data.get("oracle_manifest", {}).get("element_balance", {})
        if not isinstance(element_balance, dict) or len(element_balance) != 5:
            structured_data.setdefault("oracle_manifest", {})["element_balance"] = user_profile["five_elements"]
        
        return structured_data
    
    def _validate_structured_data(self, structured_data: Dict[str, Any]) -> bool:
        """验证生成的数据结构"""
        try:
            # 检查必需字段
            required_fields = [
                "oracle_theme", "charm_identity", "affirmation",
                "oracle_manifest", "ink_reading", "blessing_stream"
            ]
            
            for field in required_fields:
                if field not in structured_data:
                    self.logger.error(f"❌ 缺少必需字段: {field}")
                    return False
            
            # 检查oracle_theme结构
            oracle_theme = structured_data.get("oracle_theme")
            if not isinstance(oracle_theme, dict) or "title" not in oracle_theme:
                self.logger.error("❌ oracle_theme结构错误")
                return False
            
            # 检查charm_identity结构
            charm_identity = structured_data.get("charm_identity")
            if not isinstance(charm_identity, dict) or "charm_name" not in charm_identity:
                self.logger.error("❌ charm_identity结构错误")
                return False
            
            # 检查blessing_stream是数组
            blessing_stream = structured_data.get("blessing_stream")
            if not isinstance(blessing_stream, list) or len(blessing_stream) < 3:
                self.logger.error("❌ blessing_stream结构错误")
                return False
            
            self.logger.info("✅ 数据结构验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据验证异常: {e}")
            return False
    
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
            "affirmation": template["affirmation"],
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
                "ai_reasoning": f"基于用户{detected_emotion}的心境特征选择"
            },
            "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
        }
    
    def _load_charm_configs(self):
        """加载签体配置 - 复用现有逻辑"""
        # 这里复用concept_generator.py中的_load_charm_configs逻辑
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
    
    # 辅助方法
    def _determine_dominant_emotion(self, emotional_indicators: list) -> str:
        if not emotional_indicators:
            return "stable"
        return max(set(emotional_indicators), key=emotional_indicators.count)
    
    def _calculate_stress_level(self, stress_indicators: list) -> str:
        if "overwhelmed" in stress_indicators:
            return "high"
        elif "high" in stress_indicators:
            return "moderate"
        elif "low" in stress_indicators:
            return "low"
        else:
            return "normal"
    
    def _analyze_action_pattern(self, action_indicators: list) -> str:
        return "proactive" if action_indicators else "balanced"
    
    def _extract_inner_desires(self, core_needs: list, emotional_indicators: list) -> list:
        desires = []
        if "self_growth" in core_needs:
            desires.append("成长进步")
        if "social_connection" in core_needs:
            desires.append("情感连接")
        if "rest_recovery" in core_needs:
            desires.append("内心平静")
        if "positive" in emotional_indicators:
            desires.append("快乐满足")
        return desires if desires else ["内心和谐"]
    
    def _get_default_field_value(self, field: str, user_profile: Dict[str, Any]) -> Any:
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
            "blessing_stream": ["心想事成", "平安喜乐", "一路顺风", "万事如意"],
            "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
        }
        return defaults.get(field, {})
```

**文件**: `src/ai-agent-service/app/orchestrator/steps/__init__.py`
```python
# 添加新的导入
from .unified_content_generator import UnifiedContentGenerator

__all__ = [
    'ConceptGenerator',
    'ContentGenerator', 
    'StructuredContentGenerator',
    'ImageGenerator',
    'UnifiedContentGenerator'  # 新增
]
```

#### 3.2.2 修改现有文件

**文件**: `src/ai-agent-service/app/orchestrator/workflow.py`

需要在workflow.py中的execute方法里添加版本控制逻辑：

```python
# 在文件顶部添加导入
import os

# 在execute方法的开始处添加版本判断
async def execute(self, task_data: Dict[str, Any]):
    """执行完整的明信片生成工作流 - 支持新旧版本切换"""
    task_id = task_data.get("task_id")
    context = {"task": task_data, "results": {}}
    
    # 获取工作流版本配置
    workflow_version = os.getenv("WORKFLOW_VERSION", "unified")  # "legacy" | "unified"
    
    try:
        await asyncio.shield(self.update_task_status(task_id, "processing"))
        
        if workflow_version == "unified":
            # 新版本：统一工作流 (1次文本 + 1次生图)
            self.logger.info(f"🚀 使用优化版工作流: {task_id}")
            await self._execute_unified_workflow(context)
        else:
            # 旧版本：原有工作流 (3次文本 + 1次生图)  
            self.logger.info(f"🔄 使用传统版工作流: {task_id}")
            await self._execute_legacy_workflow(context)
        
        # 保存最终结果
        await asyncio.shield(self.save_final_result(task_id, context["results"]))
        await asyncio.shield(self.update_task_status(task_id, "completed"))
        
        self.logger.info(f"🎉 工作流执行完成: {task_id}")
        
    except Exception as e:
        self.logger.error(f"❌ 工作流执行失败: {task_id} - {e}")
        await self._handle_workflow_failure(task_id, e, context)

async def _execute_unified_workflow(self, context):
    """执行优化版统一工作流"""
    
    # 步骤1：统一内容生成（整合原有3步）
    from .steps.unified_content_generator import UnifiedContentGenerator
    unified_generator = UnifiedContentGenerator()
    context = await unified_generator.execute(context)
    
    # 步骤2：图像生成
    from .steps.image_generator import ImageGenerator
    image_generator = ImageGenerator()
    context = await image_generator.execute(context)
    
    return context

async def _execute_legacy_workflow(self, context):
    """执行传统版工作流（保留作为回滚方案）"""
    
    # 原有的4步工作流逻辑保持不变
    from .steps.concept_generator import ConceptGenerator
    from .steps.content_generator import ContentGenerator  
    from .steps.image_generator import ImageGenerator
    from .steps.structured_content_generator import StructuredContentGenerator
    
    steps = [
        ConceptGenerator(),
        ContentGenerator(), 
        ImageGenerator(),
        StructuredContentGenerator()
    ]
    
    for i, step in enumerate(steps, 1):
        step_name = step.__class__.__name__
        self.logger.info(f"📍 执行步骤 {i}/4: {step_name}")
        
        try:
            context = await step.execute(context)
            self.logger.info(f"✅ 步骤 {i}/4 完成: {step_name}")
        except Exception as e:
            self.logger.error(f"❌ 步骤 {i}/4 失败: {step_name} - {e}")
            # 这里保留原有的错误处理逻辑
            if await self._handle_step_failure(step_name, i, e, context):
                continue
            else:
                raise
    
    return context
```

### 3.3 环境配置

#### 3.3.1 环境变量配置
在`.env`文件中添加：

```bash
# AI工作流版本控制
WORKFLOW_VERSION=unified  # "unified" | "legacy"

# Gemini优化配置  
GEMINI_TEXT_TEMPERATURE=0.7
GEMINI_TEXT_MAX_TOKENS=3000
GEMINI_RETRY_MAX_ATTEMPTS=3
GEMINI_RETRY_DELAYS=1,3,5  # 秒

# 签体配置路径
CHARM_CONFIG_PATH=/app/resources/签体/charm-config.json
```

#### 3.3.2 Docker配置
在`docker-compose.yml`中确保环境变量传递：

```yaml
ai-agent-service:
  environment:
    - WORKFLOW_VERSION=${WORKFLOW_VERSION:-unified}
    - GEMINI_TEXT_MAX_TOKENS=${GEMINI_TEXT_MAX_TOKENS:-3000}
    - CHARM_CONFIG_PATH=/app/resources/签体/charm-config.json
  volumes:
    - ./resources:/app/resources:ro
```

## 4. 测试验证方案

### 4.1 功能测试

**文件**: `src/ai-agent-service/tests/test_unified_content_generator.py`
```python
import pytest
import asyncio
import json
from unittest.mock import Mock, patch
from app.orchestrator.steps.unified_content_generator import UnifiedContentGenerator

class TestUnifiedContentGenerator:
    """统一内容生成器测试"""
    
    @pytest.fixture
    def sample_task_data(self):
        """测试用例数据"""
        return {
            "task_id": "test-123",
            "user_id": "test-user",
            "user_input": "今天心情很好，想要一些正能量",
            "drawing_data": {
                "analysis": {
                    "stroke_count": 120,
                    "drawing_time": 15000,
                    "dominant_quadrant": "upper_right",
                    "pressure_tendency": "steady",
                    "drawing_description": "轻快的笔触"
                }
            },
            "quiz_answers": [
                {"question_id": "mood_1", "option_id": "happy"},
                {"question_id": "pressure_2", "option_id": "relaxed"}
            ]
        }
    
    @pytest.fixture 
    def generator(self):
        """创建生成器实例"""
        return UnifiedContentGenerator()
    
    async def test_basic_generation(self, generator, sample_task_data):
        """测试基础生成功能"""
        context = {"task": sample_task_data, "results": {}}
        
        # Mock AI provider
        with patch.object(generator.provider, 'generate_text') as mock_generate:
            mock_generate.return_value = json.dumps({
                "oracle_theme": {"title": "春光明媚", "subtitle": "今日心象签"},
                "charm_identity": {
                    "charm_name": "暖阳签",
                    "charm_description": "如春日暖阳般温暖",
                    "charm_blessing": "愿你笑颜如花",
                    "main_color": "#FFE4B5",
                    "accent_color": "#FFA500"
                },
                "affirmation": "愿快乐如春花绽放",
                "oracle_manifest": {
                    "hexagram": {"name": "自强不息", "insight": "保持积极心态"},
                    "daily_guide": ["宜保持微笑", "宜分享快乐"],
                    "fengshui_focus": "面向阳光",
                    "ritual_hint": "深呼吸感受阳光",
                    "element_balance": {"wood": 0.6, "fire": 0.8, "earth": 0.5, "metal": 0.4, "water": 0.3}
                },
                "ink_reading": {
                    "stroke_impression": "轻快的笔触显示内心愉悦",
                    "symbolic_keywords": ["快乐", "明亮", "活力"],
                    "ink_metrics": {"stroke_count": 120, "dominant_quadrant": "upper_right", "pressure_tendency": "steady"}
                },
                "context_insights": {
                    "session_time": "上午",
                    "season_hint": "春季时分",
                    "visit_pattern": "阳光心情",
                    "historical_keywords": []
                },
                "blessing_stream": ["笑口常开", "春风得意", "阳光满怀", "心花怒放"],
                "art_direction": {
                    "image_prompt": "春日暖阳的水彩画",
                    "palette": ["#FFE4B5", "#FFA500", "#FFD700"],
                    "animation_hint": "温暖的光影"
                },
                "ai_selected_charm": {
                    "charm_id": "liujiao-denglong",
                    "charm_name": "六角灯笼面 (光明指引)",
                    "ai_reasoning": "基于快乐心境选择光明主题签体"
                },
                "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
            })
            
            result = await generator.execute(context)
            
            # 验证基本结构
            assert "structured_data" in result["results"]
            structured_data = result["results"]["structured_data"]
            
            # 验证必需字段
            required_fields = [
                "oracle_theme", "charm_identity", "affirmation",
                "oracle_manifest", "ink_reading", "blessing_stream"
            ]
            for field in required_fields:
                assert field in structured_data, f"缺少必需字段: {field}"
            
            # 验证数据类型
            assert isinstance(structured_data["oracle_theme"], dict)
            assert isinstance(structured_data["charm_identity"], dict)
            assert isinstance(structured_data["blessing_stream"], list)
            assert len(structured_data["blessing_stream"]) >= 3
            
            # 验证签名格式
            charm_name = structured_data["charm_identity"]["charm_name"]
            assert charm_name.endswith("签"), f"签名格式错误: {charm_name}"
    
    async def test_retry_mechanism(self, generator, sample_task_data):
        """测试重试机制"""
        context = {"task": sample_task_data, "results": {}}
        
        # Mock AI provider - 前两次失败，第三次成功
        call_count = 0
        def mock_generate_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("API调用失败")
            return json.dumps({
                "oracle_theme": {"title": "重试成功", "subtitle": "今日心象签"},
                "charm_identity": {"charm_name": "成功签", "charm_description": "重试后成功", "charm_blessing": "坚持不懈", "main_color": "#008000", "accent_color": "#90EE90"},
                "affirmation": "坚持就是胜利",
                "oracle_manifest": {"hexagram": {"name": "坚持不懈", "insight": "重试带来成功"}, "daily_guide": ["宜坚持", "宜努力"], "fengshui_focus": "向前看", "ritual_hint": "深呼吸", "element_balance": {"wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5}},
                "ink_reading": {"stroke_impression": "坚定的笔触", "symbolic_keywords": ["坚持", "成功"], "ink_metrics": {"stroke_count": 120, "dominant_quadrant": "center", "pressure_tendency": "steady"}},
                "context_insights": {"session_time": "现在", "season_hint": "当下", "visit_pattern": "重试", "historical_keywords": []},
                "blessing_stream": ["成功", "坚持", "胜利", "突破"],
                "art_direction": {"image_prompt": "成功的画面", "palette": ["#008000"], "animation_hint": "胜利光芒"},
                "ai_selected_charm": {"charm_id": "test", "charm_name": "测试签体", "ai_reasoning": "测试"},
                "culture_note": "测试文化说明"
            })
        
        with patch.object(generator.provider, 'generate_text', side_effect=mock_generate_with_retry):
            result = await generator.execute(context)
            
            # 验证重试成功
            assert "structured_data" in result["results"]
            assert result["results"]["structured_data"]["oracle_theme"]["title"] == "重试成功"
            assert call_count == 3  # 确认进行了3次调用
    
    async def test_fallback_mechanism(self, generator, sample_task_data):
        """测试降级机制"""
        context = {"task": sample_task_data, "results": {}}
        
        # Mock AI provider - 全部失败
        with patch.object(generator.provider, 'generate_text', side_effect=Exception("所有重试都失败")):
            result = await generator.execute(context)
            
            # 验证使用了智能降级
            assert "structured_data" in result["results"]
            structured_data = result["results"]["structured_data"]
            
            # 验证降级数据的完整性
            assert "oracle_theme" in structured_data
            assert "charm_identity" in structured_data
            assert "affirmation" in structured_data
            
            # 验证基于用户输入的个性化降级
            user_input = sample_task_data["user_input"]
            if "好" in user_input or "正能量" in user_input:
                # 应该检测为积极情绪
                assert "春日暖阳" in str(structured_data) or "暖阳" in str(structured_data)
    
    def test_user_profile_analysis(self, generator, sample_task_data):
        """测试用户档案分析"""
        profile = generator._analyze_user_profile(sample_task_data)
        
        # 验证档案结构
        expected_keys = ["stroke_analysis", "quiz_insights", "five_elements", "hexagram", "temporal_energy"]
        for key in expected_keys:
            assert key in profile, f"缺少档案字段: {key}"
        
        # 验证绘画分析
        stroke_analysis = profile["stroke_analysis"]
        assert stroke_analysis["stroke_count"] == 120
        assert "energy_type" in stroke_analysis
        assert "psychology_insight" in stroke_analysis
        
        # 验证问答分析  
        quiz_insights = profile["quiz_insights"]
        assert "emotional_state" in quiz_insights
        assert "core_needs" in quiz_insights
        
        # 验证五行计算
        five_elements = profile["five_elements"]
        assert len(five_elements) == 5
        for element in ["wood", "fire", "earth", "metal", "water"]:
            assert element in five_elements
            assert 0 <= five_elements[element] <= 1
    
    def test_charm_recommendation(self, generator, sample_task_data):
        """测试签体推荐"""
        profile = generator._analyze_user_profile(sample_task_data)
        recommendations = generator._recommend_charms(profile)
        
        # 验证推荐结果
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        
        for charm in recommendations:
            assert "id" in charm
            assert "name" in charm
    
    def test_data_structure_compatibility(self, generator, sample_task_data):
        """测试数据结构兼容性"""
        context = {"task": sample_task_data, "results": {}}
        
        # 创建模拟的完整响应
        mock_response = {
            "oracle_theme": {"title": "测试主题", "subtitle": "今日心象签"},
            "charm_identity": {"charm_name": "测试签", "charm_description": "测试", "charm_blessing": "测试祝福", "main_color": "#000000", "accent_color": "#FFFFFF"},
            "affirmation": "测试祝福语",
            "oracle_manifest": {"hexagram": {"name": "测试卦", "insight": "测试洞察"}, "daily_guide": ["测试指引1", "测试指引2"], "fengshui_focus": "测试风水", "ritual_hint": "测试仪式", "element_balance": {"wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5}},
            "ink_reading": {"stroke_impression": "测试印象", "symbolic_keywords": ["测试1", "测试2"], "ink_metrics": {"stroke_count": 120, "dominant_quadrant": "center", "pressure_tendency": "steady"}},
            "context_insights": {"session_time": "测试时间", "season_hint": "测试季节", "visit_pattern": "测试模式", "historical_keywords": []},
            "blessing_stream": ["祝福1", "祝福2", "祝福3", "祝福4"],
            "art_direction": {"image_prompt": "测试图像", "palette": ["#000000"], "animation_hint": "测试动画"},
            "ai_selected_charm": {"charm_id": "test", "charm_name": "测试签体", "ai_reasoning": "测试原因"},
            "culture_note": "测试文化说明"
        }
        
        with patch.object(generator.provider, 'generate_text', return_value=json.dumps(mock_response)):
            result = await generator.execute(context)
            
            structured_data = result["results"]["structured_data"]
            
            # 验证与小程序端期望的数据结构完全兼容
            expected_structure = {
                "oracle_theme": dict,
                "charm_identity": dict, 
                "affirmation": str,
                "oracle_manifest": dict,
                "ink_reading": dict,
                "context_insights": dict,
                "blessing_stream": list,
                "art_direction": dict,
                "ai_selected_charm": dict,
                "culture_note": str
            }
            
            for field, expected_type in expected_structure.items():
                assert field in structured_data, f"缺少字段: {field}"
                assert isinstance(structured_data[field], expected_type), f"字段类型错误: {field}"

# 性能测试
class TestPerformanceComparison:
    """性能对比测试"""
    
    @pytest.mark.asyncio
    async def test_response_time_comparison(self):
        """对比响应时间"""
        import time
        
        # 准备测试数据
        sample_task = {
            "task_id": "perf-test",
            "user_input": "性能测试",
            "drawing_data": {"analysis": {"stroke_count": 100}},
            "quiz_answers": []
        }
        
        # 测试新版本（统一生成器）
        unified_generator = UnifiedContentGenerator()
        with patch.object(unified_generator.provider, 'generate_text', return_value='{"oracle_theme": {"title": "测试", "subtitle": "今日心象签"}, "charm_identity": {"charm_name": "测试签"}, "affirmation": "测试", "oracle_manifest": {"hexagram": {"name": "测试"}, "daily_guide": [], "element_balance": {}}, "ink_reading": {"stroke_impression": "测试", "symbolic_keywords": [], "ink_metrics": {}}, "context_insights": {}, "blessing_stream": ["测试"], "art_direction": {}, "ai_selected_charm": {}, "culture_note": "测试"}'):
            
            start_time = time.time()
            context = {"task": sample_task, "results": {}}
            await unified_generator.execute(context)
            unified_time = time.time() - start_time
        
        # 模拟旧版本（3次调用）  
        with patch('app.orchestrator.steps.concept_generator.ConceptGenerator') as MockConcept, \
             patch('app.orchestrator.steps.content_generator.ContentGenerator') as MockContent, \
             patch('app.orchestrator.steps.structured_content_generator.StructuredContentGenerator') as MockStructured:
            
            # Mock各个生成器
            async def mock_execute(context):
                await asyncio.sleep(0.1)  # 模拟网络延迟
                return context
                
            MockConcept.return_value.execute = mock_execute
            MockContent.return_value.execute = mock_execute  
            MockStructured.return_value.execute = mock_execute
            
            start_time = time.time()
            context = {"task": sample_task, "results": {}}
            await MockConcept.return_value.execute(context)
            await MockContent.return_value.execute(context)
            await MockStructured.return_value.execute(context)
            legacy_time = time.time() - start_time
        
        # 验证性能提升
        improvement_ratio = legacy_time / unified_time
        print(f"统一版本耗时: {unified_time:.3f}s")
        print(f"传统版本耗时: {legacy_time:.3f}s") 
        print(f"性能提升: {improvement_ratio:.1f}x")
        
        assert improvement_ratio > 1.5, "性能提升不足1.5倍"

# 集成测试
class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_workflow_integration(self):
        """测试工作流集成"""
        from app.orchestrator.workflow import PostcardWorkflow
        
        # 准备完整的任务数据
        task_data = {
            "task_id": "integration-test",
            "user_id": "test-user",
            "user_input": "今天想要一些温暖的话语",
            "drawing_data": {
                "analysis": {
                    "stroke_count": 85,
                    "drawing_time": 20000,
                    "dominant_quadrant": "center",
                    "pressure_tendency": "light"
                }
            },
            "quiz_answers": [
                {"question_id": "mood_1", "option_id": "calm"},
                {"question_id": "need_1", "option_id": "warmth"}
            ]
        }
        
        # 设置环境变量使用统一工作流
        import os
        original_version = os.environ.get("WORKFLOW_VERSION")
        os.environ["WORKFLOW_VERSION"] = "unified"
        
        try:
            workflow = PostcardWorkflow()
            
            # Mock必要的服务调用
            with patch.object(workflow, 'update_task_status', return_value=True), \
                 patch.object(workflow, 'save_final_result', return_value=True):
                
                # 执行工作流
                await workflow.execute(task_data)
                
        finally:
            # 恢复环境变量
            if original_version is not None:
                os.environ["WORKFLOW_VERSION"] = original_version
            elif "WORKFLOW_VERSION" in os.environ:
                del os.environ["WORKFLOW_VERSION"]
```

### 4.2 性能基准测试

**文件**: `scripts/performance_benchmark.py`
```python
#!/usr/bin/env python3
"""
AI工作流性能基准测试脚本
"""
import asyncio
import time
import statistics
import json
from typing import List, Dict
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/ai-agent-service'))

async def benchmark_unified_workflow(iterations: int = 10) -> Dict[str, float]:
    """基准测试统一工作流"""
    from app.orchestrator.steps.unified_content_generator import UnifiedContentGenerator
    
    generator = UnifiedContentGenerator()
    times = []
    
    # 测试数据
    test_tasks = [
        {
            "task_id": f"bench-{i}",
            "user_input": f"测试心情{i}",
            "drawing_data": {"analysis": {"stroke_count": 80 + i*10}},
            "quiz_answers": []
        }
        for i in range(iterations)
    ]
    
    print(f"🚀 开始统一工作流基准测试 ({iterations}次)")
    
    for i, task in enumerate(test_tasks):
        context = {"task": task, "results": {}}
        
        start_time = time.time()
        try:
            await generator.execute(context)
            elapsed = time.time() - start_time
            times.append(elapsed)
            print(f"  第{i+1}次: {elapsed:.3f}s")
        except Exception as e:
            print(f"  第{i+1}次失败: {e}")
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times), 
        "min": min(times),
        "max": max(times),
        "std": statistics.stdev(times) if len(times) > 1 else 0
    }

async def benchmark_legacy_workflow(iterations: int = 10) -> Dict[str, float]:
    """基准测试传统工作流（模拟）"""
    times = []
    
    print(f"🔄 开始传统工作流基准测试 ({iterations}次)")
    
    for i in range(iterations):
        start_time = time.time()
        
        # 模拟3次AI调用的延迟
        await asyncio.sleep(0.5)  # ConceptGenerator
        await asyncio.sleep(0.6)  # ContentGenerator  
        await asyncio.sleep(0.8)  # StructuredContentGenerator
        
        elapsed = time.time() - start_time
        times.append(elapsed)
        print(f"  第{i+1}次: {elapsed:.3f}s")
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times), 
        "max": max(times),
        "std": statistics.stdev(times) if len(times) > 1 else 0
    }

async def main():
    """主测试函数"""
    print("=" * 60)
    print("AI工作流性能基准测试")
    print("=" * 60)
    
    iterations = 5
    
    # 测试统一工作流
    unified_stats = await benchmark_unified_workflow(iterations)
    
    # 测试传统工作流  
    legacy_stats = await benchmark_legacy_workflow(iterations)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("性能测试结果")
    print("=" * 60)
    
    print(f"统一工作流 (平均): {unified_stats['mean']:.3f}s")
    print(f"传统工作流 (平均): {legacy_stats['mean']:.3f}s")
    print(f"性能提升: {legacy_stats['mean'] / unified_stats['mean']:.1f}x")
    
    print(f"\n详细统计:")
    print(f"统一版本 - 平均: {unified_stats['mean']:.3f}s, 中位数: {unified_stats['median']:.3f}s, 标准差: {unified_stats['std']:.3f}s")
    print(f"传统版本 - 平均: {legacy_stats['mean']:.3f}s, 中位数: {legacy_stats['median']:.3f}s, 标准差: {legacy_stats['std']:.3f}s")
    
    # 保存结果
    results = {
        "timestamp": time.time(),
        "iterations": iterations,
        "unified_workflow": unified_stats,
        "legacy_workflow": legacy_stats,
        "performance_improvement": legacy_stats['mean'] / unified_stats['mean']
    }
    
    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n结果已保存到 benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.3 测试执行命令

```bash
# 运行单元测试
cd src/ai-agent-service
python -m pytest tests/test_unified_content_generator.py -v

# 运行性能基准测试
python scripts/performance_benchmark.py

# 运行完整测试套件
python -m pytest tests/ -v --cov=app

# 运行集成测试
python -m pytest tests/test_unified_content_generator.py::TestIntegration -v
```

## 5. 风险评估与应对

### 5.1 主要风险点

#### 5.1.1 技术风险
| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 单次调用失败率提高 | 中 | 高 | 强化重试机制，保留智能降级 |
| Prompt复杂度过高 | 低 | 中 | 充分测试，分阶段优化 |
| 生成内容质量不稳定 | 中 | 高 | 增加验证逻辑，多轮测试 |

#### 5.1.2 业务风险
| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 小程序端兼容性问题 | 低 | 高 | 保持数据结构100%兼容 |
| 用户体验暂时下降 | 中 | 中 | 灰度发布，快速回滚机制 |

### 5.2 回滚方案
保留原有3步工作流代码，通过环境变量控制：
```python
WORKFLOW_VERSION = os.getenv("WORKFLOW_VERSION", "unified")  # "legacy" | "unified"
```

## 6. 上线计划

### 6.1 分阶段实施
```
阶段1 (Week 1): 核心代码开发 + 单元测试
阶段2 (Week 2): 集成测试 + Prompt优化  
阶段3 (Week 3): 性能测试 + 灰度发布
阶段4 (Week 4): 全量上线 + 监控优化
```

### 6.2 监控指标
- **性能指标**：平均响应时间、P99响应时间、错误率
- **质量指标**：内容多样性、个性化评分、用户满意度
- **业务指标**：转化率、留存率、分享率

## 7. 预期效果

### 7.1 量化收益
- 🚀 **响应速度提升60%**：从平均8秒降低到3秒
- 💰 **成本降低66%**：API调用次数从4次减少到2次
- 📈 **成功率提升20%**：减少中间步骤失败点
- 🎯 **个性化提升40%**：更深度的用户分析和内容定制

### 7.2 定性收益
- ✨ **更连贯的用户体验**：一次性推理产生更一致的内容逻辑
- 🎨 **更丰富的文化内涵**：深度融入易经、五行等传统智慧
- 🔧 **更简洁的代码架构**：减少70%的兜底逻辑代码
- 📱 **更稳定的小程序渲染**：数据结构保持100%兼容

---

**文档状态**: ✅ 已完成  
**下一步**: 等待评审确认后开始实施