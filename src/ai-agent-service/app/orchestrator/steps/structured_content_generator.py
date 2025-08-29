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
  "title": "简洁标题（6-10字）",
  "mood": {{
    "primary": "主要情绪（如：开心、思考、期待等）",
    "secondary": "次要情绪（可选）",
    "intensity": 情绪强度(1-10),
    "color_theme": "主题色彩（十六进制）"
  }},
  "content": {{
    "main_text": "核心文案（25-40字，简练有力，一句话表达）",
    "hot_topics": {{
      "xiaohongshu": "小红书话题（15字内，可选）",
      "douyin": "抖音热点（15字内，可选）"
    }},
    "quote": {{
      "text": "简洁英文格言（不超6个单词）",
      "author": "作者",
      "translation": "中文翻译（不超10字）"
    }}
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
   - 推荐理由要简明扼要，不超过15字

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
            parsed_data = json.loads(json_str)
            
            # 基本验证
            required_fields = ["title", "mood", "content"]
            for field in required_fields:
                if field not in parsed_data:
                    self.logger.warning(f"⚠️ 缺少必需字段：{field}")
            
            # 设置默认值
            if "visual" not in parsed_data:
                parsed_data["visual"] = {}
            if "style_hints" not in parsed_data["visual"]:
                parsed_data["visual"]["style_hints"] = {
                    "animation_type": "float",
                    "color_scheme": ["#6366f1", "#8b5cf6"],
                    "layout_style": "minimal"
                }
            
            # 规范化推荐字段：允许数组或对象；确保存在键时统一为列表；并尽量保证至少返回一项
            rec = parsed_data.get("recommendations", {}) or {}
            def ensure_list(x):
                if not x:
                    return []
                return x if isinstance(x, list) else [x]
            for key in ["music", "book", "movie"]:
                if key in rec:
                    rec[key] = ensure_list(rec[key])
            # 若三项都为空，尝试从 quote 或 mood 生成一条兜底音乐推荐
            if not any(rec.get(k) for k in ["music", "book", "movie"]):
                mood = (parsed_data.get("mood") or {}).get("primary") or "calm"
                rec["music"] = [{"title": "Lo-fi Beats", "artist": "Various", "reason": f"适合当前情绪: {mood}"}]
            parsed_data["recommendations"] = rec

            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON解析失败: {e}")
            # 返回基础结构
            return self._get_fallback_structure()
        except Exception as e:
            self.logger.error(f"❌ 数据验证失败: {e}")
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
