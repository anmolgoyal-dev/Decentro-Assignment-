from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.expense import Expense, ExpenseSplit
from app.models.settlement import Settlement
from app.models.user import User
from app.schemas.balance import DetailedBalanceItem


def compute_pairwise_debts(
    db: Session, group_id: Optional[int] = None
) -> Tuple[Dict[Tuple[int, int], Decimal], Dict[int, str]]:
    """
    Computes net pairwise debts between users.
    Returns:
      - debts: dict mapping (debtor_id, creditor_id) -> net_amount (Decimal > 0)
      - user_names: dict mapping user_id -> user.name
    """
    # 1. Fetch user map for display names
    users = db.query(User).all()
    user_names = {u.id: u.name for u in users}

    # Raw ledger: ledger[(A, B)] tracks gross amount A owes B
    gross_debt: Dict[Tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.00"))

    # 2. Account for expenses and splits
    expense_query = db.query(Expense, ExpenseSplit).join(
        ExpenseSplit, Expense.id == ExpenseSplit.expense_id
    )
    if group_id is not None:
        expense_query = expense_query.filter(Expense.group_id == group_id)

    for expense, split in expense_query.all():
        payer_id = expense.paid_by
        participant_id = split.user_id
        amount = split.amount_owed

        if participant_id != payer_id and amount > 0:
            # participant owes the payer
            gross_debt[(participant_id, payer_id)] += amount

    # 3. Account for settlements
    settlement_query = db.query(Settlement)
    if group_id is not None:
        settlement_query = settlement_query.filter(Settlement.group_id == group_id)

    for settlement in settlement_query.all():
        payer_id = settlement.payer_id
        payee_id = settlement.payee_id
        amount = settlement.amount

        # When payer pays payee, it reduces payer's debt to payee
        # (or effectively increases payee's debt to payer)
        gross_debt[(payer_id, payee_id)] -= amount

    # 4. Net out debts between each pair (A, B)
    all_pairs = set()
    for (debtor, creditor) in list(gross_debt.keys()):
        pair = tuple(sorted([debtor, creditor]))
        all_pairs.add(pair)

    net_debts: Dict[Tuple[int, int], Decimal] = {}

    for u1, u2 in all_pairs:
        u1_owes_u2 = gross_debt[(u1, u2)]
        u2_owes_u1 = gross_debt[(u2, u1)]
        net = u1_owes_u2 - u2_owes_u1

        if net > Decimal("0.00"):
            net_debts[(u1, u2)] = round(net, 2)
        elif net < Decimal("0.00"):
            net_debts[(u2, u1)] = round(abs(net), 2)

    return net_debts, user_names


def get_structured_balances(db: Session, group_id: Optional[int] = None) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Returns balances formatted in the structured JSON format specified in the PDF:
    {
      "Rahul": {
        "owes": {
          "Mohit": 400.0
        }
      },
      "Ankit": {
        "owes": {
          "Mohit": 400.0
        }
      }
    }
    """
    net_debts, user_names = compute_pairwise_debts(db, group_id)

    result: Dict[str, Dict[str, Dict[str, float]]] = {}

    for (debtor_id, creditor_id), amount in net_debts.items():
        debtor_name = user_names.get(debtor_id, f"User_{debtor_id}")
        creditor_name = user_names.get(creditor_id, f"User_{creditor_id}")

        if debtor_name not in result:
            result[debtor_name] = {"owes": {}}

        result[debtor_name]["owes"][creditor_name] = float(amount)

    return result


def get_detailed_balances(db: Session, group_id: Optional[int] = None) -> List[DetailedBalanceItem]:
    """
    Returns structured list of detailed balances with user IDs, names, and Decimal amounts.
    """
    net_debts, user_names = compute_pairwise_debts(db, group_id)
    detailed: List[DetailedBalanceItem] = []

    for (debtor_id, creditor_id), amount in sorted(net_debts.items()):
        detailed.append(
            DetailedBalanceItem(
                debtor_id=debtor_id,
                debtor_name=user_names.get(debtor_id, f"User_{debtor_id}"),
                creditor_id=creditor_id,
                creditor_name=user_names.get(creditor_id, f"User_{creditor_id}"),
                amount=amount
            )
        )

    return detailed
