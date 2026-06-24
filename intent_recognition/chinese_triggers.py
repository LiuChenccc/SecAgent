CHINESE_TRIGGER_MAP: dict[str, list[str]] = {
    "malware-analysis": [
        "恶意代码", "挖矿", "木马", "病毒", "勒索软件", "沙箱",
        "逆向", "恶意软件", "后门", "蠕虫", "Rootkit", "进程注入",
        "免杀", "加壳", "宏病毒", "无文件", "持久化",
    ],
    "threat-hunting": [
        "溯源", "攻击链", "失陷", "信标", "beacon", "C2通信",
        "威胁狩猎", "攻击路径", "横向移动", "权限维持",
        "命令控制", "数据窃取", "内网横移", "域控",
    ],
    "threat-intelligence": [
        "情报", "IOC", "APT", "TTP", "威胁情报", "攻击组织",
        "情报源", "STIX", "TAXII", "MISP", "威胁画像",
        "攻击团伙", "黑客组织",
    ],
    "network-security": [
        "流量", "抓包", "防火墙", "WAF", "IDS", "IPS", "网络",
        "端口扫描", "DDoS", "端口", "协议", "pcap", "NetFlow",
        "代理", "VPN", "NGFW", "网络隔离", "ACL",
    ],
    "vulnerability-management": [
        "漏洞扫描", "CVE", "补丁", "漏洞库", "CVSS", "漏洞",
        "弱口令", "配置缺陷", "版本漏洞", "安全公告",
        "漏洞修复", "补丁管理", "漏洞管理",
    ],
    "incident-response": [
        "应急响应", "隔离", "阻断", "恢复", "事件处置",
        "应急预案", "安全事件", "入侵响应", "应急处置",
        "备份恢复", "系统还原",
    ],
    "digital-forensics": [
        "取证", "内存dump", "磁盘镜像", "volatility", "痕迹",
        "文件恢复", "日志分析取证", "时间线", "证据",
        "硬盘镜像", "注册表", "NTFS", "MFT",
    ],
    "cloud-security": [
        "云安全", "AWS", "Azure", "GCP", "OSS", "Bucket",
        "对象存储", "云防火墙", "安全组", "VPC", "IAM角色",
        "Serverless", "云原生", "多云", "混合云",
    ],
    "web-application-security": [
        "Web安全", "SQL注入", "XSS", "OWASP", "WAF",
        "CSRF", "SSRF", "文件上传", "命令注入", "XXE",
        "反序列化", "越权", "JWT", "OAuth",
    ],
    "container-security": [
        "容器", "Docker", "Kubernetes", "K8s", "镜像安全",
        "编排", "Pod", "容器逃逸", "Harbor", "镜像扫描",
    ],
    "identity-access-management": [
        "身份", "权限", "IAM", "SSO", "MFA", "零信任",
        "认证", "授权", "账号", "密码", "RBAC", "AD域",
        "LDAP", "Kerberos", "访问控制",
    ],
    "compliance-governance": [
        "合规", "等保", "GDPR", "审计", "基线", "ISO27001",
        "等级保护", "监管", "整改", "安全评估", "风险评估",
    ],
    "soc-operations": [
        "SOC", "告警", "工单", "安全运营", "SOAR", "SIEM",
        "态势感知", "安全监控", "值班", "运营平台",
    ],
    "phishing-defense": [
        "钓鱼", "邮件安全", "社工", "欺诈", "伪基站",
        "鱼叉", "SPF", "DKIM", "DMARC", "恶意邮件",
    ],
    "endpoint-security": [
        "端点", "EDR", "HIDS", "主机安全", "防病毒",
        "终端安全", "杀毒", "主机防护", "恶意进程",
    ],
    "ransomware-defense": [
        "勒索", "Ransomware", "加密", "解密", "赎金",
        "LockBit", "Ryuk", "Sodinokibi",
    ],
    "api-security": [
        "API安全", "接口安全", "GraphQL", "REST", "Swagger",
        "API网关", "接口鉴权", "Rate Limit",
    ],
    "mobile-security": [
        "移动安全", "Android", "iOS", "APP", "移动端",
        "手机安全", "apk", "ipa", "逆向分析",
    ],
    "supply-chain-security": [
        "供应链", "SBOM", "依赖", "供应链攻击", "软件供应链",
        "第三方组件", "开源安全", "包管理",
    ],
    "cryptography": [
        "加密", "证书", "TLS", "SSL", "密码学", "HTTPS",
        "PKI", "CA", "密钥", "签名", "国密", "哈希",
    ],
    "devsecops": [
        "DevSecOps", "CI/CD", "SAST", "DAST", "代码安全",
        "代码审计", "静态扫描", "动态扫描", "流水线",
    ],
    "penetration-testing": [
        "渗透测试", "Metasploit", "Burp", "Nmap", "漏洞利用",
        "提权", "横向", "打点", "信息收集", "Webshell",
    ],
    "red-teaming": [
        "红蓝对抗", "Cobalt Strike", "C2", "免杀", "红队",
        "蓝队", "紫队", "演练", "靶场",
    ],
    "threat-detection": [
        "检测规则", "SIEM", "Sigma", "YARA", "Suricata",
        "Snort", "Zeek", "检测引擎", "规则引擎", "误报",
    ],
    "data-protection": [
        "数据安全", "DLP", "数据泄露", "脱敏", "加密存储",
        "数据分类", "数据分级", "敏感数据", "数据出境",
    ],
    "zero-trust-architecture": [
        "零信任", "Zero Trust", "SDP", "微隔离", "ZTNA",
        "软件定义边界", "微边界",
    ],
    "ot-ics-security": [
        "工控安全", "OT安全", "ICS", "SCADA", "PLC",
        "工业控制", "智能制造", "DCS", "Modbus",
    ],
    "blockchain-security": [
        "区块链安全", "智能合约", "Web3", "DeFi", "NFT",
        "以太坊", "Solidity", "链上分析",
    ],
    "ai-security": [
        "AI安全", "模型安全", "对抗样本", "LLM安全",
        "提示注入", "模型逆向", "投毒攻击",
    ],
    "deception-technology": [
        "蜜罐", "蜜网", "欺骗防御", "Honeypot", "诱捕",
        "伪装", "陷阱",
    ],
    "firmware-analysis": [
        "固件安全", "BIOS", "UEFI", "嵌入式", "IoT安全",
        "固件提取", "固件逆向",
    ],
    "privacy-compliance": [
        "隐私合规", "个人信息", "PIPL", "隐私保护", "数据合规",
    ],
    "purple-team": [
        "紫队", "紫队演练", "协同", "红蓝协同",
    ],
    "wireless-security": [
        "无线安全", "WiFi", "蓝牙", "RFID", "NFC", "无线电",
    ],
}


def get_candidate_subdomains(query: str) -> list[str]:
    scored = []
    for subdomain, triggers in CHINESE_TRIGGER_MAP.items():
        score = 0
        for trigger in triggers:
            if trigger.lower() in query.lower():
                score += len(trigger)
        if score > 0:
            scored.append((score, subdomain))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [subdomain for _, subdomain in scored]
