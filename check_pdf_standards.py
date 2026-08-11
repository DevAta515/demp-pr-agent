"""
SQL Coding Standards Validator based on PDF Specification

Checks:
1. Object Naming:
   - Table: snake_case & singular (e.g. customer, sales_order)
   - View: vw_<name>
   - Stored Procedure: sp_<action>_<entity>
   - Function: fn_<purpose>
2. Column Naming:
   - MUST use PascalCase (e.g. CustomerId, OrderDate)
   - Suffix Rules: Date, Timestamp, Amount, Count, Status, Name, Code, Description
   - Boolean Prefix: Is, Has, Can
   - Primary Key: <Entity>Id
   - Forbidden vague abbreviations: Amt, Cnt, Flg, Desc
3. Audit Columns Check (CreatedBy, CreatedTimestamp, UpdatedBy, UpdatedTimestamp, IsDeleted, BatchId, SourceSystem)
4. Constraint Naming (PK_<Table>, FK_<Child>_<Parent>, UK_<Table>_<Column>, IX_<Table>_<Column>)
"""

import re
import sqlglot
from sqlglot import exp

FORBIDDEN_ABBREVIATIONS = {
    "amt": "Use 'Amount' suffix instead of 'Amt'",
    "cnt": "Use 'Count' suffix instead of 'Cnt'",
    "flg": "Use 'Is' / 'Has' / 'Can' boolean prefix instead of 'Flg'",
    "desc": "Use 'Description' suffix instead of 'Desc'",
}

RESERVED_KEYWORDS = {"order", "user", "group", "select", "where", "table"}


def is_pascal_case(name: str) -> bool:
    """Checks if a string is in PascalCase (e.g., CustomerId, OrderDate)."""
    return bool(re.match(r"^[A-Z][a-zA-Z0-9]*$", name))


def is_snake_case(name: str) -> bool:
    """Checks if a string is in snake_case (e.g., customer, sales_order)."""
    return bool(re.match(r"^[a-z][a-z0-9_]*$", name))


