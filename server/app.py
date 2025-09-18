from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from server.mcp_handler import mcp_tools

app = FastAPI(title="THinklee MCP Server")

@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

@app.get("/")
def root():
    return {"status": "THinklee MCP running"}

@app.post("/mcp/tools/{tool_name}")
async def run_tool(tool_name: str, req: dict):
    if tool_name not in mcp_tools:
        return {"error": f"Tool {tool_name} not found"}
    return await mcp_tools[tool_name](req)
