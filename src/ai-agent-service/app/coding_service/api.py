import asyncio
import uuid
from typing import Dict, AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from .engine import engine

router = APIRouter()

class GenerateCodeRequest(BaseModel):
    """代码生成请求的数据模型"""
    prompt: str
    model: str = None  # 可选的模型参数

class GenerateCodeResponse(BaseModel):
    """代码生成请求的响应模型"""
    task_id: str
    status: str

class TaskManager:
    """
    简单的内存任务管理器。
    
    在生产环境中，这应该被替换为Redis或数据库存储，
    以支持多实例部署和任务持久化。
    """
    
    def __init__(self):
        self.tasks: Dict[str, AsyncGenerator] = {}
        self.task_status: Dict[str, str] = {}
    
    async def create_task(self, prompt: str, model: str = None) -> str:
        """创建一个新的代码生成任务"""
        task_id = str(uuid.uuid4())
        
        # 创建代码生成的异步生成器
        generator = engine.generate_code(prompt, model)
        
        # 存储任务
        self.tasks[task_id] = generator
        self.task_status[task_id] = "pending"
        
        return task_id
    
    def get_task_generator(self, task_id: str) -> AsyncGenerator:
        """获取任务的生成器"""
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> str:
        """获取任务状态"""
        return self.task_status.get(task_id, "not_found")
    
    def update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        self.task_status[task_id] = status
    
    def cleanup_task(self, task_id: str):
        """清理已完成的任务"""
        self.tasks.pop(task_id, None)
        self.task_status.pop(task_id, None)

# 创建任务管理器实例
task_manager = TaskManager()

@router.post("/generate-code", response_model=GenerateCodeResponse)
async def generate_code(request: GenerateCodeRequest):
    """
    创建代码生成任务的HTTP端点。
    
    这是一个异步端点，立即返回task_id，不等待生成完成。
    客户端需要通过WebSocket连接来接收实时的生成过程。
    """
    try:
        task_id = await task_manager.create_task(request.prompt, request.model)
        
        return GenerateCodeResponse(
            task_id=task_id,
            status="created"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建代码生成任务失败: {str(e)}"
        )

@router.websocket("/status/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: str):
    """
    通过WebSocket流式传输任务状态和生成结果的端点。
    
    客户端连接此端点后，将实时收到：
    - thought事件：AI的思考过程
    - code_chunk事件：代码片段  
    - complete事件：生成完成和最终代码
    - error事件：错误信息
    """
    await websocket.accept()
    
    try:
        # 获取任务生成器
        generator = task_manager.get_task_generator(task_id)
        
        if not generator:
            await websocket.send_json({
                "type": "error",
                "content": f"任务 {task_id} 不存在"
            })
            await websocket.close()
            return
        
        # 更新任务状态为进行中
        task_manager.update_task_status(task_id, "processing")
        
        # 流式传输生成结果
        async for event in generator:
            await websocket.send_json(event)
            
            # 如果是完成或错误事件，更新状态并结束
            if event.get("type") == "complete":
                task_manager.update_task_status(task_id, "completed")
                break
            elif event.get("type") == "error":
                task_manager.update_task_status(task_id, "failed")
                break
    
    except WebSocketDisconnect:
        print(f"客户端断开了与任务 {task_id} 的连接")
    
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"处理任务时发生错误: {str(e)}"
            })
            task_manager.update_task_status(task_id, "failed")
        except:
            pass  # 如果连接已断开，发送会失败
    
    finally:
        # 清理任务资源
        task_manager.cleanup_task(task_id)
        
        # 确保WebSocket连接正常关闭
        try:
            await websocket.close()
        except:
            pass

@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    获取任务状态的HTTP端点（可选）。
    
    主要用于调试或客户端检查任务是否存在。
    实际的结果获取应该通过WebSocket进行。
    """
    status = task_manager.get_task_status(task_id)
    
    if status == "not_found":
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {"task_id": task_id, "status": status}