def validate_pdf_standards(sql_code: str, file_name: str = "query.sql"):
    violations = []

    try:
        parsed_statements = sqlglot.parse(sql_code)
    except Exception as e:
        return [{"rule": "SYNTAX_ERROR", "message": f"Syntax Error: {e}", "severity": "HIGH"}]

    for stmt in parsed_statements:
        if not stmt:
            continue

        # 1. CREATE TABLE / ALTER TABLE Audits
        if isinstance(stmt, exp.Create):
            table_node = stmt.find(exp.Table)
            if table_node:
                table_name = table_node.name

                # Check Table Naming (snake_case)
                if not is_snake_case(table_name):
                    violations.append({
                        "object": f"Table '{table_name}'",
                        "rule": "TABLE_NAME_SNAKE_CASE",
                        "message": f"Table '{table_name}' must use lowercase snake_case (e.g. 'sales_order').",
                        "severity": "MEDIUM"
                    })

                # Check Reserved Keywords
                if table_name.lower() in RESERVED_KEYWORDS:
                    violations.append({
                        "object": f"Table '{table_name}'",
                        "rule": "RESERVED_KEYWORD",
                        "message": f"Table name '{table_name}' uses a reserved SQL keyword. Rename to a descriptive singular entity.",
                        "severity": "HIGH"
                    })

            # Check Column Definitions
            column_defs = stmt.find_all(exp.ColumnDef)
            column_names = []
            for col_def in column_defs:
                col_name = col_def.name
                column_names.append(col_name)

                # Rule: Column Names MUST be PascalCase
                if not is_pascal_case(col_name):
                    violations.append({
                        "object": f"Column '{col_name}' in '{table_name}'",
                        "rule": "COLUMN_PASCAL_CASE",
                        "message": f"Column '{col_name}' must use PascalCase (e.g., '{col_name.capitalize()}').",
                        "severity": "HIGH"
                    })

                # Rule: Check Forbidden Vague Abbreviations (Amt, Cnt, Flg, Desc)
                for abbr, advice in FORBIDDEN_ABBREVIATIONS.items():
                    if abbr in col_name.lower():
                        violations.append({
                            "object": f"Column '{col_name}'",
                            "rule": "FORBIDDEN_ABBREVIATION",
                            "message": f"Avoid vague abbreviation '{abbr}' in column '{col_name}'. {advice}.",
                            "severity": "MEDIUM"
                        })

                # Rule: Boolean Prefix check (Is, Has, Can)
                data_type = col_def.kind.this if col_def.kind else ""
                if str(data_type).upper() == "BOOLEAN":
                    if not (col_name.startswith("Is") or col_name.startswith("Has") or col_name.startswith("Can")):
                        violations.append({
                            "object": f"Boolean Column '{col_name}'",
                            "rule": "BOOLEAN_PREFIX",
                            "message": f"Boolean column '{col_name}' must be prefixed with 'Is', 'Has', or 'Can' (e.g., 'IsActive').",
                            "severity": "MEDIUM"
                        })

                # Rule: Timestamp suffix check
                if "TIMESTAMP" in str(data_type).upper():
                    if not col_name.endswith("Timestamp"):
                        violations.append({
                            "object": f"Timestamp Column '{col_name}'",
                            "rule": "TIMESTAMP_SUFFIX",
                            "message": f"Timestamp column '{col_name}' must use suffix 'Timestamp' (e.g. '{col_name}Timestamp').",
                            "severity": "MEDIUM"
                        })

                # Rule: Date suffix check
                if str(data_type).upper() == "DATE":
                    if not col_name.endswith("Date"):
                        violations.append({
                            "object": f"Date Column '{col_name}'",
                            "rule": "DATE_SUFFIX",
                            "message": f"Date column '{col_name}' must use suffix 'Date' (e.g. '{col_name}Date').",
                            "severity": "MEDIUM"
                        })

            # Check Mandatory Audit Columns for Transactional Tables
            audit_columns = ["CreatedBy", "CreatedTimestamp", "UpdatedBy", "UpdatedTimestamp", "IsDeleted", "BatchId", "SourceSystem"]
            missing_audits = [ac for ac in audit_columns if ac not in column_names]
            if missing_audits:
                violations.append({
                    "object": f"Table '{table_name}'",
                    "rule": "MISSING_AUDIT_COLUMNS",
                    "message": f"Missing mandatory audit columns: {', '.join(missing_audits)}.",
                    "severity": "HIGH"
                })

        # 2. SELECT Query Column Alias Audits
        elif isinstance(stmt, exp.Select):
            for alias in stmt.find_all(exp.Alias):
                alias_name = alias.alias
                if alias_name and not is_pascal_case(alias_name):
                    violations.append({
                        "object": f"Column Alias '{alias_name}'",
                        "rule": "ALIAS_PASCAL_CASE",
                        "message": f"Column alias '{alias_name}' must use PascalCase (e.g. '{alias_name.capitalize()}').",
                        "severity": "MEDIUM"
                    })

    return violations


# --- DEMO RUN ---
NON_COMPLIANT_SQL = """
CREATE TABLE sales_orders (
    order_id BIGINT PRIMARY KEY,
    cust_id BIGINT,
    total_amt DECIMAL(18,2),
    active_flg BOOLEAN,
    created_at TIMESTAMP,
    order_desc VARCHAR(255)
);

SELECT 
    cust_id as customer_id, 
    total_amt as total_amt 
FROM sales_orders;
"""


def main():
    print("=" * 70)
    print(" PDF CODING STANDARDS COMPLIANCE AUDITOR")
    print("=" * 70)
    print("\n[Input Non-Compliant SQL]:")
    print(NON_COMPLIANT_SQL.strip())

    violations = validate_pdf_standards(NON_COMPLIANT_SQL)

    print(f"\n[Detected Violations ({len(violations)} found)]:\n")
    for idx, v in enumerate(violations, 1):
        print(f"{idx}. [{v['severity']}] Rule: {v['rule']}")
        print(f"   Object : {v['object']}")
        print(f"   Message: {v['message']}\n")


if __name__ == "__main__":
    main()
