import os
import re
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from backend.config import settings
from backend.services.sql_service import get_db_schema
from backend.utils.sql_validator import is_safe_sql

import logging
logger = logging.getLogger("ai_analyst.llm")

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

# Gemini client initialization (if API key available)
gemini_client = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.warning(f"Warning: Could not initialize Google GenAI SDK: {str(e)}")

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
    """Extracts raw SQL from Markdown code blocks or natural language responses."""
    if not sql_text:
        return ""
    
    cleaned_input = sql_text.strip()
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


def call_gemini(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """Invokes Google Gemini with resilient candidate model fallback handling."""
    if not settings.GEMINI_API_KEY:
        raise LLMAuthError(
            "Gemini API key is missing. Set GEMINI_API_KEY in your .env file or switch to LLM_PROVIDER=ollama to use free local models."
        )

    global gemini_client
    if not gemini_client:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"GEMINI API ERROR: Could not initialize SDK: {str(e)}")
            raise LLMConnectionError(f"Could not initialize Google GenAI SDK: {str(e)}")

    primary_model = settings.GEMINI_MODEL or "gemini-3.5-flash"
    # Fallback model hierarchy prioritizing active models
    candidate_models = [primary_model, "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
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
            response = gemini_client.models.generate_content(
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
            logger.warning(f"GEMINI API ERROR: Model '{model_name}' failed: {err_str}")
            
            # Authentication failure is terminal
            if "API_KEY_INVALID" in err_str or "PERMISSION_DENIED" in err_str:
                raise LLMAuthError(f"Gemini API Authentication Error: {err_str}")
            
            # Quota/Not-found/Unavailable: try next candidate model
            if any(k in err_str for k in ("NOT_FOUND", "RESOURCE_EXHAUSTED", "429", "404", "503", "UNAVAILABLE")):
                continue
            
            continue

    logger.error(f"GEMINI API ERROR: All candidate models failed ({unique_candidates}). Last error: {str(last_err)}")
    raise LLMModelError(f"Gemini API Error: All models ({', '.join(unique_candidates)}) failed. Detail: {str(last_err)}")


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """
    Unified LLM invocation function supporting:
    1. Cloud Models via Google Gemini (Gemini 3.5 Flash, etc.)
    2. Local Pre-Trained Models via Ollama (Llama 3.2, Llama 3.3, Mistral, Qwen, etc.)
    Includes automatic graceful fallback between providers.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini":
        try:
            return call_gemini(system_prompt, user_prompt, temperature=temperature)
        except Exception as e:
            raise e

    elif provider == "ollama":
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content = resp_data.get("message", {}).get("content", "").strip()
                if not content:
                    raise LLMEmptyResponse("Ollama returned empty response.")
                return content
        except urllib.error.URLError as e:
            # If Ollama is not running, fallback to Gemini if API key is present
            if settings.GEMINI_API_KEY:
                logger.warning(f"Ollama server unreachable at {settings.OLLAMA_BASE_URL}. Falling back to Gemini API.")
                return call_gemini(system_prompt, user_prompt, temperature=temperature)
            raise LLMConnectionError(
                f"Cannot connect to local Ollama server at {settings.OLLAMA_BASE_URL} ({str(e.reason)}).\n"
                f"Please ensure Ollama is installed and running on your machine, or configure GEMINI_API_KEY in .env."
            )
        except Exception as e:
            if settings.GEMINI_API_KEY:
                logger.warning(f"Ollama error ({str(e)}). Falling back to Gemini API.")
                return call_gemini(system_prompt, user_prompt, temperature=temperature)
            raise LLMModelError(f"Ollama generation error with model '{settings.OLLAMA_MODEL}': {str(e)}")

    else:
        # Default fallback
        if settings.GEMINI_API_KEY:
            return call_gemini(system_prompt, user_prompt, temperature=temperature)
        raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'. Supported providers: 'gemini', 'ollama'.")


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
        r"(?:assume|using|with|at|apply|consider|suppose)\s*(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:profit\s+)?margin",
        r"(?:profit\s+)?margin\s*(?:of|is|=|:|at)\s*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*profit\s+margin",
        r"assume\s*(\d+(?:\.\d+)?)\s*%\s*(?:profit|margin)"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def generate_sql(
    question: str, 
    session_id: str = "default_session", 
    max_retries: int = 2, 
    table_name: Optional[str] = None, 
    columns: Optional[list] = None,
    user_margin: Optional[float] = None
) -> str:
    """
    Translates a natural language question into safe SQLite SQL.
    Strictly data-driven: never assumes or invents default profit margins.
    """
    if user_margin is None:
        user_margin = extract_explicit_margin(question)

    if table_name and columns:
        schema_lines = [
            f"DATABASE/DATASET:\n`{table_name}`\n",
            "AVAILABLE COLUMNS & TYPES:"
        ]
        for col in columns:
            schema_lines.append(f"  - {col['name']}: {col['type']}")
        schema_text = "\n".join(schema_lines)
        target_table_info = f"Target Table: You MUST execute queries exclusively on the table `{table_name}`. Do NOT query 'sales' or any other table."
        date_col = next((c["name"] for c in columns if "date" in c["name"].lower() or "time" in c["name"].lower()), "order_date")
        
        col_names_lower = [c["name"].lower() for c in columns]
        hints = []
        if "discounted_price" in col_names_lower or "retail_price" in col_names_lower or "unitprice" in col_names_lower:
            hints.append("- For revenue, sales, earnings, or price calculations, use the available price column (such as `discounted_price`, `retail_price`, or `unitprice`).")
        if "product_category_tree" in col_names_lower:
            hints.append("- For category grouping, use `product_category_tree` or `brand`.")
        if "crawl_timestamp" in col_names_lower:
            hints.append("- For dates or monthly trends, you can use `substr(crawl_timestamp, 1, 7)` to group by 'YYYY-MM'.")
        
        # Profit column identification
        profit_col = next((c["name"] for c in columns if c["name"].lower() in ["profit", "net_profit", "gross_profit", "profit_amount", "total_profit", "earnings"]), None)
        margin_col = next((c["name"] for c in columns if c["name"].lower() in ["profit_margin", "profit_margin_percent", "margin_percent", "margin_percentage", "margin"]), None)
        rev_col = next((c["name"] for c in columns if any(k in c["name"].lower() for k in ["revenue", "sales", "total_amount", "discounted_price", "retail_price", "unitprice"])), "revenue")

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
        schema_text = format_schema()
        target_table_info = "Target Table: Only use the tables and columns defined in the schema below."
        date_col = "order_date"
        extra_hints = "- If the table contains an actual profit column, use it. Never assume 18% or any default profit margin."

    context_text = get_history_context(session_id)

    system_prompt = f"""You are an SQL generation engine for an AI Business Analytics application.

Generate read-only SQLite SQL using ONLY the supplied dataset/schema.

Never invent columns.
Never invent tables.
Never invent metrics.
Never assume a profit margin.
Never use information outside the supplied dataset.

Return ONLY the SQL query.
Do not return explanations.
Do not use Markdown code fences.

If the user's question cannot be answered from the available schema, return:
CANNOT_ANSWER

Do not fabricate data.

Rules for SQL generation:
1. Only generate read-only SELECT and WITH statements. Do not generate INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, or other database-modifying commands.
2. {target_table_info}
3. The database dialect is SQLite. Ensure all functions used are valid SQLite functions.
4. Date & Time Mapping:
   - If the user question references date ranges, months, years, or time trends, map them to `{date_col}`.
   - For monthly calculations, use strftime('%Y-%m', `{date_col}`) or substr(`{date_col}`, 1, 7).
5. Analytical Questions & Trends Handling:
   - For questions like "What trends do you see in my data?", "Show trends over time", or sales growth:
     * If a date/time column is available, group by month (e.g. strftime('%Y-%m', `{date_col}`) or substr(`{date_col}`, 1, 7)) or year, and aggregate key business metrics like total sales/revenue or total orders.
     * If NO date/time column is available, analyze key categorical dimensions (e.g. top categories by revenue, top products, or regional distribution) to show distribution patterns across your data.
   - For "What are my top products?": Group by product/item and order by revenue/sales or quantity sold DESC LIMIT 10.
   - For "Which category has the highest sales?": Group by category and order by revenue/sales DESC LIMIT 1.
   - For "What is my total revenue?": Calculate SUM of the available revenue or price column.
6. STRICT PROFIT INTEGRITY RULES:
   - Profit calculation must be strictly data-driven, never assumption-driven.
   - NEVER invent, assume, infer, or calculate a default profit margin (e.g. NEVER assume 18%, 20%, or any arbitrary percentage).
   - Only generate SQL involving profit when:
     a) An actual profit column exists in the schema.
     b) An actual profit margin column exists in the schema.
     c) The user explicitly provided a profit margin in their question.
   - If none of these exist, DO NOT generate fake/estimated profit calculations.
