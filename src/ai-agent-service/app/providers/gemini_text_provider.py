from google import genai
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
            
        # 使用新SDK创建客户端，并设置http_options.base_url
        base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
        self.client = genai.Client(
            api_key=api_key,
            http_options=genai.types.HttpOptions(base_url=base_url)
        )
        
        # 配置模型参数
        self.model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash-lite")
        self.default_config = {
            "temperature": float(os.getenv("GEMINI_TEXT_TEMPERATURE", "0.7")),
            "max_output_tokens": int(os.getenv("GEMINI_TEXT_MAX_TOKENS", "2048")),
        }
        
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
            self.logger.info(f"📝 开始生成文本，模型: {self.model_name}")
            
            # 使用新SDK在线程池中运行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            )
            
            if response.candidates and len(response.candidates) > 0:
                content_parts = response.candidates[0].content.parts
                
                # 提取文本内容
                text_parts = []
                for part in content_parts:
                    if part.text is not None:
                        text_parts.append(part.text)
                
                if text_parts:
                    result = "".join(text_parts)
                    self.logger.info(f"✅ 文本生成成功，长度: {len(result)} 字符")
                    return result
                else:
                    raise Exception("Gemini返回的响应中没有文本内容")
            else:
                raise Exception("Gemini文本生成返回空响应或无候选结果")
                
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