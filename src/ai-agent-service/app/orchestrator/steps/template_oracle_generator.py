import logging
import datetime
from typing import Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class TemplateOracleGenerator:
    """模板兜底生成器 - 阶段2失败时的降级方案"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def generate(self, analysis: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于分析结果生成模板化内容"""
        
        psychological_profile = analysis.get("psychological_profile", {})
        emotion_state = psychological_profile.get("emotion_state", "calm")
        five_elements = analysis.get("five_elements", {})
        hexagram = analysis.get("hexagram_match", {})
        
        self.logger.info(f"🔄 使用模板兜底生成，情绪状态: {emotion_state}")
        
        # 情绪对应的模板配置
        templates = {
            "positive": {
                "title": "春日暖阳",
                "charm_name": "暖阳签",
                "affirmation": "愿快乐如春花绽放",
                "main_color": "#FFE4B5",
                "accent_color": "#FFA500",
                "blessing": ["心花怒放", "笑靥如花", "春风得意", "阳光满怀"],
                "daily_guide": ["宜保持微笑，传递正能量", "宜分享快乐，感染他人"],
                "fengshui_focus": "面向阳光的方向，让光明充满空间",
                "ritual_hint": "清晨面向太阳深呼吸，感受温暖能量"
            },
            "calm": {
                "title": "湖水如镜",
                "charm_name": "静心签", 
                "affirmation": "愿内心如湖水般宁静",
                "main_color": "#B0E0E6",
                "accent_color": "#87CEEB",
                "blessing": ["心如止水", "宁静致远", "岁月静好", "内心安宁"],
                "daily_guide": ["宜保持内心平静，处事不惊", "宜慢节奏生活，享受当下"],
                "fengshui_focus": "在安静的角落放置水培植物",
                "ritual_hint": "静坐冥想五分钟，聆听内心声音"
            },
            "energetic": {
                "title": "破浪前行",
                "charm_name": "活力签",
                "affirmation": "愿活力如潮水般涌现",
                "main_color": "#FF6B6B",
                "accent_color": "#FF8E53",
                "blessing": ["活力四射", "勇往直前", "破浪前行", "动力满满"],
                "daily_guide": ["宜积极行动，把握机会", "宜运动锻炼，释放活力"],
                "fengshui_focus": "在工作区域添加红色或橙色元素",
                "ritual_hint": "做几分钟有氧运动，激发身体活力"
            },
            "thoughtful": {
                "title": "月下思语",
                "charm_name": "深思签",
                "affirmation": "愿思考带来智慧光芒",
                "main_color": "#9370DB",
                "accent_color": "#BA55D3",
                "blessing": ["深思熟虑", "智慧如海", "思接千载", "洞察深邃"],
                "daily_guide": ["宜安静思考，整理思绪", "宜阅读学习，丰富内心"],
                "fengshui_focus": "在书桌旁放置紫色水晶或薰衣草",
                "ritual_hint": "晚上写下今日感悟，思考人生意义"
            },
            "hopeful": {
                "title": "晨曦初露",
                "charm_name": "希望签",
                "affirmation": "愿希望如晨曦般闪耀",
                "main_color": "#FFD700",
                "accent_color": "#FFA500",
                "blessing": ["希望满怀", "曙光在前", "梦想成真", "未来可期"],
                "daily_guide": ["宜制定目标，规划未来", "宜保持乐观，相信美好"],
                "fengshui_focus": "在东方位置摆放向日葵或黄色花朵",
                "ritual_hint": "每天写下一个小目标，点燃希望之火"
            }
        }
        
        template = templates.get(emotion_state, templates["calm"])
        
        # 获取时间信息
        temporal_info = self._get_temporal_info()
        
        # 获取绘画数据
        drawing_data = task_data.get("drawing_data", {}).get("analysis", {})
        stroke_count = drawing_data.get("stroke_count", 0)
        dominant_quadrant = drawing_data.get("dominant_quadrant", "center")
        pressure_tendency = drawing_data.get("pressure_tendency", "steady")
        
        # 生成笔触印象
        stroke_impression = self._generate_stroke_impression(emotion_state, stroke_count, pressure_tendency)
        
        # 生成关键词
        symbolic_keywords = self._generate_symbolic_keywords(emotion_state, psychological_profile)
        
        # 生成图像prompt
        image_prompt = self._generate_image_prompt(template["title"], emotion_state)
        
        # 构建完整的oracle数据结构
        oracle_data = {
            "oracle_theme": {
                "title": template["title"],
                "subtitle": "今日心象签"
            },
            "charm_identity": {
                "charm_name": template["charm_name"],
                "charm_description": f"如{template['title']}般的心境体验，体现{emotion_state}的内在特质",
                "charm_blessing": template["affirmation"],
                "main_color": template["main_color"],
                "accent_color": template["accent_color"]
            },
            "affirmation": template["affirmation"],
            "oracle_manifest": {
                "hexagram": {
                    "name": hexagram.get("modern_name", "内心和谐"),
                    "insight": hexagram.get("insight", "在变化中寻找内心的平衡")
                },
                "daily_guide": template["daily_guide"],
                "fengshui_focus": template["fengshui_focus"],
                "ritual_hint": template["ritual_hint"],
                "element_balance": five_elements if five_elements else {
                    "wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5
                }
            },
            "ink_reading": {
                "stroke_impression": stroke_impression,
                "symbolic_keywords": symbolic_keywords,
                "ink_metrics": {
                    "stroke_count": stroke_count,
                    "dominant_quadrant": dominant_quadrant,
                    "pressure_tendency": pressure_tendency
                }
            },
            "context_insights": {
                "session_time": temporal_info["time_period"],
                "season_hint": temporal_info["season_hint"],
                "visit_pattern": f"体现{emotion_state}特质的心象之旅",
                "historical_keywords": []
            },
            "blessing_stream": template["blessing"],
            "art_direction": {
                "image_prompt": image_prompt,
                "palette": [template["main_color"], template["accent_color"], "#F0F8FF"],
                "animation_hint": self._generate_animation_hint(emotion_state)
            },
            "ai_selected_charm": {
                "charm_id": "lianhua-yuanpai",
                "charm_name": "莲花圆牌 (平和雅致)",
                "ai_reasoning": f"基于用户{emotion_state}的心境特征，选择平和雅致的莲花圆牌，寓意内心如莲花般纯净美好"
            },
            "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
        }
        
        self.logger.info(f"✅ 模板兜底生成完成，主题: {template['title']}")
        return oracle_data
    
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
    
    def _generate_stroke_impression(self, emotion_state: str, stroke_count: int, pressure_tendency: str) -> str:
        """生成笔触印象"""
        base_impressions = {
            "positive": "笔触轻快明亮，如春风拂面，展现内心的喜悦与活力",
            "calm": "笔触平和稳定，如流水般自然，体现内心的宁静与从容",
            "energetic": "笔触充满力量，如燃烧的火焰，显示旺盛的生命活力",
            "thoughtful": "笔触深沉内敛，如夜空中的星辰，展现深邃的思考力",
            "hopeful": "笔触向上生长，如初升的朝阳，充满对未来的憧憬"
        }
        
        base_impression = base_impressions.get(emotion_state, "笔触自然和谐，体现内心的平衡状态")
        
        # 根据笔画数量调整描述
        if stroke_count > 120:
            stroke_desc = "，丰富的笔画显示表达欲强烈"
        elif stroke_count < 60:
            stroke_desc = "，简约的笔画体现内敛的性格"
        else:
            stroke_desc = "，适中的笔画展现平衡的心态"
        
        # 根据压力倾向调整描述
        if pressure_tendency == "heavy":
            pressure_desc = "，深沉的笔压透露专注认真的态度"
        elif pressure_tendency == "light":
            pressure_desc = "，轻柔的笔压显示放松自在的状态"
        else:
            pressure_desc = "，稳定的笔压体现内心的平衡"
        
        return base_impression + stroke_desc + pressure_desc
    
    def _generate_symbolic_keywords(self, emotion_state: str, psychological_profile: Dict) -> list:
        """生成象征关键词"""
        base_keywords = {
            "positive": ["阳光", "温暖", "绽放"],
            "calm": ["静水", "和谐", "宁静"],
            "energetic": ["火焰", "力量", "前进"],
            "thoughtful": ["深邃", "智慧", "洞察"],
            "hopeful": ["晨曦", "希望", "未来"]
        }
        
        keywords = base_keywords.get(emotion_state, ["平衡", "和谐", "美好"]).copy()
        
        # 基于核心需求添加关键词
        core_needs = psychological_profile.get("core_needs", [])
        need_keywords = {
            "social_connection": "连接",
            "self_growth": "成长",
            "creative_expression": "创意",
            "achievement": "成就",
            "inner_peace": "平静",
            "rest_recovery": "恢复"
        }
        
        for need in core_needs:
            if need in need_keywords:
                keywords.append(need_keywords[need])
                break  # 只添加一个需求关键词
        
        return keywords[:3]  # 返回前3个关键词
    
    def _generate_image_prompt(self, title: str, emotion_state: str) -> str:
        """生成图像描述"""
        style_base = "水彩画风格，柔和的色彩渐变"
        
        emotion_styles = {
            "positive": f"{title}的温暖景象，{style_base}，明亮的阳光透过树叶洒下斑驳光影",
            "calm": f"{title}的宁静景象，{style_base}，平静的湖面倒映着天空的云彩",
            "energetic": f"{title}的动感景象，{style_base}，汹涌的海浪拍击着礁石展现力量",
            "thoughtful": f"{title}的深邃景象，{style_base}，月光下的山峦静谧神秘",
            "hopeful": f"{title}的希望景象，{style_base}，地平线上升起的太阳光芒万丈"
        }
        
        return emotion_styles.get(emotion_state, f"{title}的自然景象，{style_base}，和谐美好的意境")
    
    def _generate_animation_hint(self, emotion_state: str) -> str:
        """生成动画效果提示"""
        animation_hints = {
            "positive": "温暖的光影流动，如阳光般闪烁",
            "calm": "缓慢的波纹扩散，如微风轻抚",
            "energetic": "活跃的粒子跳动，如火花飞舞",
            "thoughtful": "柔和的星光闪烁，如思绪流转",
            "hopeful": "渐亮的光芒扩散，如希望升腾"
        }
        
        return animation_hints.get(emotion_state, "温和的光影变化，营造宁静氛围")