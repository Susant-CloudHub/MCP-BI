class MetricRegistry:
    def __init__(self):
        self.metrics = {
            "net_revenue": {
                "expr": "SUM(price * qty) - SUM(discount)",
                "grain": "order_day",
                "filters": "status = 'ClosedWon'",
                "source": "snowflake.sales_orders",
            }
        }

    def list_all(self):
        return list(self.metrics.keys())

    def resolve(self, name):
        return self.metrics.get(name)
