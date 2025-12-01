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

        """
        FIX FOR RENDER ERROR:
        Groq() internally passes `proxies=` to httpx.Client(), which crashes
        on some deployments.

        Solution → Create client WITHOUT httpx wrapper (safe mode)
        """
        try:
            self.client = Groq(api_key=self.api_key, http_client=None)
        except TypeError:
            # fallback for older SDKs
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
        MAX_CHARS = 7000
        if not prompt:
            raise ValueError("Prompt is empty")
        if len(prompt) > MAX_CHARS:
            logger.warning("Prompt too large; trimming before LLM call.")
            prompt = prompt[:MAX_CHARS]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=1400,
                messages=[
                    {"role": "system", "content": "You are an expert YouTube analyst. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
            )
            return completion.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LLM call exception: {e}")

            try:
                return json.dumps({"error": str(e)})
            except:
                return json.dumps({"error": "LLM call failed"})
