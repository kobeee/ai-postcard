from typing import Dict, Type, Any
from .base_provider import BaseTextProvider, BaseImageProvider, BaseCodeProvider
from .gemini_text_provider import GeminiTextProvider
from .gemini_image_provider import GeminiImageProvider
from .laozhang_image_provider import LaoZhangImageProvider
from ..coding_service.providers.claude_provider import ClaudeCodeProvider

class ProviderFactory:
    """AI服务提供商工厂"""
    
    _text_providers: Dict[str, Type[BaseTextProvider]] = {
        "gemini": GeminiTextProvider,
        # "claude": ClaudeTextProvider,  # 如需要文本生成
    }
    
    _image_providers: Dict[str, Type[BaseImageProvider]] = {
        "gemini": GeminiImageProvider,
        "laozhang": LaoZhangImageProvider,
        # "dalle": DalleProvider,  # 未来扩展
    }
    
    _code_providers: Dict[str, Type[BaseCodeProvider]] = {
        "claude": ClaudeCodeProvider,
    }
    
    @classmethod
    def create_text_provider(cls, provider_type: str = "gemini") -> BaseTextProvider:
        """创建文本生成提供商"""
        if provider_type not in cls._text_providers:
            raise ValueError(f"不支持的文本提供商: {provider_type}")
        return cls._text_providers[provider_type]()
    
    @classmethod
    def create_image_provider(cls, provider_type: str = "gemini") -> BaseImageProvider:
        """创建图片生成提供商"""
        if provider_type not in cls._image_providers:
            raise ValueError(f"不支持的图片提供商: {provider_type}")
        return cls._image_providers[provider_type]()
    
    @classmethod
    def create_code_provider(cls, provider_type: str = "claude") -> BaseCodeProvider:
        """创建代码生成提供商"""
        if provider_type not in cls._code_providers:
            raise ValueError(f"不支持的代码提供商: {provider_type}")
        return cls._code_providers[provider_type]()
    
    @classmethod
    def list_providers(cls) -> Dict[str, list]:
        """列出所有可用的提供商"""
        return {
            "text": list(cls._text_providers.keys()),
            "image": list(cls._image_providers.keys()),
            "code": list(cls._code_providers.keys())
        }