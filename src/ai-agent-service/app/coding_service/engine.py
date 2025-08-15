import uuid
from typing import AsyncGenerator
from .providers import get_provider_instance

class CodeGenerationEngine:
    """
    AI代码生成引擎，负责协调AI Provider完成代码生成任务。
    
    这个引擎封装了任务创建、会话管理和结果流式传输的逻辑，
    为上层API提供简洁的接口。
    """
    
    def __init__(self):
        self.provider = get_provider_instance()
    
    async def generate_code(self, prompt: str, model: str = None) -> AsyncGenerator[dict, None]:
        """
        根据用户提示生成前端代码。
        
        Args:
            prompt: 用户的编码需求描述
            model: 可选的特定模型名称，如果不提供则使用默认模型
            
        Yields:
            dict: 生成过程中的事件，包括思考过程、代码片段和最终结果
        """
        # 生成唯一的会话ID用于跟踪
        session_id = f"coding_session_{uuid.uuid4().hex[:12]}"
        
        try:
            # 调用Provider进行代码生成
            async for event in self.provider.generate(prompt, session_id, model):
                yield event
                
                # 如果遇到错误或完成事件，结束生成
                if event.get("type") in ["error", "complete"]:
                    break
        
        except Exception as e:
            yield {
                "type": "error",
                "content": f"代码生成引擎发生内部错误: {str(e)}"
            }

# 创建全局引擎实例
engine = CodeGenerationEngine()




