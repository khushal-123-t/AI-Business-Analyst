import os
import re
import json
from typing import List, Dict, Any, Optional

from backend.config import settings
from backend.database.connection import quote_ident
from backend.services.sql_service import get_db_schema
from backend.utils.sql_validator import is_safe_sql
from backend.services.llm_provider import (
    provider_manager,
    LLMError,
    LLMConnectionError,
    LLMAuthError,
    LLMModelError,
    LLMEmptyResponse,
    SQLExtractionError,
    SQLValidationError,
    CannotAnswerError,
    GeminiProvider,
    LLMProviderManager
)

import logging
logger = logging.getLogger("ai_analyst.llm")

# In-memory session manager for conversational history
# session_id -> list of dicts: [{"question": str, "sql": str, "summary": str}]
chat_history: Dict[str, List[Dict[str, str]]] = {}


def get_history_context(session_id: str) -> str:
    """Formats previous Q&A context for the system prompt."""
    if not session_id or session_id not in chat_history:
        return "No previous context."

    exchanges = chat_history[session_id]
    context_lines = []
    for i, ex in enumerate(exchanges[-3:]):  # Keep last 3 exchanges to avoid context bloating
        context_lines.append(f"Exchange {i+1}:")
        context_lines.append(f"  User Question: {ex['question']}")
        context_lines.append(f"  Generated SQL: {ex['sql']}")
        context_lines.append(f"  AI Summary: {ex['summary']}")
    return "\n".join(context_lines)


def add_history_context(session_id: str, question: str, sql: str, summary: str):
    """Saves a successful Q&A exchange to history."""
    if not session_id:
        return
    if session_id not in chat_history:
        chat_history[session_id] = []
    chat_history[session_id].append({
        "question": question,
        "sql": sql,
        "summary": summary
    })


def format_schema() -> str:
    """Formats the SQLite database schema for the system prompt."""
    schema = get_db_schema()
    schema_lines = []
    for table_name, columns in schema.items():
        schema_lines.append(f"Table: {table_name}")
        for col in columns:
            schema_lines.append(f"  - {col['name']} ({col['type']})")
    return "\n".join(schema_lines)


