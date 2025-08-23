import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseProvider(ABC):
    """AI服务提供商基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    def __str__(self):
        return f"{self.__class__.__name__}"

class BaseTextProvider(BaseProvider):
    """文本生成提供商基类"""
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """生成文本"""
        pass

class BaseImageProvider(BaseProvider):
    """图片生成提供商基类"""
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成图片"""
        pass

class BaseCodeProvider(BaseProvider):
    """代码生成提供商基类"""
    
    @abstractmethod
    async def generate_code(
        self,
        prompt: str,
        language: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成代码"""
        pass