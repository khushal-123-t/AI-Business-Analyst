import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
venv_site = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "venv", "Lib", "site-packages")
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

from backend.services.llm_service import (
    generate_sql,
    validate_referenced_columns,
    sanitize_db_error_message,
    execute_query_with_retry,
    clean_generated_sql
)
from backend.services.schema_service import inspect_dataset_schema
from backend.database.connection import SessionLocal

class TestSQLCorrectionAndDialects(unittest.TestCase):
    def test_sanitize_db_error_message(self):
        raw = "Error connecting to postgresql://user:secretpassword123@dpg-render-host.com:5432/dbname"
        sanitized = sanitize_db_error_message(raw)
        self.assertNotIn("secretpassword123", sanitized)
        self.assertIn("***", sanitized)

    def test_clean_generated_sql(self):
        raw_markdown = "```sql\nSELECT * FROM \"test_table\" LIMIT 10;\n```"
        cleaned = clean_generated_sql(raw_markdown)
        self.assertEqual(cleaned, 'SELECT * FROM "test_table" LIMIT 10;')

        raw_with_think = "<think>some thought</think>SELECT employee_id, salary FROM employees;"
        cleaned = clean_generated_sql(raw_with_think)
        self.assertEqual(cleaned, 'SELECT employee_id, salary FROM employees;')

    def test_validate_referenced_columns(self):
        cols = [{"name": "salary", "type": "INTEGER"}, {"name": "department", "type": "VARCHAR"}]
        valid, msg = validate_referenced_columns("SELECT department, AVG(salary) AS avg_sal FROM tbl GROUP BY department", cols)
        self.assertTrue(valid)

    @patch("backend.services.llm_service.call_llm")
    def test_postgresql_dialect_prompt_rules(self, mock_llm):
        """Verify prompt for PostgreSQL contains dialect rules, forbid backticks, and correct date functions."""
        mock_llm.return_value = 'SELECT "department", AVG("salary") FROM "employees" GROUP BY "department";'
        
        with patch("backend.services.llm_service.get_db_dialect", return_value="postgresql"):
            sql = generate_sql(
                question="What is the average salary by department?",
                table_name="employees",
                columns=[{"name": "department", "type": "VARCHAR"}, {"name": "salary", "type": "INTEGER"}]
            )
            # Verify system prompt passed to call_llm
            args, kwargs = mock_llm.call_args
            system_prompt = args[0]
            self.assertIn("TARGET DATABASE DIALECT: POSTGRESQL", system_prompt)
            self.assertIn("NEVER use MySQL backticks", system_prompt)
            self.assertIn("TO_CHAR", system_prompt)

    @patch("backend.services.llm_service.execute_query")
    @patch("backend.services.llm_service.call_llm")
    def test_sql_error_self_correction_loop(self, mock_llm, mock_exec):
        """Verify that when execute_query fails, execute_query_with_retry retries with the error feedback."""
        # First call to LLM generates bad SQL, second call generates fixed SQL
        mock_llm.side_effect = [
            'SELECT non_existent_col FROM "employees";',
            'SELECT salary FROM "employees";'
        ]
        
        # First execution fails with database error, second execution succeeds
        mock_exec.side_effect = [
            RuntimeError('column "non_existent_col" does not exist in PostgreSQL'),
            (["salary"], [{"salary": 95000}, {"salary": 80000}])
        ]

        db_mock = MagicMock()
        final_sql, res_cols, res_rows = execute_query_with_retry(
            question="What are the salaries?",
            table_name="employees",
            columns=[{"name": "salary", "type": "INTEGER"}],
            db=db_mock,
            max_correction_retries=2
        )

        self.assertEqual(final_sql, 'SELECT salary FROM "employees";')
        self.assertEqual(res_cols, ["salary"])
        self.assertEqual(len(res_rows), 2)
        # Verify call_llm was called twice (initial + 1 self-correction)
        self.assertEqual(mock_llm.call_count, 2)
        # Second call prompt must contain error feedback
        second_prompt = mock_llm.call_args_list[1][0][1]
        self.assertIn("non_existent_col", second_prompt)

if __name__ == "__main__":
    unittest.main()
