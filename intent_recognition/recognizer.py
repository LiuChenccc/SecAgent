import json
import os
import re
from typing import Optional

from .taxonomy import MAIN_INTENT_NAMES, SUB_INTENT_NAMES
from .chinese_triggers import get_candidate_subdomains, CHINESE_TRIGGER_MAP
from .skill_mapper import INTENT_TO_SKILL_DOMAIN

# 构建分类体系文本（注入 prompt）
_TAXONOMY_TEXT = "【意图分类体系】你只能从以下分类中选择，不得自创ID：\n"
for main_id, main_name in MAIN_INTENT_NAMES.items():
    _TAXONOMY_TEXT += f"\n{main_id}. {main_name}：\n"
    for (mid, sid), sub_name in SUB_INTENT_NAMES.items():
        if mid == main_id:
            _TAXONOMY_TEXT += f"  ({mid},{sid}) {sub_name}\n"

# 反向映射：subdomain → 最佳 (main_intent_id, sub_intent_id)
_SUBDOMAIN_TO_INTENT: dict[str, tuple[int, int]] = {}
for (mid, sid), domain in INTENT_TO_SKILL_DOMAIN.items():
    if domain not in _SUBDOMAIN_TO_INTENT:
        _SUBDOMAIN_TO_INTENT[domain] = (mid, sid)


class IntentRecognizer:
    def __init__(
        self,
        backend: str = "api",
        model_id: str = "Qwen/Qwen3-8B",
        adapter_dir: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        api_model: Optional[str] = None,
    ):
        self.backend = backend
        self.model_id = model_id
        self.adapter_dir = adapter_dir
        self.api_base = api_base or os.environ.get("INTENT_API_BASE", "https://oneapi-comate.baidu-int.com/v1")
        self.api_key = api_key or os.environ.get("INTENT_API_KEY", "not-needed")
        self.api_model = api_model or os.environ.get("INTENT_MODEL", "deepseek-v4-pro")
        self._local_backend = None

        self._base_system_prompt = (
            "你是一个专业的网络安全意图识别助手。"
            "请仔细分析用户输入，识别其中包含的所有安全意图。"
            "注意：用户可能同时表达多个意图，请全部识别出来。\n\n"
            f"{_TAXONOMY_TEXT}\n"
            "【易混淆意图消歧规则】\n"
            "- (1,5)IOC提取与检索 vs (1,6)情报库关联查询：用户提供了具体的IP/域名/哈希要查询→(1,5)；用户想了解某个威胁组织/事件的关联上下文→(1,6)\n"
            "- (1,1)恶意代码分析 vs (1,7)沙箱分析触发：用户要求逆向/静态分析样本→(1,1)；用户明确要求在沙箱中动态执行→(1,7)\n"
            "- (1,1)恶意代码分析 vs (1,8)检测规则调优：用户要分析样本行为→(1,1)；用户要编写/优化Sigma/YARA/Snort检测规则→(1,8)\n"
            "- (3,1)合规基线检查 vs (3,5)策略违规扫描：用户引用了具体标准(等保/CIS/ISO)→(3,1)；用户要检查是否违反公司内部安全策略→(3,5)\n"
            "- (6,2)系统补丁分发 vs (6,5)安全补丁分发：常规系统更新/Windows Update→(6,2)；针对特定CVE/安全漏洞的紧急修复包→(6,5)\n"
            "- (2,1)漏洞扫描启动 vs (2,4)PoC验证执行：全面扫描发现漏洞→(2,1)；针对已知CVE用PoC验证是否可利用→(2,4)\n"
            "- (4,5)应急处置建议 vs (4,6)事件根因调查：用户问怎么处理/应对→(4,5)；用户问为什么发生/根本原因→(4,6)\n"
            "- (5,1)安全术语解释 vs (5,2)防护方案建议：用户问'什么是X'→(5,1)；用户问'怎么防范/防护X'→(5,2)\n\n"
            "【输出要求】\n"
            "1. 必须从上述分类中选择，main_intent_id和sub_intent_id必须是上面列出的有效组合\n"
            "2. 每个意图附带confidence字段（0.0-1.0），表示你对该分类的确信程度\n"
            "3. 输出格式为JSON数组，如果只有一个意图也用数组格式\n"
            "4. 不要输出任何其他内容，只输出JSON"
        )

    def _build_enhanced_prompt(
        self,
        user_input: str,
        skill_context: str = "",
        few_shot_context: str = "",
    ) -> str:
        parts = [self._base_system_prompt]
        if skill_context:
            parts.append(f"\n\n{skill_context}")
        if few_shot_context:
            parts.append(f"\n\n{few_shot_context}")
        parts.append(
            "\n\n请直接输出JSON数组，不要输出其他内容。"
            '示例：[{"main_intent_id": 1, "main_intent_name": "威胁检测与识别", '
            '"sub_intent_id": 1, "sub_intent_name": "恶意代码分析", "confidence": 0.92}]'
        )
        return "\n".join(parts)

    def predict(
        self,
        user_input: str,
        skill_context: str = "",
        few_shot_context: str = "",
        rag=None,
        max_new_tokens: int = 512,
    ) -> list[dict]:
        # 规则层短路：触发词得分足够高且无歧义时跳过 LLM
        shortcut = self._try_rule_shortcut(user_input)
        if shortcut:
            return shortcut

        # RAG 注入 few-shot 案例
        if rag and not few_shot_context:
            results = rag.search(user_input, top_k=3)
            few_shot_context = rag.format_context_for_prompt(results)

        system_prompt = self._build_enhanced_prompt(
            user_input, skill_context, few_shot_context
        )
        if self.backend == "local":
            raw = self._predict_local(user_input, max_new_tokens)
        else:
            raw = self._predict_api(system_prompt, user_input, max_new_tokens)
        return self._parse_response(raw)

    def _try_rule_shortcut(self, query: str) -> Optional[list[dict]]:
        """规则层短路：触发词匹配得分高且无歧义时直接返回"""
        scored = []
        for subdomain, triggers in CHINESE_TRIGGER_MAP.items():
            score = 0
            for trigger in triggers:
                if trigger.lower() in query.lower():
                    score += len(trigger)
            if score > 0:
                scored.append((score, subdomain))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        top_score = scored[0][0]
        second_score = scored[1][0] if len(scored) > 1 else 0

        # 短路条件：最高分 >= 8 且第二名 < 最高分的 30%（非常保守，确保不降低准确率）
        if top_score >= 8 and second_score < top_score * 0.3:
            subdomain = scored[0][1]
            if subdomain in _SUBDOMAIN_TO_INTENT:
                mid, sid = _SUBDOMAIN_TO_INTENT[subdomain]
                return [{
                    "main_intent_id": mid,
                    "main_intent_name": MAIN_INTENT_NAMES.get(mid, ""),
                    "sub_intent_id": sid,
                    "sub_intent_name": SUB_INTENT_NAMES.get((mid, sid), ""),
                    "confidence": 0.95,
                    "source": "rule",
                }]
        return None

    def _predict_local(self, user_input: str, max_new_tokens: int) -> str:
        if self._local_backend is None:
            from .local_backend import LocalBackend
            self._local_backend = LocalBackend(
                model_id=self.model_id, adapter_dir=self.adapter_dir
            )
        return self._local_backend.predict(user_input, max_new_tokens)

    def _predict_api(
        self, system_prompt: str, user_input: str, max_new_tokens: int
    ) -> str:
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

    def _parse_response(self, raw: str) -> list[dict]:
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
