from collections import defaultdict
from decimal import Decimal
import heapq
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.group import Group, GroupMember
from app.models.settlement import Settlement
from app.models.user import User
from app.schemas.settlement import (
    SettlementCreate,
    SettlementResponse,
    SettlementSuggestion,
    SettlementSuggestionsResponse,
)
from app.services.balance_service import compute_pairwise_debts


def simplify_debts_min_cash_flow(
    db: Session, group_id: Optional[int] = None
) -> SettlementSuggestionsResponse:
    """
    Implements the Min-Cash-Flow algorithm to simplify cross-debts among a group
    of users into the minimum number of transactions.

    Algorithm Overview:
    1. For every user, compute their net financial position:
       Net Balance = Total Credits (money they are owed) - Total Debits (money they owe).
    2. Sum of all net balances across all users is strictly 0.00.
    3. Partition users into:
       - Creditors (Net Balance > 0)
       - Debtors (Net Balance < 0)
    4. Greedily match the user who owes the most (max debtor) with the user who
       is owed the most (max creditor). Settle min(debt, credit) in a single direct transfer.
    5. Update remaining balances and repeat until all balances are settled to 0.

    Guarantees at most (N - 1) transactions, eliminating circular and multi-hop debts.
    """
    pairwise_debts, user_names = compute_pairwise_debts(db, group_id)
    total_tx_before = len(pairwise_debts)

    # 1. Compute net balance per user
    net_balances = defaultdict(lambda: Decimal("0.00"))
    for (debtor_id, creditor_id), amount in pairwise_debts.items():
        net_balances[debtor_id] -= amount
        net_balances[creditor_id] += amount

    # 2. Heaps for debtors and creditors:
    # Python heapq is a min-heap, so we store negative of amount to simulate a max-heap
    debtors = []  # (-debt_amount, user_id)
    creditors = []  # (-credit_amount, user_id)

    for user_id, net in net_balances.items():
        rounded_net = round(net, 2)
        if rounded_net < Decimal("0.00"):
            # Owes money
            heapq.heappush(debtors, (float(-abs(rounded_net)), user_id))
        elif rounded_net > Decimal("0.00"):
            # Is owed money
            heapq.heappush(creditors, (float(-rounded_net), user_id))

    suggestions: List[SettlementSuggestion] = []

    # 3. Greedy Min-Cash-Flow matching
    while debtors and creditors:
        neg_debt, debtor_id = heapq.heappop(debtors)
        neg_credit, creditor_id = heapq.heappop(creditors)

        debt_amount = Decimal(str(-neg_debt)).quantize(Decimal("0.01"))
        credit_amount = Decimal(str(-neg_credit)).quantize(Decimal("0.01"))

        transfer_amount = min(debt_amount, credit_amount)

        if transfer_amount > Decimal("0.00"):
            suggestions.append(
                SettlementSuggestion(
                    from_user_id=debtor_id,
                    from_user_name=user_names.get(debtor_id, f"User_{debtor_id}"),
                    to_user_id=creditor_id,
                    to_user_name=user_names.get(creditor_id, f"User_{creditor_id}"),
                    amount=transfer_amount
                )
            )

        remaining_debt = debt_amount - transfer_amount
        remaining_credit = credit_amount - transfer_amount

        if remaining_debt > Decimal("0.00"):
            heapq.heappush(debtors, (float(-remaining_debt), debtor_id))

        if remaining_credit > Decimal("0.00"):
            heapq.heappush(creditors, (float(-remaining_credit), creditor_id))

    return SettlementSuggestionsResponse(
        group_id=group_id,
        total_transactions_before=total_tx_before,
        simplified_transactions_count=len(suggestions),
        suggestions=suggestions
    )


def record_settlement(db: Session, settlement_in: SettlementCreate) -> SettlementResponse:
    """
    Validates and persists a direct settlement between two users.
    """
    if settlement_in.payer_id == settlement_in.payee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payer and payee cannot be the same user"
        )

    # Validate payer exists
    payer = db.query(User).filter(User.id == settlement_in.payer_id).first()
    if not payer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payer with id {settlement_in.payer_id} does not exist"
        )

    # Validate payee exists
    payee = db.query(User).filter(User.id == settlement_in.payee_id).first()
    if not payee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payee with id {settlement_in.payee_id} does not exist"
        )

    # If group_id is specified, validate group and membership
    if settlement_in.group_id is not None:
        group = db.query(Group).filter(Group.id == settlement_in.group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with id {settlement_in.group_id} does not exist"
            )

        members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
        member_ids = {m.user_id for m in members}
        if settlement_in.payer_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payer (user_id={settlement_in.payer_id}) is not a member of group '{group.name}'"
            )
        if settlement_in.payee_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payee (user_id={settlement_in.payee_id}) is not a member of group '{group.name}'"
            )

    settlement = Settlement(
        payer_id=settlement_in.payer_id,
        payee_id=settlement_in.payee_id,
        amount=settlement_in.amount,
        group_id=settlement_in.group_id,
        notes=settlement_in.notes.strip() if settlement_in.notes else None
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)

    return SettlementResponse(
        id=settlement.id,
        payer_id=payer.id,
        payer_name=payer.name,
        payee_id=payee.id,
        payee_name=payee.name,
        amount=settlement.amount,
        group_id=settlement.group_id,
        notes=settlement.notes,
        created_at=settlement.created_at
    )
