import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from core import CoreEngine
from core.handlers import register_default_handlers
from server.api.routes import register_routes
from server.database.repository import DatabaseRepository
from server.middlewares.cors import setup_cors
from server.services.context_service import ContextService
from server.services.ignore_service import IgnoreService
from server.services.profile_service import ProfileService
from server.services.project_service import ProjectService

register_default_handlers()

repo = DatabaseRepository("fs_orchestrator.db")
ignore_service = IgnoreService("fsignore_global")
context_service = ContextService(ignore_service)
engine = CoreEngine()
project_service = ProjectService(repo, context_service, engine)
profile_service = ProfileService(repo)

app = FastAPI(title="Safe AI Patch Orchestrator API", version="2.0")

setup_cors(app)

router = register_routes(repo, project_service, profile_service, context_service)
app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "safe-ai-orchestrator"}


@app.get("/images/{filename:path}")
def serve_image(filename: str):
    images_root = os.path.realpath("images")
    target = os.path.realpath(os.path.join(images_root, filename))
    if not (target == images_root or target.startswith(images_root + os.sep)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(target)


frontend_dist = os.path.abspath(os.path.join("frontend", "dist"))
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="127.0.0.1", port=18420, reload=True)