<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/f4d9b7fa-0cfc-49be-9e65-1acad7973f5b" />


# THinklee MCP Starter

A minimal **Model Context Protocol (MCP)** stack for BI with:

* **FastAPI** MCP server (tools: `discover_sources`, `list_metrics`, `query`, `calc_kpi`, `ask`, `register_s3_table`, `ask_s3`)
* **Connectors**: Snowflake (warehouse), S3 via DuckDB (files)
* **Agent** (GPT-4o mini) that converts natural language → SQL with guardrails
* **CLI** client for quick tests

---

## 0) Prerequisites

* Python **3.9+**
* An OpenAI API key for NL→SQL
* Snowflake credentials (if using Snowflake)
* AWS credentials (if your S3 object isn’t public)

### Environment variables (Mac/Linux: `bash`/`zsh`)

```bash
# OpenAI (required for ask/ask_s3)
export OPENAI_API_KEY="sk-..."

# Snowflake (required for Snowflake queries)
export SNOWFLAKE_USER="..."
export SNOWFLAKE_PASSWORD="..."
export SNOWFLAKE_ACCOUNT="..."           # e.g. abcd-xy123
export SNOWFLAKE_WAREHOUSE="..."
export SNOWFLAKE_DATABASE="..."
export SNOWFLAKE_SCHEMA="..."

# AWS (only if S3 object is private)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="eu-west-1"    # or your region
```

### Environment variables (Windows PowerShell)

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:SNOWFLAKE_USER="..."
$env:SNOWFLAKE_PASSWORD="..."
$env:SNOWFLAKE_ACCOUNT="..."
$env:SNOWFLAKE_WAREHOUSE="..."
$env:SNOWFLAKE_DATABASE="..."
$env:SNOWFLAKE_SCHEMA="..."
$env:AWS_ACCESS_KEY_ID="..."
$env:AWS_SECRET_ACCESS_KEY="..."
$env:AWS_DEFAULT_REGION="eu-west-1"
```

---

## 1) Create & activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
```

---

## 2) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If you added the S3 connector and haven’t installed DuckDB yet:

```bash
pip install duckdb
```

---

## 3) Run the MCP Server

```bash
uvicorn server.app:app --reload --port 8000
```

Health check (in another terminal):

```bash
curl -s http://localhost:8000/
# {"status":"THinklee MCP running"}
```

> Keep the server running in one terminal. Open a second terminal for the CLI commands below (and re-activate `.venv` there too).

---

## 4) CLI: Quick smoke tests

### 4.1 Discover sources

```bash
python3 client/cli.py discover_sources
# Example → {"sources": ["snowflake", "s3"]}
```

### 4.2 List metrics (from the sample registry)

```bash
python3 client/cli.py list_metrics
# Example → {"metrics": ["net_revenue"]}
```

### 4.3 Calculate a KPI (sample metric)

```bash
python3 client/cli.py calc_kpi --payload '{"metric":"net_revenue"}'
```

---

## 5) Snowflake: Natural-language Q\&A and SQL

### 5.1 Ask in natural language (NL→SQL→Snowflake)

```bash
python3 client/cli.py ask --payload '{ "question": "Total UNITS_SOLD by Online on 2025-05-28 from DAILY_SALES" }'
# → {"sql":"SELECT ...","rows":[{"row":{"TOTAL_UNITS": 66152}}]}
```

### 5.2 Run raw SQL on Snowflake

```bash
python3 client/cli.py query --payload '{
  "source": "snowflake",
  "sql": "SELECT * FROM DAILY_SALES LIMIT 5",
  "dialect": "snowflake"
}'
```

---

## 6) S3 via DuckDB: Register & ask questions

> Works with Parquet/CSV/JSON. For public buckets you can omit AWS creds.

### 6.1 Register an S3 object as a logical table (view)

```bash
python3 client/cli.py register_s3_table --payload '{
  "name": "weather_s3",
  "uri": "s3://raw-bucket/weather_data/weatherapiairflow/current_weather_data_03122023202412.csv",
  "format": "csv"
}'
# → {"status":"registered","name":"weather_s3","columns":[...]}
```

### 6.2 Preview rows from S3

```bash
python3 client/cli.py query --payload '{
  "source": "s3",
  "dialect": "duckdb",
  "sql": "SELECT * FROM weather_s3 LIMIT 5"
}'
```

### 6.3 Ask natural-language questions over S3 (DuckDB SQL)

```bash
python3 client/cli.py ask_s3 --payload '{
  "table": "weather_s3",
  "question": "Average temperature by city"
}'
```

> If your CSV is not comma-delimited or has special date formats, create a typed view with DuckDB first (example for `;` delimiter and `DD/MM/YYYY` dates):

```bash
python3 client/cli.py query --payload "{\"source\":\"s3\",\"dialect\":\"duckdb\",\"sql\":\"CREATE OR REPLACE VIEW energy_s3 AS SELECT CAST(TxnID AS INT) AS TxnID, CAST(STRPTIME(TxnDate, '%d/%m/%Y') AS DATE) AS TxnDate, CAST(STRPTIME(TxnTime, '%H:%M:%S') AS TIME) AS TxnTime, CAST(Consumption AS DOUBLE) AS Consumption FROM read_csv_auto('s3://datahubch/datahubch.csv', delim=';', header=true)\"}"
```

Then:

```bash
python3 client/cli.py ask_s3 --payload '{ "table":"energy_s3", "question":"Total Consumption by TxnDate" }'
```

---

## 7) Optional: Flask Chat UI

If you’re using the Flask UI package I shared:

```bash
# in the flask folder
export MCP_URL="http://localhost:8000/mcp/tools/ask"      # or /ask_s3
export S3_TABLE="weather_s3"                               # for ask_s3 default
python app.py
# open http://127.0.0.1:5000/
```

---

## 8) Troubleshooting

* **`JSONDecodeError` in CLI**
  The server likely returned non-JSON (usually due to an internal error).
  Check the **server terminal** for the real traceback. Our `app.py` returns `{"error":"..."}` for unhandled exceptions.

* **Quoting issues on macOS zsh**
  Prefer single quotes around JSON payloads, or escape inner quotes:

  ```bash
  python3 client/cli.py ask --payload '{ "question": "Total ..." }'
  # or
  python3 client/cli.py ask --payload "{\"question\":\"Total ...\"}"
  ```

* **Snowflake auth errors**
  Verify all `SNOWFLAKE_*` variables and that your warehouse is active.

* **S3 access errors**
  Check `AWS_*` env vars and bucket policy. For public files, creds may be unnecessary.
  Try a simpler CSV to validate the path.

-----

## License

MIT (or your preference).
