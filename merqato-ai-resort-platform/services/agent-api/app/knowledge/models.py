from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    """Explicit ISO-8601 UTC timestamp for REST payloads and Qdrant metadata.

    PostgREST treats values literally — the string "now()" is NOT evaluated
    as SQL — so timestamps are always generated here.
    """
    return datetime.now(UTC).isoformat()


class Category(enum.StrEnum):
    IDENTITY = "identity"
    ROOMS = "rooms"
    RATES = "rates"
    AMENITIES = "amenities"
    POLICIES = "policies"
    WIFI_POWER = "wifi_power"
    FOOD_BREAKFAST = "food_breakfast"
    TRANSPORT = "transport"
    EMERGENCY_CONTACTS = "emergency_contacts"
    FAQ = "faq"

    @classmethod
    def from_filename(cls, stem: str) -> Category:
        try:
            return cls(stem)
        except ValueError as err:
            raise ValueError(f"unsupported knowledge category: {stem!r}") from err

    @classmethod
    def values(cls) -> set[str]:
        return {c.value for c in cls}


class SourceType(enum.StrEnum):
    JSON_FIXTURE = "json_fixture"
    JSON_UPLOAD = "json_upload"
    DASHBOARD_FORM = "dashboard_form"
    API_IMPORT = "api_import"


class VerificationStatus(enum.StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"

    @classmethod
    def values(cls) -> set[str]:
        return {s.value for s in cls}


class IngestionStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class KnowledgeChunk:
    chunk_index: int
    text: str
    category: str
    source_filename: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddedChunk:
    id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass
class IngestionResult:
    tenant_slug: str
    category: str
    document_id: str | None
    version: int | None
    checksum: str
    skipped: bool
    indexed: bool
    job_status: str
    chunks_created: int
    error: str | None = None


def new_uuid() -> str:
    return str(uuid4())
