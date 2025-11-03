"""
执行引擎 —— 读取Skill内容，用LLM function calling逐步执行安全任务。

工作流：
1. 加载匹配到的 SKILL.md 完整内容
2. 构建 system prompt（Skill步骤 + 可用工具列表）
3. LLM 逐步判断：需要调工具 → function_call；需要推理 → 直接生成
4. 执行工具调用，结果回传LLM继续下一步
5. 汇总最终结果
"""

import json
import re
from typing import Optional

from .tools import TOOL_SCHEMAS, execute_tool

# 转为 OpenAI 标准 tools 格式
_TOOLS_FOR_API = [
    {"type": "function", "function": schema}
    for schema in TOOL_SCHEMAS
]


class Executor:
    """执行引擎 —— LLM + Tool Calling"""

    def __init__(
        self,
        api_base: str = "http://localhost:8000/v1",
        api_key: str = "not-needed",
        api_model: str = "qwen3.6-plus-2026-04-02",
        max_tool_rounds: int = 3,
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.api_model = api_model
        self.max_tool_rounds = max_tool_rounds

    def execute(
        self,
        user_input: str,
        intents: list[dict],
        skill_contents: list[dict],
        verbose: bool = True,
    ) -> dict:
        """
        执行安全任务。

        Args:
            user_input: 用户原始输入
            intents: 识别到的意图列表
            skill_contents: 匹配到的Skill内容列表
                [{"domain": "malware_analysis", "content": "SKILL.md全文", ...}, ...]
            verbose: 是否打印执行过程

        Returns:
            {"intent_results": [...], "summary": "..."}
        """
        results = []

        for intent in intents:
            main_name = intent.get("main_intent_name", "")
            sub_name = intent.get("sub_intent_name", "")
            if verbose:
                print(f"\n{'='*50}")
                print(f"执行: {main_name} → {sub_name}")

            skill_content = self._find_skill_for_intent(
                intent, skill_contents
            )

            if skill_content:
                result_text, tool_calls = self._execute_with_skill(
                    user_input, intent, skill_content, verbose
                )
            else:
                result_text, tool_calls = self._execute_without_skill(
                    user_input, intent, verbose
                )

            results.append(
                {
                    "intent": intent,
                    "result": result_text,
                    "tool_calls": tool_calls,
                }
            )

        return {
            "intent_results": results,
            "summary": self._summarize(results),
        }

    def _find_skill_for_intent(
        self, intent: dict, skill_contents: list[dict]
    ) -> Optional[str]:
        """根据意图找到对应的Skill内容"""
        for sc in skill_contents:
            domain = sc.get("domain", "")
            if domain and domain in json.dumps(intent, ensure_ascii=False):
                return sc.get("content", "")
        if skill_contents:
            return skill_contents[0].get("content", "")
        return None

    def _execute_with_skill(
        self,
        user_input: str,
        intent: dict,
        skill_content: str,
        verbose: bool,
    ):
        """有Skill内容时：按Skill步骤执行。返回 (result_str, tool_calls_log)"""
        system_prompt = self._build_execution_prompt(skill_content, intent)

        return self._run_llm_loop(
            system_prompt, user_input, verbose
        )

    def _execute_without_skill(
        self,
        user_input: str,
        intent: dict,
        verbose: bool,
    ):
        """无Skill时：让LLM基于通用知识分析。返回 (result_str, tool_calls_log)"""
        main_name = intent.get("main_intent_name", "安全分析")
        sub_name = intent.get("sub_intent_name", "")

        system_prompt = (
            f"你是一个网络安全专家。请针对用户的问题，从「{main_name} - {sub_name}」"
            f"的角度进行分析。如果需要调用工具获取数据，请使用function call。"
            f"请给出结构化的分析报告。"
        )

        return self._run_llm_loop(
            system_prompt, user_input, verbose
        )

    def _build_execution_prompt(
        self, skill_content: str, intent: dict
    ) -> str:
        """构建执行prompt"""
        main_name = intent.get("main_intent_name", "")
        sub_name = intent.get("sub_intent_name", "")

        return f"""你是一个网络安全专家。请严格按照以下工作流程执行任务。

## 任务类型
- 主意图：{main_name}
- 子意图：{sub_name}

## 工作流程
{skill_content}

## 可用工具
你可以使用 function call 调用以下工具来获取数据和执行操作：
{json.dumps(TOOL_SCHEMAS, ensure_ascii=False, indent=2)}

## 执行要求
1. 严格按照工作流程的步骤顺序执行
2. 需要获取数据时，优先使用工具调用
3. 每个步骤完成后说明结果
4. 所有步骤完成后，给出结构化的分析报告
5. 报告中包含：分析过程、关键发现、结论建议"""

    def _run_llm_loop(
        self,
        system_prompt: str,
        user_input: str,
        verbose: bool,
    ):
        """LLM对话循环 —— 支持多轮function calling。返回 (final_response, tool_calls_log)"""
        try:
            from openai import OpenAI
        except ImportError:
            return (
                "（执行引擎需要 openai 库。请安装: pip install openai）\n\n"
                f"将按照以下流程执行：\n{system_prompt[:500]}..."
            ), []

        client = OpenAI(base_url=self.api_base, api_key=self.api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        tool_calls_log = []
        final_response = ""
        for round_num in range(self.max_tool_rounds):
            response = client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                tools=_TOOLS_FOR_API,
                tool_choice="auto",
                temperature=0.0,
            )

            msg = response.choices[0].message
            messages.append(msg.model_dump())

            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    if verbose:
                        print(
                            f"  [Round {round_num+1}] 调用工具: {tool_name}"
                        )

                    tool_result = execute_tool(tool_name, arguments)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "arguments": arguments,
                        "result_summary": str(tool_result)[:300],
                    })

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                tool_result, ensure_ascii=False
                            ),
                        }
                    )
            else:
                final_response = msg.content or ""
                break

        if not final_response and messages:
            last = messages[-1]
            if last.get("role") == "assistant":
                final_response = last.get("content", "")

            if not final_response:
                messages.append({"role": "user", "content": "请根据以上工具调用结果，给出结构化的分析报告。"})
                try:
                    resp = client.chat.completions.create(
                        model=self.api_model,
                        messages=messages,
                        temperature=0.0,
                    )
                    final_response = resp.choices[0].message.content or ""
                except Exception:
                    pass

        return final_response or "（执行未产生结果）", tool_calls_log

    def _summarize(self, results: list[dict]) -> str:
        """汇总多个意图的执行结果"""
        parts = []
        for item in results:
            intent = item["intent"]
            result = item["result"]
            parts.append(
                f"### {intent.get('main_intent_name', '')} → "
                f"{intent.get('sub_intent_name', '')}\n"
                f"{result[:500]}\n"
            )
        return "\n".join(parts)