"""
主 Agent 编排 —— 串联所有模块，提供统一接口。

六步流水线：
1. Skills检索 → 2. 记忆检索 → 3. 增强意图识别
→ 4. 意图→Skill映射 → 5. 执行 → 6. 反馈存储
"""

import os
import json
from datetime import datetime
from typing import Optional

from .skills_retriever import SkillsRetriever, normalize_subdomain
from .skill_mapper import (
    get_skill_domain,
    get_skill_domains,
    MAIN_INTENT_NAMES,
    SUB_INTENT_NAMES,
)
from .memory import MemorySystem
from .executor import Executor
from .intent import IntentRecognizer


DEFAULT_EXECUTOR_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_EXECUTOR_MODEL = "qwen3.6-plus-2026-04-02"


class SecurityAgent:
    """网络安全智能体 —— 主编排器"""

    def __init__(
        self,
        skills_dir: Optional[str] = None,
        extra_skills_dirs: Optional[list[str]] = None,
        memory_path: str = "",
        intent_backend: str = "api",
        intent_adapter_dir: Optional[str] = None,
        intent_api_base: Optional[str] = None,
        intent_api_key: Optional[str] = None,
        intent_model: Optional[str] = None,
        executor_api_base: Optional[str] = None,
        executor_api_key: Optional[str] = None,
        executor_model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        api_model: Optional[str] = None,
    ):
        """
        初始化智能体。

        Args:
            skills_dir: Skills库目录路径（默认指向 GitHub 项目）
            extra_skills_dirs: 额外的 Skills 目录（如本地自定义Skills）
            memory_path: 记忆存储文件路径
            intent_backend: 意图识别后端 "api" | "local"
            intent_adapter_dir: LoRA adapter目录（local模式需提供）
            intent_api_base: 意图识别 LLM API地址（默认走 INTENT_API_BASE）
            intent_api_key: 意图识别 API密钥（默认走 INTENT_API_KEY）
            intent_model: 意图识别模型名称（默认走 INTENT_MODEL）
            executor_api_base: 执行引擎 LLM API地址（默认走 DASHSCOPE_API_BASE）
            executor_api_key: 执行引擎 API密钥（默认走 DASHSCOPE_API_KEY）
            executor_model: 执行引擎模型名称（默认走 DASHSCOPE_MODEL）
            api_base/api_key/api_model: 兼容旧入口；未指定新参数时同时作为两套配置
        """
        if skills_dir is None:
            skills_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "skills",
            )
        self.skills_dir = skills_dir
        self.extra_skills_dirs = extra_skills_dirs or []

        agent_dir = os.path.dirname(os.path.abspath(__file__))
        default_memory = os.path.join(agent_dir, "memory_store", "execution_memory.jsonl")
        self.memory_path = memory_path or default_memory

        # 兼容旧入口：api_base/api_key/api_model 未被新参数覆盖时，可同时作为两套配置。
        self.intent_api_base = intent_api_base if intent_api_base is not None else api_base
        self.intent_api_key = intent_api_key if intent_api_key is not None else api_key
        self.intent_model = intent_model if intent_model is not None else api_model

        self.executor_api_base = (
            executor_api_base
            if executor_api_base is not None
            else api_base
            if api_base is not None
            else os.environ.get("DASHSCOPE_API_BASE", DEFAULT_EXECUTOR_API_BASE)
        )
        self.executor_api_key = (
            executor_api_key
            if executor_api_key is not None
            else api_key
            if api_key is not None
            else os.environ.get("DASHSCOPE_API_KEY", "not-needed")
        )
        self.executor_model = (
            executor_model
            if executor_model is not None
            else api_model
            if api_model is not None
            else os.environ.get("DASHSCOPE_MODEL", DEFAULT_EXECUTOR_MODEL)
        )

        # 旧字段保留为执行引擎配置，兼容已有调用方读取。
        self.api_base = self.executor_api_base
        self.api_key = self.executor_api_key
        self.api_model = self.executor_model

        print("初始化 SecurityAgent...")

        print("  加载Skills检索器...")
        self.skills_retriever = SkillsRetriever(skills_dir)
        skill_count = self.skills_retriever.load_all(
            extra_dirs=self.extra_skills_dirs
        )
        print(f"    已加载 {skill_count} 个Skills")

        print("  加载记忆系统...")
        self.memory = MemorySystem(self.memory_path)
        mem_count = self.memory.load()
        if mem_count > 0:
            stats = self.memory.get_stats()
            print(
                f"    已加载 {mem_count} 条记忆 "
                f"（成功: {stats['confirmed']}, 待确认: {stats['pending']}）"
            )

        print("  初始化意图识别器...")
        self.intent_recognizer = IntentRecognizer(
            backend=intent_backend,
            adapter_dir=intent_adapter_dir,
            api_base=self.intent_api_base,
            api_key=self.intent_api_key,
            api_model=self.intent_model,
        )
        print(f"    意图识别后端: {intent_backend}")

        print("  初始化执行引擎...")
        self.executor = Executor(
            api_base=self.executor_api_base,
            api_key=self.executor_api_key,
            api_model=self.executor_model,
        )

        print("SecurityAgent 初始化完成。")

    def run(
        self,
        user_input: str,
        verbose: bool = True,
    ) -> dict:
        """
        处理用户输入，执行完整的六步流水线。

        Returns:
            {
                "user_input": str,
                "candidate_skills": [...],
                "similar_cases": [...],
                "intents": [...],
                "matched_domains": [...],
                "skill_contents": [...],
                "execution_result": {...},
                "execution_context": {...},  # 用于后续confirm
            }
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"用户输入: {user_input}")
            print(f"{'='*60}")

        # Step 1: Skills检索
        if verbose:
            print("\n[Step 1] Skills检索中...")
        candidate_skills = self.skills_retriever.search(
            user_input, top_k=5
        )
        skill_context = self.skills_retriever.format_context_for_prompt(
            candidate_skills
        )
        if verbose:
            print(
                f"  匹配到 {len(candidate_skills)} 个候选Skill: "
                f"{[s.subdomain for s in candidate_skills]}"
            )

        # Step 2: 记忆检索
        if verbose:
            print("\n[Step 2] 记忆检索中...")
        similar_cases = self.memory.search(
            user_input, top_k=2, feedback_filter="confirmed"
        )
        few_shot_context = self.memory.format_context_for_prompt(
            similar_cases
        )
        if verbose:
            print(f"  匹配到 {len(similar_cases)} 个相似历史案例")

        # Step 3: 增强意图识别
        if verbose:
            print("\n[Step 3] 增强意图识别中...")
        intents = self.intent_recognizer.predict(
            user_input,
            skill_context=skill_context,
            few_shot_context=few_shot_context,
        )
        if verbose:
            print(
                f"  识别到 {len(intents)} 个意图:"
            )
            print(self.intent_recognizer.format_intents_for_display(intents))

        # Step 4: 意图→Skill映射
        if verbose:
            print("\n[Step 4] 意图→Skill映射中...")
        matched_domains = get_skill_domains(intents)
        skill_contents = []
        for domain in matched_domains:
            # 优先按 subdomain 匹配，回退到 domain
            skill = self.skills_retriever.get_skill_by_subdomain(domain)
            if not skill:
                skill = self.skills_retriever.get_skill_by_domain(domain)
            if skill:
                skill_contents.append(
                    {
                        "domain": domain,
                        "name": skill.name,
                        "subdomain": skill.subdomain,
                        "content": skill.body,
                    }
                )
                if verbose:
                    print(f"  {domain} → {skill.name}")
            else:
                if verbose:
                    print(f"  {domain} → (Skill未找到)")

        # Step 5: 执行
        if verbose:
            print("\n[Step 5] 执行中...")
        execution_result = self.executor.execute(
            user_input=user_input,
            intents=intents,
            skill_contents=skill_contents,
            verbose=verbose,
        )

        if verbose:
            print(f"\n{'='*60}")
            print("执行完成。")

        # 构建执行上下文（用于后续反馈存储）
        execution_context = {
            "user_input": user_input,
            "intents": intents,
            "matched_domains": matched_domains,
            "skill_contents": skill_contents,
            "execution_result": execution_result,
        }

        return {
            "user_input": user_input,
            "candidate_skills": [
                {"domain": s.subdomain, "name": s.name}
                for s in candidate_skills
            ],
            "similar_cases": [
                {"query": c.user_query, "result": c.result_summary}
                for c in similar_cases
            ],
            "intents": intents,
            "matched_domains": matched_domains,
            "skill_contents": skill_contents,
            "execution_result": execution_result,
            "execution_context": execution_context,
        }

    def confirm(self, execution_context: dict) -> str:
        """
        用户确认执行结果正确，写入记忆。

        Returns:
            记忆条目ID
        """
        result = execution_context.get("execution_result", {})
        summary = result.get("summary", "")

        intents = execution_context.get("intents", [])
        domains = execution_context.get("matched_domains", [])

        all_tool_calls = []
        for item in result.get("intent_results", []):
            all_tool_calls.extend(item.get("tool_calls", []))

        entry = self.memory.save_one(
            user_query=execution_context.get("user_input", ""),
            recognized_intents=intents,
            matched_skills=domains,
            tool_calls=all_tool_calls,
            result_summary=summary[:500],
            user_feedback="confirmed",
        )

        print(f"\n已记录到记忆系统 (ID: {entry.id})")
        print(f"  意图: {len(intents)} 个")
        print(f"  技能领域: {domains}")
        return entry.id

    def reject(self, execution_context: dict) -> str:
        """
        用户反馈结果不正确，记录为失败案例。

        Returns:
            记忆条目ID
        """
        intents = execution_context.get("intents", [])
        domains = execution_context.get("matched_domains", [])

        result = execution_context.get("execution_result", {})
        all_tool_calls = []
        for item in result.get("intent_results", []):
            all_tool_calls.extend(item.get("tool_calls", []))

        entry = self.memory.save_one(
            user_query=execution_context.get("user_input", ""),
            recognized_intents=intents,
            matched_skills=domains,
            tool_calls=all_tool_calls,
            result_summary="用户反馈结果不正确",
            user_feedback="rejected",
        )

        print(f"\n已记录失败案例 (ID: {entry.id})")
        return entry.id

    def get_stats(self) -> dict:
        """获取Agent统计信息"""
        mem_stats = self.memory.get_stats()
        return {
            "skills_loaded": len(self.skills_retriever.skills),
            "memory": mem_stats,
        }