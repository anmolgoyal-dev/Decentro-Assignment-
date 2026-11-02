from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
    payer_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    payee_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_settlement_amount_positive"),
        CheckConstraint("payer_id != payee_id", name="chk_settlement_distinct_parties"),
    )

    # Relationships
    payer = relationship("User", back_populates="settlements_paid", foreign_keys=[payer_id])
    payee = relationship("User", back_populates="settlements_received", foreign_keys=[payee_id])
    group = relationship("Group", foreign_keys=[group_id])

    def __repr__(self) -> str:
        return f"<Settlement(id={self.id}, payer={self.payer_id}, payee={self.payee_id}, amount={self.amount})>"
