from fastapi import FastAPI

app = FastAPI(
    title="Gateway Service",
    description="API Gateway for routing requests to microservices, handling authentication, rate limiting, and request/response transformations.",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Gateway Service"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
