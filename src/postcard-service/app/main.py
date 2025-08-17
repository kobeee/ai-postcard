from fastapi import FastAPI

app = FastAPI(
    title="Postcard Service",
    description="Handles postcard creation, management, templates, and AI-powered content generation.",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Postcard Service"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
