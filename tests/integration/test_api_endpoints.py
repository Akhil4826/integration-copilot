"""Integration tests for all REST API endpoints."""


class TestHealthAndMetricsEndpoints:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_readiness_check(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"

    def test_prometheus_metrics(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        content = resp.text
        assert "http_requests_total" in content
        assert "agent_requests_total" in content


class TestCustomersEndpoints:
    def test_list_customers_requires_auth(self, client):
        resp = client.get("/api/v1/customers")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_list_customers_authenticated(self, client, auth_headers):
        resp = client.get("/api/v1/customers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 30
        assert data["page"] == 1

    def test_get_customer_by_id(self, client, auth_headers):
        resp = client.get("/api/v1/customers/CUST-1004", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["customer_id"] == "CUST-1004"

    def test_get_customer_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/customers/CUST-9999", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


class TestOrdersEndpoints:
    def test_list_orders_filtering_status(self, client, auth_headers):
        resp = client.get("/api/v1/orders?status=FAILED", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 10
        assert all(o["status"] == "FAILED" for o in data["items"])

    def test_get_order_by_id(self, client, auth_headers):
        resp = client.get("/api/v1/orders/ORD-1004", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == "ORD-1004"
        assert len(data["items"]) >= 1

    def test_create_order(self, client, auth_headers):
        payload = {
            "customer_id": "CUST-1001",
            "items": [
                {"product_id": "PROD-1001", "quantity": 1},
                {"product_id": "PROD-1002", "quantity": 2},
            ],
        }
        resp = client.post("/api/v1/orders", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["customer_id"] == "CUST-1001"
        assert data["order_id"].startswith("ORD-")
        assert data["total_amount"] > 0

    def test_patch_order_status(self, client, auth_headers):
        resp = client.patch(
            "/api/v1/orders/ORD-1004",
            json={"status": "PROCESSING"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PROCESSING"


class TestTicketsEndpoints:
    def test_list_tickets(self, client, auth_headers):
        resp = client.get("/api/v1/tickets?status=OPEN", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "OPEN" for t in data["items"])

    def test_create_ticket(self, client, auth_headers):
        payload = {
            "customer_id": "CUST-1004",
            "order_id": "ORD-1004",
            "title": "Delivery inquiry for failed order",
            "description": "Customer called inquiring why delivery failed.",
            "priority": "HIGH",
        }
        resp = client.post("/api/v1/tickets", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticket_id"].startswith("TCK-")
        assert data["priority"] == "HIGH"


class TestAnalyticsEndpoints:
    def test_order_analytics(self, client, auth_headers):
        resp = client.get("/api/v1/analytics/orders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] == 100
        assert data["total_revenue"] > 0

    def test_top_products(self, client, auth_headers):
        resp = client.get("/api/v1/analytics/products?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 5
        assert "product_id" in items[0]
