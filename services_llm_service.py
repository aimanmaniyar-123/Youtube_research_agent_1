# services_llm_service.py
import json
from typing import Dict, Any
from groq import Groq
from utils_logger import get_logger

logger = get_logger("llm_service")

_llm_service_instance = None

def get_llm_service(config: Dict[str, Any] = None):
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService(config)
    return _llm_service_instance

class LLMService:
    def __init__(self, config: Dict[str, Any] = None):
        if not config:
            raise ValueError("LLMService requires config")
        self.api_key = config.get("groq_api_key")
        self.model = config.get("groq_model", "llama-3.1-8b-instant")
        if not self.api_key:
            raise ValueError("Groq API key missing")
        self.client = Groq(api_key=self.api_key)

    async def test_connection(self) -> bool:
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=3,
            )
            out = res.choices[0].message.content
            return "OK" in (out or "")
        except Exception as e:
            logger.error(f"LLM test failed: {e}")
            return False

    async def async_generate(self, prompt: str) -> str:
        """
        Send a concise prompt and return text output.
        Applies basic protections against huge payloads and handles API errors.
        """
        # Basic prompt size protection
        MAX_CHARS = 7000
        if not prompt:
            raise ValueError("Prompt is empty")
        if len(prompt) > MAX_CHARS:
            logger.warning("Prompt too large; trimming before LLM call.")
            prompt = prompt[:MAX_CHARS]

        # Try request
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.15,
                max_tokens=1200,
                messages=[
                    {"role": "system", "content": "You are an expert YouTube analyst. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
            )
            output = completion.choices[0].message.content.strip()
            return output

        except Exception as e:
            # HTTP error from Groq may include rate/size info
            logger.error(f"LLM call exception: {e}")
            # try to surface detailed info if available
            try:
                err = getattr(e, "args", [None])[0]
                return json.dumps({"error": str(err)})
            except Exception:
                return json.dumps({"error": "LLM call failed"})
