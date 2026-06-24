_SUBDOMAIN_ALIASES = {
    "identity-and-access-management": "identity-access-management",
    "identity-security": "identity-access-management",
    "zero-trust": "zero-trust-architecture",
    "ot-security": "ot-ics-security",
    "security-operations": "soc-operations",
    "red-team": "red-teaming",
    "application-security": "web-application-security",
    "offensive-security": "penetration-testing",
    "social-engineering-defense": "phishing-defense",
    "governance-risk-compliance": "compliance-governance",
    "firmware-security": "firmware-analysis",
}


def normalize_subdomain(raw: str) -> str:
    if not raw:
        return ""
    return _SUBDOMAIN_ALIASES.get(raw, raw)
