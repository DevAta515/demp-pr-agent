# SQL PR Reviewer Agent
## System Design, PDF Standards & Tech Stack Specification

---

## 1. Executive Summary & Strategy

The **SQL PR Reviewer Agent** is an automated code review system designed to enforce corporate **SQL Naming & Coding Standards** (defined in the PDF specification) across database pull requests and data pipeline repositories (PostgreSQL, Snowflake, BigQuery, MySQL, etc.).

In enterprise data teams, SQL code is authored by dozens of engineers across multiple repositories — schema definitions (`CREATE TABLE`), analytical queries, ETL pipelines, stored procedures, and migration scripts. Without automated enforcement, naming inconsistencies creep in silently: one developer writes `cust_id`, another writes `CustomerId`, a third writes `customer_ID`. Over time, these inconsistencies degrade data discoverability, break downstream BI dashboards, and make onboarding painful for new team members.

Traditional solutions like manual code reviews are slow and error-prone — human reviewers miss naming violations under time pressure, and linter tools like `sqlfluff` only check formatting (indentation, keyword casing) but cannot evaluate whether a column name like `ord_mstr` is a meaningful business name or a cryptic abbreviation.

The **SQL PR Reviewer Agent** solves this by acting as an **always-on, zero-latency SQL standards enforcer** that automatically reviews every Pull Request containing `.sql` files. It combines a **deterministic AST parser** (for instant, $0-cost rule checking) with an **LLM semantic engine** (for contextual naming judgment that rigid rules cannot handle). The agent posts its findings as polished inline review comments directly on the GitHub or GitLab PR — exactly where the developer is already working.

### Core Architectural Choice: Sequential Dual-Engine Strategy
To ensure **sub-second speed**, **$0 cost on invalid SQL**, and **zero LLM hallucinations on rigid rules**, the system uses a **Sequential Dual-Engine Architecture**:

1. **Engine 1 (`sqlglot` AST & Tokenizer)**: Runs locally in **~5ms** at **$0 token cost**. It validates syntax and deterministically enforces ~80% of explicit naming rules (`PascalCase` columns, `snake_case` tables, standard suffixes/prefixes, required audit fields).
2. **Short-Circuit Guardrail**: If `sqlglot` detects a syntax error, execution halts immediately and posts a syntax error report. The LLM is **never invoked** on broken SQL, saving 100% of API token costs.
3. **Engine 2 (LLM Semantic Engine - LiteLLM + Gemini / Claude)**: Runs **ONLY** when SQL syntax is valid. It receives the raw SQL diff **enriched with AST metadata** (extracted tables, columns, CTEs, foreign keys) from Engine 1. It evaluates semantic context (e.g. valid industry acronyms like `SKU`/`URL` vs vague shorthand), foreign key entity correlations, and formats a polished GitHub Markdown review comment.

---

## 2. PDF SQL Naming & Coding Standards Reference

This system enforces the complete corporate SQL naming specification outlined in the 6-page PDF standard document:

### A. General Principles & Object Naming

| Object Type | Naming Convention | Example |
| :--- | :--- | :--- |
| **Database** | `PascalCase` | `SalesDW` |
| **Schema** | `snake_case` | `bronze`, `silver`, `gold` |
| **Table** | `snake_case` & **Singular** | `customer`, `sales_order` (❌ `sales_orders`) |
| **View** | Prefix `vw_<name>` | `vw_customer_sales` |
| **Column** | `PascalCase` | `CustomerId`, `OrderDate` |
| **Stored Procedure** | Prefix `sp_<action>_<entity>` | `sp_LoadCustomer` |
| **Function** | Prefix `fn_<purpose>` | `fn_CalculateTax` |
| **Sequence** | Prefix `seq_<table>` | `seq_customer` |

### B. Column Naming Rules & Suffixes

- **Primary Key**: `<Entity>Id` (e.g., `CustomerId`, `ProductId`, `OrderId` — ❌ `id`, `cust_id`, `pk`).
- **Foreign Key**: Match referenced entity name `<ParentEntity>Id` (e.g., `CustomerId` in `sales_order`).
- **Date Columns**: Must end with **`Date`** (e.g., `OrderDate`, `InvoiceDate`, `EffectiveDate`).
- **Timestamp Columns**: Must end with **`Timestamp`** (e.g., `CreatedTimestamp`, `UpdatedTimestamp`, `LoadTimestamp`).
- **Boolean Columns**: Must start with **`Is`**, **`Has`**, or **`Can`** (e.g., `IsActive`, `IsDeleted`, `HasAttachment`, `CanProcess`).
- **Amount Columns**: Must end with **`Amount`** (e.g., `TotalAmount`, `TaxAmount`, `NetAmount`).
- **Count Columns**: Must end with **`Count`** (e.g., `OrderCount`, `ErrorCount`, `CustomerCount`).
- **Status Columns**: Must end with **`Status`** (e.g., `OrderStatus`, `ProcessingStatus`, `PaymentStatus`).
- **Name Columns**: Must end with **`Name`** (e.g., `CustomerName`, `ProductName`, `CountryName`).
- **Code Columns**: Must end with **`Code`** (e.g., `CountryCode`, `CurrencyCode`, `DepartmentCode`).
- **Description Columns**: Must end with **`Description`** (e.g., `ProductDescription`, `ErrorDescription`).

