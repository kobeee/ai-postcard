from fastapi import FastAPI

app = FastAPI(
    title="User Service",
    description="Handles user authentication, profile management, and related operations.",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the User Service"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
