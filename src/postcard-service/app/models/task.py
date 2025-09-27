from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime

class TaskType(str, Enum):
    POSTCARD_GENERATION = "postcard_generation"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class QuizAnswer(BaseModel):
    question_id: str
    option_id: str
    option_label: str

class PostcardGenerationTask(BaseModel):
    task_id: str
    task_type: TaskType = TaskType.POSTCARD_GENERATION
    user_input: str
    style: Optional[str] = None
    theme: Optional[str] = None
    user_id: Optional[str] = None
    created_at: str
    # 🆕 版本3.0新增：直接包含base64编码的情绪图片数据
    emotion_image_base64: Optional[str] = None
    # 🆕 心象签新增：问答数据
    quiz_answers: Optional[List[QuizAnswer]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PostcardRequest(BaseModel):
    user_input: str
    style: Optional[str] = None
    theme: Optional[str] = None
    user_id: Optional[str] = None
    # 🆕 版本3.0新增：直接接收base64编码的情绪图片数据
    emotion_image_base64: Optional[str] = None
    # 🆕 心象签新增：问答数据
    quiz_answers: Optional[List[QuizAnswer]] = Field(default_factory=list)

class PostcardResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    concept: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    frontend_code: Optional[str] = None
    preview_url: Optional[str] = None
    card_image_url: Optional[str] = None
    card_html: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None  # 原始结构化数据字段
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # 🆕 版本3.0新增：扁平化字段（支持前端优先使用，避免小程序传递丢失）
    # 基础字段
    card_title: Optional[str] = None
    
    # 情绪字段
    mood_primary: Optional[str] = None
    mood_intensity: Optional[int] = None
    mood_secondary: Optional[str] = None
    mood_color_theme: Optional[str] = None
    
    # 视觉样式字段
    visual_color_scheme: Optional[List[str]] = None
    visual_layout_style: Optional[str] = None
    visual_animation_type: Optional[str] = None
    visual_background_image: Optional[str] = None
    
    # 内容字段
    content_main_text: Optional[str] = None
    content_quote_text: Optional[str] = None
    content_quote_author: Optional[str] = None
    content_quote_translation: Optional[str] = None
    content_hot_topics_douyin: Optional[str] = None
    content_hot_topics_xiaohongshu: Optional[str] = None
    
    # 上下文字段
    context_weather: Optional[str] = None
    context_location: Optional[str] = None
    context_time: Optional[str] = None
    
    # 推荐内容字段
    recommendations_music_title: Optional[str] = None
    recommendations_music_artist: Optional[str] = None
    recommendations_music_reason: Optional[str] = None
    recommendations_book_title: Optional[str] = None
    recommendations_book_author: Optional[str] = None
    recommendations_book_reason: Optional[str] = None
    recommendations_movie_title: Optional[str] = None
    recommendations_movie_director: Optional[str] = None
    recommendations_movie_reason: Optional[str] = None
    
    # 🔥 关键新增：8个扩展字段，为卡片背面提供丰富内容
    extras_reflections: Optional[Union[List[str], str]] = None
    extras_gratitude: Optional[Union[List[str], str]] = None
    extras_micro_actions: Optional[Union[List[str], str]] = None
    extras_mood_tips: Optional[Union[List[str], str]] = None
    extras_life_insights: Optional[Union[List[str], str]] = None
    extras_creative_spark: Optional[Union[List[str], str]] = None
    extras_mindfulness: Optional[Union[List[str], str]] = None
    extras_future_vision: Optional[Union[List[str], str]] = None
    
    # 🔮 心象签扁平化字段 - 覆盖原有旧字段结构
    oracle_title: Optional[str] = None
    oracle_subtitle: Optional[str] = None
    oracle_affirmation: Optional[str] = None
    oracle_hexagram_name: Optional[str] = None
    oracle_hexagram_symbol: Optional[str] = None
    oracle_hexagram_insight: Optional[str] = None
    oracle_daily_guides: Optional[List[str]] = None
    oracle_daily_guide_1: Optional[str] = None
    oracle_daily_guide_2: Optional[str] = None
    oracle_daily_guide_3: Optional[str] = None
    oracle_fengshui_focus: Optional[str] = None
    oracle_ritual_hint: Optional[str] = None
    oracle_element_wood: Optional[float] = None
    oracle_element_fire: Optional[float] = None
    oracle_element_earth: Optional[float] = None
    oracle_element_metal: Optional[float] = None
    oracle_element_water: Optional[float] = None
    oracle_stroke_impression: Optional[str] = None
    oracle_symbolic_keywords: Optional[List[str]] = None
    oracle_symbolic_keyword_1: Optional[str] = None
    oracle_symbolic_keyword_2: Optional[str] = None
    oracle_symbolic_keyword_3: Optional[str] = None
    oracle_stroke_count: Optional[int] = None
    oracle_dominant_quadrant: Optional[str] = None
    oracle_pressure_tendency: Optional[str] = None
    oracle_session_time: Optional[str] = None
    oracle_season_hint: Optional[str] = None
    oracle_visit_pattern: Optional[str] = None
    oracle_historical_keywords: Optional[List[str]] = None
    oracle_blessing_stream: Optional[List[str]] = None
    oracle_blessing_1: Optional[str] = None
    oracle_blessing_2: Optional[str] = None
    oracle_blessing_3: Optional[str] = None
    oracle_blessing_4: Optional[str] = None
    oracle_blessing_5: Optional[str] = None
    oracle_blessing_6: Optional[str] = None
    oracle_image_prompt: Optional[str] = None
    oracle_palette: Optional[List[str]] = None
    oracle_color_1: Optional[str] = None
    oracle_color_2: Optional[str] = None
    oracle_color_3: Optional[str] = None
    oracle_animation_hint: Optional[str] = None
    oracle_culture_note: Optional[str] = None

class UpdateStatusRequest(BaseModel):
    status: TaskStatus
    error_message: Optional[str] = None
    # 可选：在更新状态时一并写入最终结果
    concept: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    frontend_code: Optional[str] = None
    preview_url: Optional[str] = None
    card_image_url: Optional[str] = None
    card_html: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None  # 新增结构化数据字段

class StatusUpdateRequest(BaseModel):
    status: TaskStatus
    error_message: Optional[str] = None