"""Import every model so Base.metadata is complete for Alembic autogenerate
and for scripts/seed.py."""
from app.models.ai import AiConversation, AiMessage  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.credential import Credential  # noqa: F401
from app.models.event import Event, EventLogEntry  # noqa: F401
from app.models.infrastructure import InfrastructureInventory, Server  # noqa: F401
from app.models.device import (  # noqa: F401
    Device,
    NetworkScan,
    DeviceInventory,
    DeviceNetworkInterface,
    DeviceStorage,
    DeviceMemory,
    DeviceProcessor,
    DeviceInstalledSoftware,
    DeviceService,
    DeviceInventoryHistory,
    DeviceScanHistory,
    DeviceStatusHistory,
    DeviceIPHistory,
    DevicePartition,
    DeviceProcess,
    DeviceSecurity,
    DevicePort,
)
from app.models.knowledge import Document, DocumentChunk, RagQueryLog, RagEvaluation  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.rbac import Permission, Role, RolePermission, UserRole  # noqa: F401
from app.models.script import Script, ScriptVersion  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import RefreshToken, User  # noqa: F401
from app.models.department_designation import Department, Designation  # noqa: F401


