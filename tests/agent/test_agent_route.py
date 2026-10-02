"""Integration tests for the /api/v1/agent/chat HTTP endpoint."""


class TestAgentChatEndpoint:
    def test_chat_unauthenticated_returns_401(self, client):
        resp = client.post("/api/v1/agent/chat", json={"message": "Show failed orders."})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_chat_read_query_authenticated(self, client, auth_headers):
        payload = {"message": "Show me all failed orders."}
        resp = client.post("/api/v1/agent/chat", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert len(data["tool_trace"]) >= 1
        assert data["request_id"]
        assert data["execution_id"]

    def test_chat_write_query_requires_confirmation(self, client, auth_headers):
        payload = {
            "message": "Create a support ticket for customer CUST-1004 saying their order is delayed."
        }
        resp = client.post("/api/v1/agent/chat", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "AWAITING_CONFIRMATION"
        assert data["confirmation_request"] is not None

        conf_id = data["confirmation_request"]["confirmation_id"]

        # Confirm via endpoint
        conf_payload = {
            "message": "Confirmed",
            "confirmation_id": conf_id,
            "confirmed": True,
        }
        conf_resp = client.post("/api/v1/agent/chat", json=conf_payload, headers=auth_headers)
        assert conf_resp.status_code == 200
        conf_data = conf_resp.json()
        assert conf_data["status"] == "COMPLETED"
