"""
意图识别评估框架 —— 覆盖 6 大类 43 子意图的测试集 + 自动评估。

运行方式：
    INTENT_API_KEY=xxx python3 -m intent_recognition.eval
"""

import json
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_recognition.recognizer import IntentRecognizer

# 评估测试集：每个子意图 2 条，共 86 条 + 多意图 6 条 = 92 条
EVAL_DATASET = [
    # === 1: 威胁检测与识别 ===
    # (1,1) 恶意代码分析
    {"query": "帮我逆向分析这个exe样本，看看有没有恶意行为", "expected": [{"main_intent_id": 1, "sub_intent_id": 1}]},
    {"query": "服务器上发现可疑进程，疑似挖矿木马，需要分析一下", "expected": [{"main_intent_id": 1, "sub_intent_id": 1}]},
    # (1,2) 流量异常检测
    {"query": "最近网络流量异常增大，帮我抓包分析一下", "expected": [{"main_intent_id": 1, "sub_intent_id": 2}]},
    {"query": "检测一下内网有没有异常的DNS请求", "expected": [{"main_intent_id": 1, "sub_intent_id": 2}]},
    # (1,3) 攻击溯源
    {"query": "这次入侵事件的攻击路径是什么，帮我溯源", "expected": [{"main_intent_id": 1, "sub_intent_id": 3}]},
    {"query": "追踪一下攻击者是从哪个入口进来的", "expected": [{"main_intent_id": 1, "sub_intent_id": 3}]},
    # (1,4) 失陷主机发现
    {"query": "检查一下内网有没有已经被控制的主机", "expected": [{"main_intent_id": 1, "sub_intent_id": 4}]},
    {"query": "扫描一下哪些机器在跟C2服务器通信", "expected": [{"main_intent_id": 1, "sub_intent_id": 4}]},
    # (1,5) IOC提取与检索
    {"query": "帮我查一下这个IP 45.33.32.156的威胁情报", "expected": [{"main_intent_id": 1, "sub_intent_id": 5}]},
    {"query": "提取这份报告里的IOC指标，包括IP和域名", "expected": [{"main_intent_id": 1, "sub_intent_id": 5}]},
    # (1,6) 情报库关联查询
    {"query": "APT28组织最近有什么新的攻击活动", "expected": [{"main_intent_id": 1, "sub_intent_id": 6}]},
    {"query": "查一下这个恶意域名关联了哪些攻击组织和历史事件", "expected": [{"main_intent_id": 1, "sub_intent_id": 6}]},
    # (1,7) 沙箱分析触发
    {"query": "把这个可疑附件丢到沙箱里跑一下", "expected": [{"main_intent_id": 1, "sub_intent_id": 7}]},
    {"query": "用沙箱环境执行这个脚本看看行为", "expected": [{"main_intent_id": 1, "sub_intent_id": 7}]},
    # (1,8) 检测规则调优
    {"query": "这条Sigma规则误报太多了，帮我优化一下", "expected": [{"main_intent_id": 1, "sub_intent_id": 8}]},
    {"query": "写一条YARA规则来检测这类恶意样本", "expected": [{"main_intent_id": 1, "sub_intent_id": 8}]},

    # === 2: 漏洞发现与管理 ===
    # (2,1) 漏洞扫描启动
    {"query": "对192.168.1.0/24网段做一次全面漏洞扫描", "expected": [{"main_intent_id": 2, "sub_intent_id": 1}]},
    {"query": "用Nessus扫描一下Web服务器的漏洞", "expected": [{"main_intent_id": 2, "sub_intent_id": 1}]},
    # (2,2) 资产指纹识别
    {"query": "识别一下这台服务器跑了什么服务和版本", "expected": [{"main_intent_id": 2, "sub_intent_id": 2}]},
    {"query": "扫描一下目标主机开放了哪些端口和服务", "expected": [{"main_intent_id": 2, "sub_intent_id": 2}]},
    # (2,3) 补丁版本检查
    {"query": "检查一下系统有没有安装最新的安全补丁", "expected": [{"main_intent_id": 2, "sub_intent_id": 3}]},
    {"query": "看看Apache版本是不是有已知漏洞的旧版本", "expected": [{"main_intent_id": 2, "sub_intent_id": 3}]},
    # (2,4) PoC验证执行
    {"query": "用这个CVE-2024-1234的PoC验证一下漏洞是否存在", "expected": [{"main_intent_id": 2, "sub_intent_id": 4}]},
    {"query": "对目标系统执行漏洞利用验证", "expected": [{"main_intent_id": 2, "sub_intent_id": 4}]},
    # (2,5) 漏洞危害评估
    {"query": "评估一下这个SQL注入漏洞的影响范围和危害等级", "expected": [{"main_intent_id": 2, "sub_intent_id": 5}]},
    {"query": "这个RCE漏洞的CVSS评分是多少，影响哪些版本", "expected": [{"main_intent_id": 2, "sub_intent_id": 5}]},
    # (2,6) 修复建议查询
    {"query": "CVE-2024-5678这个漏洞怎么修复", "expected": [{"main_intent_id": 2, "sub_intent_id": 6}]},
    {"query": "给出Log4j漏洞的修复方案和临时缓解措施", "expected": [{"main_intent_id": 2, "sub_intent_id": 6}]},
    # (2,7) 漏洞生命周期跟踪
    {"query": "跟踪一下这个漏洞从发现到修复的完整状态", "expected": [{"main_intent_id": 2, "sub_intent_id": 7}]},
    {"query": "查看上个月发现的高危漏洞现在修复到什么程度了", "expected": [{"main_intent_id": 2, "sub_intent_id": 7}]},

    # === 3: 安全合规与审计 ===
    # (3,1) 合规基线检查
    {"query": "按照等保2.0三级要求检查一下服务器配置", "expected": [{"main_intent_id": 3, "sub_intent_id": 1}]},
    {"query": "对照CIS基线检查Linux系统的安全配置", "expected": [{"main_intent_id": 3, "sub_intent_id": 1}]},
    # (3,2) 敏感数据发现
    {"query": "扫描一下数据库里有没有未脱敏的身份证号", "expected": [{"main_intent_id": 3, "sub_intent_id": 2}]},
    {"query": "检查代码仓库里有没有泄露的密钥或密码", "expected": [{"main_intent_id": 3, "sub_intent_id": 2}]},
    # (3,3) 日志完整性审计
    {"query": "检查一下安全日志有没有被篡改或删除的痕迹", "expected": [{"main_intent_id": 3, "sub_intent_id": 3}]},
    {"query": "审计一下过去一周的系统日志完整性", "expected": [{"main_intent_id": 3, "sub_intent_id": 3}]},
    # (3,4) 身份权限审计
    {"query": "审计一下哪些账号有超出职责的权限", "expected": [{"main_intent_id": 3, "sub_intent_id": 4}]},
    {"query": "检查一下离职员工的账号有没有及时禁用", "expected": [{"main_intent_id": 3, "sub_intent_id": 4}]},
    # (3,5) 策略违规扫描
    {"query": "扫描一下有没有违反安全策略的配置", "expected": [{"main_intent_id": 3, "sub_intent_id": 5}]},
    {"query": "检查网络设备配置是否符合公司安全规范", "expected": [{"main_intent_id": 3, "sub_intent_id": 5}]},
    # (3,6) 审计报告生成
    {"query": "生成本季度的安全审计报告", "expected": [{"main_intent_id": 3, "sub_intent_id": 6}]},
    {"query": "输出一份等保测评的整改报告", "expected": [{"main_intent_id": 3, "sub_intent_id": 6}]},

    # === 4: 安全事件响应与处置 ===
    # (4,1) 隔离阻断指令
    {"query": "立即隔离这台被入侵的服务器，断开网络连接", "expected": [{"main_intent_id": 4, "sub_intent_id": 1}]},
    {"query": "封禁这个攻击源IP，加入防火墙黑名单", "expected": [{"main_intent_id": 4, "sub_intent_id": 1}]},
    # (4,2) 进程强杀请求
    {"query": "杀掉这个恶意进程PID 12345", "expected": [{"main_intent_id": 4, "sub_intent_id": 2}]},
    {"query": "强制终止服务器上的挖矿进程", "expected": [{"main_intent_id": 4, "sub_intent_id": 2}]},
    # (4,3) 系统备份恢复
    {"query": "把系统恢复到被攻击前的备份状态", "expected": [{"main_intent_id": 4, "sub_intent_id": 3}]},
    {"query": "从昨天的快照恢复这台数据库服务器", "expected": [{"main_intent_id": 4, "sub_intent_id": 3}]},
    # (4,4) 告警自动确认
    {"query": "这条告警是误报，帮我确认关闭", "expected": [{"main_intent_id": 4, "sub_intent_id": 4}]},
    {"query": "批量确认这些低危告警", "expected": [{"main_intent_id": 4, "sub_intent_id": 4}]},
    # (4,5) 应急处置建议
    {"query": "发现勒索软件感染，应该怎么处置", "expected": [{"main_intent_id": 4, "sub_intent_id": 5}]},
    {"query": "给出这次DDoS攻击的应急响应方案", "expected": [{"main_intent_id": 4, "sub_intent_id": 5}]},
    # (4,6) 事件根因调查
    {"query": "调查一下这次数据泄露的根本原因是什么", "expected": [{"main_intent_id": 4, "sub_intent_id": 6}]},
    {"query": "分析这次安全事件的根因，是配置问题还是漏洞", "expected": [{"main_intent_id": 4, "sub_intent_id": 6}]},
    # (4,7) 联动工单创建
    {"query": "创建一个安全事件工单派给运维团队处理", "expected": [{"main_intent_id": 4, "sub_intent_id": 7}]},
    {"query": "把这个漏洞修复任务提交到工单系统", "expected": [{"main_intent_id": 4, "sub_intent_id": 7}]},

    # === 5: 安全知识问答与教育 ===
    # (5,1) 安全术语解释
    {"query": "什么是零日漏洞", "expected": [{"main_intent_id": 5, "sub_intent_id": 1}]},
    {"query": "APT攻击是什么意思", "expected": [{"main_intent_id": 5, "sub_intent_id": 1}]},
    # (5,2) 防护方案建议
    {"query": "怎么防范SQL注入攻击", "expected": [{"main_intent_id": 5, "sub_intent_id": 2}]},
    {"query": "给出一套内网横向移动的防护方案", "expected": [{"main_intent_id": 5, "sub_intent_id": 2}]},
    # (5,3) 安全法律法规检索
    {"query": "网络安全法对数据出境有什么规定", "expected": [{"main_intent_id": 5, "sub_intent_id": 3}]},
    {"query": "GDPR对个人数据处理的要求是什么", "expected": [{"main_intent_id": 5, "sub_intent_id": 3}]},
    # (5,4) 实战攻防案例检索
    {"query": "有没有Redis未授权访问的实战攻击案例", "expected": [{"main_intent_id": 5, "sub_intent_id": 4}]},
    {"query": "找一些域渗透的经典案例学习一下", "expected": [{"main_intent_id": 5, "sub_intent_id": 4}]},
    # (5,5) 行业研报分析总结
    {"query": "总结一下今年的网络安全威胁趋势报告", "expected": [{"main_intent_id": 5, "sub_intent_id": 5}]},
    {"query": "分析一下最新的APT年度报告里的关键发现", "expected": [{"main_intent_id": 5, "sub_intent_id": 5}]},
    # (5,6) 系统手册查询
    {"query": "Snort的规则语法怎么写", "expected": [{"main_intent_id": 5, "sub_intent_id": 6}]},
    {"query": "查一下iptables的NAT配置命令", "expected": [{"main_intent_id": 5, "sub_intent_id": 6}]},

    # === 6: 系统运维与配置管理 ===
    # (6,1) 防火墙策略下发
    {"query": "在防火墙上添加一条规则允许443端口入站", "expected": [{"main_intent_id": 6, "sub_intent_id": 1}]},
    {"query": "更新防火墙策略，禁止外网访问3306端口", "expected": [{"main_intent_id": 6, "sub_intent_id": 1}]},
    # (6,2) 系统补丁分发
    {"query": "给所有Windows服务器推送最新的系统更新", "expected": [{"main_intent_id": 6, "sub_intent_id": 2}]},
    {"query": "批量分发Linux内核安全补丁到生产环境", "expected": [{"main_intent_id": 6, "sub_intent_id": 2}]},
    # (6,3) 资产信息更新
    {"query": "更新CMDB里这台服务器的IP和负责人信息", "expected": [{"main_intent_id": 6, "sub_intent_id": 3}]},
    {"query": "把新上线的三台服务器录入资产管理系统", "expected": [{"main_intent_id": 6, "sub_intent_id": 3}]},
    # (6,4) 服务重启指令
    {"query": "重启一下Nginx服务", "expected": [{"main_intent_id": 6, "sub_intent_id": 4}]},
    {"query": "MySQL服务挂了，帮我重新启动", "expected": [{"main_intent_id": 6, "sub_intent_id": 4}]},
    # (6,5) 安全补丁分发
    {"query": "紧急下发OpenSSL的安全补丁到所有受影响机器", "expected": [{"main_intent_id": 6, "sub_intent_id": 5}]},
    {"query": "把这个CVE对应的安全修复包推送到全部节点", "expected": [{"main_intent_id": 6, "sub_intent_id": 5}]},
    # (6,6) 用户权限调整
    {"query": "给张三的账号添加数据库只读权限", "expected": [{"main_intent_id": 6, "sub_intent_id": 6}]},
    {"query": "把这个用户从管理员组移除", "expected": [{"main_intent_id": 6, "sub_intent_id": 6}]},
    # (6,7) 证书到期监控
    {"query": "检查一下哪些SSL证书快要到期了", "expected": [{"main_intent_id": 6, "sub_intent_id": 7}]},
    {"query": "监控域名证书有效期，到期前30天提醒", "expected": [{"main_intent_id": 6, "sub_intent_id": 7}]},
    # (6,8) 性能瓶颈告警分析
    {"query": "服务器CPU持续100%，分析一下是什么原因", "expected": [{"main_intent_id": 6, "sub_intent_id": 8}]},
    {"query": "数据库响应变慢，帮我排查性能瓶颈", "expected": [{"main_intent_id": 6, "sub_intent_id": 8}]},
    # (6,9) 资源扩容建议
    {"query": "当前服务器负载很高，需要扩容建议", "expected": [{"main_intent_id": 6, "sub_intent_id": 9}]},
    {"query": "评估一下是否需要增加云服务器实例", "expected": [{"main_intent_id": 6, "sub_intent_id": 9}]},

    # === 多意图测试 ===
    {"query": "分析这个恶意样本，同时检查防火墙有没有放行相关IP", "expected": [{"main_intent_id": 1, "sub_intent_id": 1}, {"main_intent_id": 6, "sub_intent_id": 1}]},
    {"query": "扫描系统漏洞并生成合规审计报告", "expected": [{"main_intent_id": 2, "sub_intent_id": 1}, {"main_intent_id": 3, "sub_intent_id": 6}]},
    {"query": "隔离被入侵主机并调查根因", "expected": [{"main_intent_id": 4, "sub_intent_id": 1}, {"main_intent_id": 4, "sub_intent_id": 6}]},
    {"query": "查一下这个IP的威胁情报，然后封禁它", "expected": [{"main_intent_id": 1, "sub_intent_id": 5}, {"main_intent_id": 4, "sub_intent_id": 1}]},
    {"query": "检查SSL证书到期情况，顺便看看有没有漏洞需要打补丁", "expected": [{"main_intent_id": 6, "sub_intent_id": 7}, {"main_intent_id": 2, "sub_intent_id": 3}]},
    {"query": "帮我解释一下什么是SSRF，然后给出防护建议", "expected": [{"main_intent_id": 5, "sub_intent_id": 1}, {"main_intent_id": 5, "sub_intent_id": 2}]},
]


