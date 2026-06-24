# SecAgent — 网络安全智能体

基于 **LLM 意图识别** + **RAG 语义检索增强** + **754 个结构化安全 Skills** + **记忆闭环** 的网络安全 AI Agent。

支持中文自然语言输入，自动识别安全意图、匹配专业技能、调用工具执行任务，并通过用户反馈持续优化。

## 功能特性

- **多意图识别**：6 大类 43 子意图，支持单次输入识别多个安全意图
- **三层识别架构**：规则短路 → RAG 语义检索 → LLM 推理，兼顾速度与准确率
- **RAG 增强**：ChromaDB 向量数据库存储历史案例，语义检索 few-shot 注入 prompt
- **Skills 知识库**：754 个安全技能文档作为 RAG 知识源
- **工具调用**：LLM function calling 驱动，支持 shell 执行、文件分析、威胁情报查询等
- **记忆闭环**：用户确认的成功案例自动积累，持续提升识别效果
- **中文优化**：35 个子领域 × 中文触发词映射，精准匹配中文安全术语
- **双后端支持**：API（DeepSeek V4 Pro / 百炼）或本地（Qwen3-8B + LoRA）
- **Web 界面**：暗色安全控制台风格，支持实时交互和反馈

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/your-username/SecAgent.git
cd SecAgent
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下变量：

```bash
# 意图识别 LLM（百度 OneAPI）
INTENT_API_BASE=https://oneapi-comate.baidu-int.com/v1
INTENT_API_KEY=your-api-key
INTENT_MODEL=deepseek-v4-pro

# Embedding（RAG 向量检索）
EMBEDDING_API_BASE=https://oneapi-comate.baidu-int.com/v1
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=text-embedding-v3

# 执行引擎 LLM（独立于意图识别，可使用同一个 OneAPI Key）
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen3.6-plus-2026-04-02
```

支持任何 OpenAI 兼容 API（百度 OneAPI、阿里百炼、本地 vLLM 等）。

### 3. 下载 Skills 库

```bash
git clone https://github.com/nicpenning/El0s agent/skills
```

> Skills 目录约 35MB，包含 754 个结构化安全技能。不下载也可运行，但意图识别准确率会降低。

### 4. 初始化 RAG 向量库（可选）

```bash
python3 -c "
from intent_recognition import IntentRAG
rag = IntentRAG(embedding_mode='api')
count = rag.batch_import('intent_recognition/eval_500.json')
print(f'导入 {count} 条种子数据')
"
```

### 5. 启动服务

**Web 界面（推荐）：**

```bash
python3 agent/server.py --port 8800
```

浏览器访问 `http://localhost:8800`

**命令行模式：**

```bash
python3 -m agent.cli
```

## 系统架构

```
用户输入（中文自然语言）
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Step 1: Skills 检索                                   │
│   中文触发词 + TF-IDF → top-5 候选技能 → skill_context │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────┐
│ Step 2: 记忆检索                                      │
│   JSONL 历史记录 + bigram 相似度 → few_shot_context    │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────┐
│ Step 3: 意图识别（三层架构）                            │
│   ├─ 规则短路：触发词得分≥8 且无歧义 → 直接返回         │
│   ├─ RAG 检索：ChromaDB 语义相似案例 → few-shot 注入   │
│   └─ LLM 推理：DeepSeek V4 Pro                        │
│      (完整分类体系 + 消歧规则 + 上下文)                  │
│   → [{main_intent_id, sub_intent_id, confidence}]      │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────┐
│ Step 4: 意图→技能域映射                                │
│   43 子意图 → 34 规范子领域 → 加载 SKILL.md 工作流      │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────┐
│ Step 5: 执行引擎                                      │
│   LLM function calling 多轮循环（最多 3 轮）           │
│   工具：shell / 文件读写 / 正则搜索 / 威胁情报         │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────┐
│ Step 6: 反馈闭环                                      │
│   用户确认/拒绝 → 写入 Memory + RAG 向量库             │
└──────────────────────────────────────────────────────┘
```

## 项目结构

