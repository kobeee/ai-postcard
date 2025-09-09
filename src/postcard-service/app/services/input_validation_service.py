# -*- coding: utf-8 -*-
"""
输入验证和清洗服务
防止XSS、SQL注入、恶意输入等安全威胁
"""

import re
import html
import json
import logging
from typing import Any, Dict, Optional, List, Union
from urllib.parse import urlparse, quote
import bleach
from pydantic import BaseModel, field_validator, ValidationInfo

logger = logging.getLogger(__name__)


class InputValidationConfig:
    """输入验证配置"""
    
    # 允许的HTML标签和属性（白名单）
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'span']
    ALLOWED_ATTRIBUTES = {
        'span': ['class'],
        'p': ['class']
    }
    
    # 字符串长度限制
    MAX_INPUT_LENGTH = 2000  # 用户输入最大长度
    MAX_TITLE_LENGTH = 100   # 标题最大长度
    MAX_THEME_LENGTH = 50    # 主题最大长度
    
    # 正则表达式模式
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'user_id': re.compile(r'^[a-zA-Z0-9_-]{1,50}$'),
        'chinese_text': re.compile(r'^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\w\s\.,!?;:\'\"()（），。！？；：""''、]+$'),
        'safe_filename': re.compile(r'^[a-zA-Z0-9._-]+$'),
        'hex_color': re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'),
        'url': re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    }
    
    # 恶意模式检测
    MALICIOUS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # onload, onclick等
        re.compile(r'eval\s*\(', re.IGNORECASE),
        re.compile(r'expression\s*\(', re.IGNORECASE),
        re.compile(r'(union|select|insert|update|delete|drop|create|alter)\s+', re.IGNORECASE),
        re.compile(r'(\.\./|\.\.\\)', re.IGNORECASE),  # 路径遍历
    ]


