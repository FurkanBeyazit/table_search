import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routers import search, stats, server, analysis

import database

app = FastAPI(title="Security Analytics Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(search.router)
app.include_router(stats.router)
app.include_router(server.router)
app.include_router(analysis.router)


# ── Yeni UI (beta) — Gradio'dan bağımsız, sadece ek route ──────────────────────
_WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")

    @app.get("/app")
    def serve_dashboard():
        return FileResponse(os.path.join(_WEB_DIR, "dashboard.html"))


@app.on_event("startup")
def startup():
    database.init_db()


if __name__ == "__main__":
    import uvicorn
    print("\n  API  →  http://localhost:8090")
    print("  Docs →  http://localhost:8090/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8090, reload=True)
