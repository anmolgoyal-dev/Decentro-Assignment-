from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
    expenses_paid = relationship("Expense", back_populates="payer", foreign_keys="Expense.paid_by")
    splits = relationship("ExpenseSplit", back_populates="user")
    settlements_paid = relationship("Settlement", back_populates="payer", foreign_keys="Settlement.payer_id")
    settlements_received = relationship("Settlement", back_populates="payee", foreign_keys="Settlement.payee_id")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}')>"
