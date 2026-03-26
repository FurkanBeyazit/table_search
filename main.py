from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import search, stats, server, analysis

import database

app = FastAPI(title="Security Analytics Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(stats.router)
app.include_router(server.router)
app.include_router(analysis.router)


@app.on_event("startup")
def startup():
    database.init_db()


if __name__ == "__main__":
    import uvicorn
    print("\n  API  →  http://localhost:8000")
    print("  Docs →  http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
