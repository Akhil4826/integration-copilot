"""Deterministic seed script for populating the database with realistic business data.

Contains:
- 30 Customers
- 50 Products
- 100 Orders
- 200+ OrderItems
- 30 SupportTickets
"""

import random
from datetime import datetime, timedelta, timezone

from app.db.database import Base, SessionLocal, engine
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.ticket import SupportTicket, TicketPriority, TicketStatus

# Fix random seed for strict determinism
RANDOM_SEED = 42


def generate_seed_data(session):
    rng = random.Random(RANDOM_SEED)

    # Base reference time: 2026-10-02 12:00:00 UTC
    ref_time = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)

    # 1. 30 Customers
    first_names = [
        "James",
        "Mary",
        "Robert",
        "Patricia",
        "John",
        "Jennifer",
        "Michael",
        "Linda",
        "David",
        "Elizabeth",
        "William",
        "Barbara",
        "Richard",
        "Susan",
        "Joseph",
        "Jessica",
        "Thomas",
        "Sarah",
        "Charles",
        "Karen",
        "Christopher",
        "Nancy",
        "Daniel",
        "Lisa",
        "Matthew",
        "Betty",
        "Anthony",
        "Margaret",
        "Mark",
        "Sandra",
    ]
    last_names = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
        "Hernandez",
        "Lopez",
        "Gonzalez",
        "Wilson",
        "Anderson",
        "Thomas",
        "Taylor",
        "Moore",
        "Jackson",
        "Martin",
        "Lee",
        "Perez",
        "Thompson",
        "White",
        "Harris",
        "Sanchez",
        "Clark",
        "Ramirez",
        "Lewis",
        "Robinson",
    ]

    customers = []
    for i in range(30):
        c_id = f"CUST-{1001 + i}"
        name = f"{first_names[i]} {last_names[i]}"
        email = f"{first_names[i].lower()}.{last_names[i].lower()}{i + 1}@example.com"
        phone = f"+1-555-{100 + i:03d}-{1000 + i:04d}"
        created_at = ref_time - timedelta(days=120 - i * 3)
        cust = Customer(
            customer_id=c_id, name=name, email=email, phone=phone, created_at=created_at
        )
        customers.append(cust)
        session.add(cust)

    # 2. 50 Products across 5 categories
    product_templates = [
        # Electronics
        ("Ultra Wireless Mouse", "Electronics", 49.99, 150),
        ("Mechanical Keyboard RGB", "Electronics", 129.99, 80),
        ("4K UltraHD Monitor 27-inch", "Electronics", 349.99, 45),
        ("USB-C Dual HDMI Hub", "Electronics", 59.99, 200),
        ("Noise Cancelling Headphones", "Electronics", 199.99, 60),
        ("HD Pro Webcam 1080p", "Electronics", 79.99, 90),
        ("Portable Bluetooth Speaker", "Electronics", 39.99, 120),
        ("Wireless Charging Stand", "Electronics", 29.99, 250),
        ("Ergonomic Vertical Mouse", "Electronics", 54.99, 75),
        ("Smart LED Desk Lamp", "Electronics", 44.99, 110),
        # Office Supplies
        ("Ergonomic Mesh Chair", "Office Supplies", 249.99, 35),
        ("Electric Standing Desk", "Office Supplies", 499.99, 20),
        ("Gel Wrist Rest Pad", "Office Supplies", 14.99, 300),
        ("Monitor Arm Dual Mount", "Office Supplies", 89.99, 65),
        ("Under Desk Footrest", "Office Supplies", 34.99, 140),
        ("Cable Management Tray", "Office Supplies", 24.99, 180),
        ("Acoustic Desk Divider", "Office Supplies", 119.99, 40),
        ("Whiteboard Magnetic 3x2", "Office Supplies", 69.99, 50),
        ("Document Scanner Compact", "Office Supplies", 159.99, 30),
        ("Desk Pad Vegan Leather Large", "Office Supplies", 22.99, 220),
        # Hardware
        ("Internal NVMe SSD 1TB", "Hardware", 99.99, 85),
        ("Internal NVMe SSD 2TB", "Hardware", 179.99, 45),
        ("DDR5 RAM 32GB Kit (2x16GB)", "Hardware", 114.99, 70),
        ("External Rugged SSD 1TB", "Hardware", 109.99, 95),
        ("Modular Power Supply 750W", "Hardware", 124.99, 40),
        ("CPU Liquid Cooler 240mm", "Hardware", 89.99, 55),
        ("PCIe WiFi 6E & BT Card", "Hardware", 39.99, 130),
        ("Precision Tool Kit 64-Bit", "Hardware", 32.99, 160),
        ("Thermal Paste Compound 4g", "Hardware", 9.99, 400),
        ("Anti-Static Grounding Mat", "Hardware", 19.99, 150),
        # Networking
        ("Wi-Fi 6 Mesh Router System", "Networking", 229.99, 40),
        ("Gigabit 8-Port Managed Switch", "Networking", 69.99, 80),
        ("Cat6 Ethernet Cable 50ft", "Networking", 16.99, 250),
        ("Cat6 Ethernet Cable 100ft", "Networking", 26.99, 180),
        ("PoE Injector 30W Gigabit", "Networking", 21.99, 110),
        ("Wall Mount Server Rack 6U", "Networking", 139.99, 25),
        ("Network Patch Panel 24-Port", "Networking", 49.99, 60),
        ("Outdoor Wireless AP", "Networking", 149.99, 35),
        ("SFP+ 10G Optical Transceiver", "Networking", 28.99, 90),
        ("Crimping Tool Network Kit", "Networking", 35.99, 100),
        # Software
        ("Cloud Backup Pro 1-Yr License", "Software", 59.99, 999),
        ("Cybersecurity Suite 1-Yr", "Software", 79.99, 999),
        ("Developer IDE Studio Pro", "Software", 199.99, 999),
        ("Diagramming & Wireframe Tool", "Software", 89.99, 999),
        ("Database Client GUI License", "Software", 69.99, 999),
        ("API Testing Toolkit 1-Yr", "Software", 119.99, 999),
        ("Project Management Single User", "Software", 149.99, 999),
        ("Code Quality Linter Pro", "Software", 49.99, 999),
        ("Virtual Machine Workstation", "Software", 129.99, 999),
        ("Terminal Emulator Enterprise", "Software", 39.99, 999),
    ]

    products = []
    for i, (p_name, p_cat, p_price, p_stock) in enumerate(product_templates):
        p_id = f"PROD-{1001 + i}"
        prod = Product(
            product_id=p_id,
            name=p_name,
            category=p_cat,
            price=p_price,
            stock_quantity=p_stock,
            created_at=ref_time - timedelta(days=150 - i * 2),
        )
        products.append(prod)
        session.add(prod)

    session.flush()

    # 3. 100 Orders & 200+ OrderItems
    # Status distributions: DELIVERED (45), SHIPPED (20), PROCESSING (12), PENDING (8), FAILED (10), CANCELLED (5)
    statuses_pool = (
        [OrderStatus.DELIVERED] * 45
        + [OrderStatus.SHIPPED] * 20
        + [OrderStatus.PROCESSING] * 12
        + [OrderStatus.PENDING] * 8
        + [OrderStatus.FAILED] * 10
        + [OrderStatus.CANCELLED] * 5
    )
    rng.shuffle(statuses_pool)

    # Ensure CUST-1004 has at least 2 FAILED orders and 1 DELIVERED order for the prompt demo
    cust_1004 = "CUST-1004"

    orders = []
    all_order_items = []

    for i in range(100):
        o_id = f"ORD-{1001 + i}"

        # Specific customer assignments for predictable demo cases
        if i == 3:
            c_id = cust_1004
            status = OrderStatus.FAILED
            created_date = ref_time - timedelta(days=5, hours=2)
        elif i == 14:
            c_id = cust_1004
            status = OrderStatus.FAILED
            created_date = ref_time - timedelta(days=1, hours=4)
        elif i == 25:
            c_id = cust_1004
            status = OrderStatus.DELIVERED
            created_date = ref_time - timedelta(days=12, hours=1)
        elif i < 10:
            # Deterministic spread
            c_id = customers[i % len(customers)].customer_id
            status = statuses_pool[i]
            created_date = ref_time - timedelta(hours=(100 - i) * 6)
        else:
            c_id = customers[rng.randint(0, len(customers) - 1)].customer_id
            status = statuses_pool[i]
            # Spread across last 60 days
            created_date = ref_time - timedelta(days=rng.randint(0, 45), hours=rng.randint(1, 23))

        # Assign 2 to 4 items per order (totaling > 200 items across 100 orders)
        num_items = rng.randint(2, 4)
        order_total = 0.0

        chosen_products = rng.sample(products, num_items)
        items_for_order = []

        for prod in chosen_products:
            qty = rng.randint(1, 3)
            unit_price = prod.price
            order_total += unit_price * qty
            item = OrderItem(
                order_id=o_id, product_id=prod.product_id, quantity=qty, unit_price=unit_price
            )
            items_for_order.append(item)
            all_order_items.append(item)

        order_obj = Order(
            order_id=o_id,
            customer_id=c_id,
            status=status,
            total_amount=round(order_total, 2),
            created_at=created_date,
            updated_at=created_date + timedelta(hours=rng.randint(1, 24)),
        )
        orders.append(order_obj)
        session.add(order_obj)

    session.flush()

    for item in all_order_items:
        session.add(item)

    session.flush()

    # 4. 30 Support Tickets
    # Connect tickets to customers and orders (especially failed/delayed orders)
    ticket_definitions = [
        (
            "TCK-1001",
            "CUST-1004",
            "ORD-1015",
            "Order ORD-1015 payment failure",
            "Customer reports payment error during checkout for ORD-1015.",
            TicketPriority.HIGH,
            TicketStatus.OPEN,
            1,
        ),
        (
            "TCK-1002",
            "CUST-1004",
            "ORD-1004",
            "Delivery delayed for order ORD-1004",
            "Customer noticed order status has failed and reached out for assistance.",
            TicketPriority.CRITICAL,
            TicketStatus.IN_PROGRESS,
            4,
        ),
        (
            "TCK-1003",
            "CUST-1001",
            "ORD-1001",
            "Inquiry regarding bulk discount",
            "Customer asking about volume discount for 4K UltraHD Monitor.",
            TicketPriority.LOW,
            TicketStatus.RESOLVED,
            15,
        ),
        (
            "TCK-1004",
            "CUST-1002",
            "ORD-1002",
            "Defective keyboard switch",
            "One key on the RGB mechanical keyboard is unresponsive.",
            TicketPriority.MEDIUM,
            TicketStatus.RESOLVED,
            20,
        ),
        (
            "TCK-1005",
            "CUST-1003",
            None,
            "Billing address update request",
            "Customer needs to update tax billing address.",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            22,
        ),
        (
            "TCK-1006",
            "CUST-1005",
            "ORD-1008",
            "Package marked delivered but not received",
            "Courier tracking claims delivered yesterday but nothing in reception.",
            TicketPriority.HIGH,
            TicketStatus.OPEN,
            2,
        ),
        (
            "TCK-1007",
            "CUST-1006",
            "ORD-1010",
            "Wrong color desk lamp received",
            "Ordered black model but received silver lamp.",
            TicketPriority.MEDIUM,
            TicketStatus.IN_PROGRESS,
            3,
        ),
        (
            "TCK-1008",
            "CUST-1007",
            None,
            "Product compatibility question",
            "Will the NVMe 2TB drive fit Dell PowerEdge R740?",
            TicketPriority.LOW,
            TicketStatus.RESOLVED,
            25,
        ),
        (
            "TCK-1009",
            "CUST-1008",
            "ORD-1018",
            "Order cancellation refund delay",
            "Cancelled order last week, refund still pending on credit card statement.",
            TicketPriority.HIGH,
            TicketStatus.OPEN,
            1,
        ),
        (
            "TCK-1010",
            "CUST-1009",
            "ORD-1022",
            "Custom invoice requested",
            "Requires corporate VAT number printed on PDF receipt.",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            30,
        ),
        (
            "TCK-1011",
            "CUST-1010",
            "ORD-1027",
            "Missing power cable in box",
            "Ergonomic desk delivered without AC power adapter cable.",
            TicketPriority.MEDIUM,
            TicketStatus.RESOLVED,
            18,
        ),
        (
            "TCK-1012",
            "CUST-1011",
            None,
            "Account password reset issue",
            "Password reset link sends 404 expired token.",
            TicketPriority.HIGH,
            TicketStatus.RESOLVED,
            14,
        ),
        (
            "TCK-1013",
            "CUST-1012",
            "ORD-1033",
            "Hardware warranty inquiry",
            "How long is the warranty coverage for modular PSU 750W?",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            28,
        ),
        (
            "TCK-1014",
            "CUST-1013",
            "ORD-1037",
            "Failed transaction retry question",
            "System declined credit card twice during peak hours.",
            TicketPriority.MEDIUM,
            TicketStatus.OPEN,
            6,
        ),
        (
            "TCK-1015",
            "CUST-1014",
            None,
            "API license key generation error",
            "Customer IDE studio pro key returns invalid license on startup.",
            TicketPriority.CRITICAL,
            TicketStatus.OPEN,
            1,
        ),
        (
            "TCK-1016",
            "CUST-1015",
            "ORD-1044",
            "Damaged packaging on arrival",
            "Outer shipping box was ripped and crushed by carrier.",
            TicketPriority.MEDIUM,
            TicketStatus.IN_PROGRESS,
            5,
        ),
        (
            "TCK-1017",
            "CUST-1016",
            "ORD-1049",
            "Switch port 5 not linking",
            "Managed switch port 5 LED is off and doesn't negotiate.",
            TicketPriority.HIGH,
            TicketStatus.IN_PROGRESS,
            7,
        ),
        (
            "TCK-1018",
            "CUST-1017",
            None,
            "Security compliance certification request",
            "Requires SOC2 type II audit report for software backup suite.",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            35,
        ),
        (
            "TCK-1019",
            "CUST-1018",
            "ORD-1055",
            "Return label request",
            "Customer requests prepaid return label for unopened cables.",
            TicketPriority.LOW,
            TicketStatus.RESOLVED,
            12,
        ),
        (
            "TCK-1020",
            "CUST-1019",
            "ORD-1061",
            "Payment gateway timeout",
            "Customer card was charged but order stayed in failed state.",
            TicketPriority.CRITICAL,
            TicketStatus.OPEN,
            2,
        ),
        (
            "TCK-1021",
            "CUST-1020",
            "ORD-1068",
            "Request expedited shipping upgrade",
            "Can customer pay extra to upgrade shipping to overnight?",
            TicketPriority.MEDIUM,
            TicketStatus.RESOLVED,
            10,
        ),
        (
            "TCK-1022",
            "CUST-1021",
            None,
            "Newsletter unsubscribe request",
            "Customer wishes to opt out of promotional emails.",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            40,
        ),
        (
            "TCK-1023",
            "CUST-1022",
            "ORD-1073",
            "SSD drive SMART error",
            "Brand new SSD showing 2 reallocated sectors upon first mount.",
            TicketPriority.HIGH,
            TicketStatus.IN_PROGRESS,
            4,
        ),
        (
            "TCK-1024",
            "CUST-1023",
            "ORD-1079",
            "Incorrect quantity delivered",
            "Order was for 3 units of wireless mouse, package only had 2.",
            TicketPriority.MEDIUM,
            TicketStatus.OPEN,
            3,
        ),
        (
            "TCK-1025",
            "CUST-1024",
            None,
            "Partner reseller application status",
            "Partner program application submitted 2 weeks ago.",
            TicketPriority.LOW,
            TicketStatus.RESOLVED,
            19,
        ),
        (
            "TCK-1026",
            "CUST-1025",
            "ORD-1084",
            "Webcam microphone echo",
            "Microphone picking up severe background static noise.",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            24,
        ),
        (
            "TCK-1027",
            "CUST-1026",
            "ORD-1089",
            "Order status stuck in processing",
            "Order placed 4 days ago hasn't moved to shipped.",
            TicketPriority.HIGH,
            TicketStatus.OPEN,
            1,
        ),
        (
            "TCK-1028",
            "CUST-1027",
            "ORD-1092",
            "Refund credit not appearing",
            "Bank claims no pending incoming credit note.",
            TicketPriority.HIGH,
            TicketStatus.IN_PROGRESS,
            6,
        ),
        (
            "TCK-1029",
            "CUST-1028",
            None,
            "Product specification clarification",
            "Are cables plenum rated (CMP) or riser (CMR)?",
            TicketPriority.LOW,
            TicketStatus.CLOSED,
            33,
        ),
        (
            "TCK-1030",
            "CUST-1029",
            "ORD-1098",
            "Order cancelled by mistake",
            "Customer accidentally clicked cancel order button.",
            TicketPriority.MEDIUM,
            TicketStatus.RESOLVED,
            8,
        ),
    ]

    for t_id, c_id, o_id, title, desc, prio, stat, days_ago in ticket_definitions:
        created_time = ref_time - timedelta(days=days_ago)
        ticket = SupportTicket(
            ticket_id=t_id,
            customer_id=c_id,
            order_id=o_id,
            title=title,
            description=desc,
            priority=prio,
            status=stat,
            created_at=created_time,
            updated_at=created_time + timedelta(hours=3),
        )
        session.add(ticket)

    session.commit()
    print("Successfully seeded database with:")
    print(f" - {len(customers)} Customers")
    print(f" - {len(products)} Products")
    print(f" - {len(orders)} Orders")
    print(f" - {len(all_order_items)} OrderItems")
    print(f" - {len(ticket_definitions)} SupportTickets")


def seed():
    """Create tables if not existing and seed deterministic data."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Check if already seeded
        existing = session.query(Customer).first()
        if existing:
            print("Database already contains data. Clearing and re-seeding for consistency...")
            session.query(SupportTicket).delete()
            session.query(OrderItem).delete()
            session.query(Order).delete()
            session.query(Product).delete()
            session.query(Customer).delete()
            session.commit()

        generate_seed_data(session)
    finally:
        session.close()


if __name__ == "__main__":
    seed()
