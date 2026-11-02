from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    paid_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String(255), nullable=False)
    split_type = Column(String(20), default="EQUAL", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_expense_amount_positive"),
    )

    # Relationships
    group = relationship("Group", back_populates="expenses")
    payer = relationship("User", back_populates="expenses_paid", foreign_keys=[paid_by])
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, amount={self.amount}, paid_by={self.paid_by})>"


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_owed = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount_owed >= 0", name="chk_split_amount_non_negative"),
    )

    # Relationships
    expense = relationship("Expense", back_populates="splits")
    user = relationship("User", back_populates="splits")

    def __repr__(self) -> str:
        return f"<ExpenseSplit(expense_id={self.expense_id}, user_id={self.user_id}, owed={self.amount_owed})>"
