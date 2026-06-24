import json
import os
import tempfile

import pytest
import chromadb

from intent_recognition.rag import IntentRAG


@pytest.fixture
def rag(tmp_path):
    """使用 ChromaDB 默认 embedding 做测试（不需要外部 API 或模型）"""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma_test"))
    collection = client.get_or_create_collection(name="test_intent")
    r = IntentRAG.__new__(IntentRAG)
    r._client = client
    r._collection = collection
    r._persist_dir = str(tmp_path / "chroma_test")
    return r


def test_add_and_search(rag):
    intents = [{"main_intent_id": 1, "sub_intent_id": 5, "sub_intent_name": "IOC提取与检索"}]
    rag.add("帮我查一下这个IP的威胁情报", intents)
    assert rag.count() == 1

    results = rag.search("查询IP威胁情报", top_k=1)
    assert len(results) == 1
    assert results[0]["intents"][0]["sub_intent_id"] == 5


def test_deduplication(rag):
    intents = [{"main_intent_id": 1, "sub_intent_id": 1}]
    rag.add("分析恶意样本", intents)
    rag.add("分析恶意样本", intents)
    assert rag.count() == 1


def test_format_context():
    results = [
        {"query": "查IP情报", "intents": [{"main_intent_id": 1, "sub_intent_id": 5, "sub_intent_name": "IOC提取与检索"}]},
        {"query": "APT组织活动", "intents": [{"main_intent_id": 1, "sub_intent_id": 6, "sub_intent_name": "情报库关联查询"}]},
    ]
    text = IntentRAG.format_context_for_prompt(None, results)
    assert "语义相似案例参考" in text
    assert "IOC提取与检索" in text
    assert "情报库关联查询" in text


def test_format_empty():
    assert IntentRAG.format_context_for_prompt(None, []) == ""


def test_empty_search(rag):
    assert rag.search("任意查询") == []


def test_batch_import(rag, tmp_path):
    data = [
        {"query": "查询IP威胁情报", "expected": [{"main_intent_id": 1, "sub_intent_id": 5, "sub_intent_name": "IOC提取与检索"}]},
        {"query": "分析恶意样本", "expected": [{"main_intent_id": 1, "sub_intent_id": 1, "sub_intent_name": "恶意代码分析"}]},
        {"query": "检查等保合规", "expected": [{"main_intent_id": 3, "sub_intent_id": 1, "sub_intent_name": "合规基线检查"}]},
    ]
    data_path = str(tmp_path / "test_data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    count = rag.batch_import(data_path)
    assert count == 3
    assert rag.count() == 3