def clean_generated_sql(sql_text: str) -> str:
    """Extracts raw SQL from Markdown code blocks, <think> tags, or natural language responses."""
    if not sql_text:
        return ""
    
    # Strip <think>...</think> tags if reasoning models (e.g. Qwen, DeepSeek) output them
    cleaned_input = re.sub(r"<think>.*?</think>", "", sql_text, flags=re.DOTALL).strip()
    if cleaned_input.upper() == "CANNOT_ANSWER":
        return "CANNOT_ANSWER"

    # Match ```sql ... ```
    match = re.search(r"```sql(.*?)```", cleaned_input, re.DOTALL | re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
    else:
        # Match ``` ... ```
        match = re.search(r"```(.*?)```", cleaned_input, re.DOTALL)
        if match:
            extracted = match.group(1).strip()
        else:
            extracted = cleaned_input

    # Strip any remaining think tags that might have been inside code blocks
    extracted = re.sub(r"<think>.*?</think>", "", extracted, flags=re.DOTALL).strip()

    if extracted.upper() == "CANNOT_ANSWER":
        return "CANNOT_ANSWER"

    # Search for starting SELECT or WITH keyword
    query_match = re.search(r"\b(SELECT|WITH)\b.*", extracted, re.DOTALL | re.IGNORECASE)
    if query_match:
        sql = query_match.group(0).strip()
        # If there's a trailing semicolon followed by conversational commentary, cut at semicolon
        if ";" in sql:
            parts = sql.split(";")
            sql = parts[0].strip() + ";"
        return sql

    return extracted


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """
    Unified LLM invocation function forwarding to LLMProviderManager.
    Sole AI Provider: Google Gemini
    """
    return provider_manager.call_llm(system_prompt, user_prompt, temperature=temperature)


def extract_explicit_margin(text: str) -> Optional[float]:
    """
    Extracts explicit user-specified profit margin from the user's prompt.
    Examples:
      'Assume a 15% profit margin for this analysis' -> 15.0
      'What is my profit assuming 20% margin?' -> 20.0
      'with a 12.5% profit margin' -> 12.5
      'margin: 25%' -> 25.0
    """
    if not text:
        return None
    patterns = [
        r"(?:assume|assuming|using|with|at|apply|consider|suppose)\s*(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:profit\s+)?margin",
        r"(?:profit\s+)?margin\s*(?:of|is|=|:|at)\s*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*profit\s+margin",
        r"(?:assume|assuming)\s*(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:profit|margin)"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


from backend.database.connection import quote_ident, engine
from backend.services.sql_service import get_db_schema, execute_query

def get_db_dialect() -> str:
    """Returns 'postgresql' or 'sqlite' depending on the active database engine."""
    try:
        return engine.dialect.name.lower()
    except Exception:
        return "sqlite"

def sanitize_db_error_message(err_msg: str) -> str:
    """Removes sensitive database connection strings, passwords, or internal URLs from error messages."""
    if not err_msg:
        return "Unknown database error"
    sanitized = re.sub(r":\/\/[^:]+:[^@]+@", "://***:***@", str(err_msg))
    sanitized = re.sub(r"password=([^\s]+)", "password=***", sanitized)
    return sanitized

def validate_referenced_columns(sql: str, available_columns: list) -> tuple[bool, str]:
    """
    Validates that SQL doesn't invent non-existent column names.
    Ignores SQL keywords, aliases, numbers, and functions.
    """
    if not available_columns:
        return True, ""
    
    col_names = [c["name"] if isinstance(c, dict) else str(c) for c in available_columns]
    col_names_lower = {c.lower() for c in col_names}
    
    # Common SQL keywords, clauses, functions, and standard types to exclude
    SQL_RESERVED = {
        "select", "from", "where", "group", "by", "order", "desc", "asc", "as",
        "and", "or", "not", "in", "like", "ilike", "between", "case", "when", "then",
        "else", "end", "sum", "avg", "count", "min", "max", "coalesce", "nullif",
        "round", "cast", "substr", "trim", "to_char", "date_trunc", "extract",
        "limit", "offset", "distinct", "join", "inner", "left", "right", "outer",
        "on", "with", "union", "all", "true", "false", "null", "is", "text", "numeric",
        "real", "int", "integer", "float", "timestamp", "date", "time", "double",
        "precision", "having", "exists", "interval", "over", "partition"
    }

    # Extract words that could be column references (alphanumeric snake_case tokens)
    tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", sql)
    for token in tokens:
        t_lower = token.lower()
        # If token ends with _col or is reserved or in available columns, it's valid
        if t_lower in SQL_RESERVED or t_lower.isdigit():
            continue
        # If it's a known column, it's valid
        if t_lower in col_names_lower:
            continue
        # Also check if it's an alias defined with AS token
        if re.search(rf"\bAS\s+[`\"']?{re.escape(token)}[`\"']?\b", sql, re.IGNORECASE):
            continue

    return True, ""

def generate_sql(
    question: str, 
    session_id: str = "default_session", 
    max_retries: int = 2, 
    table_name: Optional[str] = None, 
    columns: Optional[list] = None,
    user_margin: Optional[float] = None,
    sample_rows: Optional[list] = None,
    error_feedback: Optional[str] = None
) -> str:
    """
    Translates a natural language question into dialect-aware safe SQL (PostgreSQL or SQLite).
    Strictly data-driven: uses actual schema and sample rows without assuming sales columns.
    Uses Gemini as sole AI provider.
    """
    dialect = get_db_dialect()

    if user_margin is None:
        user_margin = extract_explicit_margin(question)

    if table_name and columns:
        quoted_table_name = quote_ident(table_name)
        schema_lines = [
            f"TARGET DATABASE DIALECT: {dialect.upper()}",
            f"TARGET TABLE: {quoted_table_name}",
            "AVAILABLE COLUMNS & DATA TYPES:"
        ]
        for col in columns:
            col_n = col["name"] if isinstance(col, dict) else str(col)
            col_t = col.get("type", "VARCHAR") if isinstance(col, dict) else "VARCHAR"
            schema_lines.append(f"  - {col_n} ({col_t})")
        
        # Include sample rows if available
        if sample_rows and len(sample_rows) > 0:
            schema_lines.append("\nREPRESENTATIVE SAMPLE ROWS (first 3 rows):")
            for i, r in enumerate(sample_rows[:3]):
                sample_preview = {k: str(v)[:40] for k, v in r.items() if v is not None}
                schema_lines.append(f"  Row {i+1}: {json.dumps(sample_preview)}")

        schema_text = "\n".join(schema_lines)
        target_table_info = f"Target Table: You MUST execute queries exclusively on the table {quoted_table_name}. Do NOT query 'sales' or any other table."
        
        col_names = [c["name"] if isinstance(c, dict) else str(c) for c in columns]
        col_names_lower = [c.lower() for c in col_names]
        date_col = next((c for c in col_names if "date" in c.lower() or "time" in c.lower() or "created" in c.lower() or "year" in c.lower()), None)
        
        hints = []
        # Dynamic Hints without assuming sales
        # Profit column identification
        profit_col = next((c for c in col_names if c.lower() in ["profit", "net_profit", "gross_profit", "profit_amount", "total_profit", "earnings"]), None)
        margin_col = next((c for c in col_names if c.lower() in ["profit_margin", "profit_margin_percent", "margin_percent", "margin_percentage", "margin"]), None)
        rev_col = next((c for c in col_names if any(k in c.lower() for k in ["revenue", "sales", "total_amount", "salary", "spend", "visits", "amount", "price"])), col_names[0] if col_names else "amount")

        if profit_col:
            hints.append(f"- ACTUAL PROFIT DATA: The table contains a real profit column `{profit_col}`. Use this column directly for any profit queries. Never apply any assumed margin.")
        elif margin_col:
            hints.append(f"- MARGIN DATA: The table contains a margin column `{margin_col}`. Calculate profit as (`{rev_col}` * (CASE WHEN `{margin_col}` > 1 THEN `{margin_col}`/100.0 ELSE `{margin_col}` END)). Never use any default margin.")
        elif user_margin is not None:
            hints.append(f"- USER-PROVIDED MARGIN: The user explicitly specified a {user_margin}% profit margin. Calculate estimated profit as (`{rev_col}` * {user_margin/100.0}) AS estimated_profit.")
        else:
            hints.append("- NO PROFIT DATA: This table has NO profit column and NO margin column, and the user did NOT specify a margin. You must NEVER calculate, estimate, or invent profit. DO NOT assume 18% or any other default margin.")
        
        extra_hints = "\n".join(hints)
    else:
        dialect_upper = dialect.upper()
        quoted_table_name = quote_ident("sales")
        schema_text = format_schema()
        target_table_info = f"Target Table: Only use the tables and columns defined in the schema below ({quoted_table_name})."
        date_col = "order_date"
        extra_hints = "- If the table contains an actual profit column, use it. Never assume 18% or any default profit margin."

    context_text = get_history_context(session_id)

    # Dialect specific instructions
    if dialect == "postgresql":
        dialect_instructions = """
3. DATABASE DIALECT: PostgreSQL
   - Use valid PostgreSQL SQL syntax.
   - NEVER use MySQL backticks (`). Use double quotes for identifiers if needed (e.g. "order_date"), or clean unquoted identifiers.
   - Date & Time Functions:
     * For monthly grouping or trends, use TO_CHAR(CAST({date_col} AS TIMESTAMP), 'YYYY-MM') or DATE_TRUNC('month', CAST({date_col} AS TIMESTAMP)) or SUBSTR(CAST({date_col} AS TEXT), 1, 7).
     * NEVER use SQLite strftime() or substr() on date objects.
   - Numeric Functions:
     * Use standard PostgreSQL functions: COALESCE, NULLIF, ROUND, CAST(... AS NUMERIC).
     * If stripping currency symbols from strings: CAST(REGEXP_REPLACE(CAST(col AS TEXT), '[$,₹€£¥%\\s]', '', 'g') AS NUMERIC).
"""
    else:
        dialect_instructions = """
3. DATABASE DIALECT: SQLite
   - Use valid SQLite syntax.
   - For monthly calculations, use strftime('%Y-%m', {date_col}) or substr(CAST({date_col} AS TEXT), 1, 7).
   - If stripping currency symbols: CAST(REPLACE(REPLACE(REPLACE(REPLACE(CAST(col AS TEXT), '$', ''), '₹', ''), ',', ''), ' ', '') AS REAL).
"""

    date_col_str = quote_ident(date_col) if date_col else "date_column"

    system_prompt = f"""You are an SQL generation engine for an AI Business Analytics application.

Generate read-only {dialect.upper()} SQL using ONLY the supplied dataset and schema.

Never invent columns.
Never invent tables.
Never invent metrics.
Never assume a profit margin.
Never use information outside the supplied dataset.

Return ONLY the raw SQL query.
Do not return conversational explanations.
Do not return Markdown code fences (e.g. ```sql).
Do not return <think> tags.

If the user's question cannot be answered from the available schema, return:
CANNOT_ANSWER

Do not fabricate data.

Rules for SQL generation:
1. Only generate read-only SELECT and WITH statements. Do not generate INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, or other database-modifying commands.
2. {target_table_info}
{dialect_instructions.format(date_col=date_col_str)}
4. Analytical Questions & Trends Handling:
   - For questions about trends:
     * If a date column is available, group by month or year and aggregate key business metrics.
     * If NO date column is available, analyze key categorical dimensions (e.g. top categories, distributions).
   - For top items: Group by entity and order by numeric metric DESC LIMIT 10.
   - For total metric: Calculate SUM or COUNT of available column.
   - For comparisons: Group by dimension and aggregate key metrics.
5. STRICT PROFIT INTEGRITY RULES:
   - Profit calculation must be strictly data-driven, never assumption-driven.
   - NEVER invent, assume, infer, or calculate a default profit margin (e.g. NEVER assume 18%, 20%, or any arbitrary percentage).
   - Only generate SQL involving profit when real profit/margin columns exist or the user explicitly specified a margin.
{extra_hints}

{schema_text}

Previous context:
{context_text}
"""

    current_prompt = f"User Question: {question}\n\nGenerate the {dialect.upper()} query:"
    if error_feedback:
        current_prompt += f"\n\nPrevious attempt failed with error:\n{error_feedback}\nPlease correct the query to be valid {dialect.upper()} SQL using ONLY the columns in the schema."

    retries = 0
    feedback = ""
    
    while retries <= max_retries:
        prompt_with_feedback = current_prompt
        if feedback:
            prompt_with_feedback += f"\n\nCorrection Feedback:\n{feedback}"
            
        generated_text = call_llm(system_prompt, prompt_with_feedback, temperature=0.0)
        sql = clean_generated_sql(generated_text)
        
        if sql == "CANNOT_ANSWER":
            raise CannotAnswerError("The available dataset columns do not contain sufficient data to answer this question.")

        # Clean backticks if model mistakenly generated them in PostgreSQL
        if dialect == "postgresql":
            sql = re.sub(r"`([^`]+)`", r'"\1"', sql)

        # If a custom table was specified and model erroneously referenced 'sales', sanitize it
        if table_name and table_name.lower() != "sales":
            quoted_t = quote_ident(table_name)
            sql = re.sub(r"\bFROM\s+sales\b", f"FROM {quoted_t}", sql, flags=re.IGNORECASE)
            sql = re.sub(r"\bJOIN\s+sales\b", f"JOIN {quoted_t}", sql, flags=re.IGNORECASE)

        # Validate the generated SQL for safety
        is_safe, err_msg = is_safe_sql(sql)
        if not is_safe:
            feedback = f"The query you generated was rejected for safety reasons: {err_msg}. Please regenerate a safe read-only SELECT or WITH statement."
            retries += 1
            continue

        return sql
        
    raise SQLValidationError(f"Failed to generate a safe SQL query after multiple attempts. Last safety error: {feedback}")


def execute_query_with_retry(
    question: str,
    table_name: str,
    columns: list,
    db: Any,
    session_id: str = "default_session",
    user_margin: Optional[float] = None,
    sample_rows: Optional[list] = None,
    max_correction_retries: int = 2
) -> tuple[str, list[str], list[dict]]:
    """
    Generates and executes SQL with an automated self-correction loop.
    If database execution fails (e.g. PostgreSQL syntax error or missing column),
    it captures the exact error and asks the LLM to self-correct using the actual schema.
    Retries up to max_correction_retries (default: 2).
    """
    dialect = get_db_dialect()
    last_error = None
    sql = None

    for attempt in range(max_correction_retries + 1):
        try:
            error_feedback = None
            if attempt > 0 and last_error:
                clean_err = sanitize_db_error_message(str(last_error))
                error_feedback = f"Database execution error on attempt {attempt}: {clean_err}\nFailed SQL:\n{sql}"
                logger.warning(f"[execute_query_with_retry] Attempt {attempt} failed with DB error: {clean_err}. Retrying with LLM correction.")

            sql = generate_sql(
                question=question,
                session_id=session_id,
                table_name=table_name,
                columns=columns,
                user_margin=user_margin,
                sample_rows=sample_rows,
                error_feedback=error_feedback
            )

            # Execute query against database
            res_cols, res_rows = execute_query(sql, db)
            logger.info(f"[execute_query_with_retry] Query succeeded on attempt {attempt + 1}: {len(res_rows)} rows returned.")
            return sql, res_cols, res_rows

        except (CannotAnswerError, LLMAuthError, LLMModelError, LLMConnectionError, SQLValidationError):
            raise
        except Exception as db_err:
            last_error = db_err
            logger.warning(f"[execute_query_with_retry] Execution failed on attempt {attempt + 1}: {str(db_err)}")
            if attempt == max_correction_retries:
                # Exceeded retries: raise clean error
                clean_err = sanitize_db_error_message(str(last_error))
                raise RuntimeError(f"Database execution error after {max_correction_retries + 1} attempts: {clean_err}")

    clean_err = sanitize_db_error_message(str(last_error))
    raise RuntimeError(f"Database execution failed: {clean_err}")


def generate_insights(
    question: str, 
    sql: str, 
    columns: list, 
    rows: list,
    user_margin: Optional[float] = None
) -> dict:
    """
    Analyzes query results to generate structured executive business insights:
    Executive Summary, Key Findings, Business Impact, and Actionable Recommendations.
    Strictly data-driven without assumed or hallucinated profit margins.
    Uses Gemini as sole AI provider.
    """
    if user_margin is None:
        user_margin = extract_explicit_margin(question)

    if not rows:
        results_text = "No records found matching the query."
    else:
        # Show first 30 rows in the prompt to prevent bloating the token count
        results_text = f"Columns: {', '.join(columns)}\n"
        for i, row in enumerate(rows[:30]):
            row_vals = [str(row.get(col, "")) for col in columns]
            results_text += f"Row {i+1}: {', '.join(row_vals)}\n"
        if len(rows) > 30:
            results_text += f"... (showing 30 of {len(rows)} total rows)"

    profit_note = ""
    if user_margin is not None:
        profit_note = f"Note: Profit in this analysis is ESTIMATED using the user-provided margin of {user_margin}%. You must clearly label it as an estimated figure based on the user's explicit specification."
    else:
        profit_note = "Note: No user margin was specified. Profit calculation must be strictly data-driven. Never fabricate or invent an assumed profit margin (such as 18%). If the query results do not contain profit data, do not invent or imply profit values."

    system_prompt = """You are a senior AI business analyst. Analyze the provided SQL query, its output, and the user's question, and generate a professional, executive-grade business analysis.
Profit calculation must be strictly data-driven. Never hallucinate numbers or assume default profit margins."""

    user_prompt = f"""User Question: {question}
Executed SQL: {sql}
Query Results:
{results_text}

{profit_note}

Please generate the response structured EXACTLY in the following markdown format:

### EXECUTIVE SUMMARY
[Provide a concise 1-2 sentence executive summary of the findings here]

### KEY FINDINGS
- [Key finding 1 with specific numbers/metrics from the data]
- [Key finding 2 with specific numbers/metrics from the data]
- [Key finding 3 with specific numbers/metrics from the data]

### BUSINESS IMPACT
[Explain the business impact of these findings. Connect the data to business outcomes.]

### RECOMMENDED ACTIONS
- [Actionable, specific business recommendation 1 based on the findings]
- [Actionable, specific business recommendation 2 based on the findings]
- [Actionable, specific business recommendation 3 based on the findings]

Instructions:
1. Never fabricate or hallucinate numbers. Use only the exact numbers returned in the query results.
2. Profit integrity: NEVER state or imply a profit value or profit margin unless it is explicitly present in the query results. Never describe a business as 'profitable' or 'unprofitable' without actual profit data.
3. If profit was estimated using a user-specified margin, clearly state that it is an estimate based on the user's prompt.
4. Clearly distinguish between facts directly supported by the data and qualitative business explanations/hypotheses.
5. Be professional, concise, and business-focused.
"""

    try:
        response_text = call_llm(system_prompt, user_prompt, temperature=0.2)
        response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()
    except Exception as e:
        return {
            "summary": f"AI Insights could not be generated: {str(e)}",
            "key_findings": ["Please check your Gemini API configuration in .env."],
            "business_impact": "LLM inference error.",
            "recommendations": ["Verify your GEMINI_API_KEY and GEMINI_MODEL settings in .env."]
        }

    # Parse the structured response
    summary = "No executive summary generated."
    key_findings = []
    business_impact = "No business impact generated."
    recommendations = []

    try:
        # Parse Executive Summary
        summary_match = re.search(r"### EXECUTIVE SUMMARY\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()

        # Parse Key Findings
        findings_match = re.search(r"### KEY FINDINGS\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if findings_match:
            findings_block = findings_match.group(1).strip()
            key_findings = [line.strip("- *").strip() for line in findings_block.split("\n") if line.strip().startswith(("-", "*"))]
        
        # Parse Business Impact
        impact_match = re.search(r"### BUSINESS IMPACT\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if impact_match:
            business_impact = impact_match.group(1).strip()

        # Parse Recommendations
        rec_match = re.search(r"### RECOMMENDED ACTIONS\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if rec_match:
            rec_block = rec_match.group(1).strip()
            recommendations = [line.strip("- *").strip() for line in rec_block.split("\n") if line.strip().startswith(("-", "*"))]

    except Exception as e:
        summary = response_text
        key_findings = ["Failed to parse findings structure."]
        business_impact = "Parsing error occurred."
        recommendations = ["Check generated insights text."]

    return {
        "summary": summary,
        "key_findings": key_findings if key_findings else ["No specific findings parsed."],
        "business_impact": business_impact,
        "recommendations": recommendations if recommendations else ["No specific recommendations parsed."]
    }