def evaluate(recognizer: IntentRecognizer, dataset: list[dict], verbose: bool = False) -> dict:
    """运行评估，返回准确率指标"""
    total = len(dataset)
    main_correct = 0
    sub_correct = 0
    multi_intent_recall_sum = 0.0
    multi_intent_count = 0
    errors = []

    for i, case in enumerate(dataset):
        query = case["query"]
        expected = case["expected"]

        try:
            result = recognizer.predict(query)
        except Exception as e:
            errors.append({"index": i, "query": query, "error": str(e)})
            continue

        # 提取预测的 (main_id, sub_id) 集合
        pred_pairs = set()
        for r in result:
            mid = r.get("main_intent_id", 0)
            sid = r.get("sub_intent_id", 0)
            if isinstance(mid, int) and isinstance(sid, int):
                pred_pairs.add((mid, sid))

        expected_pairs = set()
        for e in expected:
            expected_pairs.add((e["main_intent_id"], e["sub_intent_id"]))

        # main_intent 准确率：预测的主意图集合是否包含期望的主意图
        expected_mains = {e[0] for e in expected_pairs}
        pred_mains = {p[0] for p in pred_pairs}
        if expected_mains.issubset(pred_mains):
            main_correct += 1

        # sub_intent 准确率：完全匹配（单意图）或召回率（多意图）
        if len(expected) == 1:
            if expected_pairs.issubset(pred_pairs):
                sub_correct += 1
            elif verbose:
                print(f"  MISS [{i}] {query}")
                print(f"    期望: {expected_pairs}, 预测: {pred_pairs}")
        else:
            # 多意图：计算召回率
            multi_intent_count += 1
            if len(expected_pairs) > 0:
                recall = len(expected_pairs & pred_pairs) / len(expected_pairs)
                multi_intent_recall_sum += recall
                if expected_pairs.issubset(pred_pairs):
                    sub_correct += 1
                elif verbose:
                    print(f"  PARTIAL [{i}] {query}")
                    print(f"    期望: {expected_pairs}, 预测: {pred_pairs}, recall={recall:.2f}")

        if verbose and i % 10 == 9:
            print(f"  进度: {i+1}/{total}")

        # 避免 API 限流
        time.sleep(0.3)

    main_acc = main_correct / total * 100 if total > 0 else 0
    sub_acc = sub_correct / total * 100 if total > 0 else 0
    multi_recall = (multi_intent_recall_sum / multi_intent_count * 100) if multi_intent_count > 0 else 0

    return {
        "total": total,
        "main_intent_accuracy": round(main_acc, 1),
        "sub_intent_accuracy": round(sub_acc, 1),
        "multi_intent_recall": round(multi_recall, 1),
        "errors": len(errors),
        "error_details": errors,
    }


def main():
    print("=" * 60)
    print("  意图识别评估")
    print("=" * 60)

    recognizer = IntentRecognizer(backend="api")
    print(f"  模型: {recognizer.api_model}")
    print(f"  测试集: {len(EVAL_DATASET)} 条")
    print()

    results = evaluate(recognizer, EVAL_DATASET, verbose=True)

    print()
    print("=" * 60)
    print(f"  主意图准确率: {results['main_intent_accuracy']}%")
    print(f"  子意图准确率: {results['sub_intent_accuracy']}%")
    print(f"  多意图召回率: {results['multi_intent_recall']}%")
    print(f"  API错误数: {results['errors']}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
