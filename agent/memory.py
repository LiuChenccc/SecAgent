"""
记忆系统 —— 存储和检索历史执行记录。

核心功能：
- JSONL 文件持久化存储每次成功执行
- TF-IDF + 关键词检索相似历史查询
- 检索结果注入意图识别 prompt 作为 few-shot
- 反馈闭环：用户确认 → 存储 → 下次可用
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class MemoryEntry:
    """单条记忆记录"""

    def __init__(
        self,
        mem_id: str,
        timestamp: str,
        user_query: str,
        recognized_intents: list[dict],
        matched_skills: list[str],
        tool_calls: list[dict],
        result_summary: str,
        user_feedback: str = "pending",
    ):
        self.id = mem_id
        self.timestamp = timestamp
        self.user_query = user_query
        self.recognized_intents = recognized_intents
        self.matched_skills = matched_skills
        self.tool_calls = tool_calls
        self.result_summary = result_summary
        self.user_feedback = user_feedback

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "user_query": self.user_query,
            "recognized_intents": self.recognized_intents,
            "matched_skills": self.matched_skills,
            "tool_calls": self.tool_calls,
            "result_summary": self.result_summary,
            "user_feedback": self.user_feedback,
        }

    def to_few_shot_str(self) -> str:
        """格式化为few-shot示例文本"""
        intents_str = "、".join(
            f"{i['main_intent_name']}/{i['sub_intent_name']}"
            for i in self.recognized_intents
        )
        return (
            f"案例：用户问\"{self.user_query}\" → "
            f"识别意图为[{intents_str}] → "
            f"匹配技能领域：{', '.join(self.matched_skills)} → "
            f"结果：{self.result_summary[:100]}"
        )

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(
            mem_id=d["id"],
            timestamp=d["timestamp"],
            user_query=d["user_query"],
            recognized_intents=d["recognized_intents"],
            matched_skills=d["matched_skills"],
            tool_calls=d.get("tool_calls", []),
            result_summary=d.get("result_summary", ""),
            user_feedback=d.get("user_feedback", "pending"),
        )


class MemorySystem:
    """记忆系统 —— JSONL存储 + 检索"""

    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[MemoryEntry] = []
        self._counter = 0

    def load(self) -> int:
        """从JSONL文件加载所有记忆"""
        self.entries = []
        if self.store_path.exists():
            with open(self.store_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = MemoryEntry.from_dict(json.loads(line))
                            self.entries.append(entry)
                        except (json.JSONDecodeError, KeyError):
                            pass
        self._counter = len(self.entries)
        return len(self.entries)

    def save_one(
        self,
        user_query: str,
        recognized_intents: list[dict],
        matched_skills: list[str],
        tool_calls: list[dict],
        result_summary: str,
        user_feedback: str = "confirmed",
    ) -> MemoryEntry:
        """保存一条新的记忆记录"""
        self._counter += 1
        entry = MemoryEntry(
            mem_id=f"mem_{self._counter:04d}",
            timestamp=datetime.now().isoformat(),
            user_query=user_query,
            recognized_intents=recognized_intents,
            matched_skills=matched_skills,
            tool_calls=tool_calls,
            result_summary=result_summary,
            user_feedback=user_feedback,
        )
        self.entries.append(entry)
        self._append_to_file(entry)
        return entry

    def _append_to_file(self, entry: MemoryEntry):
        """追加写入JSONL文件"""
        with open(self.store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def search(
        self,
        query: str,
        top_k: int = 3,
        feedback_filter: Optional[str] = "confirmed",
    ) -> list[MemoryEntry]:
        """
        检索与query最相似的历史记忆。

        feedback_filter: None=全部, "confirmed"=仅成功的
        """
        candidates = self.entries
        if feedback_filter:
            candidates = [
                e for e in candidates if e.user_feedback == feedback_filter
            ]

        if not candidates:
            return []

        scored = []
        query_lower = query.lower()

        for entry in candidates:
            score = self._compute_similarity(query_lower, entry)

            if entry.user_feedback == "confirmed":
                score *= 1.5

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def _compute_similarity(self, query_lower: str, entry: MemoryEntry) -> float:
        """计算query与记忆条目的相似度分数"""
        score = 0.0
        entry_text = entry.user_query.lower()

        words = re.findall(r"[一-鿿]+|[a-zA-Z]+", query_lower)
        for word in words:
            if len(word) >= 2:
                if word in entry_text:
                    score += 1.0
                for j in range(len(word) - 1):
                    bigram = word[j : j + 2]
                    if bigram in entry_text:
                        score += 0.5

        for intent in entry.recognized_intents:
            main_name = intent.get("main_intent_name", "")
            sub_name = intent.get("sub_intent_name", "")
            if main_name and main_name in query_lower:
                score += 2.0
            if sub_name and sub_name in query_lower:
                score += 3.0

        for skill in entry.matched_skills:
            if skill.replace("_", " ") in query_lower or skill in query_lower:
                score += 2.0

        return score

    def format_context_for_prompt(
        self, entries: list[MemoryEntry]
    ) -> str:
        """将历史记忆格式化为few-shot prompt上下文"""
        if not entries:
            return "（暂无相似历史案例）"

        lines = ["以下是历史相似案例供参考："]
        for i, entry in enumerate(entries, 1):
            lines.append(f"案例{i}: {entry.to_few_shot_str()}")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取记忆系统统计信息"""
        total = len(self.entries)
        confirmed = sum(
            1 for e in self.entries if e.user_feedback == "confirmed"
        )
        rejected = sum(
            1 for e in self.entries if e.user_feedback == "rejected"
        )
        return {
            "total_entries": total,
            "confirmed": confirmed,
            "rejected": rejected,
            "pending": total - confirmed - rejected,
        }