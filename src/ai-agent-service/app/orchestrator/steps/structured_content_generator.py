import logging
import json
import random
from typing import Dict, Any, Optional
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class StructuredContentGenerator:
    """结构化内容生成器 - 替代Claude Code SDK，生成丰富的结构化数据"""
    
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
            
            self.logger.info("🎨 开始生成结构化内容...")
            
            # 构建增强的Prompt
            enhanced_prompt = self._build_structured_prompt(task, concept, content)
            
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
            
            # 保存结构化数据到结果中
            results["structured_data"] = parsed_data
            
            self.logger.info("✅ 结构化内容生成完成")
            self.logger.info(f"📊 生成内容包含：{list(parsed_data.keys())}")
            
            context["results"] = results
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 结构化内容生成失败: {e}")
            raise
    
    def _build_structured_prompt(self, task: Dict[str, Any], concept: str, content: str) -> str:
        """构建结构化内容生成的Prompt"""
        user_input = task.get("user_input", "")
        style = task.get("style", "")
        theme = task.get("theme", "")
        
        # 解析用户输入中的地理位置信息
        location_info = self._extract_location_info(user_input)
        
        # 随机选择推荐类型（至少1项，通常2项，偶尔3项，提高丰富度）
        recommendation_types = ["music", "book", "movie"]
        selected_recommendations = random.sample(recommendation_types, k=random.choice([1, 2, 2, 3]))
        
        recommendations_instruction = ""
        if "music" in selected_recommendations:
            recommendations_instruction += "- 推荐至少一首适合当前情绪的歌曲（包含歌手、推荐理由），可附带第2首作为备选\n"
        if "book" in selected_recommendations:
            recommendations_instruction += "- 推荐至少一本相关的书籍（包含作者、推荐理由），可附带第2本作为备选\n"
        if "movie" in selected_recommendations:
            recommendations_instruction += "- 推荐至少一部相关的电影（包含导演、推荐理由），可附带第2部作为备选\n"
        
        prompt = f"""
请基于以下信息生成一张个性化明信片的结构化数据，以JSON格式返回：

## 用户信息
- 用户输入：{user_input}
- 风格：{style}
- 主题：{theme}
- 概念：{concept}
- 基础内容：{content}

## 生成要求
请生成包含以下结构的JSON数据：

```json
{{
  "title": "精彩标题（8-15字）",
  "mood": {{
    "primary": "主要情绪（如：开心、思考、期待等）",
    "secondary": "次要情绪（可选）",
    "intensity": 情绪强度(1-10),
    "color_theme": "主题色彩（十六进制）"
  }},
  "content": {{
    "main_text": "核心文案（25-40字，简练有力，一句话表达）",
    "sub_text": "补充文案（可选，15-25字，用于翻转后的卡片背面）",
    "hot_topics": {{
      "xiaohongshu": "小红书话题形式内容（不要#号，15-25字描述体验感受）",
      "douyin": "抖音热点形式内容（不要#号，15-25字生活化表达）"
    }},
    "quote": {{
      "text": "优美英文格言（6-12个单词，意境深远）",
      "author": "作者",
      "translation": "中文翻译（8-15字，诗意表达）"
    }}
  }},
  "extras": {{
    "reflections": ["深度反思内容（20-30字，有哲理性）", "第二条反思（18-25字，不同角度）", "深层思考（可选）"],
    "gratitude": ["具体感谢事物（15-22字，细节丰富）", "第二条感谢（12-20字，不同层面）", "细节感恩（可选）"], 
    "micro_actions": ["今日可实践的具体行动（18-25字）", "延伸行动建议（15-22字）", "进阶实践（可选）"],
    "mood_tips": ["情绪调节具体方法（20-30字）", "深层心理建议（18-25字）", "进阶技巧（可选）"],
    "life_insights": ["生活感悟（25-35字，有启发性）", "人生思考（20-30字，不同维度）", "智慧总结（可选）"],
    "creative_spark": ["创意灵感或想法（18-28字）", "艺术表达建议（15-25字）", "创作启发（可选）"],
    "mindfulness": ["当下觉察练习（20-30字）", "冥想或放松方法（18-28字）", "深度觉察（可选）"],
    "future_vision": ["对未来的美好期待（25-35字）", "具体愿景（20-30字）", "长远规划（可选）"]
  }},
  "recommendations": {{
    // 随机包含以下1-3种推荐（至少返回一种）。每种推荐可返回对象或数组；如返回多个请使用数组。
{recommendations_instruction.rstrip()}
    // 推荐格式参考（允许数组或对象）：
    // "music": [{{"title": "歌曲名", "artist": "歌手", "reason": "推荐理由"}}]
    // "book":  [{{"title": "书名", "author": "作者", "reason": "推荐理由"}}]
    // "movie": [{{"title": "电影名", "director": "导演", "reason": "推荐理由"}}]
  }},
  "visual": {{
    "style_hints": {{
      "animation_type": "动效类型：float（浮动）/pulse（脉冲）/gradient（渐变）",
      "color_scheme": ["#主色调", "#辅助色"],
      "layout_style": "布局风格：minimal（简约）/rich（丰富）/artistic（艺术）"
    }}
  }},
  "context": {{
    "location": "地理位置信息（如有）",
    "weather": "天气信息（如有）",
    "time_context": "时间背景（如：morning/afternoon/evening）"
  }}
}}
```

## 内容要求
1. **简洁精炼优先**：内容务必简洁有力，适合移动端卡片显示
   - 严格控制文字长度，避免冗长表述
   - 一句话表达核心思想，删除多余修饰
   - 推荐理由简明扼要，不超过15字

2. **个性化深度定制**：内容要有温度、有个性，能引起用户情感共鸣
   - 避免千篇一律的通用内容
   - 基于具体的地理位置、天气、时间等环境因素个性化生成
   - 杭州不要总是西湖，北京不要总是故宫，要挖掘更多独特视角

3. **时尚感与真实性**：适当融入小红书/抖音等平台的热点话题和表达方式
   - 使用年轻人喜欢的表达方式，但要自然不做作
   - 结合当下的流行元素和网络热点

4. **文化深度**：英文格言要与情绪和场景相关，翻译要优美
   - 选择有深度、有意境的格言，避免过于常见的句子
   - 中文翻译要优雅，体现文化内涵

5. **推荐精准且多元**：音乐/书籍/电影推荐要与当前情绪和场景高度匹配
   - 推荐内容要具体，包含详细理由
   - 考虑不同年龄段、兴趣爱好的多元化需求
   - 推荐理由要个人化且简洁，不超过15字

6. **视觉协调**：色彩和动效要与情绪氛围一致
   - 根据情绪强度选择合适的视觉表现形式

7. **背面内容丰富化**（extras字段）：卡片背面应提供深层次、互补性内容
   - **必须生成6-8个不同类型的extras内容**，每个类型提供2-3条内容，确保背面内容非常充实
   - 背面内容要与正面形成深度互补，而不是简单重复
   - 优先生成多条内容而非单条，让用户有更多选择和启发
   - reflections: 基于当前情绪的深度哲学思考，有启发性
   - gratitude: 具体而微的感谢对象，细节丰富有画面感
   - micro_actions: 可立即执行的小行动，实用且有意义
   - mood_tips: 实用的情绪管理技巧，不是空泛建议
   - life_insights: 人生感悟，要有深度和普适性
   - creative_spark: 创意想法或艺术表达建议
   - mindfulness: 当下觉察或冥想方法，具体可操作
   - future_vision: 对未来的美好憧憬，积极向上

## 个性化约束
- 地理位置相关内容要避免刻板印象，挖掘城市的独特魅力和隐藏故事
- 天气描述要生动有趣，不要使用"阳光明媚"等常见词汇
- 情绪表达要细腻真实，能够触动内心
- 推荐内容要有惊喜感，让用户感到"这就是为我量身定制的"

请直接返回JSON格式的结构化数据，不要添加其他文字说明。
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
        """解析并验证Gemini返回的结构化数据"""
        try:
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("响应中未找到JSON数据")
            
            json_str = response[json_start:json_end]
            raw_parsed_data = json.loads(json_str)
            
            # 🔧 修复：处理AI返回列表而非字典的情况
            self.logger.debug(f"🐛 调试：AI返回数据类型: {type(raw_parsed_data)}")
            if isinstance(raw_parsed_data, list):
                self.logger.debug(f"🐛 调试：数组长度: {len(raw_parsed_data)}")
                if len(raw_parsed_data) > 0 and isinstance(raw_parsed_data[0], dict):
                    parsed_data = raw_parsed_data[0]  # 取第一个字典元素
                    self.logger.warning("⚠️ AI返回了数组格式，已自动提取第一个对象")
                else:
                    raise ValueError("AI返回的数组中没有有效的字典对象")
            elif isinstance(raw_parsed_data, dict):
                parsed_data = raw_parsed_data
                self.logger.debug(f"🐛 调试：字典键列表: {list(raw_parsed_data.keys())}")
            else:
                raise ValueError(f"AI返回了不支持的数据类型: {type(raw_parsed_data)}")
            
            # 基本验证
            required_fields = ["title", "mood", "content"]
            for field in required_fields:
                if field not in parsed_data:
                    self.logger.warning(f"⚠️ 缺少必需字段：{field}")
            
            # 设置默认值
            if "visual" not in parsed_data:
                parsed_data["visual"] = {}
            # 🔧 修复：确保visual字段是字典类型
            if not isinstance(parsed_data["visual"], dict):
                self.logger.warning(f"⚠️ AI返回了非字典类型的visual: {type(parsed_data['visual'])}")
                parsed_data["visual"] = {}
            if "style_hints" not in parsed_data["visual"]:
                parsed_data["visual"]["style_hints"] = {
                    "animation_type": "float",
                    "color_scheme": ["#6366f1", "#8b5cf6"],
                    "layout_style": "minimal"
                }
            
            # 规范化推荐字段：允许数组或对象；确保存在键时统一为列表；并尽量保证至少返回一项
            rec_data = parsed_data.get("recommendations", {}) or {}
            self.logger.debug(f"🐛 调试：recommendations数据类型: {type(rec_data)}")
            # 🔧 修复：确保rec始终是字典类型
            if isinstance(rec_data, dict):
                rec = rec_data
                self.logger.debug(f"🐛 调试：recommendations键列表: {list(rec_data.keys())}")
            else:
                # 如果AI返回的是列表或其他类型，转换为空字典
                self.logger.warning(f"⚠️ AI返回了非字典类型的recommendations: {type(rec_data)}, 内容: {rec_data}")
                rec = {}
            
            def ensure_list(x):
                if not x:
                    return []
                return x if isinstance(x, list) else [x]
            for key in ["music", "book", "movie"]:
                if key in rec:
                    rec[key] = ensure_list(rec[key])
            # 若三项都为空，尝试从 quote 或 mood 生成一条兜底音乐推荐
            if not any(rec.get(k) for k in ["music", "book", "movie"]):
                mood_data = parsed_data.get("mood")
                self.logger.debug(f"🐛 调试：mood数据类型: {type(mood_data)}, 内容: {mood_data}")
                if isinstance(mood_data, dict):
                    mood = mood_data.get("primary", "calm")
                elif isinstance(mood_data, str):
                    mood = mood_data
                else:
                    mood = "calm"
                rec["music"] = [{"title": "Lo-fi Beats", "artist": "Various", "reason": f"适合当前情绪: {mood}"}]
            parsed_data["recommendations"] = rec

            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON解析失败: {e}")
            self.logger.error(f"🐛 AI原始响应内容: {response[:1000]}...") # 只记录前1000字符避免日志过长
            if 'json_str' in locals():
                self.logger.error(f"🐛 提取的JSON字符串: {json_str}")
            # 返回基础结构
            return self._get_fallback_structure()
        except Exception as e:
            import traceback
            self.logger.error(f"❌ 数据验证失败: {e}")
            self.logger.error(f"🐛 详细错误堆栈: {traceback.format_exc()}")
            self.logger.error(f"🐛 当前parsed_data类型: {type(parsed_data) if 'parsed_data' in locals() else 'undefined'}")
            if 'parsed_data' in locals():
                self.logger.error(f"🐛 当前parsed_data内容: {parsed_data}")
            return self._get_fallback_structure()
    
    def _get_fallback_structure(self) -> Dict[str, Any]:
        """获取降级的基础数据结构"""
        # 随机选择降级内容，避免每次都一样
        fallback_options = [
            {
                "title": "心境",
                "mood": {
                    "primary": "平静",
                    "intensity": 6,
                    "color_theme": "#6366f1"
                },
                "content": {
                    "main_text": "今天也要保持期待。",
                    "quote": {
                        "text": "Life happens while planning.",
                        "author": "John Lennon",
                        "translation": "生活就在计划中发生。"
                    }
                },
                "recommendations": {
                    "music": {
                        "title": "晴天",
                        "artist": "周杰伦",
                        "reason": "适合当下心情"
                    }
                },
                "visual": {
                    "style_hints": {
                        "animation_type": "float",
                        "color_scheme": ["#6366f1", "#8b5cf6"],
                        "layout_style": "minimal"
                    }
                }
            },
            {
                "title": "感受",
                "mood": {
                    "primary": "思考",
                    "intensity": 5,
                    "color_theme": "#10b981"
                },
                "content": {
                    "main_text": "慢下来，感受当下。",
                    "quote": {
                        "text": "Live in the moment.",
                        "author": "Thích Nhất Hạnh",
                        "translation": "活在当下。"
                    }
                },
                "recommendations": {
                    "book": {
                        "title": "正念的奇迹",
                        "author": "一行禅师",
                        "reason": "与当前心境契合"
                    }
                },
                "visual": {
                    "style_hints": {
                        "animation_type": "pulse",
                        "color_scheme": ["#10b981", "#06b6d4"],
                        "layout_style": "artistic"
                    }
                }
            }
        ]
        
        return random.choice(fallback_options)
