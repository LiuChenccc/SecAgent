"""
网络安全智能体 (SecAgent)

基于意图识别 + Skills库 + 记忆系统的网络安全智能体。
"""

from .agent import SecurityAgent
from .intent import IntentRecognizer
from .skills_retriever import SkillsRetriever, SkillInfo, normalize_subdomain
from .skill_mapper import (
    get_skill_domain,
    get_skill_domains,
    INTENT_TO_SKILL_DOMAIN,
    MAIN_INTENT_NAMES,
    SUB_INTENT_NAMES,
)
from .memory import MemorySystem
from .executor import Executor
from .chinese_trigger_map import (
    CHINESE_TRIGGER_MAP,
    get_candidate_subdomains,
)

__all__ = [
    "SecurityAgent",
    "IntentRecognizer",
    "SkillsRetriever",
    "SkillInfo",
    "MemorySystem",
    "Executor",
    "get_skill_domain",
    "get_skill_domains",
    "INTENT_TO_SKILL_DOMAIN",
    "MAIN_INTENT_NAMES",
    "SUB_INTENT_NAMES",
    "normalize_subdomain",
    "CHINESE_TRIGGER_MAP",
    "get_candidate_subdomains",
]