"""
增强意图识别模块 —— 在原有LoRA模型基础上，注入Skills检索结果和历史案例来提升多意图识别。

核心改进：
1. 原版prompt → 增强版prompt（注入候选Skills + 历史few-shot案例）
2. 支持两种模式：本地LoRA模型 / API调用
3. 解析JSON数组输出，处理格式异常
"""

import json
import os
import re
from typing import Optional


class IntentRecognizer:
    """
    增强意图识别器。

    支持两种后端：
    - local: 使用Qwen3-8B LoRA模型（需GPU）
    - api: 使用OpenAI兼容API
    """

    def __init__(
        self,
        backend: str = "api",
        model_id: str = "Qwen/Qwen3-8B",
        adapter_dir: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        api_model: str = "qwen3-8b",
    ):
        self.backend = backend
        self.model_id = model_id
        self.adapter_dir = adapter_dir
        self.api_base = api_base or "http://localhost:8000/v1"
        self.api_key = api_key or "not-needed"
        self.api_model = api_model
        self._local_analyzer = None

        self._base_system_prompt = (
            "你是一个专业的网络安全意图识别助手。"
            "请仔细分析用户输入，识别其中包含的所有安全意图。"
            "注意：用户可能同时表达多个意图，请全部识别出来。"
            "输出格式必须为 JSON 数组，每个元素包含："
            "main_intent_id, main_intent_name, sub_intent_id, sub_intent_name。"
            "如果只有一个意图，也要用数组格式。"
        )

    def _build_enhanced_prompt(
        self,
        user_input: str,
        skill_context: str = "",
        few_shot_context: str = "",
    ) -> str:
        """构建增强版system prompt，注入Skills上下文和历史案例"""
        parts = [self._base_system_prompt]

        if skill_context:
            parts.append(f"\n\n{skill_context}")

        if few_shot_context:
            parts.append(f"\n\n{few_shot_context}")

        parts.append(
            "\n\n请直接输出JSON数组，不要输出其他内容。"
            "示例输出格式：[{\"main_intent_id\": 1, \"main_intent_name\": \"威胁检测与识别\", "
            "\"sub_intent_id\": 1, \"sub_intent_name\": \"恶意代码分析\"}]"
        )
        return "\n".join(parts)

    def predict(
        self,
        user_input: str,
        skill_context: str = "",
        few_shot_context: str = "",
        max_new_tokens: int = 256,
    ) -> list[dict]:
        """
        执行增强意图识别。

        Returns:
            意图列表 [{"main_intent_id": int, "main_intent_name": str, ...}, ...]
        """
        system_prompt = self._build_enhanced_prompt(
            user_input, skill_context, few_shot_context
        )

        if self.backend == "local":
            raw = self._predict_local(system_prompt, user_input, max_new_tokens)
        else:
            raw = self._predict_api(system_prompt, user_input, max_new_tokens)

        return self._parse_response(raw)

    def _predict_local(
        self, system_prompt: str, user_input: str, max_new_tokens: int
    ) -> str:
        """使用本地LoRA模型推理"""
        if self._local_analyzer is None:
            self._init_local_model()
        return self._local_analyzer.predict(user_input, max_new_tokens)

    def _init_local_model(self):
        """延迟初始化本地模型"""
        if not self.adapter_dir:
            raise RuntimeError("本地模式需要指定 adapter_dir 参数")
        import sys
        intent_module = os.path.dirname(self.adapter_dir)
        if intent_module not in sys.path:
            sys.path.insert(0, intent_module)
        from infer import IntentAnalyzer

        self._local_analyzer = IntentAnalyzer(
            model_id=self.model_id,
            adapter_dir=self.adapter_dir,
        )

    def _predict_api(
        self, system_prompt: str, user_input: str, max_new_tokens: int
    ) -> str:
        """使用OpenAI兼容API推理"""
        try:
            from openai import OpenAI

            client = OpenAI(base_url=self.api_base, api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.api_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=max_new_tokens,
                temperature=0.0,
            )
            return response.choices[0].message.content
        except ImportError:
            raise RuntimeError(
                "API模式需要安装 openai 库: pip install openai"
            )
        except Exception as e:
            raise RuntimeError(f"API调用失败: {e}")

    def _parse_response(self, raw: str) -> list[dict]:
        """从模型原始输出中解析JSON数组"""
        if not raw:
            return []

        raw = raw.strip()
        try:
            result = json.loads(raw)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
            return []
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return []

    @staticmethod
    def format_intents_for_display(intents: list[dict]) -> str:
        """将意图列表格式化为可读字符串"""
        if not intents:
            return "（未识别到意图）"

        lines = []
        for i, intent in enumerate(intents, 1):
            main = intent.get("main_intent_name", "未知")
            sub = intent.get("sub_intent_name", "未知")
            mid = intent.get("main_intent_id", "?")
            sid = intent.get("sub_intent_id", "?")
            lines.append(f"  {i}. [{mid}-{sid}] {main} → {sub}")
        return "\n".join(lines)