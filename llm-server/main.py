from fastapi import FastAPI

app = FastAPI(title="AI Code Review API", 
              description="API for code review using various AI models")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 