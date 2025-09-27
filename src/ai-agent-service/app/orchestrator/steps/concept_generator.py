import logging
import json
import random
import os
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ConceptGenerator:
    """概念生成器 - 第1步：生成心象签概念并选择签体"""
    
    def __init__(self):
        # 文本生成使用 Gemini
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载签体配置
        self.charm_configs = self._load_charm_configs()
    
    async def execute(self, context):
        """生成心象签概念和选择签体"""
        task = context["task"]
        
        self.logger.info(f"🎯 开始生成心象签概念: {task.get('task_id')}")
        
        # 提取上下文信息
        ink_metrics = task.get('drawing_data', {}).get('analysis', {})
        emotion_image_base64 = task.get('emotion_image_base64')
        user_input = task.get('user_input', '')
        quiz_answers = task.get('quiz_answers', [])
        
        # 分析问答数据
        quiz_analysis = self._analyze_quiz_answers(quiz_answers)
        
        # 构建心象签概念生成提示词
        concept_prompt = f"""
你是一位心象签解读师，擅长将用户的情绪状态映射为自然意象和氛围描述。

用户输入：{user_input}
情绪绘画特征：{ink_metrics.get('drawing_description', '平和的笔触')}
绘画数据：笔画数 {ink_metrics.get('stroke_count', 0)}，绘制时长 {ink_metrics.get('drawing_time', 0)}ms
绘画模式：{ink_metrics.get('pattern_type', 'moderate')}，复杂度 {ink_metrics.get('complexity', 'simple')}

心境速测分析：{quiz_analysis.get('summary', '心境平和')}
问答洞察：{quiz_analysis.get('emotion_vector', {})}
行动偏好：{quiz_analysis.get('action_focus', [])}

请基于用户的心情状态、绘画特征和问答洞察，生成一个心象签概念，将心情映射为自然意象：

核心要求：
1. 将心情映射为具体的自然现象或意象（如"彩虹静落群山"、"晨雾拂过湖面"、"微风穿过竹林"）
2. 避免抽象概念，要有具体画面感的自然场景
3. 结合绘画特征和问答洞察推断情绪基调
4. 用现代语汇解释，非迷信化表达
5. 考虑适合的签体风格（沉稳庄重、温和雅致、文化底蕴等）

请以JSON格式返回，包含以下字段：
{{
    "natural_scene": "具体的自然意象描述（12字以内）",
    "emotion_tone": "情绪基调（如平静、活跃、思考、期待等）",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "atmosphere": "氛围描述（温暖、清新、深邃等）",
    "color_inspiration": "色彩灵感（如暖橙、深蓝、森林绿等）",
    "charm_style_preference": "签体风格偏好（如庄重、雅致、活泼、深邃等）"
}}

注意：
- natural_scene要有具体的画面感，不要用抽象词汇
- 结合ink_metrics的绘画特征和quiz_answers来推断用户的真实心境
- charm_style_preference要体现整体风格，为签体选择提供依据
- 保持现代化表达，避免玄学用语
"""
        
        try:
            # 调用Gemini文本生成
            concept = await self.provider.generate_text(
                prompt=concept_prompt,
                max_tokens=1024,
                temperature=0.8
            )
            
            # 选择合适的签体
            selected_charm = self._select_charm_style(concept, quiz_analysis)
            
            context["results"]["concept"] = concept
            context["results"]["selected_charm_style"] = selected_charm
            
            self.logger.info(f"✅ 概念生成完成: {len(concept)} 字符")
            self.logger.info(f"🎨 选择签体: {selected_charm['name']}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 概念生成失败: {e}")
            # 返回默认概念
            context["results"]["concept"] = self._get_default_concept(task)
            context["results"]["selected_charm_style"] = self._get_default_charm()
            return context
    
    def _load_charm_configs(self):
        """加载签体配置文件 - 使用多路径fallback策略"""
        try:
            # 定义多个可能的配置文件路径（按优先级排序）
            potential_paths = [
                # 1. 环境变量指定路径
                os.environ.get('CHARM_CONFIG_PATH'),
                # 2. 项目根目录绝对路径（最可靠）
                '/app/resources/签体/charm-config.json',
                # 3. 相对于当前文件的路径（原方案，保留兼容）
                os.path.join(os.path.dirname(__file__), '../../../../resources/签体/charm-config.json'),
                # 4. 开发环境路径
                os.path.join(os.getcwd(), 'resources/签体/charm-config.json'),
                # 5. 备用相对路径
                os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..', 'resources/签体/charm-config.json'))
            ]
            
            # 过滤掉None值
            potential_paths = [p for p in potential_paths if p is not None]
            
            # 尝试每个路径
            for config_path in potential_paths:
                try:
                    if os.path.exists(config_path):
                        self.logger.info(f"🔍 找到签体配置文件: {config_path}")
                        with open(config_path, 'r', encoding='utf-8') as f:
                            configs = json.load(f)
                            if isinstance(configs, list) and len(configs) > 0:
                                self.logger.info(f"✅ 成功加载 {len(configs)} 个签体配置")
                                return configs
                            else:
                                self.logger.warning(f"⚠️ 配置文件格式异常: {config_path}")
                    else:
                        self.logger.debug(f"🔍 路径不存在: {config_path}")
                except Exception as path_error:
                    self.logger.debug(f"🔍 无法读取路径 {config_path}: {path_error}")
                    continue
            
            # 所有路径都失败，记录详细错误信息
            self.logger.error(f"❌ 所有签体配置文件路径都无法访问:")
            for i, path in enumerate(potential_paths, 1):
                self.logger.error(f"   {i}. {path} {'✓存在' if os.path.exists(path) else '✗不存在'}")
            
            self.logger.warning("⚠️ 使用默认签体配置（仅3个签体）")
            return self._get_default_charm_configs()
            
        except Exception as e:
            self.logger.error(f"❌ 加载签体配置失败: {e}")
            return self._get_default_charm_configs()
    
    def _get_default_charm_configs(self):
        """获取默认签体配置（兜底方案）- 包含完整的18种签体"""
        return [
            {
                "id": "bagua-jinnang",
                "name": "八角锦囊 (神秘守护)",
                "image": "八角锦囊 (神秘守护).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 4,
                    "lineHeight": 72,
                    "fontSize": 68,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 660},
                    "maxChars": 10,
                    "fontSize": 30,
                    "color": "#2E3A4A"
                },
                "glow": {
                    "shape": "octagon",
                    "radius": [380, 380],
                    "opacity": 0.4,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#5DA9E9", "#F2D7EE"],
                "note": "八角造型较稳重，竖排签名置中效果最佳。"
            },
            {
                "id": "liujiao-denglong",
                "name": "六角灯笼面 (光明指引)",
                "image": "六角灯笼面 (光明指引).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 530},
                    "maxChars": 4,
                    "lineHeight": 68,
                    "fontSize": 64,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 660},
                    "maxChars": 10,
                    "fontSize": 28,
                    "color": "#2C3E50"
                },
                "glow": {
                    "shape": "hexagon",
                    "radius": [360, 360],
                    "opacity": 0.35,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#FFD166", "#F6E7CD"],
                "note": "灯笼顶部空间收紧，适合竖排签名。"
            },
            {
                "id": "juanzhou-huakuang",
                "name": "卷轴画框 (徐徐展开)",
                "image": "卷轴画框 (徐徐展开).png",
                "title": {
                    "type": "horizontal",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 6,
                    "lineHeight": 56,
                    "fontSize": 56,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 600},
                    "maxChars": 16,
                    "fontSize": 30,
                    "color": "#4A3728"
                },
                "glow": {
                    "shape": "rectangle",
                    "radius": [420, 320],
                    "opacity": 0.35,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#E9C46A", "#F4A261"],
                "note": "卷轴横向空间充足，支持横排签名。"
            },
            {
                "id": "shuangyu-jinnang",
                "name": "双鱼锦囊 (年年有余)",
                "image": "双鱼锦囊 (年年有余).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 525},
                    "maxChars": 4,
                    "lineHeight": 70,
                    "fontSize": 66,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 655},
                    "maxChars": 10,
                    "fontSize": 28,
                    "color": "#274060"
                },
                "glow": {
                    "shape": "ellipse",
                    "radius": [360, 420],
                    "opacity": 0.42,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#94D1BE", "#F9C74F"],
                "note": "双鱼造型优雅，适合竖排签名。"
            },
            {
                "id": "siyue-jinjie",
                "name": "四叶锦结 (幸运相伴)",
                "image": "四叶锦结 (幸运相伴).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 500},
                    "maxChars": 4,
                    "lineHeight": 72,
                    "fontSize": 68,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": False
                },
                "glow": {
                    "shape": "clover",
                    "radius": [360, 360],
                    "opacity": 0.4,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#52B788", "#D8F3DC"],
                "note": "四叶形中心紧凑，建议只显示主签名。"
            },
            {
                "id": "ruyi-jie",
                "name": "如意结 (万事如意)",
                "image": "如意结 (万事如意).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 4,
                    "lineHeight": 70,
                    "fontSize": 66,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 660},
                    "maxChars": 10,
                    "fontSize": 28,
                    "color": "#432C7A"
                },
                "glow": {
                    "shape": "loop",
                    "radius": [360, 400],
                    "opacity": 0.4,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#7D5BA6", "#FFE5F1"],
                "note": "如意结造型经典，适合竖排签名。"
            },
            {
                "id": "fangsheng-jie",
                "name": "方胜结 (同心永结)",
                "image": "方胜结 (同心永结).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 4,
                    "lineHeight": 68,
                    "fontSize": 64,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": False
                },
                "glow": {
                    "shape": "diamond",
                    "radius": [360, 360],
                    "opacity": 0.38,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#48B8D0", "#E8F6FD"],
                "note": "菱形内部空间较小，适合竖排签名。"
            },
            {
                "id": "zhuchi-changpai",
                "name": "朱漆长牌 (言简意赅)",
                "image": "朱漆长牌 (言简意赅).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 540},
                    "maxChars": 3,
                    "lineHeight": 80,
                    "fontSize": 70,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 700},
                    "maxChars": 8,
                    "fontSize": 28,
                    "color": "#4F1D1D"
                },
                "glow": {
                    "shape": "rectangle",
                    "radius": [320, 440],
                    "opacity": 0.32,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#D62828", "#F77F00"],
                "note": "牌身狭长，签名控制在3个字以内。"
            },
            {
                "id": "haitang-muchuang",
                "name": "海棠木窗 (古典窗格)",
                "image": "海棠木窗 (古典窗格).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 530},
                    "maxChars": 4,
                    "lineHeight": 70,
                    "fontSize": 64,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 660},
                    "maxChars": 12,
                    "fontSize": 30,
                    "color": "#362C2A"
                },
                "glow": {
                    "shape": "rounded-square",
                    "radius": [380, 380],
                    "opacity": 0.38,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#A47148", "#F4E6D4"],
                "note": "窗格花纹细密，适合竖排签名。"
            },
            {
                "id": "xiangyun-liucai",
                "name": "祥云流彩 (梦幻意境)",
                "image": "祥云流彩 (梦幻意境).png",
                "title": {
                    "type": "horizontal",
                    "position": {"x": 512, "y": 540},
                    "maxChars": 6,
                    "lineHeight": 54,
                    "fontSize": 52,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 620},
                    "maxChars": 12,
                    "fontSize": 28,
                    "color": "#2B3A55"
                },
                "glow": {
                    "shape": "ellipse",
                    "radius": [420, 320],
                    "opacity": 0.4,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#5F0A87", "#B5A0FF"],
                "note": "云纹延展，适合横排签名。"
            },
            {
                "id": "xiangyun-hulu",
                "name": "祥云葫芦 (福禄绵延)",
                "image": "祥云葫芦 (福禄绵延).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 560},
                    "maxChars": 3,
                    "lineHeight": 78,
                    "fontSize": 70,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 700},
                    "maxChars": 8,
                    "fontSize": 30,
                    "color": "#3E2723"
                },
                "glow": {
                    "shape": "gourd",
                    "radius": [320, 420],
                    "opacity": 0.36,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#FFB703", "#FB8500"],
                "note": "葫芦造型独特，适合3字签名。"
            },
            {
                "id": "zhujie-changtiao",
                "name": "竹节长条 (虚心有节)",
                "image": "竹节长条 (虚心有节).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 540},
                    "maxChars": 3,
                    "lineHeight": 78,
                    "fontSize": 68,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 700},
                    "maxChars": 8,
                    "fontSize": 28,
                    "color": "#1B4332"
                },
                "glow": {
                    "shape": "rectangle",
                    "radius": [300, 440],
                    "opacity": 0.3,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#40916C", "#95D5B2"],
                "note": "竹节笔直，适合3字签名。"
            },
            {
                "id": "lianhua-yuanpai",
                "name": "莲花圆牌 (平和雅致)",
                "image": "莲花圆牌 (平和雅致).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 4,
                    "lineHeight": 72,
                    "fontSize": 68,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 645},
                    "maxChars": 10,
                    "fontSize": 30,
                    "color": "#2F3E46"
                },
                "glow": {
                    "shape": "circle",
                    "radius": [380, 380],
                    "opacity": 0.38,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#6BC9B0", "#FFE5D9"],
                "note": "圆牌留白充足，可保留副标题。"
            },
            {
                "id": "jinbian-moyu",
                "name": "金边墨玉璧 (沉稳庄重)",
                "image": "金边墨玉璧 (沉稳庄重).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 3,
                    "lineHeight": 74,
                    "fontSize": 66,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 650},
                    "maxChars": 8,
                    "fontSize": 28,
                    "color": "#1D3557"
                },
                "glow": {
                    "shape": "circle",
                    "radius": [360, 360],
                    "opacity": 0.32,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#264653", "#E9C46A"],
                "note": "墨玉色调沉稳，适合3字签名。"
            },
            {
                "id": "yinxing-ye",
                "name": "银杏叶 (坚韧与永恒)",
                "image": "银杏叶 (坚韧与永恒).png",
                "title": {
                    "type": "horizontal",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 6,
                    "lineHeight": 52,
                    "fontSize": 52,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 600},
                    "maxChars": 14,
                    "fontSize": 28,
                    "color": "#3F3B2C"
                },
                "glow": {
                    "shape": "leaf",
                    "radius": [460, 340],
                    "opacity": 0.36,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#E4CFA3", "#6D9773"],
                "note": "银杏叶横幅较宽，适合横排签名。"
            },
            {
                "id": "zhangming-suo",
                "name": "长命锁 (富贵安康)",
                "image": "长命锁 (富贵安康).png",
                "title": {
                    "type": "vertical",
                    "position": {"x": 512, "y": 540},
                    "maxChars": 3,
                    "lineHeight": 78,
                    "fontSize": 70,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 690},
                    "maxChars": 10,
                    "fontSize": 28,
                    "color": "#623412"
                },
                "glow": {
                    "shape": "cloud",
                    "radius": [360, 360],
                    "opacity": 0.34,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#F4A261", "#FEF3C7"],
                "note": "锁体呈祥云形，适合3字签名。"
            },
            {
                "id": "qingyu-tuanshan",
                "name": "青玉团扇 (清风徐来)",
                "image": "青玉团扇 (清风徐来).png",
                "title": {
                    "type": "horizontal",
                    "position": {"x": 512, "y": 530},
                    "maxChars": 6,
                    "lineHeight": 52,
                    "fontSize": 52,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 610},
                    "maxChars": 14,
                    "fontSize": 28,
                    "color": "#1E3A34"
                },
                "glow": {
                    "shape": "fan",
                    "radius": [420, 340],
                    "opacity": 0.34,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#6ABEA7", "#B7E4C7"],
                "note": "团扇上半部较宽，适合横排签名。"
            },
            {
                "id": "qinghua-cishan",
                "name": "青花瓷扇 (文化底蕴)",
                "image": "青花瓷扇 (文化底蕴).png",
                "title": {
                    "type": "horizontal",
                    "position": {"x": 512, "y": 520},
                    "maxChars": 6,
                    "lineHeight": 50,
                    "fontSize": 50,
                    "fontWeight": 600
                },
                "subtitle": {
                    "visible": True,
                    "position": {"x": 512, "y": 600},
                    "maxChars": 14,
                    "fontSize": 28,
                    "color": "#1F3C88"
                },
                "glow": {
                    "shape": "fan",
                    "radius": [440, 340],
                    "opacity": 0.34,
                    "blendMode": "screen"
                },
                "suggestedPalette": ["#1F3C88", "#A8C5F0"],
                "note": "青花纹路典雅，适合横排签名。"
            }
        ]
    
    def _analyze_quiz_answers(self, quiz_answers):
        """分析问答数据，生成洞察"""
        if not quiz_answers:
            return {
                "summary": "心境平和，内心安宁",
                "emotion_vector": {"calm": 0.7, "confidence": 0.6},
                "action_focus": ["保持平静"]
            }
        
        try:
            # 分析问答类别分布
            categories = {}
            for answer in quiz_answers:
                question_id = answer.get('question_id', '')
                category = question_id.split('_')[0] if '_' in question_id else 'unknown'
                if category not in categories:
                    categories[category] = []
                categories[category].append(answer.get('option_id', ''))
            
            # 基于问答生成洞察
            summary_parts = []
            emotion_vector = {}
            action_focus = []
            
            if 'mood' in categories:
                summary_parts.append("情绪状态有待关注")
                emotion_vector['awareness'] = 0.8
            if 'pressure' in categories:
                summary_parts.append("需要释放压力")
                emotion_vector['stress'] = 0.6
                action_focus.append("压力管理")
            if 'needs' in categories:
                summary_parts.append("内在需求清晰")
                emotion_vector['clarity'] = 0.7
            if 'action' in categories:
                summary_parts.append("行动意识强烈")
                action_focus.append("积极行动")
            if 'future' in categories:
                summary_parts.append("对未来有期待")
                emotion_vector['hope'] = 0.8
                action_focus.append("未来规划")
            
            return {
                "summary": "，".join(summary_parts) if summary_parts else "心境平和，内心安宁",
                "emotion_vector": emotion_vector if emotion_vector else {"calm": 0.7},
                "action_focus": action_focus if action_focus else ["保持平静"]
            }
            
        except Exception as e:
            self.logger.error(f"❌ 分析问答数据失败: {e}")
            return {
                "summary": "心境平和，内心安宁",
                "emotion_vector": {"calm": 0.7, "confidence": 0.6},
                "action_focus": ["保持平静"]
            }
    
    def _select_charm_style(self, concept, quiz_analysis):
        """基于概念和问答分析选择合适的签体"""
        try:
            # 解析概念数据
            concept_data = {}
            if isinstance(concept, str) and concept.strip().startswith('{'):
                concept_data = json.loads(concept)
            
            emotion_tone = concept_data.get('emotion_tone', '平静')
            atmosphere = concept_data.get('atmosphere', '温暖')
            charm_preference = concept_data.get('charm_style_preference', '雅致')
            
            # 签体选择逻辑
            style_mapping = {
                '庄重': ['jinbian-moyu', 'zhuchi-changpai', 'haitang-muchuang'],
                '雅致': ['lianhua-yuanpai', 'qingyu-tuanshan', 'qinghua-cishan'],
                '活泼': ['shuangyu-jinnang', 'xiangyun-liucai', 'yinxing-ye'],
                '深邃': ['bagua-jinnang', 'ruyi-jie', 'fangsheng-jie'],
                '温和': ['siyue-jinjie', 'zhangming-suo', 'xiangyun-hulu'],
                '清新': ['liujiao-denglong', 'zhujie-changtiao', 'juanzhou-huakuang']
            }
            
            # 根据氛围和偏好选择
            preferred_styles = []
            for style, charm_ids in style_mapping.items():
                if style in charm_preference or style in atmosphere:
                    preferred_styles.extend(charm_ids)
            
            # 如果没有匹配，使用默认列表
            if not preferred_styles:
                preferred_styles = ['lianhua-yuanpai', 'jinbian-moyu', 'qinghua-cishan']
            
            # 从匹配的签体中随机选择
            matched_charms = []
            for charm_config in self.charm_configs:
                if charm_config['id'] in preferred_styles:
                    matched_charms.append(charm_config)
            
            # 如果有匹配的签体，随机选择一个
            if matched_charms:
                return random.choice(matched_charms)
            
            # 兜底：从所有签体中随机选择
            return random.choice(self.charm_configs)
            
        except Exception as e:
            self.logger.error(f"❌ 选择签体失败: {e}")
            return self._get_default_charm()
    
    def _get_default_charm(self):
        """获取默认签体"""
        if self.charm_configs:
            return self.charm_configs[0]
        return {
            "id": "lianhua-yuanpai",
            "name": "莲花圆牌 (平和雅致)",
            "image": "莲花圆牌 (平和雅致).png"
        }
    
    def _get_default_concept(self, task):
        """获取默认心象签概念（兜底方案）"""
        return f"""{{
    "natural_scene": "晨光照进窗",
    "emotion_tone": "平静",
    "keywords": ["温和", "希望", "新开始"],
    "atmosphere": "温暖",
    "color_inspiration": "金黄",
    "charm_style_preference": "雅致"
}}"""