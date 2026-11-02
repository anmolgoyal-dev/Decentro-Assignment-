from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.group import Group, GroupMember
from app.models.user import User
from app.models.expense import Expense
from app.schemas.group import GroupCreate, GroupResponse, GroupAddMember, GroupMemberResponse
from app.schemas.expense import ExpenseResponse, ExpenseSplitResponse
from app.services.balance_service import get_structured_balances
from app.services.settlement_service import simplify_debts_min_cash_flow
from app.schemas.settlement import SettlementSuggestionsResponse

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group_in: GroupCreate, db: Session = Depends(get_db)):
    """
    Create a new group.
    """
    new_group = Group(
        name=group_in.name.strip(),
        description=group_in.description.strip() if group_in.description else None
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group


@router.get("", response_model=List[GroupResponse])
def list_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Return all groups in the system.
    """
    groups = db.query(Group).offset(skip).limit(limit).all()
    return groups


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    """
    Fetch a group by ID.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )
    return group


@router.post("/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED)
def add_user_to_group(group_id: int, member_in: GroupAddMember, db: Session = Depends(get_db)):
    """
    Add a user to a group.
    Supports either {"user_id": 2} or {"group_id": 1, "user_id": 2}.
    """
    # 1. Verify group exists
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )

    # 2. Verify user exists
    user = db.query(User).filter(User.id == member_in.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {member_in.user_id} not found."
        )

    # 3. Check if already a member
    existing_membership = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member_in.user_id
    ).first()

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.name}' is already a member of group '{group.name}'."
        )

    membership = GroupMember(
        group_id=group_id,
        user_id=member_in.user_id
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return GroupMemberResponse(
        id=membership.id,
        user_id=user.id,
        name=user.name,
        joined_at=membership.joined_at
    )


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
def list_group_members(group_id: int, db: Session = Depends(get_db)):
    """
    Return all members belonging to a group.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )

    memberships = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    user_ids = [m.user_id for m in memberships]
    users_by_id = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    return [
        GroupMemberResponse(
            id=m.id,
            user_id=m.user_id,
            name=users_by_id.get(m.user_id, f"User_{m.user_id}"),
            joined_at=m.joined_at
        )
        for m in memberships
    ]


@router.get("/{group_id}/expenses", response_model=List[ExpenseResponse])
def list_group_expenses(group_id: int, db: Session = Depends(get_db)):
    """
    Return all expenses for a particular group.
    Format adheres to PDF specification: description, amount, paid_by (user name).
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )

    expenses = db.query(Expense).filter(Expense.group_id == group_id).order_by(Expense.created_at.asc()).all()

    # Pre-fetch user names
    all_users = {u.id: u.name for u in db.query(User).all()}

    results = []
    for exp in expenses:
        split_responses = [
            ExpenseSplitResponse(
                user_id=s.user_id,
                user_name=all_users.get(s.user_id, f"User_{s.user_id}"),
                amount_owed=s.amount_owed
            )
            for s in exp.splits
        ]
        results.append(
            ExpenseResponse(
                id=exp.id,
                description=exp.description,
                amount=exp.amount,
                paid_by=all_users.get(exp.paid_by, f"User_{exp.paid_by}"),
                paid_by_id=exp.paid_by,
                group_id=exp.group_id,
                split_type=exp.split_type,
                created_at=exp.created_at,
                splits=split_responses
            )
        )
    return results


@router.get("/{group_id}/balances")
def get_group_balances(group_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Calculate and return net balances within a group matching the PDF format.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )

    return get_structured_balances(db, group_id=group_id)


@router.get("/{group_id}/settlements/suggestions", response_model=SettlementSuggestionsResponse)
def get_group_settlement_suggestions(group_id: int, db: Session = Depends(get_db)):
    """
    Smart settlement suggestions for a specific group using the Min-Cash-Flow algorithm.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )

    return simplify_debts_min_cash_flow(db, group_id=group_id)
