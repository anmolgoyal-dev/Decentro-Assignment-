# Expense Sharing Service - Project Progress & Engineering Log

## Project Overview
A production-ready expense sharing backend service built with Python, FastAPI, SQLAlchemy, and PostgreSQL. The service enables groups of users to manage group expenses, split costs equally (with penny-level precision), track pairwise net balances, record debt settlements, and simplify complex cross-debts using a greedy Min-Cash-Flow graph algorithm (Smart Settlement Suggestions).

---

## Requirements Checklist & Status

### Mandatory Requirements
- [x] **Requirement Analysis**: Analyzed and parsed all functional requirements from the Decentro assignment PDF.
- [x] **Part 1 - User Management**:
  - [x] `POST /users`: Create user (`name`, optional `email`).
  - [x] `GET /users`: List all registered users.
  - [x] `GET /users/{id}`: Fetch user by ID.
- [x] **Part 2 - Group Management**:
  - [x] `POST /groups`: Create group (`name`, optional `description`).
  - [x] `GET /groups`: List all groups.
  - [x] `POST /groups/{group_id}/members`: Add user to group (handles duplicate membership prevention).
  - [x] `GET /groups/{group_id}/members`: List all members belonging to a group.
- [x] **Part 3 - Expense Management**:
  - [x] `POST /expenses`: Record expense (`group_id`, `paid_by`, `amount`, `description`).
  - [x] Validation: Amount > 0, valid group, payer must belong to the group, group must not be empty.
  - [x] Equal split among all group members with exact penny balancing (deterministic cent distribution, 0 leakage).
  - [x] Optional custom/exact splits support (`split_type: EXACT`) with sum matching validation.
  - [x] `GET /groups/{group_id}/expenses`: List all expenses for a group matching the PDF response format.
- [x] **Part 4 - Balance Calculation**:
  - [x] Pairwise balance calculation between all group members (taking into account expenses & settlements).
  - [x] `GET /balances` & `GET /groups/{group_id}/balances`: Output matching the exact format specified in the PDF:
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
  - [x] `GET /balances/detailed`: Enriched list format with user IDs and Decimals for client applications.
- [x] **Part 5 - Product Enhancement (Mandatory)**:
  - [x] **Smart Settlement Suggestions**: Debt simplification using the Min-Cash-Flow algorithm.
  - [x] Solves $O(N^2)$ cross debts down to at most $N-1$ optimal direct transactions.
  - [x] `GET /groups/{group_id}/settlements/suggestions` & `GET /settlements/suggestions`.
  - [x] `POST /settlements`: Settle outstanding balances between members (full or partial).
  - [x] `GET /settlements`: Audit log of past settlements.
- [x] **Testing & Quality Assurance**:
  - [x] Pytest test suite covering users, groups, expenses, penny-split precision, balances, settlements, edge cases, and 404/400 validation handlers.
  - [x] **32 tests passed, 96% total code coverage**.
- [x] **DevOps & Documentation**:
  - [x] Dockerfile & docker-compose.yml (FastAPI + PostgreSQL 16 Alpine with healthchecks).
  - [x] Verified Docker image build (`expense-sharing-service:latest`) and container health execution.
  - [x] .env.example & local .env fallback.
  - [x] Postman collection (`postman_collection.json`) covering all workflows.
  - [x] Comprehensive README.md with database schema explanation, architecture diagram, enhancement deep-dive, setup instructions, and API examples.

---

## Architectural & Design Decisions
1. **Financial Accuracy (No Float Errors)**:
   - Used SQLAlchemy `Numeric(10, 2)` and Python's `decimal.Decimal`.
   - For odd splits (e.g. ₹100 split 3 ways), remainder cents are systematically distributed so the sum of split records equals the total expense down to 0.00.
2. **Normalized Schema with Explicit Split Records (`expense_splits`)**:
   - Rather than computing splits on-the-fly from current group membership, each expense creates immutable `expense_splits` rows at the time of creation.
   - This ensures auditability: adding or removing a member in the future does not corrupt past historical expense splits.
3. **Database Portability**:
   - Application supports PostgreSQL for production and Docker, with seamless fallback to SQLite for local development and in-memory test execution.
4. **Greedy Min-Cash-Flow Priority Queues**:
   - Computes net balance across all participants ($\sum \text{net} = 0$).
   - Pairs max creditor with max debtor using two heaps, terminating in at most $N-1$ optimal transactions.

---

## Verification Summary
- `pytest -v`: **32 passed in 1.2s**
- `pytest --cov=app`: **96% code coverage**
- Docker build: **Successful**
- Container healthcheck: `{"status": "healthy"}`
