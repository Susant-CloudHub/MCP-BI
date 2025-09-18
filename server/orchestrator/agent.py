# server/orchestrator/agent.py
import os
import re
from langchain_openai import ChatOpenAI

class ThinkleeAgent:
    def __init__(self, connectors, metrics):
        """
        connectors: list[BaseConnector] – e.g., [SnowflakeConnector(), SQLiteConnector()]
        metrics: MetricRegistry
        """
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.metrics = metrics
        # map by connector.name (e.g., "snowflake", "sqlite")
        self.connectors = {c.name: c for c in connectors}

    # ---------- Utility ----------
    def _connector(self, name: str):
        if name not in self.connectors:
            raise ValueError(f"Connector '{name}' not registered. Available: {list(self.connectors)}")
        return self.connectors[name]

    def _clean_sql(self, sql: str) -> str:
        # strip code fences like ```sql ... ```
        sql = re.sub(r"```.*?\n", "", sql, flags=re.IGNORECASE)
        sql = sql.replace("```", "").strip()
        # remove stray backticks (Snowflake doesn't use them)
        sql = sql.replace("`", "")
        # keep only the first statement
        if ";" in sql:
            sql = sql.split(";")[0].strip()
        return sql

    # ---------- Public Tools ----------
    def discover_sources(self):
        return list(self.connectors.keys())

    async def calc_kpi(self, req):
        """
        req = {"metric": "net_revenue", ...}
        """
        metric = self.metrics.resolve(req["metric"])
        if not metric:
            raise ValueError(f"Unknown metric: {req['metric']}")
        sql = f"SELECT {metric['expr']} AS VALUE FROM {metric['source']} WHERE {metric['filters']}"
        # default to snowflake if present
        connector_name = metric.get("connector", "snowflake") if "snowflake" in self.connectors else next(iter(self.connectors))
        connector = self._connector(connector_name)
        return list(connector.execute(sql, connector_name))

    async def query(self, req):
        """
        req = {"source": "snowflake", "sql": "...", "dialect": "snowflake"}
        """
        source = req["source"]
        connector = self._connector(source)
        return list(connector.execute(req["sql"], req.get("dialect", source)))

    async def ask(self, req):
        """
        Natural language → Snowflake SQL → execute on DAILY_SALES
        req = {"question": "..."}
        """
        question = req["question"]

        # Describe the table explicitly; adjust columns as needed
        ddl = """
        TABLE DAILY_SALES (
          SALES_ID INT,
          DATE DATE,
          PRODUCT_ID INT,
          ACCOUNT_ID INT,
          USER_ID INT,
          UNITS_SOLD INT,
          CHANNEL STRING,        -- 'Online', 'Hospital', ...
          SALES_TYPE STRING,     -- 'Primary','Secondary','Tertiary'
          DISTRIBUTOR_ID INT,
          CUSTOMER_ID INT,
          LOAD_DATE DATE,
          NET_PRICE FLOAT,
          UNIT_PRICE FLOAT
        )
        """

        system = (
            "You generate STRICT Snowflake SQL for the provided schema. "
            "Return ONLY SQL, no commentary, no code fences. "
            "Use single quotes for string/date literals. "
            "When filtering by date, compare to a quoted date literal like '2025-05-28'. "
            "Always alias aggregates (e.g., SUM(UNITS_SOLD) AS TOTAL_UNITS)."
        )

        user = f"""Schema:
{ddl}

User question:
{question}

Constraints:
- Query ONLY the DAILY_SALES table.
- If a channel is mentioned (e.g., Online), filter WHERE CHANNEL = 'Online'.
- If a specific date is mentioned, filter WHERE DATE = 'YYYY-MM-DD'.
- If a month is mentioned, use an explicit BETWEEN 'YYYY-MM-01' AND 'YYYY-MM-31' (or the correct end day).
- Use GROUP BY when aggregating by a dimension like CHANNEL.
- Return only the columns necessary to answer.
"""

        raw = self.llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]).content

        sql = self._clean_sql(raw)

        # Guardrails
        up = sql.upper()
        if "DAILY_SALES" not in up:
            return {"error": "Guardrail blocked: must query DAILY_SALES only", "sql": sql}
        if any(tok in up for tok in [" DROP ", " DELETE ", " UPDATE ", " INSERT "]):
            return {"error": "Guardrail blocked: mutating statements are not allowed", "sql": sql}
        if any(k in sql for k in ["--", "/*", "*/"]):
            return {"error": "Guardrail blocked: comments not allowed", "sql": sql}

        try:
            connector = self._connector("snowflake" if "snowflake" in self.connectors else next(iter(self.connectors)))
            rows = list(connector.execute(sql, "snowflake"))
            return {"sql": sql, "rows": rows}
        except Exception as e:
            # Return the SQL to help diagnose Snowflake errors quickly
            return {"error": str(e), "sql": sql}

    async def ask_s3(self, req):
        """
        Natural language → DuckDB SQL → execute against a registered S3 view.
        req = {"table": "<view name you registered>", "question": "..."}
        """
        table = req.get("table")
        question = (req.get("question") or "").strip()
        if not table or not question:
            return {"error": "Missing 'table' or 'question'"}

        # grab the S3 connector and build a live schema DDL for prompting
        s3 = self._connector("s3")
        try:
            cols = s3.get_schema(table)
        except Exception as e:
            return {"error": f"Unknown S3 table '{table}'. Did you call register_s3_table? {e}"}

        ddl_cols = "\n".join([f"  {c['name']} {c['type']}" for c in cols])
        ddl = f"TABLE {table} (\n{ddl_cols}\n)"

        system = (
            "You generate STRICT DuckDB SQL for the provided schema. "
            "Return ONLY SQL, no commentary, no code fences. "
            "Use single quotes for string/date literals. "
            "Always alias aggregates (e.g., SUM(units) AS total_units)."
        )

        user = f"""Schema:
{ddl}

User question:
{question}

Constraints:
- Query ONLY the table {table}.
- If a date or channel column exists, use it exactly as named.
- Use GROUP BY when aggregating by a dimension.
- Return only necessary columns.
"""

        raw = self.llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]).content

        sql = self._clean_sql(raw)

        # guardrails
        if table.lower() not in sql.lower():
            return {"error": "Guardrail blocked: must query specified table", "sql": sql}
        if any(k in sql for k in ["--", "/*", "*/"]):
            return {"error": "Guardrail blocked: comments not allowed", "sql": sql}

        try:
            rows = list(s3.execute(sql, "duckdb"))
            return {"sql": sql, "rows": rows}
        except Exception as e:
            return {"error": str(e), "sql": sql}
