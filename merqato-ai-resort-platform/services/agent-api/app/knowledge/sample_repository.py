from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class KnowledgeEntry:
    source_id: str
    title: str
    content: str
    verified: bool = True


@dataclass
class ResortKnowledge:
    resort_id: str
    is_sample: bool
    entries: list[KnowledgeEntry] = field(default_factory=list)

    @property
    def context(self) -> str:
        return "\n\n".join(
            f"- {e.title}: {e.content} (source: {e.source_id}, verified={e.verified})"
            for e in self.entries
        )


class KnowledgeRepository(ABC):
    """Loads verified knowledge scoped to a single resort.

    Implementations MUST isolate one resort's knowledge from every other and
    MUST report when requested information is missing.
    """

    @abstractmethod
    def load(self, resort_id: str) -> ResortKnowledge:
        raise NotImplementedError


class SampleKnowledgeRepository(KnowledgeRepository):
    """Local-dev fixture. Clearly labeled SAMPLE — NOT BAIA Resort data.

    LEGACY / NOT ON THE ACTIVE CONCIERGE PATH. The multi-tenant knowledge
    foundation (app.knowledge.repository.KnowledgeRepository, the Supabase +
    Qdrant pipeline) has superseded this for production retrieval. Kept only as
    a labeled sample and to avoid breaking unrelated references.
    """

    def load(self, resort_id: str) -> ResortKnowledge:
        return ResortKnowledge(
            resort_id=resort_id,
            is_sample=True,
            entries=[
                KnowledgeEntry(
                    source_id="sample:welcome",
                    title="Welcome",
                    content=(
                        "This is SAMPLE demonstration knowledge for resort "
                        f"'{resort_id}'. It is not real resort information."
                    ),
                    verified=True,
                ),
                KnowledgeEntry(
                    source_id="sample:hours",
                    title="Front desk hours",
                    content="Front desk is open 24/7 in this sample dataset.",
                    verified=True,
                ),
            ],
        )


_repository: KnowledgeRepository | None = None


def get_knowledge_repository() -> KnowledgeRepository:
    global _repository
    if _repository is None:
        _repository = SampleKnowledgeRepository()
    return _repository
