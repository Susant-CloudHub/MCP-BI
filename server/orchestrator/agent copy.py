from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

class ThinkleeAgent:
    def __init__(self, connectors, metrics):
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.metrics = metrics
        self.connectors = {c.name: c for c in connectors}

    def discover_sources(self):
        return list(self.connectors.keys())

    async def calc_kpi(self, req):
        metric = self.metrics.resolve(req["metric"])
        sql = f"SELECT {metric['expr']} FROM {metric['source']} WHERE {metric['filters']}"
        connector = self.connectors["snowflake"]
        return list(connector.execute(sql, "snowflake"))

    async def query(self, req):
        source = req["source"]
        connector = self.connectors[source]
        return list(connector.execute(req["sql"], req["dialect"]))
