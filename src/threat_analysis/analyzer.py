from typing import Any


THREAT_DATABASE = {
    "DDoS": {
        "severity": "HIGH",
        "description": (
            "Distributed Denial-of-Service activity that attempts to "
            "overwhelm a service or network resource with traffic."
        ),
        "indicators": [
            "High traffic volume",
            "Abnormal packet or flow rates",
            "Large backward traffic volume",
            "Unusual packet-length patterns",
        ],
        "mitigation": [
            "Rate-limit suspicious traffic",
            "Apply firewall or ACL filtering",
            "Use DDoS protection or traffic scrubbing",
            "Monitor affected services for continued abnormal traffic",
        ],
    },

    "PortScan": {
        "severity": "MEDIUM",
        "description": (
            "Network reconnaissance activity in which an attacker "
            "probes ports or services to identify accessible targets."
        ),
        "indicators": [
            "Connections to multiple destination ports",
            "Repeated connection attempts",
            "Unusual scanning patterns",
        ],
        "mitigation": [
            "Restrict unnecessary exposed ports",
            "Apply firewall rules",
            "Monitor repeated connection attempts",
            "Block or rate-limit suspicious scanning sources",
        ],
    },

    "Bot": {
        "severity": "HIGH",
        "description": (
            "Traffic associated with a compromised host or automated "
            "bot activity."
        ),
        "indicators": [
            "Automated traffic patterns",
            "Abnormal communication behavior",
            "Repeated or coordinated network activity",
        ],
        "mitigation": [
            "Isolate the suspected host",
            "Investigate running processes and connections",
            "Block malicious destinations",
            "Scan the host for malware",
        ],
    },

    "DoS Hulk": {
        "severity": "HIGH",
        "description": (
            "Denial-of-Service traffic associated with the Hulk attack "
            "pattern, designed to exhaust application resources."
        ),
        "indicators": [
            "High request rate",
            "Repeated HTTP traffic",
            "Abnormal flow frequency",
        ],
        "mitigation": [
            "Apply HTTP rate limiting",
            "Use web application firewall rules",
            "Block abusive sources",
            "Monitor application resource utilization",
        ],
    },

    "DoS GoldenEye": {
        "severity": "HIGH",
        "description": (
            "Denial-of-Service activity associated with the GoldenEye "
            "HTTP attack pattern."
        ),
        "indicators": [
            "Repeated HTTP requests",
            "Abnormal request frequency",
            "Resource exhaustion patterns",
        ],
        "mitigation": [
            "Apply HTTP rate limiting",
            "Use WAF protections",
            "Block suspicious sources",
            "Monitor server resource usage",
        ],
    },

    "DoS Slowhttptest": {
        "severity": "HIGH",
        "description": (
            "Slow HTTP denial-of-service behavior intended to keep "
            "connections open and consume server resources."
        ),
        "indicators": [
            "Long-lived connections",
            "Low-rate incomplete requests",
            "Unusual connection duration",
        ],
        "mitigation": [
            "Configure connection timeouts",
            "Limit concurrent connections",
            "Apply reverse-proxy protections",
            "Use rate limiting",
        ],
    },

    "DoS slowloris": {
        "severity": "HIGH",
        "description": (
            "Slow HTTP denial-of-service behavior that keeps many "
            "connections partially open."
        ),
        "indicators": [
            "Long-lived connections",
            "Incomplete HTTP requests",
            "Large numbers of concurrent connections",
        ],
        "mitigation": [
            "Configure aggressive connection timeouts",
            "Limit concurrent connections",
            "Use reverse-proxy or WAF protections",
            "Rate-limit suspicious clients",
        ],
    },

    "FTP-Patator": {
        "severity": "HIGH",
        "description": (
            "Automated FTP authentication attack involving repeated "
            "login attempts."
        ),
        "indicators": [
            "Repeated FTP login attempts",
            "Abnormal authentication frequency",
            "Multiple failed credentials",
        ],
        "mitigation": [
            "Rate-limit authentication attempts",
            "Lock or temporarily block abusive accounts",
            "Use strong authentication",
            "Restrict FTP exposure",
        ],
    },

    "SSH-Patator": {
        "severity": "HIGH",
        "description": (
            "Automated SSH authentication attack involving repeated "
            "login attempts."
        ),
        "indicators": [
            "Repeated SSH login attempts",
            "Multiple authentication failures",
            "Abnormal SSH connection frequency",
        ],
        "mitigation": [
            "Use key-based authentication",
            "Disable password authentication where appropriate",
            "Rate-limit SSH connections",
            "Block repeated failed-login sources",
        ],
    },

    "Heartbleed": {
        "severity": "CRITICAL",
        "description": (
            "Traffic associated with exploitation of the Heartbleed "
            "vulnerability in vulnerable TLS implementations."
        ),
        "indicators": [
            "Suspicious TLS heartbeat requests",
            "Unexpected heartbeat response sizes",
            "Repeated abnormal TLS traffic",
        ],
        "mitigation": [
            "Patch vulnerable TLS libraries",
            "Restart affected services",
            "Rotate potentially exposed credentials and keys",
            "Review systems for possible information exposure",
        ],
    },

    "Infiltration": {
        "severity": "CRITICAL",
        "description": (
            "Network activity associated with an intrusion or "
            "compromised internal system."
        ),
        "indicators": [
            "Unexpected internal communication",
            "Abnormal host behavior",
            "Suspicious outbound connections",
        ],
        "mitigation": [
            "Isolate the suspected host",
            "Investigate system and network logs",
            "Block malicious destinations",
            "Perform malware and compromise analysis",
        ],
    },

    "Web Attack � Brute Force": {
        "severity": "HIGH",
        "description": (
            "Repeated web authentication attempts intended to discover "
            "valid credentials."
        ),
        "indicators": [
            "Repeated authentication requests",
            "Multiple failed login attempts",
            "High request frequency",
        ],
        "mitigation": [
            "Apply login rate limiting",
            "Use multi-factor authentication",
            "Temporarily block abusive sources",
            "Implement account lockout protections",
        ],
    },

    "Web Attack � Sql Injection": {
        "severity": "CRITICAL",
        "description": (
            "Web traffic associated with attempts to inject SQL "
            "commands into application input."
        ),
        "indicators": [
            "Suspicious request parameters",
            "Abnormal database-oriented input patterns",
            "Repeated malicious web requests",
        ],
        "mitigation": [
            "Use parameterized queries",
            "Validate and sanitize input",
            "Deploy appropriate WAF rules",
            "Review database access permissions",
        ],
    },

    "Web Attack � XSS": {
        "severity": "HIGH",
        "description": (
            "Web traffic associated with attempts to inject executable "
            "client-side content through application input."
        ),
        "indicators": [
            "Suspicious web parameters",
            "Encoded or script-like input",
            "Repeated malicious requests",
        ],
        "mitigation": [
            "Apply contextual output encoding",
            "Validate user input",
            "Use an appropriate Content Security Policy",
            "Deploy WAF protections",
        ],
    },
}


def analyze_threat(attack_type: str) -> dict[str, Any]:
    """
    Return threat intelligence associated with a predicted attack type.
    """

    threat = THREAT_DATABASE.get(attack_type)

    if threat is None:
        return {
            "attack_type": attack_type,
            "severity": "UNKNOWN",
            "description": "No threat-analysis profile is available.",
            "indicators": [],
            "mitigation": [],
        }

    return {
        "attack_type": attack_type,
        **threat,
    }
