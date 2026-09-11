import sys
import unittest
from unittest.mock import patch, MagicMock
import json

sys.path.insert(0, '.')

from backend.config import settings
from backend.services.llm_provider import (
    BaseLLMProvider, GeminiProvider, LLMProviderManager,
    LLMError, LLMConnectionError, LLMAuthError, LLMModelError, LLMEmptyResponse
)
from backend.services.llm_service import clean_generated_sql, extract_explicit_margin, generate_sql
from backend.utils.sql_validator import is_safe_sql
from backend.main import verify_sql_isolation


class TestLLMProviderLayer(unittest.TestCase):

    def test_01_gemini_provider_attributes_and_configuration(self):
        """Verify GeminiProvider initializes correctly with name, model, and configuration check."""
        provider = GeminiProvider(api_key="mock_key", model="gemini-3.6-flash")
        self.assertEqual(provider.name, "gemini")
        self.assertEqual(provider.model, "gemini-3.6-flash")
        self.assertTrue(provider.is_configured())
        ok, msg = provider.health_check()
        self.assertTrue(ok)
        self.assertIn("configured", msg.lower())

    def test_02_gemini_provider_unconfigured(self):
        """Verify GeminiProvider raises LLMAuthError when API key is empty."""
        provider = GeminiProvider(api_key="", model="gemini-3.6-flash")
        self.assertFalse(provider.is_configured())
        ok, msg = provider.health_check()
        self.assertFalse(ok)
        with self.assertRaises(LLMAuthError) as ctx:
            provider.generate("System", "User")
        self.assertIn("API key is missing", str(ctx.exception))

    def test_03_gemini_provider_generate_success(self):
        """Verify GeminiProvider invokes the GenAI client generate_content and returns text."""
        provider = GeminiProvider(api_key="mock_valid_key", model="gemini-3.6-flash")
        mock_response = MagicMock()
        mock_response.text = "SELECT * FROM sales LIMIT 10;"

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.generate("System prompt", "User prompt", temperature=0.0)
            self.assertEqual(result, "SELECT * FROM sales LIMIT 10;")
            mock_client.models.generate_content.assert_called_once()
            call_kwargs = mock_client.models.generate_content.call_args[1]
            self.assertEqual(call_kwargs["model"], "gemini-3.6-flash")
            self.assertEqual(call_kwargs["contents"], "User prompt")

    def test_04_gemini_provider_empty_response(self):
        """Verify GeminiProvider raises LLMModelError (empty response on all candidates)."""
        provider = GeminiProvider(api_key="mock_valid_key", model="gemini-3.6-flash")
        mock_response = MagicMock()
        mock_response.text = "   "

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            with self.assertRaises(LLMModelError):
                provider.generate("System", "User")

    def test_05_provider_manager_delegation_to_gemini(self):
        """Verify LLMProviderManager uses GeminiProvider directly with no Ollama dependency."""
        mgr = LLMProviderManager(
            gemini_api_key="mock_valid_key",
            gemini_model="gemini-3.6-flash"
        )
        self.assertEqual(mgr.provider_setting, "gemini")
        self.assertFalse(hasattr(mgr, "ollama_provider"))

        with patch.object(mgr.gemini_provider, "generate", return_value="SELECT revenue FROM sales;") as mock_gemini:
            result = mgr.call_llm("System prompt", "User prompt")
            self.assertEqual(result, "SELECT revenue FROM sales;")
            mock_gemini.assert_called_once_with("System prompt", "User prompt", temperature=0.1)

    def test_06_provider_manager_status_gemini_only(self):
        """Verify LLMProviderManager.get_status returns solely Gemini diagnostics."""
        mgr = LLMProviderManager(
            gemini_api_key="mock_key",
            gemini_model="gemini-3.6-flash"
        )
        status = mgr.get_status()
        self.assertEqual(status["active_provider"], "gemini")
        self.assertIn("gemini", status)
        self.assertNotIn("ollama", status)
        self.assertTrue(status["gemini"]["configured"])
        self.assertEqual(status["gemini"]["model"], "gemini-3.6-flash")

    def test_07_clean_generated_sql_reasoning_tags(self):
        """Verify clean_generated_sql strips <think> tags from model output."""
        raw_output = "<think>We need to select sum of revenue grouped by month</think>```sql\nSELECT substr(order_date, 1, 7) as month, SUM(revenue) FROM sales GROUP BY month;\n```"
        cleaned = clean_generated_sql(raw_output)
        self.assertEqual(cleaned, "SELECT substr(order_date, 1, 7) as month, SUM(revenue) FROM sales GROUP BY month;")

    def test_08_clean_generated_sql_commentary(self):
        """Verify clean_generated_sql handles trailing commentary after query."""
        raw_output = "SELECT category, SUM(revenue) as total FROM sales GROUP BY category;\n\nHere is the breakdown of sales by category."
        cleaned = clean_generated_sql(raw_output)
        self.assertEqual(cleaned, "SELECT category, SUM(revenue) as total FROM sales GROUP BY category;")

    def test_09_profit_margin_extraction(self):
        """Verify explicit profit margin extraction patterns."""
        self.assertEqual(extract_explicit_margin("What is my profit assuming 20% margin?"), 20.0)
        self.assertEqual(extract_explicit_margin("Assume a 15.5% profit margin"), 15.5)
        self.assertEqual(extract_explicit_margin("with 12% profit margin"), 12.0)
        self.assertIsNone(extract_explicit_margin("What is my total sales?"))
        self.assertIsNone(extract_explicit_margin("What is my profit?"))

    def test_10_verify_sql_isolation(self):
        """Verify cross-table access is strictly blocked."""
        allowed = "dataset_client_1_abc"
        self.assertTrue(verify_sql_isolation(f"SELECT * FROM `{allowed}` WHERE amount > 100", allowed))
        self.assertFalse(verify_sql_isolation("SELECT * FROM `users`", allowed))
        self.assertFalse(verify_sql_isolation(f"SELECT * FROM `{allowed}` JOIN clients ON 1=1", allowed))
        self.assertFalse(verify_sql_isolation(f"SELECT * FROM `{allowed}`, clients", allowed))

    def test_11_sql_validator_safety(self):
        """Verify safety checks on destructive commands."""
        self.assertTrue(is_safe_sql("SELECT COUNT(*) FROM sales")[0])
        self.assertTrue(is_safe_sql("WITH monthly AS (SELECT order_date FROM sales) SELECT * FROM monthly")[0])
        self.assertFalse(is_safe_sql("DROP TABLE sales")[0])
        self.assertFalse(is_safe_sql("DELETE FROM sales WHERE id=1")[0])
        self.assertFalse(is_safe_sql("UPDATE sales SET revenue=0")[0])
        self.assertFalse(is_safe_sql("INSERT INTO sales VALUES (1, 2)")[0])
        self.assertFalse(is_safe_sql("ALTER TABLE sales ADD COLUMN test TEXT")[0])


if __name__ == "__main__":
    unittest.main()