7. Numeric & Currency Sanitization:
   - If any numeric, price, revenue, profit, or count column might contain currency symbols ($, ₹, €, £) or commas, safely strip them in SQLite using CAST(REPLACE(REPLACE(REPLACE(REPLACE(CAST(col AS TEXT), '$', ''), '₹', ''), ',', ''), ' ', '') AS REAL) before aggregating with SUM/AVG or arithmetic.
{extra_hints}

{schema_text}

Previous context:
{context_text}
"""

    current_prompt = f"User Question: {question}\n\nGenerate the SQLite query:"
    
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

        # If a custom table was specified and model erroneously referenced 'sales', sanitize it
        if table_name and table_name.lower() != "sales":
            sql = re.sub(r"\bFROM\s+sales\b", f"FROM `{table_name}`", sql, flags=re.IGNORECASE)
            sql = re.sub(r"\bJOIN\s+sales\b", f"JOIN `{table_name}`", sql, flags=re.IGNORECASE)

        # Validate the generated SQL
        is_safe, err_msg = is_safe_sql(sql)
        if is_safe:
            return sql
        
        # If unsafe, increment retry count and provide feedback
        feedback = f"The query you generated was rejected for safety reasons: {err_msg}. Please regenerate a safe read-only SELECT or WITH statement."
        retries += 1
        
    raise SQLValidationError(f"Failed to generate a safe SQL query after multiple attempts. Last safety error: {feedback}")


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
    except Exception as e:
        return {
            "summary": f"AI Insights could not be generated: {str(e)}",
            "key_findings": ["Please check your LLM configuration or ensure the local model server is running."],
            "business_impact": "LLM inference error.",
            "recommendations": ["Verify your LLM_PROVIDER and model settings in .env."]
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

