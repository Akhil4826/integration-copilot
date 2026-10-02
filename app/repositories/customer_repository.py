"""Customer data-access repository."""

from typing import List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:
    """Encapsulates database operations for Customer entity."""

    def get_by_customer_id(self, db: Session, customer_id: str) -> Optional[Customer]:
        stmt = select(Customer).where(Customer.customer_id == customer_id.strip().upper())
        return db.execute(stmt).scalar_one_or_none()

    def search_customers(
        self, db: Session, query: Optional[str] = None, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Customer], int]:
        stmt = select(Customer)
        if query:
            q = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Customer.customer_id.ilike(q),
                    Customer.name.ilike(q),
                    Customer.email.ilike(q),
                    Customer.phone.ilike(q),
                )
            )

        # Get total count
        all_matches = db.execute(stmt).scalars().all()
        total = len(all_matches)

        # Paginate
        paginated_stmt = stmt.order_by(Customer.created_at.desc()).offset(offset).limit(limit)
        items = list(db.execute(paginated_stmt).scalars().all())

        return items, total

    def create(self, db: Session, customer: Customer) -> Customer:
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer
