from server.connectors.snowflake import SnowflakeConnector
from server.connectors.s3_duckdb import S3DuckDBConnector   # ← NEW
from server.metrics.registry import MetricRegistry
from server.orchestrator.agent import ThinkleeAgent

snowflake = SnowflakeConnector()
s3 = S3DuckDBConnector()                                     # ← NEW
metrics = MetricRegistry()
agent = ThinkleeAgent([snowflake, s3], metrics)               # include S3

async def discover_sources(req):
    return {"sources": agent.discover_sources()}

async def list_metrics(req):
    return {"metrics": metrics.list_all()}

async def calc_kpi(req):
    return await agent.calc_kpi(req)

async def query(req):
    return await agent.query(req)

async def ask(req):
    return await agent.ask(req)

# ---------- NEW: S3 tools ----------
async def register_s3_table(req):
    """
    req = {"name": "sales_s3", "uri": "s3://bucket/path/file.parquet", "format": "parquet|csv|json|auto"}
    """
    name = req.get("name")
    uri = req.get("uri")
    fmt = req.get("format", "auto")
    if not name or not uri:
        return {"error": "Missing 'name' or 'uri'"}
    info = s3.register(name, uri, fmt)
    return {"status": "registered", **info}

async def ask_s3(req):
    """
    req = {"table": "sales_s3", "question": "..."}
    """
    return await agent.ask_s3(req)

mcp_tools = {
    "discover_sources": discover_sources,
    "list_metrics": list_metrics,
    "calc_kpi": calc_kpi,
    "query": query,
    # NEW
    "register_s3_table": register_s3_table,
    "ask_s3": ask_s3,
}
