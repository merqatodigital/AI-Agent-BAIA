from __future__ import annotations

# Legacy SAMPLE repository coverage. The multi-tenant knowledge foundation
# (app.knowledge.repository.KnowledgeRepository) superseded this for production
# retrieval; these tests keep the SAMPLE fixture honest (never BAIA data).
from app.knowledge.sample_repository import (
    SampleKnowledgeRepository,
    get_knowledge_repository,
)


def test_knowledge_is_scoped_by_resort_id():
    repo = SampleKnowledgeRepository()
    k1 = repo.load("baia")
    k2 = repo.load("other-resort")
    # Each load is scoped; BAIA fixture is clearly SAMPLE, never presented as BAIA data.
    assert k1.resort_id == "baia"
    assert k2.resort_id == "other-resort"
    assert k1.is_sample is True
    assert "SAMPLE" in k1.entries[0].content
    assert "BAIA" not in k1.entries[0].content.replace("'baia'", "")


def test_repository_isolates_resorts():
    repo = get_knowledge_repository()
    a = repo.load("resort_a")
    b = repo.load("resort_b")
    assert a.resort_id != b.resort_id


def test_sample_data_not_presented_as_baia():
    repo = SampleKnowledgeRepository()
    k = repo.load("baia")
    # The fixture must never claim to be real BAIA Resort knowledge.
    assert k.is_sample is True
    for e in k.entries:
        assert "sample" in e.content.lower()
