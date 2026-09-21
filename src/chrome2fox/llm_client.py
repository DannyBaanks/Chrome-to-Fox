"""
LLM Client — OpenAI-compatible API client for repair patches.

Works with:
- NVIDIA API (integrate.api.nvidia.com)
- OpenRouter
- OpenAI
- Local LLMs (Ollama, vLLM, etc.)
- Any OpenAI-compatible endpoint
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LLMConfig:
    """Configuration for LLM client."""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    api_key: str = ""
    model: str = "meta/llama-3.1-70b-instruct"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 60


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """
    OpenAI-compatible LLM client.
    
    Works with any API that implements the OpenAI chat completions format.
    
    Usage:
        client = LLMClient(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="nvapi-...",
            model="meta/llama-3.1-70b-instruct"
        )
        
        response = client.chat([
            {"role": "user", "content": "Fix this manifest..."}
        ])
    """
    
    def __init__(self, config: LLMConfig | None = None, **kwargs):
        """
        Initialize the LLM client.
        
        Args:
            config: LLMConfig object, or use kwargs
            **kwargs: Configuration options (base_url, api_key, model, etc.)
        """
        if config:
            self.config = config
        else:
            self.config = LLMConfig(**kwargs)
        
        # Use environment variable for API key if not provided
        if not self.config.api_key:
            self.config.api_key = os.environ.get("OPENAI_API_KEY", "")
            if not self.config.api_key:
                self.config.api_key = os.environ.get("NVIDIA_API_KEY", "")
        
        self._client = None
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout
                )
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
        return self._client
    
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None
    ) -> LLMResponse:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            response_format: Response format (e.g., {"type": "json_object"})
            
        Returns:
            LLMResponse with the model's response
        """
        client = self._get_client()
        
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = client.chat.completions.create(**kwargs)
            
            # Extract content
            content = response.choices[0].message.content or ""
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                finish_reason=response.choices[0].finish_reason or "",
                raw_response=response.model_dump()
            )
            
        except Exception as e:
            raise LLMError(f"Chat completion failed: {e}")
    
    def generate_patch(
        self,
        failure_envelope: dict[str, Any],
        system_prompt: str | None = None
    ) -> dict[str, Any]:
        """
        Generate a repair patch from a failure envelope.
        
        Args:
            failure_envelope: FailureEnvelope as dict
            system_prompt: Optional system prompt override
            
        Returns:
            Patch dict with file_patches and explanation
        """
        if system_prompt is None:
            system_prompt = REPAIR_SYSTEM_PROMPT
        
        # Build user prompt from envelope
        user_prompt = self._build_repair_prompt(failure_envelope)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Request JSON response
        response = self.chat(
            messages,
            response_format={"type": "json_object"},
            temperature=0.2,  # Lower temperature for more deterministic patches
            max_tokens=4096
        )
        
        # Parse JSON response
        try:
            patch = json.loads(response.content)
            return patch
        except json.JSONDecodeError:
            # Try to extract JSON from response
            return self._extract_json(response.content)
    
    def _build_repair_prompt(self, envelope: dict[str, Any]) -> str:
        """Build a repair prompt from the failure envelope."""
        parts = []
        
        # Extension info
        parts.append(f"Extension: {envelope.get('extension_name', 'unknown')}")
        parts.append(f"Version: {envelope.get('extension_version', 'unknown')}")
        parts.append(f"Chrome Manifest V{envelope.get('chrome_manifest_version', 2)}")
        parts.append(f"Firefox Version: {envelope.get('firefox_version', 'unknown')}")
        parts.append(f"Compatibility Score: {envelope.get('compatibility_score', 0):.2%}")
        parts.append("")
        
        # Failures
        if envelope.get('manifest_failures'):
            parts.append("MANIFEST FAILURES:")
            for f in envelope['manifest_failures']:
                parts.append(f"- {json.dumps(f)}")
            parts.append("")
        
        if envelope.get('runtime_failures'):
            parts.append("RUNTIME FAILURES:")
            for f in envelope['runtime_failures']:
                parts.append(f"- {json.dumps(f)}")
            parts.append("")
        
        if envelope.get('api_mismatches'):
            parts.append("API MISMATCHES:")
            for f in envelope['api_mismatches']:
                parts.append(f"- {json.dumps(f)}")
            parts.append("")
        
        if envelope.get('permission_failures'):
            parts.append("PERMISSION FAILURES:")
            for f in envelope['permission_failures']:
                parts.append(f"- {json.dumps(f)}")
            parts.append("")
        
        # Files involved
        if envelope.get('files_involved'):
            parts.append("FILES INVOLVED:")
            for f in envelope['files_involved']:
                parts.append(f"- {f.get('path', 'unknown')}: {f.get('action', 'unknown')}")
            parts.append("")
        
        # Available APIs
        if envelope.get('available_firefox_apis'):
            parts.append(f"AVAILABLE FIREFOX APIS: {', '.join(envelope['available_firefox_apis'][:20])}")
            parts.append("")
        
        # Error logs
        if envelope.get('error_logs'):
            parts.append("ERROR LOGS:")
            for log in envelope['error_logs'][:5]:
                parts.append(f"```\n{log}\n```")
            parts.append("")
        
        # Request
        parts.append("Generate a JSON patch with:")
        parts.append("- file_patches: [{path, old_content, new_content}]")
        parts.append("- explanation: string describing changes")
        
        return "\n".join(parts)
    
    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from text that may contain other content."""
        # Try to find JSON block
        import re
        
        # Look for JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Look for JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Return raw content as error
        return {
            "error": "Could not parse JSON from response",
            "raw_content": text
        }
    
    def health_check(self) -> bool:
        """Check if the LLM endpoint is reachable."""
        try:
            response = self.chat([
                {"role": "user", "content": "Say 'ok' if you can read this."}
            ], max_tokens=10)
            return "ok" in response.content.lower()
        except Exception:
            return False


class LLMError(Exception):
    """LLM client error."""
    pass


# Default system prompt for repair patches
REPAIR_SYSTEM_PROMPT = """You are a Chrome-to-Firefox extension repair expert.