```
SecAgent/
├── intent_recognition/              # 意图识别独立模块
│   ├── recognizer.py                # 核心识别器（规则+RAG+LLM三层）
│   ├── rag.py                       # RAG增强（ChromaDB + 双模式Embedding）
│   ├── taxonomy.py                  # 意图分类体系（6大类43子意图）
│   ├── chinese_triggers.py          # 中文触发词映射（35个子领域）
│   ├── skill_mapper.py              # 意图→技能域映射表
│   ├── normalize.py                 # 子领域别名规范化
│   ├── local_backend.py             # 本地LoRA推理后端
│   ├── eval.py                      # 评估框架（92条手写测试集）
│   ├── eval_500.json                # 高质量评估集（500条）
│   ├── eval_500_run.py              # 500条评估运行脚本
│   ├── extract_quality_eval.py      # 从训练数据抽取高质量评估集
│   ├── rag_store/                   # ChromaDB持久化存储
│   └── tests/                       # 单元测试（37项）
│       ├── test_recognizer.py
│       ├── test_rag.py
│       ├── test_chinese_triggers.py
│       ├── test_skill_mapper.py
│       ├── test_normalize.py
│       └── test_taxonomy.py
├── agent/
│   ├── agent.py                     # 主编排器 SecurityAgent（六步流水线）
│   ├── skills_retriever.py          # Skills检索层（TF-IDF + 中文触发词）
│   ├── executor.py                  # 执行引擎（LLM function calling循环）
│   ├── tools.py                     # 工具集（7个工具）
│   ├── memory.py                    # 记忆系统（JSONL持久化 + bigram检索）
│   ├── server.py                    # FastAPI Web服务
│   ├── cli.py                       # 命令行交互界面
│   ├── skills/                      # 754个安全技能文档
│   ├── memory_store/                # 记忆持久化存储
│   └── static/
│       └── index.html               # Web前端（暗色安全控制台）
├── requirements.txt
├── .env.example
└── README.md
```

## 意图识别模块

### 三层识别架构

| 层级 | 机制 | 延迟 | 适用场景 |
|------|------|------|---------|
| 规则短路 | 中文触发词加权匹配 | <1ms | 高置信单意图（如"漏洞扫描"） |
| RAG 检索 | ChromaDB 语义相似 top-3 | ~100ms | 为 LLM 提供 few-shot 案例 |
| LLM 推理 | DeepSeek V4 Pro | ~2s | 复杂/多意图/模糊查询 |

### 评估结果（500 条测试集）

| 指标 | 结果 |
|------|------|
| 主意图准确率 | 93.4% |
| 子意图准确率 | 86.4% |
| 多意图召回率 | 85.7% |

### RAG 增强使用

```python
from intent_recognition import IntentRecognizer, IntentRAG

# 初始化
rag = IntentRAG(embedding_mode="api")       # API embedding
# rag = IntentRAG(embedding_mode="local")   # 本地 bge-small-zh

# 导入种子数据
rag.batch_import("intent_recognition/eval_500.json")

# 意图识别（自动注入 RAG few-shot）
recognizer = IntentRecognizer(backend="api")
result = recognizer.predict("帮我查一下这个IP的威胁情报", rag=rag)

# 反馈循环
rag.add("帮我查一下这个IP的威胁情报", result, source="feedback")
```

## 意图分类体系

| ID | 一级意图 | 子意图数 | 示例子意图 |
|----|---------|---------|-----------|
| 1 | 威胁检测与识别 | 8 | 恶意代码分析、流量异常检测、攻击溯源、失陷主机发现、IOC提取与检索、情报库关联查询、沙箱分析触发、检测规则调优 |
| 2 | 漏洞发现与管理 | 7 | 漏洞扫描启动、资产指纹识别、补丁版本检查、PoC验证执行、漏洞危害评估、修复建议查询、漏洞生命周期跟踪 |
| 3 | 安全合规与审计 | 6 | 合规基线检查、敏感数据发现、日志完整性审计、身份权限审计、策略违规扫描、审计报告生成 |
| 4 | 安全事件响应与处置 | 7 | 隔离阻断指令、进程强杀请求、系统备份恢复、告警自动确认、应急处置建议、事件根因调查、联动工单创建 |
| 5 | 安全知识问答与教育 | 6 | 安全术语解释、防护方案建议、安全法律法规检索、实战攻防案例检索、行业研报分析总结、系统手册查询 |
| 6 | 系统运维与配置管理 | 9 | 防火墙策略下发、系统补丁分发、资产信息更新、服务重启指令、安全补丁分发、用户权限调整、证书到期监控、性能瓶颈告警分析、资源扩容建议 |

## 可用工具

