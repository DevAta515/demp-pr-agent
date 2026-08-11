"""
SQLGlot Demo Script
Demonstrates AST parsing, table/column extraction, syntax error detection, and dialect transpilation.
"""

import sqlglot
from sqlglot import exp

# Valid SQL query for AST inspection
VALID_SQL = "SELECT u.user_id, u.Email, o.amount FROM users AS u LEFT JOIN orders AS o ON u.user_id = o.user_id WHERE u.status = 'active'"

# Invalid SQL query with syntax errors (trailing comma, missing closing paren)
INVALID_SQL = "SELECT user_id, email, FROM users WHERE (status = 'active'"

# Postgres SQL for transpilation demo
POSTGRES_SQL = "SELECT user_id, created_at::DATE FROM users WHERE email ILIKE '%@gmail.com' LIMIT 10"


def demo_ast_parsing():
    print("=" * 60)
    print(" 1. DEMO: AST PARSING & METADATA EXTRACTION")
    print("=" * 60)
    print("\n[Input SQL]:\n", VALID_SQL)

    # Parse SQL into AST Tree
    expression = sqlglot.parse_one(VALID_SQL)

    # Extract tables and columns
    tables = [table.name for table in expression.find_all(exp.Table)]
    columns = [column.name for column in expression.find_all(exp.Column)]

    print("\n[Extracted Metadata]:")
    print(f" • Tables referenced:  {list(set(tables))}")
    print(f" • Columns referenced: {list(set(columns))}")
    print(f"\n[AST Tree Representation]:\n{repr(expression)}")


def demo_syntax_error_detection():
    print("\n" + "=" * 60)
    print(" 2. DEMO: SYNTAX ERROR DETECTION")
    print("=" * 60)
    print("\n[Invalid SQL Input]:\n", INVALID_SQL)

    try:
        sqlglot.parse_one(INVALID_SQL)
    except sqlglot.errors.ParseError as e:
        print("\n[Caught ParseError Details]:")
        for err in e.errors:
            print(f" • Line {err['line']}, Col {err['col']}: {err['description']} (near '{err['highlight']}')")


def demo_transpilation():
    print("\n" + "=" * 60)
    print(" 3. DEMO: DIALECT TRANSPILATION (Postgres -> Snowflake)")
    print("=" * 60)
    print("\n[Postgres Input SQL]:\n", POSTGRES_SQL)

    # Transpile Postgres SQL to Snowflake SQL
    snowflake_sql = sqlglot.transpile(POSTGRES_SQL, read="postgres", write="snowflake")[0]
    print("\n[Transpiled Snowflake SQL]:\n", snowflake_sql)


def main():
    demo_ast_parsing()
    demo_syntax_error_detection()
    demo_transpilation()


if __name__ == "__main__":
    main()
