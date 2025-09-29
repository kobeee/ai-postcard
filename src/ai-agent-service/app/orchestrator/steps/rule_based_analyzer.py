import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RuleBasedAnalyzer:
    """规则降级分析器 - 阶段1失败时的降级方案"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def analyze(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于关键词和规则的快速心理分析"""
        
        user_input = task_data.get("user_input", "")
        drawing_data = task_data.get("drawing_data", {}).get("analysis", {})
        quiz_answers = task_data.get("quiz_answers", [])
        
        self.logger.info("🔄 使用规则降级分析")
        
        # 情绪关键词检测
        emotion_mapping = {
            "positive": ["开心", "快乐", "高兴", "愉快", "兴奋", "激动", "喜悦", "满足", "幸福"],
            "calm": ["平静", "安静", "宁静", "淡然", "从容", "放松", "平和", "安详", "祥和"],
            "energetic": ["活力", "精力", "动力", "充满", "积极", "奋斗", "拼搏", "努力", "进取"],
            "thoughtful": ["思考", "沉思", "想念", "回忆", "深思", "反思", "冥想", "内省", "感悟"],
            "hopeful": ["希望", "期待", "梦想", "未来", "目标", "愿望", "憧憬", "向往", "期盼"]
        }
        
        detected_emotion = "calm"  # 默认情绪
        emotion_score = 0
        
        # 检测最匹配的情绪
        for emotion, keywords in emotion_mapping.items():
            score = sum(1 for keyword in keywords if keyword in user_input)
            if score > emotion_score:
                emotion_score = score
                detected_emotion = emotion
        
        # 基于绘画数据调整情绪判断
        stroke_count = drawing_data.get("stroke_count", 0)
        drawing_time = drawing_data.get("drawing_time", 0)
        pressure_tendency = drawing_data.get("pressure_tendency", "steady")
        
        if stroke_count > 150:
            # 笔画多，倾向于活跃情绪
            if detected_emotion == "calm":
                detected_emotion = "energetic"
        elif stroke_count < 50:
            # 笔画少，倾向于内省情绪
            if detected_emotion == "energetic":
                detected_emotion = "thoughtful"
        
        if pressure_tendency == "heavy":
            # 压力大，可能是焦虑或专注
            if detected_emotion in ["positive", "calm"]:
                detected_emotion = "thoughtful"
        
        # 基于问答数据进一步调整
        core_needs = self._infer_needs_from_quiz(quiz_answers, detected_emotion)
        
        # 基于检测情绪的五行配置
        element_configs = {
            "positive": {"wood": 0.7, "fire": 0.8, "earth": 0.6, "metal": 0.4, "water": 0.3},
            "calm": {"wood": 0.4, "fire": 0.3, "earth": 0.7, "metal": 0.5, "water": 0.8},
            "energetic": {"wood": 0.8, "fire": 0.9, "earth": 0.5, "metal": 0.6, "water": 0.2},
            "thoughtful": {"wood": 0.3, "fire": 0.2, "earth": 0.4, "metal": 0.8, "water": 0.9},
            "hopeful": {"wood": 0.6, "fire": 0.7, "earth": 0.5, "metal": 0.6, "water": 0.4}
        }
        
        # 卦象匹配
        hexagram_mapping = {
            "positive": {"name": "泽天夬", "modern_name": "阳光心境", "insight": "保持积极心态，迎接美好时光"},
            "calm": {"name": "坤为地", "modern_name": "厚德载物", "insight": "在宁静中积累内在力量"},
            "energetic": {"name": "乾为天", "modern_name": "自强不息", "insight": "顺应天行健，持续前进"},
            "thoughtful": {"name": "艮为山", "modern_name": "静思明志", "insight": "在深思中寻找人生方向"},
            "hopeful": {"name": "雷天大壮", "modern_name": "希望之光", "insight": "心怀希望，力量自生"}
        }
        
        # 生成主导特质
        dominant_traits = self._generate_dominant_traits(detected_emotion, stroke_count, pressure_tendency)
        
        # 生成关键洞察
        key_insights = self._generate_key_insights(detected_emotion, core_needs, user_input)
        
        result = {
            "psychological_profile": {
                "emotion_state": detected_emotion,
                "core_needs": core_needs,
                "energy_type": self._determine_energy_type(detected_emotion, stroke_count),
                "dominant_traits": dominant_traits
            },
            "five_elements": element_configs.get(detected_emotion, element_configs["calm"]),
            "hexagram_match": hexagram_mapping.get(detected_emotion, hexagram_mapping["calm"]),
            "key_insights": key_insights
        }
        
        self.logger.info(f"✅ 规则分析完成，检测情绪: {detected_emotion}")
        return result
    
    def _infer_needs_from_quiz(self, quiz_answers: list, emotion_state: str) -> list:
        """从问答中推断核心需求"""
        if not quiz_answers:
            return self._default_needs_for_emotion(emotion_state)
        
        needs = []
        for answer in quiz_answers:
            option_id = answer.get("option_id", "").lower()
            
            # 基于选项推断需求
            if any(keyword in option_id for keyword in ["rest", "relax", "calm"]):
                needs.append("rest_recovery")
            if any(keyword in option_id for keyword in ["social", "friend", "connect"]):
                needs.append("social_connection")
            if any(keyword in option_id for keyword in ["learn", "grow", "improve"]):
                needs.append("self_growth")
            if any(keyword in option_id for keyword in ["create", "art", "express"]):
                needs.append("creative_expression")
            if any(keyword in option_id for keyword in ["achieve", "goal", "success"]):
                needs.append("achievement")
        
        # 如果没有检测到具体需求，基于情绪给默认需求
        if not needs:
            needs = self._default_needs_for_emotion(emotion_state)
        
        return list(set(needs))[:3]  # 最多3个需求
    
    def _default_needs_for_emotion(self, emotion_state: str) -> list:
        """基于情绪的默认需求"""
        emotion_needs = {
            "positive": ["joy_sharing", "social_connection"],
            "calm": ["inner_peace", "stability"],
            "energetic": ["achievement", "self_growth"],
            "thoughtful": ["self_understanding", "inner_wisdom"],
            "hopeful": ["goal_achievement", "future_planning"]
        }
        return emotion_needs.get(emotion_state, ["inner_balance", "harmony"])
    
    def _determine_energy_type(self, emotion_state: str, stroke_count: int) -> str:
        """确定能量类型"""
        if emotion_state in ["energetic", "positive"] or stroke_count > 120:
            return "活跃"
        elif emotion_state in ["thoughtful", "calm"] or stroke_count < 60:
            return "内省"
        else:
            return "平衡"
    
    def _generate_dominant_traits(self, emotion_state: str, stroke_count: int, pressure_tendency: str) -> list:
        """生成主导特质"""
        base_traits = {
            "positive": ["乐观", "开朗", "积极"],
            "calm": ["平和", "稳定", "从容"],
            "energetic": ["活力", "进取", "热情"],
            "thoughtful": ["深思", "内敛", "智慧"],
            "hopeful": ["乐观", "坚韧", "向上"]
        }
        
        traits = base_traits.get(emotion_state, ["平衡", "和谐", "稳定"]).copy()
        
        # 基于绘画特征调整
        if stroke_count > 150:
            traits.append("表达丰富")
        elif stroke_count < 50:
            traits.append("简约内敛")
        
        if pressure_tendency == "heavy":
            traits.append("专注认真")
        elif pressure_tendency == "light":
            traits.append("轻松自在")
        
        return traits[:3]  # 返回前3个特质
    
    def _generate_key_insights(self, emotion_state: str, core_needs: list, user_input: str) -> list:
        """生成关键洞察"""
        emotion_insights = {
            "positive": ["展现积极心态", "善于发现美好", "具有感染力"],
            "calm": ["追求内心平衡", "重视稳定感", "善于调节情绪"],
            "energetic": ["充满行动力", "目标导向", "不断进取"],
            "thoughtful": ["善于深度思考", "注重精神世界", "具有洞察力"],
            "hopeful": ["对未来充满期待", "具有韧性", "积极规划"]
        }
        
        insights = emotion_insights.get(emotion_state, ["追求内心和谐", "注重平衡发展", "具有包容心"]).copy()
        
        # 基于核心需求添加洞察
        need_insights = {
            "social_connection": "渴望真诚的人际连接",
            "self_growth": "有强烈的成长意愿",
            "creative_expression": "具有创造性思维",
            "achievement": "有明确的目标追求",
            "inner_peace": "追求内心的宁静"
        }
        
        for need in core_needs:
            if need in need_insights:
                insights.append(need_insights[need])
        
        # 基于用户输入添加个性化洞察
        if len(user_input) > 20:
            insights.append("善于表达内心想法")
        elif len(user_input) < 10:
            insights.append("简洁而深刻")
        
        return insights[:3]  # 返回前3个洞察