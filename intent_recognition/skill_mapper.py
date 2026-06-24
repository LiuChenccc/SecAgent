from .normalize import normalize_subdomain

INTENT_TO_SKILL_DOMAIN: dict[tuple[int, int], str] = {
    (1, 1): "malware-analysis",
    (1, 2): "network-security",
    (1, 3): "threat-hunting",
    (1, 4): "threat-hunting",
    (1, 5): "threat-intelligence",
    (1, 6): "threat-intelligence",
    (1, 7): "malware-analysis",
    (1, 8): "threat-detection",
    (2, 1): "vulnerability-management",
    (2, 2): "network-security",
    (2, 3): "vulnerability-management",
    (2, 4): "penetration-testing",
    (2, 5): "vulnerability-management",
    (2, 6): "vulnerability-management",
    (2, 7): "vulnerability-management",
    (3, 1): "compliance-governance",
    (3, 2): "data-protection",
    (3, 3): "threat-detection",
    (3, 4): "identity-access-management",
    (3, 5): "compliance-governance",
    (3, 6): "compliance-governance",
    (4, 1): "incident-response",
    (4, 2): "incident-response",
    (4, 3): "incident-response",
    (4, 4): "soc-operations",
    (4, 5): "incident-response",
    (4, 6): "digital-forensics",
    (4, 7): "soc-operations",
    (5, 1): "threat-intelligence",
    (5, 2): "zero-trust-architecture",
    (5, 3): "compliance-governance",
    (5, 4): "threat-hunting",
    (5, 5): "threat-intelligence",
    (5, 6): "network-security",
    (6, 1): "network-security",
    (6, 2): "vulnerability-management",
    (6, 3): "network-security",
    (6, 4): "incident-response",
    (6, 5): "vulnerability-management",
    (6, 6): "identity-access-management",
    (6, 7): "cryptography",
    (6, 8): "network-security",
    (6, 9): "cloud-security",
}


def get_skill_domain(main_intent_id: int, sub_intent_id: int) -> str:
    return INTENT_TO_SKILL_DOMAIN.get(
        (int(main_intent_id), int(sub_intent_id)),
        "threat-intelligence",
    )


def get_skill_domains(intents: list[dict]) -> list[str]:
    domains = []
    seen = set()
    for intent in intents:
        domain = get_skill_domain(
            intent.get("main_intent_id", 0),
            intent.get("sub_intent_id", 0),
        )
        normalized = normalize_subdomain(domain)
        if normalized not in seen:
            domains.append(normalized)
            seen.add(normalized)
    return domains