执行引擎通过 function calling 按需调用以下工具：

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `run_shell` | 执行 shell 命令（30s 超时） | 运行安全扫描工具、查询系统状态 |
| `read_file` | 读取文件内容（500行/8000字符） | 分析配置文件、日志文件 |
| `grep_file` | 正则搜索文件（支持 glob） | 搜索日志中的异常 IP、错误码 |
| `query_threat` | 威胁情报查询（AlienVault OTX） | 查询 IP/域名/哈希的威胁情报 |
| `web_search` | 网络搜索 | 搜索 CVE 详情、安全最佳实践 |
| `api_call` | 外部 API 调用 | 对接第三方安全平台 |
| `write_file` | 写入文件 | 生成分析报告、导出结果 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取系统统计信息（技能数、记忆数） |
| POST | `/api/chat` | 发送安全分析请求 |
| POST | `/api/feedback` | 提交用户反馈（confirmed/rejected） |

**POST /api/chat**

```json
// 请求
{"message": "分析IP 45.33.32.156的威胁情报"}

// 响应
{
  "intents": [
    {"main_intent_id": 1, "sub_intent_id": 5, "sub_intent_name": "IOC提取与检索", "confidence": 0.95}
  ],
  "matched_domains": ["threat-intelligence"],
  "summary": "分析报告...",
  "intent_results": [{"intent": {...}, "result": "...", "tool_calls": [...]}]
}
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `INTENT_API_BASE` | 意图识别 API 地址 | `https://oneapi-comate.baidu-int.com/v1` |
| `INTENT_API_KEY` | 意图识别 API 密钥 | - |
| `INTENT_MODEL` | 意图识别模型 | `deepseek-v4-pro` |
| `EMBEDDING_API_BASE` | Embedding API 地址 | 同 INTENT_API_BASE |
| `EMBEDDING_API_KEY` | Embedding API 密钥 | 同 INTENT_API_KEY |
| `EMBEDDING_MODEL` | Embedding 模型 | `text-embedding-v3` |
| `RAG_PERSIST_DIR` | RAG 向量库存储路径 | `./intent_recognition/rag_store` |
| `RAG_EMBEDDING_MODE` | Embedding 模式 | `api`（可选 `local`） |
| `DASHSCOPE_API_KEY` | 执行引擎 API 密钥 | - |
| `DASHSCOPE_API_BASE` | 执行引擎 API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `DASHSCOPE_MODEL` | 执行引擎模型 | `qwen3.6-plus-2026-04-02` |

### 命令行参数

默认情况下，意图识别读取 `INTENT_*`，执行引擎读取 `DASHSCOPE_*`，两套模型配置互相独立：

```bash
# Web 服务：使用环境变量中的两套模型配置
python3 agent/server.py --port 8800 --backend api

# CLI 交互：使用环境变量中的两套模型配置
python3 -m agent.cli --backend api
```

也可以通过参数显式指定两套模型：

```bash
python3 agent/server.py --port 8800 \
  --intent-api-base https://oneapi-comate.baidu-int.com/v1 \
  --intent-api-key your-intent-key \
  --intent-model gpt-5.5 \
  --executor-api-base https://oneapi-comate.baidu-int.com/v1 \
  --executor-api-key your-executor-key \
  --executor-model gpt-5.5
```

旧参数仍可用作兼容快捷方式；它们会同时设置意图识别和执行引擎：

```bash
python3 -m agent.cli \
  --api-base https://oneapi-comate.baidu-int.com/v1 \
  --api-key your-api-key \
  --model gpt-5.5
```

本地意图识别模型仍使用：

```bash
python3 -m agent.cli --backend local --adapter-dir /path/to/lora/adapter
```

## 运行测试

```bash
# 意图识别模块测试（37项）
python3 -m pytest intent_recognition/tests/ -v

# 全量评估（需要 API Key）
INTENT_API_KEY=your-key python3 -m intent_recognition.eval_500_run

# Agent 集成测试
python3 test_agent.py
```

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 意图识别 LLM | DeepSeek V4 Pro / Qwen3-8B + LoRA |
| 向量数据库 | ChromaDB（嵌入式，持久化） |
| Embedding | API（text-embedding-v3）/ 本地（bge-small-zh） |
| Web 框架 | FastAPI + Uvicorn |
| Skills 检索 | scikit-learn TF-IDF + 中文触发词 |
| 威胁情报 | AlienVault OTX（免费） |
| 前端 | 原生 HTML/CSS/JS（暗色控制台风格） |

## License

Apache-2.0