Your task is to fix Firefox extension failures by generating targeted patches.

RULES:
1. Only fix what's broken - don't rewrite working code
2. Use Firefox-compatible APIs (browser.* namespace)
3. Preserve original functionality as much as possible
4. Keep changes minimal and focused
5. Explain every change

COMMON FIXES:
- chrome.* → browser.* (except chrome-extension:// URLs)
- service_worker → background.scripts
- side_panel → sidebar_action
- chrome.debugger → polyfill bridge
- chrome.usb → WebUSB API
- chrome.serial → Web Serial API
- chrome.hid → WebHID API
- chrome.tts → Web Speech API
- chrome.tabCapture → browser.tabCapture or getUserMedia

OUTPUT FORMAT:
{
  "file_patches": [
    {
      "path": "manifest.json",
      "old_content": "original content",
      "new_content": "fixed content"
    }
  ],
  "explanation": "Description of changes"
}

Be precise. Generate valid patches that can be applied directly."""


def create_llm_client(
    base_url: str = "https://integrate.api.nvidia.com/v1",
    api_key: str = "",
    model: str = "meta/llama-3.1-70b-instruct"
) -> LLMClient:
    """
    Convenience function to create an LLM client.
    
    Args:
        base_url: API endpoint URL
        api_key: API key (or use NVIDIA_API_KEY env var)
        model: Model name
        
    Returns:
        LLMClient instance
    """
    return LLMClient(
        base_url=base_url,
        api_key=api_key,
        model=model
    )


if __name__ == "__main__":
    import sys
    
    print("LLM Client for Chrome-to-Fox Repair")
    print("=" * 60)
    print("Supported providers:")
    print("- NVIDIA API (integrate.api.nvidia.com)")
    print("- OpenRouter (openrouter.ai)")
    print("- OpenAI (api.openai.com)")
    print("- Local (Ollama, vLLM, etc.)")
    print("")
    print("Usage:")
    print("  from chrome2fox.llm_client import LLMClient")
    print("  client = LLMClient(base_url='...', api_key='...')")
    print("  response = client.chat([{'role': 'user', 'content': '...'}])")
