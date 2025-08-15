from pydantic_settings import BaseSettings
from typing import Optional

class CodingServiceSettings(BaseSettings):
    """
    AI编码服务的配置管理器。
    
    使用Pydantic BaseSettings从环境变量中加载配置，
    支持多Provider的可扩展配置结构。
    """
    
    # --- 通用设置 ---
    APP_NAME: str = "AI Postcard Coding Service"
    API_V1_STR: str = "/api/v1"
    
    # --- Provider 路由配置 ---
    AI_PROVIDER_TYPE: str = "claude"  # 'claude', 'gemini', 'qwen'
    
    # --- Claude Provider 配置 ---
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: Optional[str] = None  # 可选，用于代理或自定义端点
    CLAUDE_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_FALLBACK_MODEL: Optional[str] = None  # 用于K2等备用模型
    
    # --- Gemini Provider 配置 (未来扩展) ---
    GEMINI_API_KEY: Optional[str] = None
    
    # --- Qwen Provider 配置 (未来扩展) ---
    QWEN_API_KEY: Optional[str] = None
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量，避免与其他服务的配置冲突

# 创建全局配置实例
settings = CodingServiceSettings()




