import google.generativeai as genai
from typing import Dict, Any, Optional
from .base_provider import BaseTextProvider
import os
import asyncio

class GeminiTextProvider(BaseTextProvider):
    """Gemini文本生成服务提供商"""
    
    def __init__(self):
        super().__init__()
        
        # 配置Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY环境变量未配置")
            
        genai.configure(api_key=api_key)
        
        # 配置模型参数
        self.model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash-lite")
        self.default_config = {
            "temperature": float(os.getenv("GEMINI_TEXT_TEMPERATURE", "0.7")),
            "max_output_tokens": int(os.getenv("GEMINI_TEXT_MAX_TOKENS", "2048")),
            "top_p": 0.8,
            "top_k": 40
        }
        
        # 初始化模型
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.GenerationConfig(**self.default_config)
        )
        
        self.logger.info(f"✅ Gemini文本提供商初始化成功: {self.model_name}")
    
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """生成文本内容"""
        try:
            # 动态配置生成参数
            config = self.default_config.copy()
            if max_tokens:
                config["max_output_tokens"] = max_tokens
            if temperature is not None:
                config["temperature"] = temperature
            
            # 重新配置模型
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.GenerationConfig(**config)
            )
            
            # 生成内容 - 使用同步调用然后包装为异步
            self.logger.info(f"📝 开始生成文本，模型: {self.model_name}")
            
            # Gemini Python SDK 目前主要是同步的，我们在线程池中运行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: model.generate_content(prompt)
            )
            
            if response.parts:
                result = response.text
                self.logger.info(f"✅ 文本生成成功，长度: {len(result)} 字符")
                return result
            else:
                raise Exception("Gemini返回空响应")
                
        except Exception as e:
            self.logger.error(f"❌ Gemini文本生成失败: {e}")
            raise
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            test_response = await self.generate_text("测试连接", max_tokens=10)
            return bool(test_response)
        except:
            return False