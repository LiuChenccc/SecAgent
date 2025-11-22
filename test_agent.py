"""
SecAgent 验证测试脚本 —— 测试各模块独立功能。

运行方式：
    python test_agent.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.skills_retriever import SkillsRetriever, normalize_subdomain
from agent.skill_mapper import (
    get_skill_domain,
    get_skill_domains,
    INTENT_TO_SKILL_DOMAIN,
)
from agent.memory import MemorySystem
from agent.tools import execute_tool, run_shell, read_file, grep_file, query_threat, write_file
from agent.intent import IntentRecognizer
from agent.chinese_trigger_map import get_candidate_subdomains


def test_skills_retriever():
    """测试Skills检索 — 使用 GitHub 真实 Skills 库"""
    print("\n" + "=" * 60)
    print("测试 1: Skills 检索层")
    print("=" * 60)

    # 默认加载 GitHub 项目
    retriever = SkillsRetriever()
    count = retriever.load_all()

    print(f"  加载Skills数量: {count}")
    if count == 0:
        print("  [跳过] Skills 目录为空，跳过检索测试")
        return retriever

    test_queries = [
        ("分析服务器内存dump有没有挖矿木马", "malware-analysis"),
        ("帮我扫描一下系统漏洞并检查补丁", "vulnerability-management"),
        ("防火墙策略需要更新一下", "network-security"),
        ("帮我查一下GDPR的相关条款", "compliance-governance"),
        ("发现了可疑告警需要紧急处理", "incident-response"),
        ("能给我讲讲零日漏洞是什么意思吗", "threat-intelligence"),
    ]

    for query, expected_subdomain in test_queries:
        results = retriever.search(query, top_k=5)
        domains = [r.subdomain for r in results]
        print(f"  Q: {query}")
        print(f"    匹配: {domains[:5]}")
        assert len(results) > 0, f"'{query}' 应至少匹配1个Skill"

        context = retriever.format_context_for_prompt(results)
        assert len(context) > 50, "格式化上下文不应为空"

    print("  测试 1 通过")
    return retriever


def test_chinese_trigger_map():
    """测试中文触发词映射"""
    print("\n" + "=" * 60)
    print("测试 2: 中文触发词映射")
    print("=" * 60)

    candidates = get_candidate_subdomains("服务器上有挖矿木马进程")
    print(f"  '挖矿木马' → {candidates}")
    assert "malware-analysis" in candidates, f"应包含malware-analysis，实际{candidates}"

    candidates = get_candidate_subdomains("进行漏洞扫描并检查CVE")
    print(f"  '漏洞扫描CVE' → {candidates}")
    assert "vulnerability-management" in candidates

    candidates = get_candidate_subdomains("检查防火墙策略和证书到期情况")
    print(f"  '防火墙+证书' → {candidates}")
    assert "network-security" in candidates
    assert "cryptography" in candidates

    print("  测试 2 通过")


def test_skill_mapper():
    """测试意图→Skill映射"""
    print("\n" + "=" * 60)
    print("测试 3: 意图→Skill映射表")
    print("=" * 60)

    test_cases = [
        ((1, 1), "malware-analysis"),
        ((1, 5), "threat-intelligence"),
        ((2, 1), "vulnerability-management"),
        ((3, 1), "compliance-governance"),
        ((4, 6), "digital-forensics"),
        ((5, 2), "zero-trust-architecture"),
        ((6, 1), "network-security"),
        ((6, 7), "cryptography"),
        ((99, 99), "threat-intelligence"),  # 默认回退
    ]

    for (main_id, sub_id), expected_domain in test_cases:
        domain = get_skill_domain(main_id, sub_id)
        print(f"  ({main_id}, {sub_id}) → {domain}")
        assert domain == expected_domain, (
            f"期望{expected_domain}，实际{domain}"
        )

    intents = [
        {"main_intent_id": 1, "sub_intent_id": 1},
        {"main_intent_id": 6, "sub_intent_id": 1},
        {"main_intent_id": 2, "sub_intent_id": 3},
    ]
    domains = get_skill_domains(intents)
    print(f"  多意图映射: {len(intents)}个意图 → {len(domains)}个领域: {domains}")
    assert len(domains) == 3

    assert len(INTENT_TO_SKILL_DOMAIN) >= 43, (
        f"映射表至少43条，实际{len(INTENT_TO_SKILL_DOMAIN)}条"
    )

    print("  测试 3 通过")


def test_subdomain_normalization():
    """测试子领域别名规范化"""
    print("\n" + "=" * 60)
    print("测试 4: 子领域别名规范化")
    print("=" * 60)

    alias_cases = [
        ("security-operations", "soc-operations"),
        ("red-team", "red-teaming"),
        ("offensive-security", "penetration-testing"),
        ("zero-trust", "zero-trust-architecture"),
        ("application-security", "web-application-security"),
        ("identity-and-access-management", "identity-access-management"),
        ("malware-analysis", "malware-analysis"),  # 已是规范名
    ]

    for alias, expected_canonical in alias_cases:
        result = normalize_subdomain(alias)
        print(f"  {alias} → {result}")
        assert result == expected_canonical, (
            f"期望{expected_canonical}，实际{result}"
        )

    print("  测试 4 通过")


def test_memory_system():
    """测试记忆系统"""
    print("\n" + "=" * 60)
    print("测试 5: 记忆系统")
    print("=" * 60)

    mem_path = os.path.join(
        os.path.dirname(__file__), "agent", "memory_store", "test_memory.jsonl"
    )
    if os.path.exists(mem_path):
        os.remove(mem_path)

    memory = MemorySystem(mem_path)
    count = memory.load()
    print(f"  初始记忆数: {count}")
    assert count == 0

    entry1 = memory.save_one(
        user_query="分析服务器A的内存dump有没有挖矿木马",
        recognized_intents=[
            {
                "main_intent_id": 1,
                "main_intent_name": "威胁检测与识别",
                "sub_intent_id": 1,
                "sub_intent_name": "恶意代码分析",
            }
        ],
        matched_skills=["malware-analysis"],
        tool_calls=[],
        result_summary="发现挖矿木马进程，已关联威胁情报确认",
        user_feedback="confirmed",
    )
    print(f"  保存记忆: {entry1.id}")

    entry2 = memory.save_one(
        user_query="帮我检查防火墙策略和证书到期情况",
        recognized_intents=[
            {
                "main_intent_id": 6,
                "main_intent_name": "系统运维与配置管理",
                "sub_intent_id": 1,
                "sub_intent_name": "防火墙策略下发",
            },
            {
                "main_intent_id": 6,
                "main_intent_name": "系统运维与配置管理",
                "sub_intent_id": 7,
                "sub_intent_name": "证书到期监控",
            },
        ],
        matched_skills=["network-security", "cryptography"],
        tool_calls=[],
        result_summary="防火墙策略已更新，发现2个即将到期证书",
        user_feedback="confirmed",
    )
    print(f"  保存记忆: {entry2.id}")

    results = memory.search("服务器内存dump分析挖矿")
    print(f"  搜索'服务器内存dump分析挖矿': 匹配 {len(results)} 条")
    assert len(results) > 0
    assert "挖矿" in results[0].user_query

    results = memory.search("检查证书")
    print(f"  搜索'检查证书': 匹配 {len(results)} 条")
    assert len(results) > 0
    assert "证书" in results[0].user_query

    few_shot = memory.format_context_for_prompt(results)
    print(f"  Few-shot上下文长度: {len(few_shot)} 字符")
    assert len(few_shot) > 30

    stats = memory.get_stats()
    print(f"  记忆统计: {stats}")
    assert stats["confirmed"] == 2

    os.remove(mem_path)
    print("  测试 5 通过")


def test_tools():
    """测试工具执行"""
    print("\n" + "=" * 60)
    print("测试 6: 工具执行")
    print("=" * 60)

    # run_shell
    result = run_shell("echo 'hello security'")
    print(f"  run_shell: {result}")
    assert result["success"]
    assert "hello security" in result["stdout"]

    # read_file
    skill_path = os.path.join(
        os.path.dirname(__file__),
        "agent", "skills", "analyzing-malware-persistence-with-autoruns", "SKILL.md"
    )
    if os.path.exists(skill_path):
        result = read_file(skill_path)
        print(f"  read_file(SKILL.md): success={result['success']}, lines={result.get('total_lines', 0)}")
        assert result["success"]
    else:
        result = read_file(os.path.join(os.path.dirname(__file__), "test_agent.py"))
        print(f"  read_file(test_agent.py): success={result['success']}, lines={result.get('total_lines', 0)}")
        assert result["success"]

    # grep_file
    print("\n  grep_file 测试:")
    test_file = os.path.join(
        os.path.dirname(__file__),
        "agent", "tools.py",
    )
    result = grep_file("def grep_file", test_file, context_lines=2)
    print(f"    搜索'def grep_file': matched={result['total_matched']}, showed={result['shown_matches']}")
    assert result["success"]
    assert result["total_matched"] >= 1
    assert "def" in result["matches"][0]["line"]

    result = grep_file(r"os\.path\.\w+", test_file, max_matches=5)
    print(f"    搜索'os.path.*': matched={result['total_matched']}, showed={result['shown_matches']}")
    assert result["success"]

    result = grep_file("nonexistent_pattern_xyz", test_file)
    print(f"    搜索不存在的模式: matched={result['total_matched']}")
    assert result["success"]
    assert result["total_matched"] == 0

    result = grep_file("[invalid(regex", test_file)
    print(f"    无效正则: success={result['success']}")
    assert not result["success"]

    # query_threat (依赖网络，失败不阻塞)
    print("\n  query_threat 测试:")
    result = query_threat("8.8.8.8")
    if result["success"]:
        print(f"    8.8.8.8: pulse_count={result.get('pulse_count', 'N/A')}, malicious={result.get('malicious')}")
    else:
        print(f"    8.8.8.8: 查询失败（网络问题或API不可达）→ {result.get('error', '')}")

    result = query_threat("example.com")
    if result["success"]:
        print(f"    example.com: pulse_count={result.get('pulse_count', 'N/A')}, malicious={result.get('malicious')}")
    else:
        print(f"    example.com: 查询失败 → {result.get('error', '')}")

    # 验证指标类型识别
    from agent.tools import _classify_indicator
    assert _classify_indicator("8.8.8.8") == "ip"
    assert _classify_indicator("example.com") == "domain"
    assert _classify_indicator("d41d8cd98f00b204e9800998ecf8427e") == "hash"
    assert _classify_indicator("https://evil.com/path") == "url"
    print("    指标类型识别: ip ✓ | domain ✓ | hash ✓ | url ✓")

    # write_file
    print("\n  write_file 测试:")
    tmp = "/tmp/secagent_test_write.txt"
    result = write_file(tmp, "SecAgent 测试输出")
    print(f"    write: success={result['success']}, bytes={result['bytes_written']}")
    assert result["success"]

    result = read_file(tmp)
    assert "SecAgent 测试输出" in result["content"]
    os.remove(tmp)

    # execute_tool 统一入口
    result = execute_tool("grep_file", {"pattern": "import", "path": test_file, "max_matches": 3})
    print(f"  execute_tool(grep_file): matched={result['total_matched']}")
    assert result["success"]

    result = execute_tool("unknown_tool", {})
    print(f"  execute_tool(unknown): {result}")
    assert not result["success"]

    print("  测试 6 通过")


def test_intent_parsing():
    """测试意图解析（不需要LLM API）"""
    print("\n" + "=" * 60)
    print("测试 7: 意图解析")
    print("=" * 60)

    recognizer = IntentRecognizer(backend="api")

    valid_json = '[{"main_intent_id": 1, "main_intent_name": "威胁检测与识别", "sub_intent_id": 1, "sub_intent_name": "恶意代码分析"}]'
    result = recognizer._parse_response(valid_json)
    print(f"  标准JSON: {len(result)} 个意图")
    assert len(result) == 1
    assert result[0]["main_intent_id"] == 1

    multi_json = '[{"main_intent_id": 1, "main_intent_name": "威胁检测与识别", "sub_intent_id": 1, "sub_intent_name": "恶意代码分析"}, {"main_intent_id": 6, "main_intent_name": "系统运维与配置管理", "sub_intent_id": 1, "sub_intent_name": "防火墙策略下发"}]'
    result = recognizer._parse_response(multi_json)
    print(f"  多意图JSON: {len(result)} 个意图")
    assert len(result) == 2

    messy_json = '一些前缀文字\n[{"main_intent_id": 2, "main_intent_name": "漏洞发现与管理", "sub_intent_id": 1, "sub_intent_name": "漏洞扫描启动"}]\n一些后缀'
    result = recognizer._parse_response(messy_json)
    print(f"  含噪音JSON: {len(result)} 个意图")
    assert len(result) == 1

    empty = ""
    result = recognizer._parse_response(empty)
    print(f"  空字符串: {len(result)} 个意图")
    assert result == []

    display = recognizer.format_intents_for_display([
        {"main_intent_id": 1, "main_intent_name": "威胁检测与识别", "sub_intent_id": 1, "sub_intent_name": "恶意代码分析"},
        {"main_intent_id": 6, "main_intent_name": "系统运维与配置管理", "sub_intent_id": 7, "sub_intent_name": "证书到期监控"},
    ])
    print(f"  格式化输出:\n{display}")
    assert "威胁检测与识别" in display
    assert "证书到期监控" in display

    print("  测试 7 通过")


def test_enhanced_prompt():
    """测试增强prompt构建"""
    print("\n" + "=" * 60)
    print("测试 8: 增强Prompt构建")
    print("=" * 60)

    recognizer = IntentRecognizer(backend="api")

    # 使用 GitHub 真实 Skills
    retriever = SkillsRetriever()
    count = retriever.load_all()

    if count == 0:
        print("  [跳过] Skills 目录为空，跳过增强Prompt测试")
        return

    skills = retriever.search(
        "分析服务器内存dump有没有挖矿木马，同时检查防火墙策略", top_k=3
    )
    skill_context = retriever.format_context_for_prompt(skills)

    prompt = recognizer._build_enhanced_prompt(
        "分析服务器内存dump，检查防火墙策略",
        skill_context=skill_context,
        few_shot_context="案例1: 历史成功案例...",
    )

    print(f"  Prompt长度: {len(prompt)} 字符")
    assert "候选" in prompt or "安全领域" in prompt
    assert "JSON" in prompt
    assert "案例" in prompt
    print("  Prompt包含: Skills上下文 ✓ | 历史案例 ✓ | JSON输出约束 ✓")

    print("  测试 8 通过")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SecAgent 模块验证测试")
    print("=" * 60)

    test_skills_retriever()
    test_chinese_trigger_map()
    test_skill_mapper()
    test_subdomain_normalization()
    test_memory_system()
    test_tools()
    test_intent_parsing()
    test_enhanced_prompt()

    print("\n" + "=" * 60)
    print("  全部测试通过")
    print("=" * 60)