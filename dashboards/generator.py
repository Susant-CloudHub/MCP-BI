def generate_dashboard(metrics, filters=None):
    # Stub: returns VegaLite-compatible JSON
    return {
        "title": "THinklee Dashboard",
        "data": {"name": "table"},
        "mark": "bar",
        "encoding": {
            "x": {"field": "category", "type": "ordinal"},
            "y": {"field": "value", "type": "quantitative"}
        }
    }
