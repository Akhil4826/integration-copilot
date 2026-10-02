"""Customer business service layer."""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.errors import NotFoundException, ValidationException
from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate


class CustomerService:
    def __init__(self, repository: Optional[CustomerRepository] = None):
        self.repo = repository or CustomerRepository()

    def get_customer(self, db: Session, customer_id: str) -> Customer:
        if not customer_id or not customer_id.strip():
            raise ValidationException("customer_id cannot be empty")
        customer = self.repo.get_by_customer_id(db, customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)
        return customer

    def search_customers(
        self, db: Session, query: Optional[str] = None, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Customer], int]:
        return self.repo.search_customers(db, query=query, offset=offset, limit=limit)

    def create_customer(self, db: Session, data: CustomerCreate) -> Customer:
        # Check existing email
        items, _ = self.repo.search_customers(db, query=data.email, limit=1)
        for item in items:
            if item.email.lower() == data.email.lower():
                raise ValidationException(f"Customer with email '{data.email}' already exists")

        # Generate customer ID if missing
        if not data.customer_id:
            _, total = self.repo.search_customers(db, limit=1)
            customer_id = f"CUST-{1001 + total}"
        else:
            customer_id = data.customer_id.strip().upper()
            if self.repo.get_by_customer_id(db, customer_id):
                raise ValidationException(f"Customer ID '{customer_id}' already exists")

        customer = Customer(
            customer_id=customer_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
        )
        return self.repo.create(db, customer)
