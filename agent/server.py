"""
SecAgent Web API 服务。

启动方式：
    python3 agent/server.py
    python3 agent/server.py --port 8800 --api-base http://localhost:8000/v1
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


DEFAULT_INTENT_API_BASE = "https://oneapi-comate.baidu-int.com/v1"
DEFAULT_INTENT_MODEL = "deepseek-v4-pro"
DEFAULT_EXECUTOR_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_EXECUTOR_MODEL = "qwen3.6-plus-2026-04-02"

_SESSIONS: dict[str, dict] = {}
_AGENT = None


def _resolve_option(explicit_value, legacy_value, env_name, default):
    """解析新参数、旧兼容参数、环境变量和默认值的优先级。"""
    if explicit_value is not None:
        return explicit_value
    if legacy_value is not None:
        return legacy_value
    return os.environ.get(env_name, default)


class ChatRequest(BaseModel):
    message: str


class FeedbackRequest(BaseModel):
    message: str
    feedback: str  # "confirmed" | "rejected"


def _get_agent():
    global _AGENT
    if _AGENT is None:
        raise HTTPException(status_code=503, detail="Agent 尚未初始化完成")
    return _AGENT


def _import_seed_memory(memory):
    """如果记忆库为空，导入种子数据"""
    if len(memory.entries) > 0:
        return 0
    seed_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "memory_store", "seed_memory.jsonl",
    )
    if not os.path.exists(seed_path):
        return 0
    count = 0
    with open(seed_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
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


def create_app() -> FastAPI:
    app = FastAPI(title="SecAgent API", version="1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/stats")
    async def get_stats():
        agent = _get_agent()
        return agent.get_stats()

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        agent = _get_agent()
        result = agent.run(req.message, verbose=False)

        sid = uuid.uuid4().hex[:12]
        ctx = result.get("execution_context")
        if ctx:
            _SESSIONS[sid] = ctx
            _SESSIONS[f"msg:{req.message}"] = ctx

        intent_results = result.get("execution_result", {}).get("intent_results", [])

        return {
            "session_id": sid,
            "message": req.message,
            "intents": result.get("intents", []),
            "candidate_skills": result.get("candidate_skills", []),
            "similar_cases_count": len(result.get("similar_cases", [])),
            "matched_domains": result.get("matched_domains", []),
            "summary": result.get("execution_result", {}).get("summary", ""),
            "intent_results": [
                {
                    "intent": r["intent"],
                    "result": r["result"],
                    "tool_calls": r.get("tool_calls", []),
                }
                for r in intent_results
            ],
            "stats": agent.get_stats(),
        }

    @app.post("/api/feedback")
    async def feedback(req: FeedbackRequest):
        agent = _get_agent()
        ctx = _SESSIONS.get(f"msg:{req.message}")
        if not ctx:
            ctx = {
                "user_input": req.message,
                "intents": [],
                "matched_domains": [],
                "execution_result": {"intent_results": [], "summary": ""},
            }

        if req.feedback == "confirmed":
            mid = agent.confirm(ctx)
        elif req.feedback == "rejected":
            mid = agent.reject(ctx)
        else:
            raise HTTPException(status_code=400, detail="feedback 必须为 confirmed 或 rejected")

        return {"ok": True, "memory_id": mid}

    return app


app = create_app()

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(_static_dir / "index.html"))


def main():
    parser = argparse.ArgumentParser(description="SecAgent Web Server")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--backend", default="api",
                        choices=["api", "local"])
    parser.add_argument("--intent-api-base", default=None,
                        help="意图识别 API地址 (默认: INTENT_API_BASE 或 OneAPI)")
    parser.add_argument("--intent-api-key", default=None,
                        help="意图识别 API密钥 (默认: INTENT_API_KEY)")
    parser.add_argument("--intent-model", default=None,
                        help="意图识别模型 (默认: INTENT_MODEL 或 deepseek-v4-pro)")
    parser.add_argument("--executor-api-base", default=None,
                        help="执行引擎 API地址 (默认: DASHSCOPE_API_BASE 或 DashScope)")
    parser.add_argument("--executor-api-key", default=None,
                        help="执行引擎 API密钥 (默认: DASHSCOPE_API_KEY)")
    parser.add_argument("--executor-model", default=None,
                        help="执行引擎模型 (默认: DASHSCOPE_MODEL 或 qwen)")
    parser.add_argument("--api-base", default=None,
                        help="兼容旧参数：同时设置意图识别和执行引擎 API地址")
    parser.add_argument("--api-key", default=None,
                        help="兼容旧参数：同时设置意图识别和执行引擎 API密钥")
    parser.add_argument("--model", default=None,
                        help="兼容旧参数：同时设置意图识别和执行引擎模型")
    parser.add_argument("--adapter-dir", default=None)
    parser.add_argument("--no-seed", action="store_true",
                        help="跳过种子数据导入")
    args = parser.parse_args()

    intent_api_base = _resolve_option(
        args.intent_api_base, args.api_base, "INTENT_API_BASE", DEFAULT_INTENT_API_BASE
    )
    intent_api_key = _resolve_option(
        args.intent_api_key, args.api_key, "INTENT_API_KEY", "not-needed"
    )
    intent_model = _resolve_option(
        args.intent_model, args.model, "INTENT_MODEL", DEFAULT_INTENT_MODEL
    )
    executor_api_base = _resolve_option(
        args.executor_api_base, args.api_base, "DASHSCOPE_API_BASE", DEFAULT_EXECUTOR_API_BASE
    )
    executor_api_key = _resolve_option(
        args.executor_api_key, args.api_key, "DASHSCOPE_API_KEY", "not-needed"
    )
    executor_model = _resolve_option(
        args.executor_model, args.model, "DASHSCOPE_MODEL", DEFAULT_EXECUTOR_MODEL
    )

    # 确保项目根目录在 sys.path 中，使 agent 包可被导入
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    global _AGENT
    from agent.agent import SecurityAgent

    print("正在初始化 SecAgent...")
    _AGENT = SecurityAgent(
        intent_backend=args.backend,
        intent_api_base=intent_api_base,
        intent_api_key=intent_api_key,
        intent_model=intent_model,
        executor_api_base=executor_api_base,
        executor_api_key=executor_api_key,
        executor_model=executor_model,
        intent_adapter_dir=args.adapter_dir,
    )

    if not args.no_seed:
        n = _import_seed_memory(_AGENT.memory)
        if n > 0:
            print(f"已导入 {n} 条种子记忆")

    import uvicorn
    print(f"\n  SecAgent Web 服务启动: http://{args.host}:{args.port}")
    print("  按 Ctrl+C 停止\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()