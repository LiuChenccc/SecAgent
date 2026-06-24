"""
从 test.jsonl 中抽取 500 条高质量评估样本，保证 43 个子意图均匀分布。

质量过滤规则：
1. 排除用户输入为"无"或过于模糊的样本
2. 排除标注与内容明显不一致的样本（关键词交叉验证）
3. 优先选择对话轮次少、意图表达清晰的样本

运行：python3 -m intent_recognition.extract_quality_eval
"""

import json
import os
import random
from collections import defaultdict

from .taxonomy import MAIN_INTENT_NAMES, SUB_INTENT_NAMES

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lora_code_extracted", "security_intent", "data", "test.jsonl",
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "eval_500.json"
)

# 每个子意图的关键词（用于交叉验证标注质量）
_INTENT_KEYWORDS: dict[tuple[int, int], list[str]] = {
    (1, 1): ["恶意", "木马", "病毒", "样本", "逆向", "挖矿", "后门", "蠕虫", "勒索"],
    (1, 2): ["流量", "抓包", "DNS", "网络异常", "带宽", "DDoS", "数据包"],
    (1, 3): ["溯源", "攻击路径", "入口", "追踪", "攻击链", "来源"],
    (1, 4): ["失陷", "C2", "被控", "肉鸡", "僵尸", "远控"],
    (1, 5): ["IOC", "IP", "域名", "哈希", "MD5", "SHA", "威胁情报", "查询"],
    (1, 6): ["APT", "组织", "关联", "情报", "活动", "历史事件"],
    (1, 7): ["沙箱", "动态执行", "行为分析", "sandbox"],
    (1, 8): ["规则", "Sigma", "YARA", "Snort", "误报", "调优", "检测规则"],
    (2, 1): ["漏洞扫描", "Nessus", "全面扫描", "扫描启动"],
    (2, 2): ["指纹", "端口", "服务识别", "版本识别", "资产发现"],
    (2, 3): ["补丁版本", "安全补丁检查", "版本过旧", "更新检查"],
    (2, 4): ["PoC", "验证", "利用", "exploit", "CVE.*验证"],
    (2, 5): ["危害", "评估", "CVSS", "影响范围", "风险等级"],
    (2, 6): ["修复", "修补", "缓解", "remediation", "怎么修"],
    (2, 7): ["生命周期", "跟踪", "状态", "修复进度", "工单流转"],
    (3, 1): ["等保", "CIS", "基线", "合规", "ISO"],
    (3, 2): ["敏感数据", "脱敏", "身份证", "密钥泄露", "密码泄露"],
    (3, 3): ["日志完整", "篡改", "日志审计", "日志缺失"],
    (3, 4): ["权限审计", "账号", "离职", "越权", "身份"],
    (3, 5): ["策略违规", "安全规范", "违反策略", "内部策略"],
    (3, 6): ["审计报告", "报告生成", "整改报告", "测评报告"],
    (4, 1): ["隔离", "阻断", "封禁", "黑名单", "断网"],
    (4, 2): ["杀", "进程", "终止", "PID", "强杀"],
    (4, 3): ["备份", "恢复", "快照", "还原", "回滚"],
    (4, 4): ["告警", "误报", "确认", "关闭告警"],
    (4, 5): ["应急", "处置", "怎么办", "响应方案", "应对"],
    (4, 6): ["根因", "根本原因", "为什么", "调查原因"],
    (4, 7): ["工单", "派发", "提交", "创建任务"],
    (5, 1): ["什么是", "术语", "含义", "解释", "是什么意思"],
    (5, 2): ["防护", "防范", "怎么防", "防御方案", "安全方案"],
    (5, 3): ["法律", "法规", "GDPR", "数据安全法", "网络安全法", "条款"],
    (5, 4): ["案例", "实战", "攻防", "渗透案例"],
    (5, 5): ["研报", "趋势", "年度报告", "威胁报告", "分析总结"],
    (5, 6): ["手册", "命令", "语法", "配置指南", "操作手册"],
    (6, 1): ["防火墙", "规则", "ACL", "端口策略", "iptables"],
    (6, 2): ["系统更新", "Windows Update", "补丁分发", "批量更新"],
    (6, 3): ["CMDB", "资产录入", "资产更新", "资产管理"],
    (6, 4): ["重启", "启动服务", "restart", "服务挂了"],
    (6, 5): ["安全补丁", "CVE.*修复", "紧急补丁", "热补丁"],
    (6, 6): ["权限", "账号", "添加权限", "移除权限", "用户管理"],
    (6, 7): ["证书", "SSL", "到期", "有效期", "续期"],
    (6, 8): ["CPU", "内存", "性能", "瓶颈", "负载高", "响应慢"],
    (6, 9): ["扩容", "增加实例", "资源不足", "容量规划"],
}


def _extract_user_text(messages: list[dict]) -> str:
    """提取 user role 的完整文本"""
    for msg in messages:
        if msg["role"] == "user":
            return msg["content"]
    return ""


def _parse_labels(messages: list[dict]) -> list[tuple[int, int]]:
    """从 assistant content 解析意图标签"""
    for msg in messages:
        if msg["role"] == "assistant":
            try:
                items = json.loads(msg["content"])
                if isinstance(items, list):
                    return [(it["main_intent_id"], it["sub_intent_id"]) for it in items]
            except (json.JSONDecodeError, KeyError):
                pass
    return []


