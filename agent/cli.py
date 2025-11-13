"""
SecAgent 交互式命令行入口。

用法：
    python -m agent.cli
    python -m agent.cli --backend local --adapter-dir /path/to/adapter

初次启动时自动导入种子记忆数据。
"""

import argparse
import os
import sys


def _import_seed_memory(memory):
    """如果记忆库为空，导入种子数据"""
    if len(memory.entries) > 0:
        return 0

    seed_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "memory_store", "seed_memory.jsonl",
    )
    if not os.path.exists(seed_path):
        print("（种子记忆文件不存在，跳过导入）")
        return 0

    count = 0
    with open(seed_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                import json
                data = json.loads(line)
                memory.save_one(
                    user_query=data["user_query"],
                    recognized_intents=data["recognized_intents"],
                    matched_skills=data["matched_skills"],
                    tool_calls=data.get("tool_calls", []),
                    result_summary=data.get("result_summary", ""),
                    user_feedback=data.get("user_feedback", "confirmed"),
                )
                count += 1
            except (json.JSONDecodeError, KeyError):
                pass

    return count


def _prompt_feedback():
    """询问用户反馈"""
    while True:
        ans = input("\n这个结果是否正确？(y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("请输入 y 或 n")


def main():
    parser = argparse.ArgumentParser(
        description="SecAgent - 网络安全智能体交互式命令行",
    )
    parser.add_argument("--backend", default="api",
                        choices=["api", "local"],
                        help="意图识别后端 (default: api)")
    parser.add_argument("--api-base", default="http://localhost:8000/v1",
                        help="LLM API地址 (default: http://localhost:8000/v1)")
    parser.add_argument("--api-key", default="not-needed",
                        help="API密钥")
    parser.add_argument("--model", default="qwen3-8b",
                        help="模型名称 (default: qwen3-8b)")
    parser.add_argument("--adapter-dir", default=None,
                        help="LoRA adapter目录（local模式必需）")
    args = parser.parse_args()

    from agent.agent import SecurityAgent

    print("=" * 60)
    print("  SecAgent - 网络安全智能体")
    print("=" * 60)

    agent = SecurityAgent(
        intent_backend=args.backend,
        api_base=args.api_base,
        api_key=args.api_key,
        api_model=args.model,
        intent_adapter_dir=args.adapter_dir,
    )

    seed_count = _import_seed_memory(agent.memory)
    if seed_count > 0:
        print(f"\n已导入 {seed_count} 条种子记忆")

    stats = agent.get_stats()
    print(f"\nSkills库: {stats['skills_loaded']} 个")
    print(f"记忆库: {stats['memory']['total_entries']} 条 "
          f"(confirmed: {stats['memory']['confirmed']})")

    print("\n" + "-" * 60)
    print("输入你的安全需求，输入 /stats 查看统计，/quit 退出")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("再见！")
            break

        if user_input == "/stats":
            s = agent.get_stats()
            print(f"\nSkills: {s['skills_loaded']}  |  "
                  f"记忆: {s['memory']['total_entries']} 条"
                  f"（成功: {s['memory']['confirmed']}, "
                  f"失败: {s['memory']['rejected']}, "
                  f"待确认: {s['memory']['pending']}）")
            continue

        result = agent.run(user_input)

        execution_result = result.get("execution_result", {})
        summary = execution_result.get("summary", "")
        if summary:
            print(f"\n{'─' * 40}")
            print("执行摘要:")
            print(summary)

        ctx = result.get("execution_context")
        if ctx:
            ok = _prompt_feedback()
            if ok:
                agent.confirm(ctx)
            else:
                agent.reject(ctx)


if __name__ == "__main__":
    main()