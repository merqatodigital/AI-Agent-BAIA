# mypy: ignore-errors
# CrewAI's CrewBase metaclass/decorators (@agent/@task/@crew) perform runtime
# magic that mypy cannot statically model (dynamic config-dict attributes and
# decorator self-binding). The pytest suites prove runtime correctness.

from __future__ import annotations

from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from pydantic import ConfigDict

from app.config import get_settings
from app.knowledge.embeddings import EmbeddingProvider, get_embedding_provider
from app.knowledge.qdrant_store import TenantQdrantStore
from app.services.tenant_resolver import TenantContext, TenantResolutionError


class TenantKnowledgeTool(BaseTool):
    """Typed tenant-specific retrieval tool wrapping qdrant_store.py.

    This is the ACCEPTABLE custom adapter. It performs semantic search
    EXCLUSIVELY within the verified tenant's Qdrant collection. There is no
    cross-tenant search method, and the collection name is fixed at construction
    from the verified TenantContext (never a client override).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "tenant_knowledge_search"
    description: str = (
        "Semantic search over the verified tenant's knowledge base. "
        "Use to answer guest questions about this resort only. "
        "Input is the guest's question in natural language."
    )
    ctx: TenantContext
    embedder: EmbeddingProvider
    store: TenantQdrantStore

    def __init__(
        self,
        ctx: TenantContext,
        embedder: EmbeddingProvider,
        store: TenantQdrantStore | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            ctx=ctx,
            embedder=embedder,
            store=store or TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug),
            **kwargs,
        )

    @property
    def collection_name(self) -> str:
        return self.ctx.qdrant_collection

    def _run(self, query: str, *, limit: int = 5) -> str:
        vec = self.embedder.embed_one(query)
        hits = self.store.search(vec, limit=limit)
        if not hits:
            return "(no tenant knowledge found)"
        parts = []
        for h in hits:
            payload = h.get("payload", {})
            text = payload.get("text", "")
            parts.append(f"[{payload.get('category', 'knowledge')}] {text}")
        return "\n\n".join(parts)



@CrewBase
class ConciergeCrew:
    """Builds the real CrewAI concierge crew for a verified tenant.

    Agent and task instructions are loaded from config/agents.yaml and
    config/tasks.yaml (the maintainable CrewAI structure). Construction REQUIRES
    a verified TenantContext and a tenant-specific retrieval tool. The LLM key is
    injected at runtime (never placed in YAML). It executes via crew.kickoff().
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self,
        ctx: TenantContext,
        llm: LLM | None = None,
        knowledge_tool: TenantKnowledgeTool | None = None,
        embedder: EmbeddingProvider | None = None,
        openrouter_api_key: str | None = None,
    ) -> None:
        if not isinstance(ctx, TenantContext):
            raise TenantResolutionError("verified tenant context is required")
        self.ctx = ctx
        self.settings = get_settings()
        # The resolved per-resort key (CredentialsProvider) wins over the
        # environment-wide key; the key never appears in YAML or logs.
        self._openrouter_api_key = openrouter_api_key or self.settings.openrouter_api_key
        # Fail closed: no fake embeddings in production. Tests inject a fake.
        self._embedder = embedder or get_embedding_provider()
        self._llm = llm or self._build_llm()
        self._knowledge_tool = knowledge_tool or TenantKnowledgeTool(
            ctx, self._embedder
        )

    def _build_llm(self) -> LLM:
        return LLM(
            model=self.settings.openrouter_model,
            provider="openrouter",
            api_key=self._openrouter_api_key,
            temperature=0.3,
        )

    @agent
    def concierge_agent(self) -> Agent:
        cfg = self.agents_config["concierge_agent"]
        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            verbose=bool(cfg.get("verbose", False)),
            allow_delegation=bool(cfg.get("allow_delegation", False)),
            llm=self._llm,
            tools=[self._knowledge_tool],
        )

    @task
    def concierge_task(self) -> Task:
        cfg = self.tasks_config["concierge_task"]
        return Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self.concierge_agent(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.concierge_agent()],
            tasks=[self.concierge_task()],
            process=Process.sequential,
            verbose=False,
        )

    def build(self) -> Crew:
        return self.crew()

    def kickoff(self, inputs: dict[str, Any]) -> Any:
        return self.crew().kickoff(inputs=inputs)
