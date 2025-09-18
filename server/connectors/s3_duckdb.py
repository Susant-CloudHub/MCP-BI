# server/connectors/s3_duckdb.py
import os
import duckdb
from typing import Dict, Any, Generator
from server.connectors.base import BaseConnector

def _q_ident(name: str) -> str:
    # safe identifier quoting for DuckDB
    return '"' + name.replace('"', '""') + '"'

class S3DuckDBConnector(BaseConnector):
    """Query S3 CSV/Parquet/JSON via DuckDB (httpfs). Register objects as views, then query them."""
    def __init__(self):
        self.name = "s3"
        self.version = "1.0"
        self.con = duckdb.connect(database=":memory:")
        # enable S3/http
        self.con.execute("INSTALL httpfs; LOAD httpfs;")

        # credentials (optional for public objects)
        ak = os.getenv("AWS_ACCESS_KEY_ID")
        sk = os.getenv("AWS_SECRET_ACCESS_KEY")
        tok = os.getenv("AWS_SESSION_TOKEN")
        region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION")
        if ak and sk:
            self.con.execute(f"SET s3_access_key_id='{ak}';")
            self.con.execute(f"SET s3_secret_access_key='{sk}';")
        if tok:
            self.con.execute(f"SET s3_session_token='{tok}';")
        if region:
            self.con.execute(f"SET s3_region='{region}';")

        # logical views you register: {"sales_s3": {"uri": "...", "format": "parquet"}}
        self.tables: Dict[str, Dict[str, Any]] = {}

    def capabilities(self) -> Dict[str, Any]:
        return {"dialect": "duckdb", "streaming": False, "formats": ["parquet", "csv", "json", "auto"]}

    def discover(self) -> Dict[str, Any]:
        return {"tables": list(self.tables.keys())}

    def register(self, name: str, uri: str, fmt: str = "auto") -> Dict[str, Any]:
        """Create/replace a VIEW pointing at an S3 object/prefix."""
        fmt = (fmt or "auto").lower()
        u = uri.lower()
        if fmt == "parquet" or (fmt == "auto" and (u.endswith(".parquet") or u.endswith(".parq") or u.endswith("/*.parquet"))):
            scan = f"parquet_scan('{uri}')"
        elif fmt == "csv" or (fmt == "auto" and u.endswith(".csv")):
            scan = f"read_csv_auto('{uri}')"
        elif fmt == "json" or (fmt == "auto" and u.endswith(".json")):
            scan = f"read_json_auto('{uri}')"
        else:
            # best-effort fallback
            scan = f"read_csv_auto('{uri}')"

        self.con.execute(f"CREATE OR REPLACE VIEW {_q_ident(name)} AS SELECT * FROM {scan}")
        self.tables[name] = {"uri": uri, "format": fmt}
        cols = self.get_schema(name)
        return {"name": name, "uri": uri, "format": fmt, "columns": cols}

    def get_schema(self, name: str):
        rows = self.con.execute(f"PRAGMA table_info({_q_ident(name)})").fetchall()
        # pragma columns: [cid, name, type, notnull, dflt_value, pk]
        return [{"name": r[1], "type": r[2]} for r in rows]

    def execute(self, query: str, dialect: str, stream: bool = True) -> Generator[Dict[str, Any], None, None]:
        cur = self.con.execute(query)
        if not cur.description:
            return
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            yield {"row": {cols[i]: row[i] for i in range(len(cols))}}