def _quality_score(user_text: str, labels: list[tuple[int, int]]) -> float:
    """计算样本质量分（0-1），越高越好"""
    if not labels or not user_text:
        return 0.0

    # 惩罚：用户说"无"或内容过短
    last_line = user_text.strip().split("\n")[-1]
    if "用户: 无" in user_text or len(user_text) < 10:
        return 0.0

    score = 0.5  # 基础分

    # 关键词匹配验证
    for mid, sid in labels:
        keywords = _INTENT_KEYWORDS.get((mid, sid), [])
        if keywords:
            matches = sum(1 for kw in keywords if kw in user_text)
            if matches > 0:
                score += 0.3 * min(matches / 2, 1.0)
            else:
                score -= 0.3  # 无关键词命中，可能标注有误

    # 对话轮次少加分（更清晰）
    turns = user_text.count("用户:")
    if turns <= 2:
        score += 0.1
    elif turns >= 5:
        score -= 0.1

    return max(0.0, min(1.0, score))


def extract():
    """主抽取逻辑"""
    # 读取全部数据
    samples = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            samples.append(json.loads(line))

    print(f"总样本数: {len(samples)}")

    # 按主意图分桶，计算质量分
    buckets: dict[tuple[int, int], list] = defaultdict(list)
    for sample in samples:
        messages = sample["messages"]
        labels = _parse_labels(messages)
        user_text = _extract_user_text(messages)
        q_score = _quality_score(user_text, labels)

        if q_score < 0.3:
            continue  # 过滤低质量

        # 单意图样本按标签分桶
        if len(labels) == 1:
            buckets[labels[0]].append((q_score, sample, labels))
        else:
            # 多意图样本放入第一个标签的桶（后面单独处理）
            buckets[("multi",)].append((q_score, sample, labels))

    # 目标：500 条，43 个子意图各 ~10 条 + 多意图 ~70 条
    TARGET = 500
    MULTI_TARGET = 70
    SINGLE_TARGET = TARGET - MULTI_TARGET  # 430
    PER_INTENT = SINGLE_TARGET // 43  # 10

    selected = []

    # 1. 每个子意图选 top-N
    for (mid, sid) in SUB_INTENT_NAMES.keys():
        bucket = buckets.get((mid, sid), [])
        bucket.sort(key=lambda x: x[0], reverse=True)
        chosen = bucket[:PER_INTENT]
        for q_score, sample, labels in chosen:
            selected.append(_format_eval_case(sample, labels))

    # 2. 多意图样本
    multi_bucket = buckets.get(("multi",), [])
    multi_bucket.sort(key=lambda x: x[0], reverse=True)
    for q_score, sample, labels in multi_bucket[:MULTI_TARGET]:
        selected.append(_format_eval_case(sample, labels))

    # 3. 如果不够 500，从剩余高质量样本补充
    current = len(selected)
    if current < TARGET:
        remaining = []
        for (mid, sid) in SUB_INTENT_NAMES.keys():
            bucket = buckets.get((mid, sid), [])
            bucket.sort(key=lambda x: x[0], reverse=True)
            remaining.extend(bucket[PER_INTENT:])
        remaining.sort(key=lambda x: x[0], reverse=True)
        for q_score, sample, labels in remaining[: TARGET - current]:
            selected.append(_format_eval_case(sample, labels))

    random.seed(42)
    random.shuffle(selected)

    # 统计分布
    dist = defaultdict(int)
    multi_count = 0
    for case in selected:
        if len(case["expected"]) > 1:
            multi_count += 1
        for exp in case["expected"]:
            dist[(exp["main_intent_id"], exp["sub_intent_id"])] += 1

    print(f"\n抽取结果: {len(selected)} 条")
    print(f"  多意图样本: {multi_count} 条")
    print(f"  子意图分布:")
    for (mid, sid), name in sorted(SUB_INTENT_NAMES.items()):
        count = dist.get((mid, sid), 0)
        print(f"    ({mid},{sid}) {name}: {count}")

    # 保存
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到: {OUTPUT_PATH}")


def _format_eval_case(sample: dict, labels: list[tuple[int, int]]) -> dict:
    """转换为评估格式"""
    user_text = _extract_user_text(sample["messages"])
    # 提取最后一轮用户输入或助手总结作为 query
    # 优先用助手的总结（更简洁）
    lines = user_text.split("\n")
    # 找最后一个"助手:"开头的行作为总结
    summary = ""
    for line in reversed(lines):
        if line.startswith("助手:") or line.startswith("助手: "):
            summary = line.replace("助手:", "").replace("助手: ", "").strip()
            break

    # 如果没有助手总结，用完整 user_text
    query = summary if summary else user_text

    expected = []
    for mid, sid in labels:
        expected.append({
            "main_intent_id": mid,
            "sub_intent_id": sid,
            "main_intent_name": MAIN_INTENT_NAMES.get(mid, ""),
            "sub_intent_name": SUB_INTENT_NAMES.get((mid, sid), ""),
        })

    return {"query": query, "expected": expected}


if __name__ == "__main__":
    extract()
