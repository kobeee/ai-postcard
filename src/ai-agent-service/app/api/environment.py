"""
环境感知API端点
提供地理位置查询、天气信息、热点新闻等基于Claude API智能服务
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging
from ..services.location_service import LocationService
from ..services.weather_news_service import WeatherNewsService
from ..services.trending_service import TrendingService
from ..services.free_news_api_service import FreeNewsAPIService
# from ..services.real_news_api_service import RealNewsAPIService  # 删除mock数据服务
from ..services.gemini_trending_service import GeminiTrendingService

logger = logging.getLogger(__name__)

router = APIRouter()

# 服务实例
location_service = LocationService()
weather_news_service = WeatherNewsService()
trending_service = TrendingService()
free_news_service = FreeNewsAPIService()
# real_news_service = RealNewsAPIService()  # 删除mock数据服务
gemini_trending_service = GeminiTrendingService()


@router.get("/health")
async def environment_health():
    """环境感知服务健康检查"""
    return {
        "status": "healthy",
        "service": "environment-service",
        "features": [
            "地理位置查询 (BigDataCloud/Nominatim 免费API)",
            "天气信息查询 (Open-Meteo 免费API)", 
            "热点新闻查询 (Claude WebSearch + 免费API)",
            "实时热点推荐 (Gemini Google Search Grounding)",
            "美食推荐查询 (Gemini专项搜索)"
        ],
        "note": "集成Claude和Gemini双AI引擎，提供真实时效的热点推荐"
    }


@router.get("/location/reverse")
async def reverse_geocode(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度"),
    language: str = Query("zh", description="语言")
):
    """
    使用Claude Code WebSearch工具进行逆地理解析
    根据经纬度获取城市信息
    """
    try:
        logger.info(f"📍 逆地理解析请求: {latitude}, {longitude}")
        result = await location_service.reverse_geocode(latitude, longitude)
        return result
        
    except Exception as e:
        logger.error(f"❌ 逆地理解析API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"地理位置查询失败: {str(e)}"
        )


@router.get("/weather")
async def get_weather(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度"),
    city: str = Query(None, description="城市名称(可选)")
):
    """
    使用Open-Meteo免费API查询实时天气信息
    """
    try:
        logger.info(f"🌤️ 天气查询请求: {latitude}, {longitude}, 城市: {city}")
        result = await weather_news_service.get_weather(latitude, longitude, city)
        return result
        
    except Exception as e:
        logger.error(f"❌ 天气查询API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"天气查询失败: {str(e)}"
        )


@router.get("/trending/news")
async def get_trending_news(
    city: str = Query(..., description="城市名称")
):
    """
    使用Claude API Web Search查询城市最新热点新闻
    """
    try:
        logger.info(f"📰 热点新闻查询请求: {city}")
        result = await weather_news_service.get_trending_news(city)
        return result
        
    except Exception as e:
        logger.error(f"❌ 热点新闻API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"热点新闻查询失败: {str(e)}"
        )


@router.get("/trending/social")
async def get_social_trends(
    city: str = Query(..., description="城市名称")
):
    """
    使用Claude API Web Search查询社交媒体热点话题（与综合查询相同）
    """
    try:
        logger.info(f"📱 社交热点查询请求: {city}")
        result = await weather_news_service.get_trending_news(city)
        return result
        
    except Exception as e:
        logger.error(f"❌ 社交热点API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"社交热点查询失败: {str(e)}"
        )


@router.get("/trending/comprehensive")
async def get_comprehensive_trends(
    city: str = Query(..., description="城市名称")
):
    """
    综合查询：使用修正后的Claude WebSearch获取城市最新热点信息
    """
    try:
        logger.info(f"🌟 综合热点查询请求: {city}")
        result = await trending_service.get_trending_news(city)
        return result
        
    except Exception as e:
        logger.error(f"❌ 综合热点API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"综合热点查询失败: {str(e)}"
        )


@router.get("/trending/fast")
async def get_fast_trending(
    city: str = Query(..., description="城市名称")
):
    """
    快速热点查询：使用免费新闻API，响应时间更短
    """
    try:
        logger.info(f"⚡ 快速热点查询请求: {city}")
        result = await free_news_service.get_trending_news(city)
        return result
        
    except Exception as e:
        logger.error(f"❌ 快速热点API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"快速热点查询失败: {str(e)}"
        )


@router.get("/trending/gemini")
async def get_gemini_trending(
    city: str = Query(..., description="城市名称")
):
    """
    Gemini实时热点查询：使用Google Search grounding获取真实的推荐类热点内容
    专注于美食、景点、活动等心情导向的推荐
    """
    try:
        logger.info(f"🔍 Gemini实时热点查询请求: {city}")
        result = await gemini_trending_service.get_trending_news(city)
        return result
        
    except Exception as e:
        logger.error(f"❌ Gemini热点API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Gemini热点查询失败: {str(e)}"
        )


@router.get("/trending/food")  
async def get_food_recommendations(
    city: str = Query(..., description="城市名称")
):
    """
    美食推荐：使用Gemini专门搜索美食相关的热点推荐
    """
    try:
        logger.info(f"🍽️ 美食推荐查询请求: {city}")
        result = await gemini_trending_service.get_food_recommendations(city)
        return result
        
    except Exception as e:
        logger.error(f"❌ 美食推荐API失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"美食推荐查询失败: {str(e)}"
        )


@router.get("/complete")
async def get_complete_environment(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度")
):
    """
    一站式环境信息查询
    包含位置信息、天气、以及基于位置的热点内容
    """
    try:
        logger.info(f"🎯 完整环境信息查询: {latitude}, {longitude}")
        
        # 并行查询位置信息
        import asyncio
        location_task = asyncio.create_task(location_service.reverse_geocode(latitude, longitude))
        location_result = await location_task
        
        # 获取城市名称用于天气和热点查询
        city_name = None
        if location_result.get("code") == 0 and location_result.get("data", {}).get("city"):
            city_name = location_result["data"]["city"]
        
        # 并行查询天气和热点（如果有城市名称）
        tasks = []
        weather_task = asyncio.create_task(weather_news_service.get_weather(latitude, longitude, city_name))
        tasks.append(weather_task)
        
        if city_name:
            trending_task = asyncio.create_task(weather_news_service.get_trending_news(city_name))
            tasks.append(trending_task)
        
        results = await asyncio.gather(*tasks)
        weather_result = results[0]
        trending_result = results[1] if len(results) > 1 else {"data": {"city": "Unknown", "news_items": [], "social_trends": [], "total_count": 0}}
        
        # 构建完整响应
        complete_data = {
            "location": location_result.get("data"),
            "weather": weather_result.get("data"),
            "trending": trending_result.get("data"),
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "query_time": int(asyncio.get_event_loop().time())
        }
        
        return {
            "code": 0,
            "message": "完整环境信息查询成功",
            "data": complete_data
        }
        
    except Exception as e:
        logger.error(f"❌ 完整环境信息查询失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"环境信息查询失败: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_environment_cache():
    """清理环境感知相关缓存（位置、天气、热点）。用于调试或强制刷新。"""
    try:
        # 清理地理位置缓存
        location_cleared = location_service.clear_cache()
        # 清理天气和热点缓存
        weather_cleared = weather_news_service.clear_cache()
        
        total_cleared = location_cleared + weather_cleared
        
        return {
            "code": 0, 
            "message": "缓存已清理", 
            "data": {
                "cleared": total_cleared, 
                "location": location_cleared, 
                "weather_trending": weather_cleared
            }
        }
    except Exception as e:
        logger.error(f"❌ 清理缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")