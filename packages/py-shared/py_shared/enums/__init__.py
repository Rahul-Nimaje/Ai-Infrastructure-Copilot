"""Enums mirroring the VARCHAR status/type columns in docs/04-database-design.md.

Kept as plain str Enums (not Postgres native enums) to match the schema's own
convention of VARCHAR + comment, so adding a new value is a data migration, not
a schema migration.
"""
from enum import Enum


class OrgStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class UserStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class OsType(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"


class ServerEnvironment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CredentialType(str, Enum):
    WINRM = "winrm"
    SSH_PASSWORD = "ssh_password"
    SSH_KEY = "ssh_key"
    API_KEY = "api_key"
    CLOUD_IAM = "cloud_iam"
    SNMP_V2C = "snmp_v2c"
    SNMP_V3 = "snmp_v3"


class VaultEngine(str, Enum):
    HASHICORP_VAULT = "hashicorp_vault"
    LOCAL_ENCRYPTED = "local_encrypted"  # MVP simplification, see plan Section "MVP simplifications" #3


class ScriptLanguage(str, Enum):
    POWERSHELL = "powershell"
    BASH = "bash"
    PYTHON = "python"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    SCRIPT_EXECUTION = "script_execution"
    WORKFLOW_STEP = "workflow_step"
    REMEDIATION = "remediation"


class TaskStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXECUTION_SKIPPED_FLAGGED_OFF = "execution_skipped_flagged_off"


class ExecutionMethod(str, Enum):
    WINRM = "winrm"
    SSH = "ssh"


class EventLogChannel(str, Enum):
    APPLICATION = "Application"
    SYSTEM = "System"
    SECURITY = "Security"


class EventLogLevel(str, Enum):
    INFORMATION = "Information"
    WARNING = "Warning"
    ERROR = "Error"
    CRITICAL = "Critical"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentName(str, Enum):
    """Canonical agent names — must match docs/README.md exactly."""

    PLANNER = "Planner Agent"
    COORDINATOR = "Coordinator Agent"
    WINDOWS = "Windows Agent"
    POWERSHELL = "PowerShell Agent"
    RAG = "RAG Agent"


class ToolAnnotation(str, Enum):
    """Mutation boundary per docs/06-ai-architecture.md Section 5.1 — enforced
    at the tool-function level, not trusted from LLM behavior."""

    READ = "read"
    PROPOSE = "propose"


class DocumentStatus(str, Enum):
    """Lifecycle states for knowledge-base documents."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETING = "deleting"


class DocumentType(str, Enum):
    """Supported file types for knowledge-base ingestion."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "md"
    CSV = "csv"
    HTML = "html"
    POWERSHELL = "ps1"
    BASH = "sh"


class QueryIntent(str, Enum):
    """Planner-classified intent for AI chat queries."""

    GENERAL = "general"
    RAG = "rag"
    INFRASTRUCTURE = "infrastructure"
    RAG_AND_INFRASTRUCTURE = "rag_and_infrastructure"


class DeviceType(str, Enum):
    """Classification produced by discovery's identify_device() step."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    PRINTER = "printer"
    NAS = "nas"
    VMWARE_ESXI = "vmware_esxi"
    HYPER_V = "hyper-v"
    KUBERNETES_NODE = "kubernetes_node"
    DOCKER_HOST = "docker_host"
    VIRTUAL_MACHINE = "virtual_machine"
    ACCESS_POINT = "access_point"
    IP_CAMERA = "ip_camera"
    IOT = "iot"
    PROXMOX = "proxmox"
    UNKNOWN = "unknown"


class DeviceIdentificationConfidence(str, Enum):
    """How identify_device() arrived at Device.device_type — never claim
    'confirmed' from a heuristic alone."""

    CONFIRMED = "confirmed"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class DeviceStatus(str, Enum):
    """Network reachability, distinct from ScanStatus/DeviceScanStatus which
    track inventory-collection lifecycle."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class ScanStatus(str, Enum):
    """NetworkScan.status lifecycle."""

    PENDING = "pending"
    DISCOVERING = "discovering"
    IDENTIFYING = "identifying"
    SCANNING = "scanning"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CREDENTIALS_REQUIRED = "credentials_required"
    CANCELLED = "cancelled"


class DeviceScanStatus(str, Enum):
    """Device.scan_status — per-device inventory-collection lifecycle."""

    DISCOVERED = "discovered"
    IDENTIFYING = "identifying"
    SCANNING = "scanning"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CREDENTIALS_REQUIRED = "credentials_required"
    OFFLINE = "offline"


class ScanMode(str, Enum):
    """Depth of a discovery scan, selected by the user in the UI."""

    QUICK = "quick"
    STANDARD = "standard"
    FULL = "full"
