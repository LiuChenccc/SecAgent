"""
工具定义 —— Agent可调用的工具集。

工具列表：
  run_shell     执行shell命令
  read_file     读取文件内容
  grep_file     按模式搜索文件（正则/glob，安全分析核心工具）
  query_threat  威胁情报查询（AlienVault OTX，免费无需认证）
  web_search    网络搜索（占位）
  api_call      外部API调用（占位）
  write_file    写文件（报告/配置输出）
"""

import glob
import json
import os
import re
import subprocess
from typing import Any, Optional


def run_shell(command: str, timeout: int = 30) -> dict:
    """执行shell命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"命令超时（{timeout}秒）"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_file(path: str, max_lines: int = 500) -> dict:
    """读取文件内容"""
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"文件不存在: {path}"}
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        content = "".join(lines[:max_lines])
        return {
            "success": True,
            "total_lines": total,
            "shown_lines": min(total, max_lines),
            "content": content[:8000],
            "truncated": total > max_lines,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def grep_file(
    pattern: str,
    path: str,
    context_lines: int = 0,
    max_matches: int = 200,
    ignore_case: bool = True,
) -> dict:
    """按正则模式搜索文件内容，支持 glob 通配符匹配多文件。

    安全分析中最高频操作：搜日志里的异常IP、错误码、可疑进程名等。
    """
    try:
        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return {"success": False, "error": f"正则表达式无效: {e}"}

        files = sorted(glob.glob(path, recursive=True))
        if not files:
            return {"success": False, "error": f"没有匹配到文件: {path}"}

        matches = []
        total_matched = 0
        files_searched = 0

        for filepath in files:
            if not os.path.isfile(filepath):
                continue
            files_searched += 1

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except (PermissionError, OSError):
                continue

            for i, line in enumerate(lines):
                if regex.search(line):
                    total_matched += 1
                    if len(matches) >= max_matches:
                        break

                    entry = {
                        "file": filepath,
                        "line_num": i + 1,
                        "line": line.rstrip("\n")[:500],
                    }
                    if context_lines > 0:
                        before = lines[
                            max(0, i - context_lines): i
                        ]
                        after = lines[
                            i + 1: min(len(lines), i + 1 + context_lines)
                        ]
                        entry["context_before"] = [
                            l.rstrip("\n")[:200] for l in before
                        ]
                        entry["context_after"] = [
                            l.rstrip("\n")[:200] for l in after
                        ]
                    matches.append(entry)

            if len(matches) >= max_matches:
                break

        return {
            "success": True,
            "pattern": pattern,
            "files_searched": files_searched,
            "total_matched": total_matched,
            "shown_matches": len(matches),
            "matches": matches,
            "truncated": total_matched > max_matches,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_threat(indicator: str) -> dict:
    """查询威胁情报 —— 对接 AlienVault OTX（免费，无需 API Key）。

    支持 IP地址、域名、URL、文件哈希（MD5/SHA1/SHA256）。
    """
    try:
        import requests
    except ImportError:
        return {
            "success": False,
            "error": "需要 requests 库: pip install requests",
        }

    indicator = indicator.strip()
    if not indicator:
        return {"success": False, "error": "请输入要查询的威胁指标"}

    # 自动识别类型
    ioc_type = _classify_indicator(indicator)
    if ioc_type is None:
        return {
            "success": False,
            "error": f"无法识别指标类型: {indicator}。支持: IP/域名/URL/哈希",
        }

    otx_types = {
        "ip": "IPv4",
        "domain": "domain",
        "url": "url",
        "hash": "file",
    }

    try:
        url = (
            f"https://otx.alienvault.com/api/v1/indicators/"
            f"{otx_types[ioc_type]}/{indicator}/general"
        )
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "SecAgent/1.0",
        })
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return {"success": False, "error": "OTX 查询超时"}
    except Exception as e:
        return {"success": False, "error": f"OTX 查询失败: {e}"}

    pulses = data.get("pulse_info", {}).get("pulses", [])
    validation = data.get("validation", [])

    threats = []
    for p in pulses[:10]:
        threats.append({
            "name": p.get("name", ""),
            "description": p.get("description", "")[:300],
            "created": p.get("created", ""),
            "tags": p.get("tags", [])[:10],
            "adversary": p.get("adversary", ""),
            "malware_families": p.get("malware_families", []),
            "tlp": p.get("TLP", ""),
            "attack_ids": [
                a.get("id", "")
                for a in p.get("attack_ids", [])
            ][:5],
        })

    return {
        "success": True,
        "indicator": indicator,
        "type": ioc_type,
        "pulse_count": data.get("pulse_info", {}).get("count", 0),
        "malicious": len(pulses) > 0,
        "threats": threats,
        "validation": [v.get("name", "") for v in validation],
        "whois": data.get("whois", ""),
        "aliases": data.get("alexa", ""),
    }


def _classify_indicator(value: str) -> Optional[str]:
    """自动识别威胁指标类型"""
    # IPv4
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        return "ip"
    # IPv6
    if re.match(r"^[0-9a-fA-F:]+$", value) and ":" in value:
        return "ip"
    # 哈希
    if re.match(r"^[a-fA-F0-9]{32}$", value):
        return "hash"  # MD5
    if re.match(r"^[a-fA-F0-9]{40}$", value):
        return "hash"  # SHA1
    if re.match(r"^[a-fA-F0-9]{64}$", value):
        return "hash"  # SHA256
    # URL
    if value.startswith("http://") or value.startswith("https://"):
        return "url"
    # 域名
    if "." in value and not value.startswith("http"):
        return "domain"
    return None


def web_search(query: str) -> dict:
    """网络搜索（占位实现，实际可对接搜索API）"""
    return {
        "success": True,
        "query": query,
        "note": "搜索功能需配置实际搜索API",
        "results": [],
    }


def api_call(endpoint: str, params: dict = None) -> dict:
    """调用外部安全平台API（占位实现）"""
    return {
        "success": True,
        "endpoint": endpoint,
        "params": params or {},
        "note": "API调用需配置实际平台凭证",
        "data": None,
    }


def write_file(path: str, content: str, mode: str = "w") -> dict:
    """写文件 —— 用于输出安全分析报告、配置文件等"""
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        return {
            "success": True,
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# 工具schema（供LLM function calling使用）
TOOL_SCHEMAS = [
    {
        "name": "run_shell",
        "description": "执行shell命令并返回标准输出和错误输出。用于运行安全分析工具、查询系统状态等。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的shell命令",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "读取文件内容。用于分析配置文件、安全报告等。大文件会自动截断。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "最大读取行数，默认500",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep_file",
        "description": "按正则模式搜索文件内容，支持 glob 通配符。用于搜索日志中的异常IP、错误码、可疑进程名等。安全分析核心工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "搜索模式（正则表达式），如 '45\\.33\\.\\\\d+\\\\.\\\\d+' 或 'ERROR'",
                },
                "path": {
                    "type": "string",
                    "description": "文件路径，支持 glob 通配符，如 '/var/log/*.log'",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "返回匹配行前后各多少行上下文，默认0",
                },
                "max_matches": {
                    "type": "integer",
                    "description": "最多返回多少条匹配，默认200",
                },
                "ignore_case": {
                    "type": "boolean",
                    "description": "是否忽略大小写，默认true",
                },
            },
            "required": ["pattern", "path"],
        },
    },
    {
        "name": "query_threat",
        "description": "查询IP/域名/URL/文件哈希的威胁情报。对接AlienVault OTX免费情报源。返回是否恶意、关联攻击组织、恶意软件家族等信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "indicator": {
                    "type": "string",
                    "description": "威胁指标：IP地址(1.2.3.4)、域名(evil.com)、哈希(MD5/SHA1/SHA256)",
                },
            },
            "required": ["indicator"],
        },
    },
    {
        "name": "web_search",
        "description": "搜索网络安全相关信息，如CVE漏洞详情、威胁情报、安全最佳实践等。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询字符串",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "api_call",
        "description": "调用外部安全平台API，如威胁情报平台、漏洞管理平台、SIEM/SOAR系统等。",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "API端点路径",
                },
                "params": {
                    "type": "object",
                    "description": "API调用参数",
                },
            },
            "required": ["endpoint"],
        },
    },
    {
        "name": "write_file",
        "description": "将内容写入文件。用于生成安全分析报告、导出结果、保存配置等。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "输出文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                },
                "mode": {
                    "type": "string",
                    "description": "写入模式：w=覆盖写，a=追加写。默认w",
                },
            },
            "required": ["path", "content"],
        },
    },
]

# 工具名 → 执行函数的映射
TOOL_EXECUTORS: dict[str, callable] = {
    "run_shell": lambda **kwargs: run_shell(kwargs.get("command", "")),
    "read_file": lambda **kwargs: read_file(
        kwargs.get("path", ""),
        max_lines=kwargs.get("max_lines", 500),
    ),
    "grep_file": lambda **kwargs: grep_file(
        kwargs.get("pattern", ""),
        kwargs.get("path", ""),
        context_lines=kwargs.get("context_lines", 0),
        max_matches=kwargs.get("max_matches", 200),
        ignore_case=kwargs.get("ignore_case", True),
    ),
    "query_threat": lambda **kwargs: query_threat(
        kwargs.get("indicator", ""),
    ),
    "web_search": lambda **kwargs: web_search(kwargs.get("query", "")),
    "api_call": lambda **kwargs: api_call(
        kwargs.get("endpoint", ""), kwargs.get("params")
    ),
    "write_file": lambda **kwargs: write_file(
        kwargs.get("path", ""),
        kwargs.get("content", ""),
        mode=kwargs.get("mode", "w"),
    ),
}


def execute_tool(name: str, arguments: dict) -> dict:
    """根据工具名和参数执行工具"""
    executor = TOOL_EXECUTORS.get(name)
    if executor is None:
        return {"success": False, "error": f"未知工具: {name}"}
    return executor(**arguments)