"""
AI Agent 工作进程
独立运行的消息队列消费者，用于处理明信片生成任务
"""

import asyncio
import logging
import signal
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from .queue.consumer import TaskConsumer

class Worker:
    """AI Agent 工作进程"""
    
    def __init__(self):
        self.consumer = TaskConsumer()
        self.running = False
    
    async def start(self):
        """启动工作进程"""
        try:
            logger.info("🚀 启动 AI Agent Worker")
            
            # 连接Redis
            await self.consumer.connect()
            
            # 设置信号处理
            self.setup_signal_handlers()
            
            # 开始消费任务
            self.running = True
            await self.consumer.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("📧 收到中断信号")
        except Exception as e:
            logger.error(f"❌ Worker启动失败: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """停止工作进程"""
        if self.running:
            logger.info("🔄 停止 AI Agent Worker")
            self.running = False
            await self.consumer.stop_consuming()
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"📧 收到信号 {signum}")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """主函数"""
    worker = Worker()
    try:
        await worker.start()
    except Exception as e:
        logger.error(f"❌ Worker运行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())