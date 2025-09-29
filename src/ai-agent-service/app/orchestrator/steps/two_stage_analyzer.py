import logging
import json
import asyncio
from typing import Dict, Any, Optional
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class TwoStageAnalyzer:
    """阶段1：用户洞察分析器 - 专注心理分析"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 重试配置
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # 指数退避
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行用户洞察分析"""
        task = context["task"]
        task_id = task.get("task_id")
        
        self.logger.info(f"🧠 开始用户洞察分析: {task_id}")
        
        # 带重试的分析执行
        analysis_result = await self._analyze_with_retry(task)
        
        # 将分析结果保存到context
        context["results"]["analysis"] = analysis_result
        
        self.logger.info(f"✅ 用户洞察分析完成: {task_id}")
        return context
    
    async def _analyze_with_retry(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """带重试机制的分析执行"""
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"📝 第{attempt+1}次分析尝试")
                
                # 构建分析prompt
                prompt = self._build_analysis_prompt(task)
                
                # 调用Gemini
                response = await self.provider.generate_text(
                    prompt=prompt,
                    max_tokens=800,
                    temperature=0.7 + attempt * 0.1  # 逐步提高创造性
                )
                
                # 解析响应
                analysis_result = self._parse_analysis_response(response)
                
                # 验证结果
                if self._validate_analysis_result(analysis_result):
                    return analysis_result
                else:
                    raise ValueError("分析结果验证失败")
                    
            except Exception as e:
                self.logger.error(f"❌ 第{attempt+1}次分析失败: {e}")
                
                if attempt < self.max_retries - 1:
                    # 还有重试机会
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # 最后一次失败，使用规则降级
                    self.logger.warning(f"⚠️ 所有重试失败，使用规则降级")
                    return self._get_rule_based_analysis(task)
    
    def _build_analysis_prompt(self, task: Dict[str, Any]) -> str:
        """构建分析prompt"""
        
        user_input = task.get("user_input", "")
        drawing_data = task.get("drawing_data", {}).get("analysis", {})
        quiz_answers = task.get("quiz_answers", [])
        
        # 处理绘画数据
        stroke_count = drawing_data.get("stroke_count", 0)
        drawing_time = drawing_data.get("drawing_time", 0)
        dominant_quadrant = drawing_data.get("dominant_quadrant", "center")
        pressure_tendency = drawing_data.get("pressure_tendency", "steady")
        
        # 处理问答数据
        quiz_summary = self._summarize_quiz_answers(quiz_answers)
        
        prompt = f"""你是专业的心理分析师，专门从用户行为中洞察内在心理状态。

## 分析任务
基于以下用户数据进行深度心理分析，输出结构化报告。

## 输入数据
**用户描述**: {user_input}
**绘画分析**: 笔画{stroke_count}笔，{drawing_time}ms，主要区域{dominant_quadrant}，压力{pressure_tendency}
**问答结果**: {quiz_summary}

## 分析维度

### 1. 心理特征识别
- 从绘画笔触推断当前情绪状态
- 从问答模式识别核心心理需求
- 综合判断整体心境类型

### 2. 五行能量评估
基于心理状态计算五行能量分布（0.0-1.0）：
- 木(成长活力) - 创新学习倾向
- 火(热情表达) - 社交展现欲望  
- 土(稳定平和) - 安全平衡需求
- 金(坚韧精进) - 目标达成意志
- 水(智慧内省) - 深度思考特质

### 3. 卦象匹配
选择最符合用户当前状态的易经卦象，给出现代化解读。

## 输出格式
严格按以下JSON格式返回：

```json
{{
  "psychological_profile": {{
    "emotion_state": "平静/焦虑/兴奋/沉思/愉悦",
    "core_needs": ["具体需求1", "具体需求2"],
    "energy_type": "活跃/平衡/内省",
    "dominant_traits": ["特质1", "特质2", "特质3"]
  }},
  "five_elements": {{
    "wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5
  }},
  "hexagram_match": {{
    "name": "卦象名称",
    "modern_name": "现代化解读名",
    "insight": "一句话核心启示(不超过20字)"
  }},
  "key_insights": ["洞察1", "洞察2", "洞察3"]
}}
```

专注分析，保持客观专业，避免创作内容。"""
        
        return prompt
    
    def _summarize_quiz_answers(self, quiz_answers: list) -> str:
        """总结问答结果"""
        if not quiz_answers:
            return "未提供问答数据"
        
        summary_parts = []
        for answer in quiz_answers[:3]:  # 只取前3个答案
            question_id = answer.get("question_id", "")
            option_id = answer.get("option_id", "")
            summary_parts.append(f"{question_id}选择{option_id}")
        
        return "，".join(summary_parts)
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析分析响应"""
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
    
    def _validate_analysis_result(self, analysis: Dict[str, Any]) -> bool:
        """验证分析结果"""
        try:
            # 检查必需字段
            required_fields = ["psychological_profile", "five_elements", "hexagram_match", "key_insights"]
            for field in required_fields:
                if field not in analysis:
                    self.logger.error(f"❌ 缺少必需字段: {field}")
                    return False
            
            # 检查心理档案结构
            profile = analysis.get("psychological_profile", {})
            profile_fields = ["emotion_state", "core_needs", "energy_type", "dominant_traits"]
            for field in profile_fields:
                if field not in profile:
                    self.logger.error(f"❌ 心理档案缺少字段: {field}")
                    return False
            
            # 检查五行数据
            five_elements = analysis.get("five_elements", {})
            element_names = ["wood", "fire", "earth", "metal", "water"]
            for element in element_names:
                if element not in five_elements:
                    self.logger.error(f"❌ 五行缺少元素: {element}")
                    return False
                
                # 检查数值范围
                value = five_elements[element]
                if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                    self.logger.error(f"❌ 五行数值错误: {element}={value}")
                    return False
            
            # 检查卦象匹配
            hexagram = analysis.get("hexagram_match", {})
            hexagram_fields = ["name", "modern_name", "insight"]
            for field in hexagram_fields:
                if field not in hexagram:
                    self.logger.error(f"❌ 卦象匹配缺少字段: {field}")
                    return False
            
            self.logger.info("✅ 分析结果验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 验证异常: {e}")
            return False
    
    def _get_rule_based_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """规则降级分析"""
        from .rule_based_analyzer import RuleBasedAnalyzer
        
        analyzer = RuleBasedAnalyzer()
        return analyzer.analyze(task)