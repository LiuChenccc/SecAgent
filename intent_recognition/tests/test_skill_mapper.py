from intent_recognition.skill_mapper import (
    INTENT_TO_SKILL_DOMAIN,
    get_skill_domain,
    get_skill_domains,
)


def test_known_mappings():
    assert get_skill_domain(1, 1) == "malware-analysis"
    assert get_skill_domain(1, 5) == "threat-intelligence"
    assert get_skill_domain(2, 1) == "vulnerability-management"
    assert get_skill_domain(4, 6) == "digital-forensics"
    assert get_skill_domain(6, 7) == "cryptography"


def test_default_fallback():
    assert get_skill_domain(99, 99) == "threat-intelligence"


def test_get_skill_domains_dedup():
    intents = [
        {"main_intent_id": 1, "sub_intent_id": 1},
        {"main_intent_id": 1, "sub_intent_id": 7},  # also malware-analysis
    ]
    domains = get_skill_domains(intents)
    assert domains == ["malware-analysis"]


def test_get_skill_domains_multiple():
    intents = [
        {"main_intent_id": 1, "sub_intent_id": 1},
        {"main_intent_id": 6, "sub_intent_id": 1},
        {"main_intent_id": 2, "sub_intent_id": 3},
    ]
    domains = get_skill_domains(intents)
    assert len(domains) == 3


def test_get_skill_domains_empty():
    assert get_skill_domains([]) == []


def test_mapping_table_completeness():
    assert len(INTENT_TO_SKILL_DOMAIN) >= 43
