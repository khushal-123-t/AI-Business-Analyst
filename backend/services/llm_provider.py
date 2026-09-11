import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List

from backend.config import settings

logger = logging.getLogger("ai_analyst.llm_provider")


# --- Categorized Error Classes ---
class LLMError(Exception):
    """Base class for LLM service exceptions."""
    pass


class LLMConnectionError(LLMError):
    """Cannot connect to LLM provider."""
    pass


class LLMAuthError(LLMError):
    """Authentication failed (missing or bad API key)."""
    pass


class LLMModelError(LLMError):
    """Model unavailable, not found, or quota exceeded."""
    pass


class LLMEmptyResponse(LLMError):
    """LLM returned an empty response."""
    pass


class SQLExtractionError(LLMError):
    """Could not extract valid SQL from LLM response."""
    pass


class SQLValidationError(LLMError):
    """Generated SQL failed security/syntax validation."""
    pass


class CannotAnswerError(LLMError):
    """The question cannot be answered from the available schema."""
    pass


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        pass

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Generates raw text response given system and user prompts."""
        pass

    @abstractmethod
    def health_check(self) -> Tuple[bool, str]:
        """Verifies if the provider is reachable and operational."""
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Dedicated cloud LLM provider connecting to Google Gemini API.
    Sole AI provider for the application.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-3.6-flash"
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        """Returns True if Gemini API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self):
        if not self.is_configured():
            raise LLMAuthError(
                "Gemini API key is missing. Set GEMINI_API_KEY in your .env file."
            )
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"[GeminiProvider] Could not initialize SDK: {str(e)}")
                raise LLMConnectionError(f"Could not initialize Google GenAI SDK: {str(e)}")
        return self._client

    def health_check(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Gemini API key is not configured."
        return True, "Gemini is configured."

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        client = self._get_client()
        # Ensure only currently supported models are queried (avoiding retired models like gemini-2.0-flash)
        candidate_models = [
            self.model,
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-3.8-flash"
        ]
        unique_candidates = list(dict.fromkeys(candidate_models))

        from google.genai import types
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        last_err = None
        for model_name in unique_candidates:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config
                )
                if response and response.text and response.text.strip():
                    return response.text.strip()
                raise LLMEmptyResponse(f"Gemini model '{model_name}' returned empty response text.")
            except Exception as e:
                last_err = e
                err_str = str(e)
                logger.warning(f"[GeminiProvider] Model '{model_name}' failed: {err_str}")

                if "API_KEY_INVALID" in err_str or "PERMISSION_DENIED" in err_str:
                    raise LLMAuthError(f"Gemini API Authentication Error: {err_str}")

                if any(k in err_str for k in ("NOT_FOUND", "RESOURCE_EXHAUSTED", "429", "404", "503", "UNAVAILABLE")):
                    continue

                continue

        logger.error(f"[GeminiProvider] All candidate models failed ({unique_candidates}). Last error: {str(last_err)}")
        raise LLMModelError(f"Gemini API Error: All models ({', '.join(unique_candidates)}) failed. Detail: {str(last_err)}")


class LLMProviderManager:
    """
    Manages LLM provider execution. Gemini is the sole provider.
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None
    ):
        self.provider_setting = "gemini"
        self.gemini_provider = GeminiProvider(api_key=gemini_api_key, model=gemini_model)

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic info about configured Gemini provider and connectivity."""
        return {
            "active_provider": "gemini",
            "gemini": {
                "configured": self.gemini_provider.is_configured(),
                "model": self.gemini_provider.model
            }
        }

    def call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """
        Executes prompt generation directly via GeminiProvider.
        """
        try:
            return self.gemini_provider.generate(system_prompt, user_prompt, temperature=temperature)
        except (LLMAuthError, LLMModelError, LLMEmptyResponse, LLMConnectionError):
            raise
        except Exception as err:
            logger.error(f"[LLMProviderManager] Gemini generation error: {str(err)}")
            raise LLMModelError(f"Gemini generation error: {str(err)}")


# Global singleton instance
provider_manager = LLMProviderManager()
