import requests
import argparse
import ast
import json

def call(tool, payload):
    url = f"http://localhost:8000/mcp/tools/{tool}"
    r = requests.post(url, json=payload)
    try:
        print(r.json())
    except Exception:
        print(f"HTTP {r.status_code}")
        print("Server returned non-JSON response:")
        print(r.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tool", help="MCP tool to call (e.g., ask, query, calc_kpi)")
    parser.add_argument("question", nargs="*", help="Optional plain-text question for 'ask'")
    parser.add_argument("--payload", default="{}", help="Explicit JSON payload")

    args = parser.parse_args()

    # If using ask with plain text
    if args.tool == "ask" and args.question:
        payload = {"question": " ".join(args.question)}
    else:
        # Try to parse --payload string safely
        try:
            payload = ast.literal_eval(args.payload)
        except Exception:
            try:
                payload = json.loads(args.payload)
            except Exception:
                payload = {}

    call(args.tool, payload)
