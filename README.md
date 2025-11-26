# SecAgent — 网络安全智能体

基于 **LLM 意图识别** + **754 个结构化安全 Skills（RAG）** + **记忆闭环** 的网络安全 AI Agent。

支持中文自然语言输入，自动识别安全意图、匹配专业技能、调用工具执行任务，并通过用户反馈持续优化。

## 功能特性

- **多意图识别**：6 大类 43 子意图，支持单次输入识别多个安全意图
- **Skills RAG**：754 个安全技能作为知识源，检索增强意图识别准确率
- **工具调用**：LLM function calling 驱动，支持 shell 执行、文件分析、威胁情报查询等
- **记忆闭环**：用户确认的成功案例自动积累，持续提升识别效果
- **中文优化**：35 个子领域 × 中文触发词映射，精准匹配中文安全术语
- **Web 界面**：暗色安全控制台风格，支持实时交互和反馈

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/your-username/SecAgent.git
cd SecAgent
pip install -r requirements.txt
```

### 2. 配置 API Key

复制环境变量模板并填入你的 API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY
```

支持阿里云百炼平台（DashScope）或任何 OpenAI 兼容 API。

### 3. 下载 Skills 库

Skills 库包含 754 个结构化安全技能文件，需单独下载：

```bash
git clone https://github.com/nicpenning/El0s agent/skills
```

> Skills 目录约 35MB。不下载也可运行，但意图识别准确率会降低。

### 4. 启动服务

**Web 界面（推荐）：**

```bash
export DASHSCOPE_API_KEY=your-api-key-here
python3 agent/server.py --port 8800
```

浏览器访问 `http://localhost:8800`

**命令行模式：**

```bash
python3 agent/cli.py
```

## 系统架构

```
用户输入（中文自然语言）
    │
    ▼
┌──────────────────────┐
│ 1. Skills 检索       │ ← 754个安全技能作为RAG知识源
│    中英文混合检索     │    chinese_trigger_map 中文触发词映射
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ 2. 记忆检索          │ ← 历史成功/失败案例
│    JSONL持久化        │    confirmed 加权 1.5x
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ 3. 增强意图识别       │ ← LLM + Skills上下文 + 历史few-shot
│    注入 Skills + 历史  │    6大类 43子意图
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ 4. 意图→技能映射      │ ← 43子意图 → 34规范子领域
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ 5. 执行引擎          │ ← LLM function calling
│    工具调用循环       │    按Skill步骤逐步执行
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│ 6. 反馈闭环          │ ← 用户确认/拒绝 → 写入记忆
└──────────────────────┘
```

## 项目结构

```
SecAgent/
├── agent/
│   ├── agent.py                  # 主编排器 SecurityAgent（六步流水线）
│   ├── skills_retriever.py       # Skills 检索层（TF-IDF + 中文触发词）
│   ├── chinese_trigger_map.py    # 中文触发词 → 子领域映射（35个子领域）
│   ├── skill_mapper.py           # 意图ID → 子领域映射表（43条）
│   ├── intent.py                 # 增强意图识别器（API/本地双后端）
│   ├── executor.py               # 执行引擎（LLM function calling循环）
│   ├── tools.py                  # 工具集（shell/文件/搜索/威胁情报/写文件）
│   ├── memory.py                 # 记忆系统（JSONL持久化 + bigram检索）
│   ├── server.py                 # FastAPI Web服务
│   ├── cli.py                    # 命令行交互界面
│   ├── memory_store/
│   │   └── seed_memory.jsonl     # 种子记忆（20条预置案例）
│   └── static/
│       └── index.html            # Web前端（暗色安全控制台）
├── test_agent.py                 # 模块验证测试（8项）
├── requirements.txt
├── .env.example
└── .gitignore
```

## 可用工具

执行引擎通过 function calling 按需调用以下工具：

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `run_shell` | 执行 shell 命令 | 运行安全扫描工具、查询系统状态 |
| `read_file` | 读取文件内容 | 分析配置文件、日志文件 |
| `grep_file` | 正则搜索文件 | 搜索日志中的异常IP、错误码 |
| `query_threat` | 威胁情报查询 | 查询IP/域名/哈希的威胁情报（OTX） |
| `web_search` | 网络搜索 | 搜索CVE详情、安全最佳实践 |
| `write_file` | 写入文件 | 生成分析报告、导出结果 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取系统统计信息 |
| POST | `/api/chat` | 发送安全分析请求 |
| POST | `/api/feedback` | 提交用户反馈（confirmed/rejected） |

**POST /api/chat 请求：**

```json
{"message": "分析IP 45.33.32.156的威胁情报"}
```

**响应：**

```json
{
  "intents": [...],
  "matched_domains": ["threat-intelligence"],
  "summary": "分析报告...",
  "intent_results": [{"intent": {...}, "result": "...", "tool_calls": [...]}]
}
```

## 意图体系

| ID | 一级意图 | 子意图数 | 示例 |
|----|---------|---------|------|
| 1 | 威胁检测与识别 | 8 | 恶意代码分析、流量异常检测、攻击溯源 |
| 2 | 漏洞发现与管理 | 7 | 漏洞扫描、PoC验证、修复建议 |
| 3 | 安全合规与审计 | 6 | 基线检查、日志审计、报告生成 |
| 4 | 安全事件响应与处置 | 7 | 隔离阻断、根因调查、应急建议 |
| 5 | 安全知识问答与教育 | 6 | 术语解释、防护方案、案例检索 |
| 6 | 系统运维与配置管理 | 9 | 防火墙策略、证书监控、性能分析 |

## 配置说明

环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | API 密钥 | - |
| `DASHSCOPE_API_BASE` | API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `DASHSCOPE_MODEL` | 模型名称 | `qwen3.6-plus-2026-04-02` |

命令行参数：

```bash
python3 agent/server.py --port 8800 --api-base http://localhost:8000/v1 --model qwen3-8b
python3 agent/cli.py --backend api --model qwen3.6-plus-2026-04-02
```

## 运行测试

```bash
python3 test_agent.py
```

8 项测试覆盖：Skills 检索、中文触发词映射、意图映射、别名规范化、记忆系统、工具执行、意图解析、增强 Prompt。

> 未下载 Skills 库时，测试 1 和测试 8 会自动跳过。

## License

Apache-2.0
