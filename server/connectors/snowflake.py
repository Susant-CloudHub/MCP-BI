import snowflake.connector
from server.connectors.base import BaseConnector

class SnowflakeConnector(BaseConnector):
    def __init__(self):
        self.name = "snowflake"
        self.version = "1.0"

    def capabilities(self):
        return {"dialect": "snowflake", "streaming": True}

    def discover(self):
        # Example: list tables
        return {"tables": ["DAILY_SALES", "PRODUCTS"]}

    def execute(self, query, dialect, stream=True):
        conn = snowflake.connector.connect(

            user = "IDXX",
            password= "PWDDXX5",
            account= "XXX-VCB97661",
            database= "XYZ",
            warehouse = "COMPUTE_WH",
            schema= "PXX_SALES",
        )
        cur = conn.cursor()
        cur.execute(query)
        for row in cur:
            yield {"row": dict(zip([col[0] for col in cur.description], row))}
        cur.close()
        conn.close()
