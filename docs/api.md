# REST API Specification & Endpoint Reference

The REST API is built on FastAPI and exposes complete OpenAPI documentation with Swagger UI at `/docs` and ReDoc at `/redoc`.

---

## Base Configuration & Authentication

- **Base URL**: `http://localhost:8000/api/v1`
- **Default Auth Header**:
  ```http
  Authorization: Bearer development-token
  ```
- **Error Format**: All errors return a standard JSON envelope:
  ```json
  {
    "error": {
      "code": "ORDER_NOT_FOUND",
      "message": "Order ORD-1001 was not found",
      "request_id": "req_5f2d..."
    }
  }
  ```

---

## 1. Customers

### List Customers
- **Endpoint**: `GET /api/v1/customers`
- **Query Parameters**:
  - `query` (string, optional): Search term for customer name or email.
  - `page` (int, default=1): Page number.
  - `page_size` (int, default=20, max=100): Results per page.
- **Response**: `200 OK` with paginated list of customers.

### Get Customer by ID
- **Endpoint**: `GET /api/v1/customers/{customer_id}`
- **Parameters**: `customer_id` (e.g. `CUST-1004`).
- **Response**: `200 OK` with customer details.

---

## 2. Orders

### List & Filter Orders
- **Endpoint**: `GET /api/v1/orders`
- **Query Parameters**:
  - `status` (`PENDING`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `FAILED`, `CANCELLED`): Filter by order status.
  - `customer_id` (string): Filter by customer ID.
  - `start_date` (ISO-8601): Filter orders created on or after date.
  - `end_date` (ISO-8601): Filter orders created on or before date.
  - `minimum_amount` (float): Minimum total amount.
  - `maximum_amount` (float): Maximum total amount.
  - `sort_by` (`created_at`, `total_amount`, `status`, `order_id`, default=`created_at`).
  - `sort_order` (`asc`, `desc`, default=`desc`).
  - `page` (int, default=1), `page_size` (int, default=20).
- **Example Request**:
  ```bash
  curl -H "Authorization: Bearer development-token" \
       "http://localhost:8000/api/v1/orders?status=FAILED&page=1&page_size=10"
  ```

### Get Order by ID
- **Endpoint**: `GET /api/v1/orders/{order_id}`
- **Response**: `200 OK` with order header and line items.

### Create Order
- **Endpoint**: `POST /api/v1/orders`
- **Payload**:
  ```json
  {
    "customer_id": "CUST-1001",
    "items": [
      { "product_id": "PROD-1001", "quantity": 2 }
    ]
  }
  ```

### Update Order Status
- **Endpoint**: `PATCH /api/v1/orders/{order_id}`
- **Payload**:
  ```json
  {
    "status": "PROCESSING"
  }
  ```

---

## 3. Support Tickets

### List Tickets
- **Endpoint**: `GET /api/v1/tickets`
- **Query Parameters**: `status`, `priority`, `customer_id`, `order_id`, `page`, `page_size`.

### Get Ticket by ID
- **Endpoint**: `GET /api/v1/tickets/{ticket_id}`

### Create Ticket
- **Endpoint**: `POST /api/v1/tickets`
- **Payload**:
  ```json
  {
    "customer_id": "CUST-1004",
    "order_id": "ORD-1012",
    "title": "Delayed delivery complaint",
    "description": "Customer called reporting package has not arrived.",
    "priority": "HIGH"
  }
  ```

### Update Ticket
- **Endpoint**: `PATCH /api/v1/tickets/{ticket_id}`
- **Payload**:
  ```json
  {
    "status": "IN_PROGRESS",
    "priority": "CRITICAL"
  }
  ```

---

## 4. Analytics

### Order Analytics
- **Endpoint**: `GET /api/v1/analytics/orders`
- **Returns**: Total orders, successful, failed, cancelled, total revenue, average order value.

### Revenue Breakdown
- **Endpoint**: `GET /api/v1/analytics/revenue`
- **Returns**: Revenue grouped by time window.

### Top Products
- **Endpoint**: `GET /api/v1/analytics/products?limit=5`
- **Returns**: Top products by revenue, units sold, and stock quantity.

---

## 5. AI Agent Chat

### Send Conversational Query
- **Endpoint**: `POST /api/v1/agent/chat`
- **Payload**:
  ```json
  {
    "message": "Show me all failed orders."
  }
  ```
- **Response**:
  ```json
  {
    "execution_id": "exec_8d2f...",
    "response": "I found 8 failed orders in the database...",
    "tool_trace": [
      {
        "step": 1,
        "tool": "search_orders",
        "arguments": { "status": "FAILED" },
        "duration_ms": 14.2,
        "status": "success",
        "result_count": 8
      }
    ],
    "requires_confirmation": false,
    "confirmation": null,
    "completed": true
  }
  ```

### Confirming a Write Operation
- **Endpoint**: `POST /api/v1/agent/chat`
- **Payload**:
  ```json
  {
    "confirmation_token": "c71e2b...",
    "confirmed": true
  }
  ```
- **Response**: Returns confirmation completion and created entity ID.

---

## 6. Health & Metrics

### Health Check
- **Endpoint**: `GET /health`
- **Response**: `{"status": "ok"}`

### Readiness Check
- **Endpoint**: `GET /ready`
- **Response**: `{"status": "ready", "database": "connected", "llm": "reachable", ...}`

### Prometheus Metrics
- **Endpoint**: `GET /metrics`
- **Format**: Prometheus text format exposing counters and histograms.
