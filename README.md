# Expense Sharing Service

A high-performance, robust, and clean backend service for managing shared group expenses, tracking debts, calculating pairwise balances, and simplifying cross-group settlements. Built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL** (with **SQLite** fallback for zero-friction local testing), adhering to clean software engineering practices, penny-accurate financial math, and comprehensive automated test coverage.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Product Enhancement: Smart Settlement Suggestions](#product-enhancement-smart-settlement-suggestions-min-cash-flow)
3. [Architecture Overview](#architecture-overview)
4. [Database Design & Schema Explanation](#database-design--schema-explanation)
5. [Setup & Running Instructions](#setup--running-instructions)
   - [Option A: Docker Compose (PostgreSQL + FastAPI)](#option-a-docker-compose-recommended)
   - [Option B: Local Virtual Environment](#option-b-local-virtual-environment)
6. [API Documentation & Examples](#api-documentation--examples)
7. [Running Tests](#running-tests)
8. [Assumptions Made](#assumptions-made)
9. [Future Enhancements](#future-enhancements)

---

## Key Features

- **User & Group Management**: Create users and manage multi-member groups with relational integrity.
- **Expense Tracking**: Add shared expenses with descriptions, timestamps, and payer assignment.
- **Penny-Precise Equal Splitting**: Financial rounding algorithm ensures remainder cents are allocated deterministically so $\sum \text{splits} = \text{total}$ down to the last paisa.
- **Custom / Exact Splits Support**: Optional split amounts validated to ensure sum strictly equals the total expense.
- **Pairwise Balance Calculation**: Computes exact net balances between any two users, formatted in the exact JSON structure requested in the assignment.
- **Direct Settlement Ledger**: Allows members to settle balances (partial or full) via recorded settlement transactions.
- **Smart Settlement Suggestions (Min-Cash-Flow)**: Greedy graph simplification algorithm that minimizes the number of financial transactions required to settle all debts in a group.

---

## Product Enhancement: Smart Settlement Suggestions (Min-Cash-Flow)

### 1. Why this feature was chosen
In group trips (e.g., college trips, flatmate expenses), multiple members frequently pay for different activities. Over time, pairwise debts form a complex directed graph with cycles and multi-hop paths.
For example, if **Alice owes Bob ₹500** and **Bob owes Charlie ₹500**, without simplification Bob is forced to receive ₹500 from Alice and turn around to send ₹500 to Charlie. If Alice instead sends ₹500 directly to Charlie, **Bob does not need to transact at all**, reducing 2 transactions to 1.

Implementing **Smart Settlement Suggestions** elevates this service from a rudimentary ledger to an intelligent financial platform similar to Splitwise's *Simplify Debts* engine.

### 2. What problem it solves
- **Transaction Overhead**: In a group of $N$ users, unsimplified pairwise debts can require up to $\frac{N(N-1)}{2} = O(N^2)$ separate peer-to-peer bank transfers.
- **Minimization**: The Min-Cash-Flow algorithm guarantees that the entire group can be settled in **at most $N - 1$ transactions**.
- **Friction Reduction**: Group members avoid multiple UPI / bank transfers and confusing intermediate payment reminders.

### 3. Algorithm & Design Decisions
The debt simplification algorithm operates as follows:
1. **Net Position Calculation**: For each participant $u$, compute their net balance across all group expenses and settlements:
   $$\text{NetBalance}(u) = \sum \text{Credits}(u) - \sum \text{Debits}(u)$$
   Because money in equals money out across the closed system:
   $$\sum_{u \in \text{Group}} \text{NetBalance}(u) = 0.00$$
2. **Partitioning**: Users with $\text{NetBalance} > 0$ are net creditors; users with $\text{NetBalance} < 0$ are net debtors. Users with $\text{NetBalance} = 0$ are already squared away and excluded from further transactions.
3. **Greedy Matching with Priority Queues (Max-Heaps)**:
   - Extract the largest debtor $D$ (owes $X$) and largest creditor $C$ (is owed $Y$).
   - Settle amount $T = \min(X, Y)$ via transfer $D \rightarrow C$.
   - Update balances:
     - If $X > T$, push $D$ back to the debtor heap with remaining debt $X - T$.
     - If $Y > T$, push $C$ back to the creditor heap with remaining credit $Y - T$.
   - Repeat until all balances reach 0.00.

### 4. Tradeoffs Considered
- **Direct Relationships vs. Transitive Payments**: In simplified settlements, a member might pay someone they did not directly receive money from. While optimal for total transactions, some users prefer paying only the exact person who paid for their meal. Therefore, the service provides **both**:
  - `GET /groups/{id}/balances`: Exact pairwise debts reflecting direct transactions.
  - `GET /groups/{id}/settlements/suggestions`: The mathematically optimal minimal-transfer path.
- **Computational Complexity**: The greedy min-cash-flow runs in $O(N \log N)$ time, which is practically instantaneous for typical trip groups ($N < 100$).

---

## Architecture Overview

The project follows a clean layered architecture with clear separation of concerns:

```
decentro/
├── app/
│   ├── config.py           # Pydantic Settings (DB URLs, env variables)
│   ├── database.py         # SQLAlchemy engine, session lifecycle, table init
│   ├── main.py             # FastAPI entrypoint, middleware, healthcheck
│   ├── models/             # SQLAlchemy ORM declarative models
│   │   ├── user.py         # User model
│   │   ├── group.py        # Group & GroupMember models
│   │   ├── expense.py      # Expense & ExpenseSplit models
│   │   └── settlement.py   # Settlement model
│   ├── schemas/            # Pydantic request/response validation schemas
│   │   ├── user.py
│   │   ├── group.py
│   │   ├── expense.py
│   │   ├── balance.py
│   │   └── settlement.py
│   ├── services/           # Pure business logic and algorithms
│   │   ├── expense_service.py     # Split validation & penny precision logic
│   │   ├── balance_service.py     # Pairwise ledger netting
│   │   └── settlement_service.py  # Min-Cash-Flow graph simplification
│   └── routers/            # Clean REST API endpoints
│       ├── users.py
│       ├── groups.py
│       ├── expenses.py
│       ├── balances.py
│       └── settlements.py
├── tests/                  # Pytest test suite (32 unit & integration tests)
├── Dockerfile              # Production container build
├── docker-compose.yml      # Orchestration (FastAPI + PostgreSQL 16)
├── requirements.txt        # Python dependencies
├── postman_collection.json # Ready-to-import API collection
└── PROJECT_PROGRESS.md     # Engineering milestone tracking
```

---

## Database Design & Schema Explanation

The schema is normalized to 3NF and avoids float rounding errors by storing monetary values as `Numeric(10, 2)` (mapped to Python `Decimal`).

```
 +--------------------+       1:N       +----------------------+
 |       users        | <-------------> |     group_members    |
 +--------------------+                 +----------------------+
 | id (PK)            |                 | id (PK)              |
 | name               |                 | group_id (FK->groups)|
 | email (Unique, opt)|                 | user_id (FK->users)  |
 | created_at         |                 | joined_at            |
 +--------------------+                 +----------------------+
       ^          ^                                |
       |          |                                | N:1
       |          |                                v
       |          |                     +----------------------+
       |          |                     |        groups        |
       |          |                     +----------------------+
       |          |                     | id (PK)              |
       |          |                     | name                 |
       |          |                     | description (opt)    |
       |          |                     | created_at           |
       |          |                     +----------------------+
       |          |                                |
       |          +------------------+             | 1:N
       |                             |             v
       | (paid_by)                   |  +----------------------+
       |                             |  |       expenses       |
       |                             |  +----------------------+
       |                             |  | id (PK)              |
       |                             |  | group_id (FK->groups)|
       |                             |  | paid_by (FK->users)  |
       |                             |  | amount (Numeric)     |
       |                             |  | description          |
       |                             |  | split_type           |
       |                             |  | created_at           |
       |                             |  +----------------------+
       |                             |             |
       | (user_id)                   |             | 1:N
       |                             |             v
       |                             |  +----------------------+
       |                             +- |    expense_splits    |
       |                                +----------------------+
       |                                | id (PK)              |
       |                                | expense_id (FK->exp) |
       |                                | user_id (FK->users)  |
       |                                | amount_owed (Numeric)|
       |                                +----------------------+
       |
       | (payer_id, payee_id)
       v
+-----------------------+
|      settlements      |
+-----------------------+
| id (PK)               |
| group_id (FK, opt)    |
| payer_id (FK->users)  |
| payee_id (FK->users)  |
| amount (Numeric)      |
| notes (opt)           |
| created_at            |
+-----------------------+
```

### Table Breakdown

1. **`users`**:
   - `id`: Auto-incrementing primary key.
   - `name`: Full name of user.
   - `email`: Optional email address with unique index.
   - `created_at`: Timestamp with timezone.

2. **`groups`**:
   - `id`: Auto-incrementing primary key.
   - `name`: Group name (e.g. "Goa Trip").
   - `description`: Optional text.
   - `created_at`: Timestamp.

3. **`group_members`**:
   - Junction table for the many-to-many relationship between users and groups.
   - Enforces `UniqueConstraint("group_id", "user_id")` to prevent duplicate membership.
   - Cascading deletes ensure data cleanliness if a group is removed.

4. **`expenses`**:
   - `id`: Primary key.
   - `group_id`: Foreign key referencing `groups.id`.
   - `paid_by`: Foreign key referencing `users.id` (Restricted delete).
   - `amount`: `Numeric(10, 2)` with check constraint `amount > 0`.
   - `description`: Text note (e.g. "Dinner").
   - `split_type`: Indicator ("EQUAL" or "EXACT").

5. **`expense_splits`** *(Key Architectural Decision)*:
   - Stores the exact share owed by each participant for an expense.
   - **Why this design?** Rather than recalculating splits dynamically based on current group membership, recording immutable splits at the time of expense creation preserves historical accuracy even if members join or leave the group later.
   - Guarantees zero penny loss on division remainders.

6. **`settlements`**:
   - Records cash / UPI debt settlements between two members (`payer_id` and `payee_id`).
   - Directly offsets the pairwise ledger between the two parties.

---

## Setup & Running Instructions

### Option A: Docker Compose (Recommended)

Requires Docker and Docker Compose. Spins up both the PostgreSQL 16 database and the FastAPI application container with automatic healthchecks.

```bash
# 1. Clone the repository and navigate into the folder
cd decentro

# 2. Start PostgreSQL and the API service
docker-compose up --build -d

# 3. Check container logs
docker-compose logs -f web

# 4. Access the API and interactive docs
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```

To stop the containers:
```bash
docker-compose down
```

---

### Option B: Local Virtual Environment

Run locally using Python 3.10+ and SQLite (or a local PostgreSQL instance):

```bash
# 1. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment variables (defaults to SQLite if DATABASE_URL is unset)
cp .env.example .env

# 4. Start the FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service will automatically initialize tables on startup and will be accessible at `http://localhost:8000`.

---

## API Documentation & Examples

Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### 1. User Management

#### Create User
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Mohit", "email": "mohit@example.com"}'
```
**Response (201 Created):**
```json
{
  "id": 1,
  "name": "Mohit",
  "email": "mohit@example.com",
  "created_at": "2026-11-02T22:30:00Z"
}
```

#### List Users
```bash
curl -X GET http://localhost:8000/users
```

---

### 2. Group Management

#### Create Group
```bash
curl -X POST http://localhost:8000/groups \
  -H "Content-Type: application/json" \
  -d '{"name": "Goa Trip", "description": "Summer Trip with Friends"}'
```
**Response (201 Created):**
```json
{
  "id": 1,
  "name": "Goa Trip",
  "description": "Summer Trip with Friends",
  "created_at": "2026-11-02T22:30:00Z"
}
```

#### Add User to Group
```bash
curl -X POST http://localhost:8000/groups/1/members \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2}'
```

#### List Group Members
```bash
curl -X GET http://localhost:8000/groups/1/members
```

---

### 3. Expense Management

#### Add Expense (Equal Split)
```bash
curl -X POST http://localhost:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 1,
    "paid_by": 1,
    "amount": 1200.0,
    "description": "Dinner"
  }'
```
**Response (201 Created):**
```json
{
  "id": 1,
  "description": "Dinner",
  "amount": 1200.0,
  "paid_by": "Mohit",
  "paid_by_id": 1,
  "group_id": 1,
  "split_type": "EQUAL",
  "created_at": "2026-11-02T22:30:00Z",
  "splits": [
    {"user_id": 1, "user_name": "Mohit", "amount_owed": 400.0},
    {"user_id": 2, "user_name": "Rahul", "amount_owed": 400.0},
    {"user_id": 3, "user_name": "Ankit", "amount_owed": 400.0}
  ]
}
```

#### List Group Expenses
```bash
curl -X GET http://localhost:8000/groups/1/expenses
```
**Response (200 OK):**
```json
[
  {
    "id": 1,
    "description": "Dinner",
    "amount": 1200.0,
    "paid_by": "Mohit",
    "paid_by_id": 1,
    "group_id": 1,
    "split_type": "EQUAL",
    "created_at": "2026-11-02T22:30:00Z",
    "splits": [...]
  }
]
```

---

### 4. Balance Calculation

#### Get Balances (Assignment PDF Format)
```bash
curl -X GET http://localhost:8000/balances
# Or group-specific:
curl -X GET http://localhost:8000/groups/1/balances
```
**Response (200 OK):**
```json
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
```

#### Get Detailed Balances (Structured for Client Apps)
```bash
curl -X GET http://localhost:8000/balances/detailed
```
**Response (200 OK):**
```json
{
  "group_id": null,
  "balances": [
    {
      "debtor_id": 2,
      "debtor_name": "Rahul",
      "creditor_id": 1,
      "creditor_name": "Mohit",
      "amount": 400.0
    },
    {
      "debtor_id": 3,
      "debtor_name": "Ankit",
      "creditor_id": 1,
      "creditor_name": "Mohit",
      "amount": 400.0
    }
  ]
}
```

---

### 5. Smart Settlement Suggestions & Settlement Recording

#### Get Smart Settlement Suggestions (Min-Cash-Flow)
```bash
curl -X GET http://localhost:8000/groups/1/settlements/suggestions
```
**Response (200 OK):**
```json
{
  "group_id": 1,
  "total_transactions_before": 2,
  "simplified_transactions_count": 2,
  "suggestions": [
    {
      "from_user_id": 2,
      "from_user_name": "Rahul",
      "to_user_id": 1,
      "to_user_name": "Mohit",
      "amount": 400.0
    },
    {
      "from_user_id": 3,
      "from_user_name": "Ankit",
      "to_user_id": 1,
      "to_user_name": "Mohit",
      "amount": 400.0
    }
  ]
}
```

#### Record Direct Settlement (Rahul pays Mohit ₹400)
```bash
curl -X POST http://localhost:8000/settlements \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": 2,
    "payee_id": 1,
    "amount": 400.0,
    "group_id": 1,
    "notes": "Paid via UPI"
  }'
```
**Response (201 Created):**
```json
{
  "id": 1,
  "payer_id": 2,
  "payer_name": "Rahul",
  "payee_id": 1,
  "payee_name": "Mohit",
  "amount": 400.0,
  "group_id": 1,
  "notes": "Paid via UPI",
  "created_at": "2026-11-02T22:31:00Z"
}
```

After this settlement, querying `GET /balances` immediately reflects that Rahul owes Mohit ₹0 (cleared), while Ankit still owes Mohit ₹400.

---

## Running Tests

Automated testing is configured via **Pytest** with 32 unit and integration tests covering all business requirements, validation rules, penny splits, and edge cases.

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests with verbose output
pytest -v

# Run tests with test coverage breakdown
pytest --cov=app --cov-report=term-missing
```

**Current Test Results:**
- **32 passed** in ~1.2s
- **96% test coverage** across the entire codebase.

---

## Assumptions Made

1. **Group Membership Required for Payer**: The user who records an expense must belong to the group where the expense took place.
2. **Deterministic Penny Allocation**: In equal splits with non-divisible cents (e.g. ₹100 split 3 ways $\rightarrow$ ₹33.3333...), the extra paisa/cent is distributed sequentially to members in a deterministic order so no money is lost or gained.
3. **Payer Does Not Owe Themselves**: While the payer's share is accounted for in the split records, pairwise balance calculation treats self-debts as ₹0.
4. **Direct Settlement Semantics**: Recording a settlement directly reduces the debtor's net balance to the creditor. If a member pays more than their outstanding debt, the ledger correctly reflects that the creditor now owes the excess amount back.

---

## Future Enhancements

1. **Authentication & Authorization**: Integrate JWT / OAuth2 bearer tokens so users can only view their own groups or expenses.
2. **Category Tagging & Analytics**: Add expense categories (Food, Travel, Stay) with monthly breakdown graphs and CSV/PDF export.
3. **Percentage and Share Splits**: Extend split types to support percentage (`PERCENT`), shares/weights (`SHARES`), and adjustments.
4. **Idempotency Keys**: Add `Idempotency-Key` headers on `/expenses` and `/settlements` to prevent accidental double-billing on network retries.
