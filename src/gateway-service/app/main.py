from fastapi import FastAPI
import os
import logging
from logging.handlers import RotatingFileHandler

app = FastAPI(
    title="Gateway Service",
    description="API Gateway for routing requests to microservices, handling authentication, rate limiting, and request/response transformations.",
    version="0.1.0"
)

# 日志到 /app/logs
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(log_dir, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = RotatingFileHandler(os.path.join(log_dir, 'gateway-service.log'), maxBytes=10*1024*1024, backupCount=5)
fh.setFormatter(fmt)
fh.setLevel(logging.INFO)
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(fh)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Gateway Service"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
