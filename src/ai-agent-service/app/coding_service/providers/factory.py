from .base import BaseCodeProvider
from .claude_provider import ClaudeCodeProvider
from ..config import settings

def get_provider() -> BaseCodeProvider:
    """
    根据环境变量配置，返回一个具体的代码生成提供者实例。
    
    这是一个工厂函数，支持动态选择不同的AI服务商。
    当前支持 'claude'，未来可扩展到 'gemini', 'qwen' 等。
    
    Returns:
        BaseCodeProvider: 配置的代码生成提供者实例
        
    Raises:
        ValueError: 当配置了不支持的提供者类型时
    """
    provider_name = settings.AI_PROVIDER_TYPE.lower()
    
    if provider_name == "claude":
        return ClaudeCodeProvider()
    # elif provider_name == "gemini":
    #     return GeminiCLIProvider()
    # elif provider_name == "qwen":
    #     return QwenCoderProvider()
    else:
        raise ValueError(f"不支持的AI提供者: {provider_name}. 当前支持: claude")

# 创建全局单例实例
# 注意：这个实例会在模块导入时创建，确保整个应用共享同一个provider
_provider_instance = None

def get_provider_instance() -> BaseCodeProvider:
    """获取Provider的单例实例"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = get_provider()
    return _provider_instance




