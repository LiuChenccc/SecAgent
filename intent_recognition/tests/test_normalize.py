from intent_recognition.normalize import normalize_subdomain, _SUBDOMAIN_ALIASES


def test_alias_resolution():
    assert normalize_subdomain("identity-and-access-management") == "identity-access-management"
    assert normalize_subdomain("zero-trust") == "zero-trust-architecture"
    assert normalize_subdomain("red-team") == "red-teaming"
    assert normalize_subdomain("offensive-security") == "penetration-testing"


def test_canonical_passthrough():
    assert normalize_subdomain("malware-analysis") == "malware-analysis"
    assert normalize_subdomain("network-security") == "network-security"


def test_empty_string():
    assert normalize_subdomain("") == ""


def test_unknown_passthrough():
    assert normalize_subdomain("unknown-domain") == "unknown-domain"


def test_all_aliases_resolve():
    for alias, canonical in _SUBDOMAIN_ALIASES.items():
        assert normalize_subdomain(alias) == canonical
