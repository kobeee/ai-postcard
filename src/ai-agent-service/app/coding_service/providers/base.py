from abc import ABC, abstractmethod
from typing import AsyncGenerator

class BaseCodeProvider(ABC):
    """
    AI代码生成模型的抽象基类，定义了统一的调用接口。
    
    这个抽象层隔离了不同AI服务商(Claude、Gemini等)的SDK、API或CLI实现差异，
    为上层业务逻辑提供统一、稳定的调用接口。
    """
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str,
        session_id: str,
        model: str | None = None
    ) -> AsyncGenerator[dict, None]:
        """
        根据给定的prompt异步生成代码。
        
        这是一个异步生成器，会 yield 不同类型的事件字典。
        
        Args:
            prompt (str): 用户的输入描述，描述要生成的前端代码需求。
            session_id (str): 用于跟踪和调试的会话ID。
            model (str | None): 指定要使用的具体模型。
                                  如果为None，则使用Provider的默认模型。
        
        Yields:
            dict: 代表生成事件的字典，可能的事件类型：
                - {"type": "thought", "content": "AI的思考过程..."}
                - {"type": "code_chunk", "content": "<button>...</button>"}
                - {"type": "error", "content": "错误信息..."}
                - {"type": "complete", "final_code": "完整的HTML/CSS/JS代码"}
        """
        # 这是一个抽象方法，不应该有实际的实现
        # yield 语句在这里只是为了文档目的
        yield {}




