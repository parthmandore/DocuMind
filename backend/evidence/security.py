"""Security and Prompt Injection Defense Module (Phase 4.2)

Detects adversarial prompt injections, instruction overrides, system prompt exfiltration,
credential dumps, and environment variable probing without blocking legitimate questions
about security architectures, authentication protocols, or compliance policies.
"""

import re
from typing import Tuple, List, Optional
from pydantic import BaseModel

class SecurityAnalysisResult(BaseModel):
    is_injection_or_secret_probe: bool
    attack_category: Optional[str] = None
    matched_pattern: Optional[str] = None
    reasoning: str = ""

class SecurityPromptAnalyzer:
    """
    Analyzes queries to detect adversarial prompt attacks, jailbreaks, instruction overrides,
    and credential extraction attempts while permitting legitimate documentation inquiries.
    """
    def __init__(self):
        # 1. Instruction Overrides & Jailbreaks
        self.override_patterns = [
            r'<\s*untrusted(?:_document_context)?\s*>',
            r'<\s*/\s*untrusted(?:_document_context)?\s*>',
            r'\bOVERRIDE\s*:',
            r'\bdisregard\s+(?:all\s+)?(?:previous|prior)\s+instructions\b',
            r'\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b',
            r'\byou\s+are\s+now\s+(?:an?\s+)?unrestricted\s+ai\b',
            r'\bdeveloper\s+maintenance\s+mode\b',
            r'\bjailbreak\b',
            r'\bact\s+as\s+(?:an?\s+)?unconstrained\b',
            r'\bforget\s+(?:all\s+)?rules\b'
        ]

        # 2. System Prompt & Hidden Context Extraction
        self.prompt_extraction_patterns = [
            r'\boutput\s+(?:the\s+)?system\s+prompt\b',
            r'\breveal\s+(?:the\s+)?system\s+prompt\b',
            r'\bprint\s+(?:the\s+)?system\s+prompt\b',
            r'\bshow\s+(?:the\s+)?system\s+prompt\b',
            r'\bverbatim\s+system\s+prompt\b',
            r'\bhidden\s+(?:system\s+)?instructions\b',
            r'\bextract\s+hidden\s+context\b',
            r'\bdisplay\s+(?:your\s+)?initial\s+prompt\b'
        ]

        # 3. Direct Credential & Secret Extraction
        self.credential_extraction_patterns = [
            r'\breveal\s+(?:all\s+)?(?:system\s+)?credentials\b',
            r'\blist\s+(?:all\s+)?(?:user\s+)?(?:email\s+addresses\s+and\s+)?passwords\b',
            r'\bwhat\s+is\s+the\s+(?:admin(?:istrative)?|root|internal)\s+password\b',
            r'\bgive\s+me\s+(?:the\s+)?(?:api|secret|private)\s+key\b',
            r'\bshow\s+(?:me\s+)?(?:the\s+)?(?:passwords|api\s*keys|private\s*keys|root\s*credentials)\b',
            r'\breveal\s+(?:internal\s+)?secrets\b',
            r'\bdump\s+(?:all\s+)?credentials\b'
        ]

        # 4. Environment Variable Probing
        self.env_probing_patterns = [
            r'\breveal\s+(?:all\s+)?environment\s+variables\b',
            r'\bshow\s+(?:all\s+)?(?:env\s+vars|environment\s+variables)\b',
            r'\bprint\s+(?:the\s+)?env\s+variables\b',
            r'\bprintenv\b',
            r'\$env:\w+',
            r'\bos\.environ\b'
        ]

        # Benign security query indicators (should NOT be flagged)
        self.benign_inquiry_patterns = [
            r'\bwhat\s+(?:signing\s+)?algorithm\b',
            r'\bwhat\s+protocol\b',
            r'\bhow\s+(?:are|is)\s+(?:credentials|tokens|keys)\s+(?:rotated|stored|configured)\b',
            r'\bwhat\s+is\s+the\s+token\s+ttl\b',
            r'\bdoes\s+the\s+(?:gateway|policy|api)\s+(?:permit|require|support)\s+tls\b',
            r'\bwhat\s+ciphers\s+are\s+permitted\b',
            r'\bsecurity\s+incident\s+notification\b',
            r'\bwhat\s+are\s+the\s+security\s+requirements\b'
        ]

    def analyze(self, query: str) -> SecurityAnalysisResult:
        """
        Determines whether a query is an adversarial prompt attack or credential probe.
        """
        q_lower = query.lower()

        # Check if the query is an adversarial override
        for pat in self.override_patterns:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                return SecurityAnalysisResult(
                    is_injection_or_secret_probe=True,
                    attack_category="instruction_override",
                    matched_pattern=m.group(0),
                    reasoning=f"Instruction override or jailbreak cue detected: '{m.group(0)}'."
                )

        # Check if query attempts to exfiltrate system prompt
        for pat in self.prompt_extraction_patterns:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                return SecurityAnalysisResult(
                    is_injection_or_secret_probe=True,
                    attack_category="prompt_extraction",
                    matched_pattern=m.group(0),
                    reasoning=f"System prompt exfiltration attempt detected: '{m.group(0)}'."
                )

        # Check if query attempts to extract credentials or secrets
        for pat in self.credential_extraction_patterns:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                return SecurityAnalysisResult(
                    is_injection_or_secret_probe=True,
                    attack_category="credential_extraction",
                    matched_pattern=m.group(0),
                    reasoning=f"Direct credential or secret extraction attempt detected: '{m.group(0)}'."
                )

        # Check if query attempts to probe environment variables
        for pat in self.env_probing_patterns:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                return SecurityAnalysisResult(
                    is_injection_or_secret_probe=True,
                    attack_category="environment_probing",
                    matched_pattern=m.group(0),
                    reasoning=f"Environment variable probing attempt detected: '{m.group(0)}'."
                )

        # Standalone password / credential check:
        # If query asks for "password" or "credentials" in an extractive manner without architectural context
        if re.search(r'\b(?:what|where|show|give|reveal|dump)\b.*\b(?:passwords?|credentials?|api[_\s-]*keys?|private[_\s-]*keys?|secret[_\s-]*keys?|internal[_\s-]*secrets?|system[_\s-]*secrets?|admin[_\s-]*credentials?)\b', q_lower):
            # Verify it's not a benign inquiry
            is_benign = any(re.search(bp, q_lower) for bp in self.benign_inquiry_patterns)
            if not is_benign:
                return SecurityAnalysisResult(
                    is_injection_or_secret_probe=True,
                    attack_category="credential_extraction",
                    matched_pattern="extractive_credential_query",
                    reasoning="Query attempts to extract operational passwords, credentials, or secrets."
                )

        return SecurityAnalysisResult(
            is_injection_or_secret_probe=False,
            reasoning="Query is a standard informational question."
        )

security_analyzer = SecurityPromptAnalyzer()
