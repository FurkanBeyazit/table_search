from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import search

app = FastAPI(title="Security Analytics Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(search.router)

if __name__ == "__main__":
    import uvicorn
    print("\n  API  →  http://localhost:8000")
    print("  Docs →  http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
