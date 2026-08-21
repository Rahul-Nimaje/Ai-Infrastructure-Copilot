from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.modules.authentication.router import router as auth_router
from app.modules.credentials.router import router as credentials_router
from app.modules.infrastructure_inventory.router import router as inventory_router
from app.modules.windows_event_log_analyzer.router import router as event_log_router
from app.modules.scripts.router import router as scripts_router
from app.modules.tasks.router import router as tasks_router
from app.modules.ai_chat.router import router as ai_chat_router
from app.modules.users.router import router as users_router
from app.modules.rbac.router import router as rbac_router
from app.modules.discovery import discovery_router, network_router, inventory_router as discovery_inventory_router, devices_router
from app.modules.departments.router import router as departments_router
from app.modules.designations.router import router as designations_router
from app.modules.knowledge.router import router as knowledge_router, rag_router
from app.socket_app import socket_asgi_app

app = FastAPI(title="AI Infrastructure Copilot API", version="0.1.0-phase1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(credentials_router)
app.include_router(inventory_router)
app.include_router(event_log_router)
app.include_router(scripts_router)
app.include_router(tasks_router)
app.include_router(ai_chat_router)
app.include_router(users_router)
app.include_router(rbac_router)
app.include_router(discovery_router)
app.include_router(network_router)
app.include_router(discovery_inventory_router)
app.include_router(devices_router)
app.include_router(departments_router)
app.include_router(designations_router)
app.include_router(knowledge_router)
app.include_router(rag_router)

app.mount("/socket.io", socket_asgi_app)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}

