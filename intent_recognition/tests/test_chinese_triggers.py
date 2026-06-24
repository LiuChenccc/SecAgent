from intent_recognition.chinese_triggers import (
    CHINESE_TRIGGER_MAP,
    get_candidate_subdomains,
)


def test_malware_trigger():
    result = get_candidate_subdomains("服务器上有挖矿木马进程")
    assert "malware-analysis" in result


def test_vulnerability_trigger():
    result = get_candidate_subdomains("进行漏洞扫描并检查CVE")
    assert "vulnerability-management" in result


def test_multi_domain_match():
    result = get_candidate_subdomains("检查防火墙策略和证书到期情况")
    assert "network-security" in result
    assert "cryptography" in result


def test_longer_match_ranks_higher():
    result = get_candidate_subdomains("进行漏洞扫描")
    idx_vuln = result.index("vulnerability-management")
    assert idx_vuln == 0


def test_no_match():
    result = get_candidate_subdomains("今天天气怎么样")
    assert result == []


def test_case_insensitive_english():
    result = get_candidate_subdomains("检查docker容器安全")
    assert "container-security" in result


def test_map_completeness():
    assert len(CHINESE_TRIGGER_MAP) >= 30
