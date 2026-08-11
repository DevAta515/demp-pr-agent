# Multi-Dialect SQL PR Reviewer Agent
## Implementation & Validation Guide

---

## 1. Overview

This document provides the practical implementation details, AST capabilities, LLM prompt engineering guidelines, and local/CI verification procedures for the **SQL PR Reviewer Agent**.

---

## 2. Engine 1: Deterministic AST Implementation (`check_pdf_standards.py`)

The deterministic engine utilizes `sqlglot` to parse SQL queries into an Abstract Syntax Tree (AST), enforcing ~80% of PDF coding rules deterministically without invoking the LLM.

### Key Validation Logic:
1. **Syntax Validation**: Parses SQL with `sqlglot.parse()`. If `ParseError` occurs, execution short-circuits immediately.
2. **Table Naming**: Enforces lowercase `snake_case` on `exp.Table` nodes.
3. **Column Naming**: Enforces `PascalCase` on `exp.ColumnDef` nodes.
4. **DataType Suffixes**:
   - `DATE` $\rightarrow$ must end with `Date`
   - `TIMESTAMP` $\rightarrow$ must end with `Timestamp`
   - `BOOLEAN` $\rightarrow$ must start with `Is`, `Has`, or `Can`
5. **Forbidden Abbreviations**: Flags explicit vague substrings (`Amt`, `Cnt`, `Flg`, `Desc`).
6. **Audit Columns**: Verifies presence of all 7 required transactional audit columns (`CreatedBy`, `CreatedTimestamp`, `UpdatedBy`, `UpdatedTimestamp`, `IsDeleted`, `BatchId`, `SourceSystem`).

---

## 3. AST Capability Showcase (`demo_complex_ast.py`)

SQLGlot provides built-in, native tree traversal methods (`ast.find_all(...)`) that extract schema elements, CTEs, Window functions, JSON path extractions, Foreign Keys, and Constraints with minimal logic code.

### Minimal Native AST Extraction Code:
```python
import sqlglot
from sqlglot import exp

ast = sqlglot.parse_one(sql_query, read="postgres")

# 1. Extract Referenced Tables & Columns
tables = list(set(t.name for t in ast.find_all(exp.Table)))
columns = list(set(c.name for c in ast.find_all(exp.Column)))

# 2. Extract Defined CTEs
ctes = list(set(cte.alias for cte in ast.find_all(exp.CTE)))

# 3. Extract Foreign Keys (Native AST)
foreign_keys = [fk.sql() for fk in ast.find_all(exp.ForeignKey)]

# 4. Extract All Constraints (Primary Key, Unique, Check, Default)
constraints = [c.sql() for c in ast.find_all((exp.Constraint, exp.ColumnConstraint))]
```

---

## 4. Engine 2: LLM Semantic Engine & Prompt Engineering

The LLM receives raw SQL diffs **enriched with AST metadata** extracted by Engine 1. 

### LLM System Prompt Rules & Guardrails:
```markdown
You are a Senior Principal Data Architect evaluating SQL Pull Requests.
Your job is to perform a semantic code review based on the provided SQL query and AST metadata.

### Rules & Guidelines:
1. DETERMINISTIC FILTERING:
   - Engine 1 (AST Parser) has already checked syntax, casing conventions (PascalCase/snake_case), 
     and mandatory audit columns. DO NOT re-flag basic casing or syntax errors.

2. ABBREVIATION AUDIT:
   - ACCEPT industry standard acronyms: [SKU, URL, UUID, VAT, ISO, IP, JSON, API, SSN].
   - REJECT obscure custom abbreviations (e.g., 'cust_dtl', 'ord_mstr'). Suggest full names.

3. ENTITY & RELATIONSHIP CORRELATION:
   - Verify Foreign Keys logically correlate with target entities (e.g. CustomerId -> customer table).
   - Ensure CTE names describe their computation (flag 'cte1', 'temp_tbl').

4. LOGICAL SANITY CHECKS:
   - Flag potential logical bugs (e.g. joining user_id to order_id, redundant DISTINCT on primary keys).

5. OUTPUT FORMAT:
   - Return Pydantic-validated JSON containing findings, severity levels, line numbers, and suggested diffs.
```

---

## 5. Local Execution & Verification Guide

### A. Run Deterministic PDF Auditor Demo
```bash
# Activate virtual environment
source venv/bin/activate

# Execute PDF standards compliance check
python3 check_pdf_standards.py
```

### B. Run AST Metadata & Constraint Parsing Demo
```bash
python3 demo_complex_ast.py
```

### C. Run Agent CLI on a Pull Request (Local Terminal)
```bash
export GITHUB_TOKEN="ghp_your_github_token"
export GEMINI_API_KEY="your_gemini_api_key"

python -m src.main \
  --pr-url https://github.com/my-org/my-sql-repo/pull/42 \
  --dialect postgres
```

### D. Run Centralized Webhook Container (Docker)
```bash
# Build Docker container
docker build -t sql-pr-reviewer:latest .

# Run container locally
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="your_key" \
  -e WEBHOOK_SECRET="your_secret" \
  sql-pr-reviewer:latest
```