class InputValidationService:
    """输入验证和清洗服务"""
    
    def __init__(self):
        self.config = InputValidationConfig()
        
    def validate_and_sanitize_user_input(self, user_input: str) -> Dict[str, Any]:
        """验证和清洗用户输入"""
        result = {
            "is_valid": True,
            "sanitized_input": "",
            "errors": [],
            "warnings": []
        }
        
        try:
            # 1. 基础检查
            if not user_input or not isinstance(user_input, str):
                result["is_valid"] = False
                result["errors"].append("输入内容不能为空")
                return result
            
            # 2. 长度检查
            if len(user_input) > self.config.MAX_INPUT_LENGTH:
                result["is_valid"] = False
                result["errors"].append(f"输入内容过长，最大允许{self.config.MAX_INPUT_LENGTH}字符")
                return result
            
            # 3. 恶意模式检测
            malicious_found = self._detect_malicious_patterns(user_input)
            if malicious_found:
                result["is_valid"] = False
                result["errors"].append("检测到潜在的安全风险内容")
                logger.warning(f"🚨 恶意输入检测: {malicious_found[:100]}...")
                return result
            
            # 4. HTML清洗
            sanitized = self._sanitize_html(user_input)
            
            # 5. 中文文本验证
            if not self._is_valid_chinese_text(sanitized):
                result["warnings"].append("输入包含特殊字符，已进行清理")
            
            result["sanitized_input"] = sanitized
            
        except Exception as e:
            logger.error(f"❌ 输入验证失败: {str(e)}")
            result["is_valid"] = False
            result["errors"].append("输入验证过程出现错误")
        
        return result
    
    def validate_theme_and_style(self, theme: str, style: str) -> Dict[str, Any]:
        """验证主题和样式参数"""
        result = {
            "is_valid": True,
            "sanitized_theme": "",
            "sanitized_style": "",
            "errors": []
        }
        
        try:
            # 验证主题
            if theme:
                if len(theme) > self.config.MAX_THEME_LENGTH:
                    result["errors"].append(f"主题名称过长，最大允许{self.config.MAX_THEME_LENGTH}字符")
                    result["is_valid"] = False
                
                if self._detect_malicious_patterns(theme):
                    result["errors"].append("主题包含不安全内容")
                    result["is_valid"] = False
                else:
                    result["sanitized_theme"] = self._sanitize_plain_text(theme)
            
            # 验证样式
            if style:
                if len(style) > self.config.MAX_THEME_LENGTH:
                    result["errors"].append(f"样式名称过长，最大允许{self.config.MAX_THEME_LENGTH}字符")
                    result["is_valid"] = False
                
                if self._detect_malicious_patterns(style):
                    result["errors"].append("样式包含不安全内容")
                    result["is_valid"] = False
                else:
                    result["sanitized_style"] = self._sanitize_plain_text(style)
        
        except Exception as e:
            logger.error(f"❌ 主题样式验证失败: {str(e)}")
            result["is_valid"] = False
            result["errors"].append("主题样式验证出现错误")
        
        return result
    
    def validate_user_id(self, user_id: str) -> Dict[str, Any]:
        """验证用户ID格式"""
        result = {
            "is_valid": True,
            "sanitized_user_id": "",
            "errors": []
        }
        
        try:
            if not user_id or not isinstance(user_id, str):
                result["is_valid"] = False
                result["errors"].append("用户ID不能为空")
                return result
            
            if not self.config.PATTERNS['user_id'].match(user_id):
                result["is_valid"] = False
                result["errors"].append("用户ID格式不正确")
                return result
            
            result["sanitized_user_id"] = user_id
            
        except Exception as e:
            logger.error(f"❌ 用户ID验证失败: {str(e)}")
            result["is_valid"] = False
            result["errors"].append("用户ID验证出现错误")
        
        return result
    
    def validate_emotion_image_data(self, image_data: str) -> Dict[str, Any]:
        """验证情绪图片数据"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            if not image_data:
                # 情绪图片是可选的
                return result
            
            # 检查Base64格式
            if not self._is_valid_base64_image(image_data):
                result["is_valid"] = False
                result["errors"].append("图片数据格式不正确")
                return result
            
            # 检查数据大小（避免过大的图片）
            if len(image_data) > 5 * 1024 * 1024:  # 5MB limit
                result["is_valid"] = False
                result["errors"].append("图片数据过大，请使用更小的图片")
                return result
        
        except Exception as e:
            logger.error(f"❌ 图片数据验证失败: {str(e)}")
            result["is_valid"] = False
            result["errors"].append("图片数据验证出现错误")
        
        return result
    
    def _detect_malicious_patterns(self, text: str) -> Optional[str]:
        """检测恶意模式"""
        for pattern in self.config.MALICIOUS_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group()
        return None
    
    def _sanitize_html(self, text: str) -> str:
        """清洗HTML内容"""
        # 使用bleach库清洗HTML
        cleaned = bleach.clean(
            text,
            tags=self.config.ALLOWED_TAGS,
            attributes=self.config.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        # 额外的HTML实体编码
        cleaned = html.escape(cleaned, quote=False)
        
        return cleaned.strip()
    
    def _sanitize_plain_text(self, text: str) -> str:
        """清洗纯文本"""
        # 移除控制字符
        cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # HTML实体编码
        cleaned = html.escape(cleaned, quote=True)
        
        return cleaned.strip()
    
    def _is_valid_chinese_text(self, text: str) -> bool:
        """检查是否为有效的中文文本"""
        return self.config.PATTERNS['chinese_text'].match(text) is not None
    
    def _is_valid_base64_image(self, data: str) -> bool:
        """检查是否为有效的Base64图片数据"""
        try:
            # 检查Base64格式前缀
            valid_prefixes = ['data:image/jpeg;base64,', 'data:image/png;base64,', 'data:image/gif;base64,']
            
            if not any(data.startswith(prefix) for prefix in valid_prefixes):
                return False
            
            # 提取Base64部分
            base64_data = data.split(',', 1)[1]
            
            # 检查Base64字符
            import base64
            base64.b64decode(base64_data, validate=True)
            return True
            
        except Exception:
            return False


class RequestValidationMiddleware:
    """请求验证中间件"""
    
    def __init__(self):
        self.validator = InputValidationService()
        
    async def validate_postcard_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证明信片创建请求"""
        result = {
            "is_valid": True,
            "sanitized_data": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # 验证用户ID（在JWT方案下为可选，若由认证中间件注入则无需校验请求体）
            incoming_user_id = request_data.get('user_id', '')
            if incoming_user_id:
                user_id_result = self.validator.validate_user_id(incoming_user_id)
                if not user_id_result["is_valid"]:
                    result["is_valid"] = False
                    result["errors"].extend(user_id_result["errors"])
                else:
                    result["sanitized_data"]["user_id"] = user_id_result["sanitized_user_id"]
            
            # 验证用户输入
            user_input_result = self.validator.validate_and_sanitize_user_input(
                request_data.get('user_input', '')
            )
            if not user_input_result["is_valid"]:
                result["is_valid"] = False
                result["errors"].extend(user_input_result["errors"])
            else:
                result["sanitized_data"]["user_input"] = user_input_result["sanitized_input"]
                result["warnings"].extend(user_input_result["warnings"])
            
            # 验证主题和样式
            theme_style_result = self.validator.validate_theme_and_style(
                request_data.get('theme', ''),
                request_data.get('style', '')
            )
            if not theme_style_result["is_valid"]:
                result["is_valid"] = False
                result["errors"].extend(theme_style_result["errors"])
            else:
                result["sanitized_data"]["theme"] = theme_style_result["sanitized_theme"]
                result["sanitized_data"]["style"] = theme_style_result["sanitized_style"]
            
            # 验证情绪图片数据（可选）
            image_data_result = self.validator.validate_emotion_image_data(
                request_data.get('emotion_image_base64', '')
            )
            if not image_data_result["is_valid"]:
                result["is_valid"] = False
                result["errors"].extend(image_data_result["errors"])
            else:
                result["sanitized_data"]["emotion_image_base64"] = request_data.get('emotion_image_base64', '')
                result["warnings"].extend(image_data_result["warnings"])
            
        except Exception as e:
            logger.error(f"❌ 请求验证失败: {str(e)}")
            result["is_valid"] = False
            result["errors"].append("请求验证过程出现错误")
        
        return result


# Pydantic模型用于API请求验证
class PostcardCreateRequestModel(BaseModel):
    """明信片创建请求模型"""
    user_id: str
    user_input: str
    theme: Optional[str] = ""
    style: Optional[str] = ""
    emotion_image_base64: Optional[str] = ""
    
    @field_validator('user_id')
    def validate_user_id(cls, v):
        validator_service = InputValidationService()
        result = validator_service.validate_user_id(v)
        if not result["is_valid"]:
            raise ValueError(f"用户ID验证失败: {', '.join(result['errors'])}")
        return result["sanitized_user_id"]
    
    @field_validator('user_input')
    def validate_user_input(cls, v):
        validator_service = InputValidationService()
        result = validator_service.validate_and_sanitize_user_input(v)
        if not result["is_valid"]:
            raise ValueError(f"用户输入验证失败: {', '.join(result['errors'])}")
        return result["sanitized_input"]
    
    @field_validator('theme', 'style')
    def validate_theme_style(cls, v, info: ValidationInfo):
        if not v:
            return v
        validator_service = InputValidationService()
        result = validator_service.validate_theme_and_style(v, v)
        field_key = "sanitized_theme" if (getattr(info, 'field_name', None) == "theme") else "sanitized_style"
        if not result["is_valid"]:
            field_name = getattr(info, 'field_name', 'field')
            raise ValueError(f"{field_name}验证失败: {', '.join(result['errors'])}")
        return result[field_key]
    
    @field_validator('emotion_image_base64')
    def validate_emotion_image(cls, v):
        if not v:
            return v
        validator_service = InputValidationService()
        result = validator_service.validate_emotion_image_data(v)
        if not result["is_valid"]:
            raise ValueError(f"情绪图片验证失败: {', '.join(result['errors'])}")
        return v
