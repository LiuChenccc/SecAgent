"""
意图 → Skill 领域映射表

将 43 个子意图 (main_intent_id, sub_intent_id) 映射到 GitHub Skills 的 34 个规范子领域。
"""

from .skills_retriever import normalize_subdomain

# 子领域别名 → 规范名（与 GitHub validate-skill.py 保持一致）
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

# 意图识别模型的 43 个子意图 → GitHub Skills 34 个规范子领域
INTENT_TO_SKILL_DOMAIN: dict[tuple[int, int], str] = {
    # === 1: 威胁检测与识别 ===
    (1, 1): "malware-analysis",           # 恶意代码分析
    (1, 2): "network-security",           # 流量异常检测
    (1, 3): "threat-hunting",             # 攻击溯源
    (1, 4): "threat-hunting",             # 失陷主机发现
    (1, 5): "threat-intelligence",        # IOC提取与检索
    (1, 6): "threat-intelligence",        # 情报库关联查询
    (1, 7): "malware-analysis",           # 沙箱分析触发
    (1, 8): "threat-detection",           # 检测规则调优

    # === 2: 漏洞发现与管理 ===
    (2, 1): "vulnerability-management",   # 漏洞扫描启动
    (2, 2): "network-security",           # 资产指纹识别
    (2, 3): "vulnerability-management",   # 补丁版本检查
    (2, 4): "penetration-testing",        # PoC验证执行
    (2, 5): "vulnerability-management",   # 漏洞危害评估
    (2, 6): "vulnerability-management",   # 修复建议查询
    (2, 7): "vulnerability-management",   # 漏洞生命周期跟踪

    # === 3: 安全合规与审计 ===
    (3, 1): "compliance-governance",      # 合规基线检查
    (3, 2): "data-protection",            # 敏感数据发现
    (3, 3): "threat-detection",           # 日志完整性审计
    (3, 4): "identity-access-management", # 身份权限审计
    (3, 5): "compliance-governance",      # 策略违规扫描
    (3, 6): "compliance-governance",      # 审计报告生成

    # === 4: 安全事件响应与处置 ===
    (4, 1): "incident-response",          # 隔离阻断指令
    (4, 2): "incident-response",          # 进程强杀请求
    (4, 3): "incident-response",          # 系统备份恢复
    (4, 4): "soc-operations",             # 告警自动确认
    (4, 5): "incident-response",          # 应急处置建议
    (4, 6): "digital-forensics",          # 事件根因调查
    (4, 7): "soc-operations",             # 联动工单创建

    # === 5: 安全知识问答与教育 ===
    (5, 1): "threat-intelligence",        # 安全术语解释
    (5, 2): "zero-trust-architecture",    # 防护方案建议
    (5, 3): "compliance-governance",      # 安全法律法规检索
    (5, 4): "threat-hunting",             # 实战攻防案例检索
    (5, 5): "threat-intelligence",        # 行业研报分析总结
    (5, 6): "network-security",           # 系统手册查询

    # === 6: 系统运维与配置管理 ===
    (6, 1): "network-security",           # 防火墙策略下发
    (6, 2): "vulnerability-management",   # 系统补丁分发
    (6, 3): "network-security",           # 资产信息更新
    (6, 4): "incident-response",          # 服务重启指令
    (6, 5): "vulnerability-management",   # 安全补丁分发
    (6, 6): "identity-access-management", # 用户权限调整
    (6, 7): "cryptography",               # 证书到期监控
    (6, 8): "network-security",           # 性能瓶颈告警分析
    (6, 9): "cloud-security",             # 资源扩容建议
}


def get_skill_domain(main_intent_id: int, sub_intent_id: int) -> str:
    """根据意图ID获取对应的Skill规范子领域名"""
    return INTENT_TO_SKILL_DOMAIN.get(
        (int(main_intent_id), int(sub_intent_id)),
        "threat-intelligence",  # 默认回退
    )


def get_skill_domains(intents: list[dict]) -> list[str]:
    """从意图列表提取去重的Skill规范子领域列表"""
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


MAIN_INTENT_NAMES = {
    1: "威胁检测与识别",
    2: "漏洞发现与管理",
    3: "安全合规与审计",
    4: "安全事件响应与处置",
    5: "安全知识问答与教育",
    6: "系统运维与配置管理",
}

SUB_INTENT_NAMES: dict[tuple[int, int], str] = {
    (1, 1): "恶意代码分析", (1, 2): "流量异常检测",
    (1, 3): "攻击溯源", (1, 4): "失陷主机发现",
    (1, 5): "IOC提取与检索", (1, 6): "情报库关联查询",
    (1, 7): "沙箱分析触发", (1, 8): "检测规则调优",
    (2, 1): "漏洞扫描启动", (2, 2): "资产指纹识别",
    (2, 3): "补丁版本检查", (2, 4): "PoC验证执行",
    (2, 5): "漏洞危害评估", (2, 6): "修复建议查询",
    (2, 7): "漏洞生命周期跟踪",
    (3, 1): "合规基线检查", (3, 2): "敏感数据发现",
    (3, 3): "日志完整性审计", (3, 4): "身份权限审计",
    (3, 5): "策略违规扫描", (3, 6): "审计报告生成",
    (4, 1): "隔离阻断指令", (4, 2): "进程强杀请求",
    (4, 3): "系统备份恢复", (4, 4): "告警自动确认",
    (4, 5): "应急处置建议", (4, 6): "事件根因调查",
    (4, 7): "联动工单创建",
    (5, 1): "安全术语解释", (5, 2): "防护方案建议",
    (5, 3): "安全法律法规检索", (5, 4): "实战攻防案例检索",
    (5, 5): "行业研报分析总结", (5, 6): "系统手册查询",
    (6, 1): "防火墙策略下发", (6, 2): "系统补丁分发",
    (6, 3): "资产信息更新", (6, 4): "服务重启指令",
    (6, 5): "安全补丁分发", (6, 6): "用户权限调整",
    (6, 7): "证书到期监控", (6, 8): "性能瓶颈告警分析",
    (6, 9): "资源扩容建议",
}