import sys
import unittest

sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app, on_startup
from backend.config import settings

class TestBackendStartupAndHealth(unittest.TestCase):
    def test_startup_gemini_configuration(self):
        """Verify startup handler executes and logs Gemini status without Ollama."""
        try:
            on_startup()
            started = True
        except Exception as e:
            started = False
            self.fail(f"Startup crashed with: {e}")
        self.assertTrue(started)

    def test_health_endpoint_returns_gemini_status(self):
        """Verify /api/health includes active Gemini provider and status without Ollama."""
        client = TestClient(app)
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print("\nHealth check response:", data)
        self.assertEqual(data["status"], "connected")
        self.assertIn("llm", data)
        self.assertEqual(data["llm"]["active_provider"], "gemini")
        self.assertIn("gemini", data["llm"])
        self.assertNotIn("ollama", data["llm"])
        self.assertTrue(data["llm"]["gemini"]["configured"])
        self.assertEqual(data["llm"]["gemini"]["model"], settings.GEMINI_MODEL)

if __name__ == "__main__":
    unittest.main()
