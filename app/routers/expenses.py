from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.expense import Expense
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseSplitResponse
from app.services.expense_service import create_expense

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def add_expense(expense_in: ExpenseCreate, db: Session = Depends(get_db)):
    """
    Record a shared expense for a group.
    Splits equally among all members by default (with penny balance handling),
    or uses custom split amounts if split_type is 'EXACT'.
    """
    expense = create_expense(db, expense_in)

    all_users = {u.id: u.name for u in db.query(User).all()}

    split_responses = [
        ExpenseSplitResponse(
            user_id=s.user_id,
            user_name=all_users.get(s.user_id, f"User_{s.user_id}"),
            amount_owed=s.amount_owed
        )
        for s in expense.splits
    ]

    return ExpenseResponse(
        id=expense.id,
        description=expense.description,
        amount=expense.amount,
        paid_by=all_users.get(expense.paid_by, f"User_{expense.paid_by}"),
        paid_by_id=expense.paid_by,
        group_id=expense.group_id,
        split_type=expense.split_type,
        created_at=expense.created_at,
        splits=split_responses
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    """
    Retrieve expense details by ID.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )

    all_users = {u.id: u.name for u in db.query(User).all()}

    split_responses = [
        ExpenseSplitResponse(
            user_id=s.user_id,
            user_name=all_users.get(s.user_id, f"User_{s.user_id}"),
            amount_owed=s.amount_owed
        )
        for s in expense.splits
    ]

    return ExpenseResponse(
        id=expense.id,
        description=expense.description,
        amount=expense.amount,
        paid_by=all_users.get(expense.paid_by, f"User_{expense.paid_by}"),
        paid_by_id=expense.paid_by,
        group_id=expense.group_id,
        split_type=expense.split_type,
        created_at=expense.created_at,
        splits=split_responses
    )
