"""
RAG 增强模块 —— 基于 ChromaDB 的语义检索，为意图识别提供 few-shot 案例。

支持两种 Embedding 模式：
- api: 调用 OpenAI 兼容的 /v1/embeddings 接口（百度OneAPI / 百炼等）
- local: 使用 sentence-transformers 本地模型（如 bge-small-zh）
"""

import hashlib
import json
import os
from typing import Optional

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings


class APIEmbeddingFunction(EmbeddingFunction):
    """OpenAI 兼容的 Embedding 接口"""

    def __init__(self, api_base: str, api_key: str, model: str):
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:
        import requests
        resp = requests.post(
            f"{self._api_base}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "input": input},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda x: x["index"])
        return [d["embedding"] for d in data]


class LocalEmbeddingFunction(EmbeddingFunction):
    """sentence-transformers 本地 Embedding"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "本地 embedding 需要安装 sentence-transformers: "
                "pip install sentence-transformers"
            )
        self._model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        return self._model.encode(input).tolist()


class IntentRAG:
    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "intent_examples",
        embedding_mode: Optional[str] = None,
        embedding_api_base: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        local_model_name: str = "BAAI/bge-small-zh-v1.5",
    ):
        self._persist_dir = persist_dir or os.environ.get(
            "RAG_PERSIST_DIR",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_store"),
        )
        mode = embedding_mode or os.environ.get("RAG_EMBEDDING_MODE", "api")

        if mode == "local":
            ef = LocalEmbeddingFunction(local_model_name)
        else:
            api_base = embedding_api_base or os.environ.get(
                "EMBEDDING_API_BASE",
                os.environ.get("INTENT_API_BASE", "https://oneapi-comate.baidu-int.com/v1"),
            )
            api_key = embedding_api_key or os.environ.get(
                "EMBEDDING_API_KEY",
                os.environ.get("INTENT_API_KEY", "not-needed"),
            )
            model = embedding_model or os.environ.get("EMBEDDING_MODEL", "text-embedding-v3")
            ef = APIEmbeddingFunction(api_base, api_key, model)

        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef,
        )

    @staticmethod
    def _make_id(query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()[:16]

    def add(self, query: str, intents: list, source: str = "feedback") -> None:
        doc_id = self._make_id(query)
        self._collection.upsert(
            ids=[doc_id],
            documents=[query],
            metadatas=[{"intents_json": json.dumps(intents, ensure_ascii=False), "source": source}],
        )

    def batch_import(self, data_path: str) -> int:
        with open(data_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        ids, docs, metas = [], [], []
        for item in dataset:
            query = item["query"]
            doc_id = self._make_id(query)
            ids.append(doc_id)
            docs.append(query)
            metas.append({
                "intents_json": json.dumps(item["expected"], ensure_ascii=False),
                "source": "seed",
            })

        # ChromaDB 单次最多 batch 5461 条
        batch_size = 5000
        for i in range(0, len(ids), batch_size):
            self._collection.upsert(
                ids=ids[i:i + batch_size],
                documents=docs[i:i + batch_size],
                metadatas=metas[i:i + batch_size],
            )
        return len(ids)

    def search(self, query: str, top_k: int = 3) -> list:
        if self._collection.count() == 0:
            return []
        results = self._collection.query(query_texts=[query], n_results=top_k)
        out = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            intents = json.loads(meta["intents_json"])
            out.append({"query": doc, "intents": intents})
        return out

    def format_context_for_prompt(self, results: list) -> str:
        if not results:
            return ""
        lines = ["【语义相似案例参考】"]
        for i, r in enumerate(results, 1):
            intent_strs = []
            for it in r["intents"]:
                mid = it.get("main_intent_id", "?")
                sid = it.get("sub_intent_id", "?")
                name = it.get("sub_intent_name", "")
                intent_strs.append(f"({mid},{sid}){name}")
            lines.append(f'案例{i}: "{r["query"]}" → [{", ".join(intent_strs)}]')
        return "\n".join(lines)

    def count(self) -> int:
        return self._collection.count()
