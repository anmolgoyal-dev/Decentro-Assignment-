from decimal import Decimal, ROUND_DOWN
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.group import Group, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.user import User
from app.schemas.expense import ExpenseCreate


def calculate_equal_splits(amount: Decimal, user_ids: List[int]) -> List[Tuple[int, Decimal]]:
    """
    Splits an amount equally among user_ids with penny precision.
    Distributes remainder cents sequentially so the sum of splits
    strictly equals the total amount.
    """
    n = len(user_ids)
    if n == 0:
        raise ValueError("Cannot split expense among 0 participants")

    # Base share rounded down to 2 decimal places
    base_share = (amount / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    total_distributed = base_share * n
    remainder = amount - total_distributed

    # Calculate how many participants get an extra 0.01 cent
    extra_cents = int((remainder / Decimal("0.01")).to_integral_value())

    splits: List[Tuple[int, Decimal]] = []
    for i, user_id in enumerate(user_ids):
        share = base_share + (Decimal("0.01") if i < extra_cents else Decimal("0.00"))
        splits.append((user_id, share))

    return splits


def create_expense(db: Session, expense_in: ExpenseCreate) -> Expense:
    """
    Validates business rules and creates a new Expense record along with
    individual ExpenseSplit records.
    """
    # 1. Validate Group exists
    group = db.query(Group).filter(Group.id == expense_in.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {expense_in.group_id} does not exist"
        )

    # 2. Validate Payer exists
    payer = db.query(User).filter(User.id == expense_in.paid_by).first()
    if not payer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User (payer) with id {expense_in.paid_by} does not exist"
        )

    # 3. Retrieve group members
    group_member_records = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    member_user_ids = {m.user_id for m in group_member_records}

    if not member_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record an expense for a group with no members"
        )

    if expense_in.paid_by not in member_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payer (user_id={expense_in.paid_by}) is not a member of group '{group.name}'"
        )

    # 4. Compute splits based on split_type
    splits_to_create: List[Tuple[int, Decimal]] = []

    if expense_in.split_type == "EXACT":
        if not expense_in.splits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom splits list must be provided when split_type is 'EXACT'"
            )

        split_total = Decimal("0.00")
        for s in expense_in.splits:
            if s.user_id not in member_user_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Split user_id {s.user_id} is not a member of the group"
                )
            splits_to_create.append((s.user_id, s.amount))
            split_total += s.amount

        if split_total != expense_in.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of custom splits ({split_total}) must equal expense amount ({expense_in.amount})"
            )
    else:
        # Default: EQUAL split among all members of the group
        sorted_members = sorted(list(member_user_ids))
        splits_to_create = calculate_equal_splits(expense_in.amount, sorted_members)

    # 5. Persist Expense and Splits in a single transaction
    new_expense = Expense(
        group_id=expense_in.group_id,
        paid_by=expense_in.paid_by,
        amount=expense_in.amount,
        description=expense_in.description.strip(),
        split_type=expense_in.split_type or "EQUAL"
    )
    db.add(new_expense)
    db.flush()  # populate new_expense.id

    for user_id, amount_owed in splits_to_create:
        split_record = ExpenseSplit(
            expense_id=new_expense.id,
            user_id=user_id,
            amount_owed=amount_owed
        )
        db.add(split_record)

    db.commit()
    db.refresh(new_expense)
    return new_expense