### C. Forbidden Vague Abbreviations
- ❌ **`Amt`** → Use `Amount`
- ❌ **`Cnt`** → Use `Count`
- ❌ **`Flg`** → Use `Is...` / `Has...` / `Can...` boolean prefix
- ❌ **`Desc`** → Use `Description`
- ❌ **SQL Reserved Keywords** as object names (`Order`, `User`, `Group`).

### D. Mandatory Audit Columns (Transactional Tables)
Every transactional table must include all 7 mandatory audit fields:
`CreatedBy`, `CreatedTimestamp`, `UpdatedBy`, `UpdatedTimestamp`, `IsDeleted`, `BatchId`, `SourceSystem` (`RecordVersion` optional).

### E. Constraint Naming Conventions
- **Primary Key**: `PK_<Table>` (e.g., `PK_Customer`)
- **Foreign Key**: `FK_<Child>_<Parent>` (e.g., `FK_Order_Customer`)
- **Unique Key**: `UK_<Table>_<Column>` (e.g., `UK_Customer_Email`)
- **Check Constraint**: `CK_<Table>_<Column>` (e.g., `CK_Employee_Age`)
- **Default Constraint**: `DF_<Table>_<Column>` (e.g., `DF_Customer_IsActive`)
- **Index**: `IX_<Table>_<Column>` (e.g., `IX_Customer_Email`)

---

## 3. Sequential Dual-Engine Pipeline Architecture

The architecture follows a **Phase-by-Phase Execution Pipeline**:

```
[Phase 1: Event Trigger]
           │
           ▼
[Phase 2: Deployment Mode (Actions / Webhook)]
           │
           ▼
[Phase 3: CLI Runner (src/main.py)]
           │
           ▼
[Phase 4: Deterministic Engine (sqlglot + sqlfluff)] ──(Syntax Error?)──► [Short-Circuit Exit]
           │
           ▼
[Phase 5: LLM Semantic Engine (LiteLLM + Pydantic)]
           │
           ▼
[Phase 6: Formatting & Publishing (Jinja2 + PyGithub)]
```

---

## 4. Comprehensive Tech Stack Specification

| Subsystem / Phase | Technologies Used | Key Responsibilities |
| :--- | :--- | :--- |
| **Event Trigger** | GitHub Actions (`pull_request`), Webhook POST | Detects `.sql` file updates in real-time. |
| **CLI Runner** | Python 3.12, `argparse`, `asyncio` | Environment-agnostic entrypoint (`src/main.py`). |
| **Deterministic Engine** | `sqlglot`, `sqlfluff`, `re` | Syntax parsing, AST traversal, casing & suffix enforcement (~5ms, $0 cost). |
| **Semantic Engine** | `LiteLLM`, `Pydantic v2`, Gemini 2.5 Flash / Claude | Evaluates domain abbreviations, entity correlations, logical sanity, and PR feedback formatting. |
| **Publishing & Aggregation** | `Jinja2`, `PyGithub`, `python-gitlab` | Merges findings, maps line numbers, posts inline GitHub PR comments. |
| **Deployment Layer** | Docker, `FastAPI`, `uvicorn`, GCP Cloud Run / AWS ECS | Centralized webhook container for multi-repo enterprise setups. |

---

## 5. Deployment Topologies

1. **GitHub Actions (CI-Native)**: Executes directly inside GitHub Actions workflow (`.github/workflows/sql-reviewer.yml`). Zero extra infrastructure cost.
2. **GitLab CI/CD**: Executes in `.gitlab-ci.yml` pipeline on Merge Requests.
3. **Centralized Webhook Microservice (Docker on Cloud)** ⭐ *Recommended for Enterprise*: Single FastAPI Docker container deployed to GCP Cloud Run / AWS ECS. Uses **1 Organization Webhook** to serve 100+ repositories with centralized secret management and single-place rule updates.
