"""
Skills 检索层 —— 将Skills库作为RAG知识源，在意图识别前检索相关Skills。

支持双格式 SKILL.md：
- GitHub 格式：name, description, domain, subdomain, tags, d3fend_techniques, nist_csf
- 本地格式：triggers(中文), keywords, frameworks

核心思路：
- 解析所有 SKILL.md 的 YAML frontmatter
- 中文触发词映射 → 锁定候选子领域 → 范围 TF-IDF + 关键词匹配
- 用户输入 → 检索 Top-K 相关Skill → 提取触发词和领域描述
- 检索结果注入意图识别 prompt，帮助模型识别多意图
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional

from .chinese_trigger_map import get_candidate_subdomains
from intent_recognition import normalize_subdomain


class SkillInfo:
    """单个Skill的结构化信息，兼容 GitHub 格式和本地格式"""

    def __init__(self, domain: str, path: str, frontmatter: dict, body: str):
        self.path = path
        self.body = body

        # 通用字段
        self.name = frontmatter.get("name", domain)
        self.description = frontmatter.get("description", "")
        self.domain = frontmatter.get("domain", domain)

        # GitHub 格式字段
        raw_subdomain = frontmatter.get("subdomain", "")
        self.subdomain = normalize_subdomain(raw_subdomain) if raw_subdomain else domain
        self.tags = [str(t).strip() for t in frontmatter.get("tags", []) if t is not None]
        self.d3fend_techniques = frontmatter.get("d3fend_techniques", [])
        self.nist_csf = frontmatter.get("nist_csf", [])
        self.version = str(frontmatter.get("version", ""))
        self.author = str(frontmatter.get("author", ""))

        # 本地格式字段（向后兼容）
        self.triggers = frontmatter.get("triggers", [])
        self.keywords = frontmatter.get("keywords", [])
        self.frameworks = frontmatter.get("frameworks", [])

    def to_search_text(self) -> str:
        """生成用于检索的聚合文本，合并双格式字段"""
        parts = [
            self.name,
            self.description,
            self.subdomain,
            " ".join(self.tags),
            " ".join(self.triggers),
            " ".join(self.keywords),
            self.domain,
        ]
        return " ".join(filter(None, parts))

    def to_context_str(self) -> str:
        """生成注入prompt的简短上下文描述，优先使用 GitHub tags"""
        if self.tags:
            tag_str = ", ".join(self.tags[:8])
            return (
                f"- {self.name}（子领域：{self.subdomain}）\n"
                f"  标签：{tag_str}"
            )
        # 本地格式回退
        trigger_str = "、".join(self.triggers[:5]) if self.triggers else "无"
        keyword_str = "、".join(self.keywords[:5]) if self.keywords else "无"
        return (
            f"- {self.name}（领域：{self.domain}）\n"
            f"  触发场景：{trigger_str}\n"
            f"  关键词：{keyword_str}"
        )


class SkillsRetriever:
    """Skills 检索器 —— 加载 + 中文触发词过滤 + TF-IDF 检索"""

    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            skills_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "skills",
            )
        self.skills_dir = Path(skills_dir)
        self._extra_dirs: list[Path] = []
        self.skills: list[SkillInfo] = []
        self._skill_texts: list[str] = []
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None

    def load_all(self, extra_dirs: list[str] = None) -> int:
        """加载所有 SKILL.md 文件，支持多目录"""
        self.skills = []
        self._skill_texts = []

        search_dirs = [self.skills_dir]
        if extra_dirs:
            for d in extra_dirs:
                search_dirs.append(Path(d))

        for d in search_dirs:
            if not d.exists():
                continue
            for skill_md in d.rglob("SKILL.md"):
                domain = skill_md.parent.name
                content = skill_md.read_text(encoding="utf-8")
                frontmatter, body = self._parse_skill(content)

                skill = SkillInfo(
                    domain=domain,
                    path=str(skill_md),
                    frontmatter=frontmatter,
                    body=body,
                )
                self.skills.append(skill)
                self._skill_texts.append(skill.to_search_text())

        if self.skills:
            self._build_index()
        elif not extra_dirs:
            print(
                "  [提示] Skills 目录为空或不存在。请下载 Skills 库：\n"
                "    git clone https://github.com/nicpenning/El0s agent/skills\n"
                "  详见 README.md"
            )
        return len(self.skills)

    def _parse_skill(self, content: str) -> tuple[dict, str]:
        """解析SKILL.md：分离YAML frontmatter和正文"""
        frontmatter = {}
        body = content

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                pass
            body = content[match.end():]

        return frontmatter, body.strip()

    def _build_index(self):
        """构建 TF-IDF 索引"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=2000,
                ngram_range=(1, 2),
                analyzer="char_wb",
            )
            self._tfidf_matrix = self._tfidf_vectorizer.fit_transform(
                self._skill_texts
            )
        except ImportError:
            pass

    def search(
        self, query: str, top_k: int = 5, use_tfidf: bool = True,
    ) -> list[SkillInfo]:
        """
        检索与 query 最相关的 Top-K Skills。

        流程：中文触发词 → 候选子领域 → 范围 TF-IDF → 综合评分
        """
        if not self.skills:
            return []

        candidate_subdomains = get_candidate_subdomains(query)

        if candidate_subdomains:
            scoped_skills = [
                s for s in self.skills
                if s.subdomain in candidate_subdomains
            ]
            if len(scoped_skills) >= top_k:
                return self._scoped_search(query, top_k, scoped_skills)

        return self._full_search(query, top_k)

    def _scoped_search(
        self, query: str, top_k: int, scoped_skills: list[SkillInfo],
    ) -> list[SkillInfo]:
        """在候选子领域范围内做关键词匹配，子领域匹配本身贡献基础分"""
        scored = []
        query_lower = query.lower()

        for skill in scoped_skills:
            score = 3  # 基础分：子领域匹配
            search_text = skill.to_search_text().lower()

            for tag in skill.tags:
                tag_lower = tag.lower()
                if tag_lower in query_lower:
                    score += 4
                # 也检查中文分词后的子串匹配
                for j in range(len(tag_lower) - 1):
                    if tag_lower[j:j + 2] in query_lower:
                        score += 0.5
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    score += 3
            for keyword in skill.keywords:
                if keyword.lower() in query_lower:
                    score += 2

            # 描述文本匹配（GitHub Skills 描述是英文或中英混合）
            desc_words = re.findall(r"[a-zA-Z]+", skill.description.lower())
            query_words = re.findall(r"[a-zA-Z]+", query_lower)
            for qw in query_words:
                if len(qw) >= 3 and qw in skill.description.lower():
                    score += 2

            # 中文 bigram 匹配
            words = re.findall(r"[一-鿿]+", query_lower)
            for word in words:
                if len(word) >= 2:
                    if word in search_text:
                        score += 2
                    for j in range(len(word) - 1):
                        bigram = word[j:j + 2]
                        if bigram in search_text:
                            score += 0.5

            scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]

    def _full_search(
        self, query: str, top_k: int,
    ) -> list[SkillInfo]:
        """全量搜索：优先 TF-IDF，回退关键词"""
        if self._tfidf_vectorizer is not None:
            try:
                query_vec = self._tfidf_vectorizer.transform([query])
                scores = (self._tfidf_matrix @ query_vec.T).toarray().flatten()
                top_indices = scores.argsort()[::-1][:top_k]
                return [self.skills[i] for i in top_indices if scores[i] > 0]
            except Exception:
                pass

        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[SkillInfo]:
        """回退方案：基于关键词 + 字符级匹配"""
        scored = []
        query_lower = query.lower()

        for skill in self.skills:
            score = 0
            search_text = skill.to_search_text().lower()

            for tag in skill.tags:
                if tag.lower() in query_lower:
                    score += 4
            for keyword in skill.keywords:
                if keyword.lower() in query_lower:
                    score += 3
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    score += 2

            words = re.findall(r"[一-鿿]+|[a-zA-Z]+", query_lower)
            for word in words:
                if len(word) >= 2:
                    if word in search_text:
                        score += 1
                    for j in range(len(word) - 1):
                        bigram = word[j:j + 2]
                        if bigram in search_text:
                            score += 0.5

            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]

    def format_context_for_prompt(
        self, skills: list[SkillInfo],
    ) -> str:
        """将检索到的Skills格式化为prompt上下文"""
        if not skills:
            return "（未找到匹配的安全技能领域）"

        lines = ["以下是与用户输入可能相关的安全领域及触发条件："]
        for skill in skills:
            lines.append(skill.to_context_str())
        return "\n".join(lines)

    def get_skill_by_domain(self, domain: str) -> Optional[SkillInfo]:
        """按领域名获取Skill（优先匹配 subdomain，回退匹配 domain）"""
        for skill in self.skills:
            if skill.subdomain == domain or skill.domain == domain:
                return skill
        return None

    def get_skill_by_subdomain(self, subdomain: str) -> Optional[SkillInfo]:
        """按规范子领域名获取Skill（返回第一个匹配）"""
        for skill in self.skills:
            if skill.subdomain == subdomain:
                return skill
        return None