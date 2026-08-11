"""
Complex AST Parsing & Syntax Error Demo using SQLGlot
"""

import sqlglot
from sqlglot import exp

# 1. Complex PostgreSQL Query (CTE, Window Function, JSON Extraction, Type Casting)
POSTGRES_COMPLEX_SQL = """
WITH monthly_user_stats AS (
    SELECT 
        u.user_id,
        u.email,
        payload->>'region' AS region,
        COUNT(o.order_id) AS total_orders,
        SUM(o.amount)::NUMERIC(10,2) AS total_spent,
        ROW_NUMBER() OVER (PARTITION BY payload->>'region' ORDER BY SUM(o.amount) DESC) AS rank_in_region
    FROM users AS u
    LEFT JOIN orders AS o ON u.user_id = o.user_id
    WHERE u.created_at >= '2024-01-01' AND u.status = 'active'
    GROUP BY u.user_id, u.email, payload->>'region'
    HAVING COUNT(o.order_id) > 2
)
SELECT 
    user_id, 
    email, 
    region, 
    total_spent 
FROM monthly_user_stats 
WHERE rank_in_region <= 3
ORDER BY region ASC, total_spent DESC;
"""

# 2. Complex Snowflake Query (CTE, QUALIFY clause, JSON path notation)
SNOWFLAKE_COMPLEX_SQL = """
WITH high_value_orders AS (
    SELECT 
        o.order_id,
        o.user_id,
        o.raw_payload:shipping.city::STRING AS shipping_city,
        o.amount,
        ROW_NUMBER() OVER (PARTITION BY o.user_id ORDER BY o.amount DESC) AS rn
    FROM analytics.orders AS o
    WHERE o.created_at >= DATEADD('month', -6, CURRENT_DATE())
    QUALIFY rn = 1
)
SELECT 
    h.user_id,
    h.shipping_city,
    h.amount
FROM high_value_orders AS h
ORDER BY h.amount DESC;
"""

# 3. DDL Query with Foreign Keys & Constraints
CREATE_TABLE_CONSTRAINTS_SQL = """
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    amount NUMERIC(10,2) CHECK (amount > 0),
    status VARCHAR(50) DEFAULT 'pending',
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT unique_user_order UNIQUE (user_id, order_id)
);
"""

# 4. Query with an intentional Syntax Error (trailing comma after email & missing closing paren)
SYNTAX_ERROR_SQL = """
WITH broken_cte AS (
    SELECT user_id, email, FROM users WHERE (status = 'active'
)
SELECT * FROM broken_cte;
"""


def print_ast(title: str, dialect: str, sql: str):
    print("=" * 70)
    print(f" {title} (Dialect: {dialect.upper()})")
    print("=" * 70)
    print("\n[Input SQL Query]:\n", sql.strip())

    try:
        ast = sqlglot.parse_one(sql, read=dialect)
        
        # Extract Metadata using AST Nodes
        tables = list(set(table.name for table in ast.find_all(exp.Table)))
        columns = list(set(column.name for column in ast.find_all(exp.Column)))
        ctes = list(set(cte.alias for cte in ast.find_all(exp.CTE)))
        
        # Foreign Keys & Constraints (natively extracted from AST with minimal logic code)
        foreign_keys = [fk.sql() for fk in ast.find_all(exp.ForeignKey)]
        constraints = [c.sql() for c in ast.find_all((exp.Constraint, exp.ColumnConstraint))]

        # Detailed JOIN Inspection
        join_details = []
        for j in ast.find_all(exp.Join):
            side = j.args.get("side", "") or "INNER"
            joined_table = j.this.name if hasattr(j.this, 'name') else str(j.this)
            on_clause = j.args.get("on").sql() if j.args.get("on") else "None"
            join_details.append(f"{side} JOIN {joined_table} ON {on_clause}")

        # Token Casing Check for JOIN keywords in raw query
        join_keyword_casings = []
        tokens = sqlglot.tokenize(sql, read=dialect)
        for token in tokens:
            if token.text.upper() in ("JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS"):
                join_keyword_casings.append(f"'{token.text}' (is_uppercase={token.text.isupper()})")

        print("\n[Extracted AST Metadata]:")
        print(f" • Referenced Tables : {tables}")
        print(f" • Referenced Columns: {columns}")
        print(f" • Defined CTEs      : {ctes}")
        print(f" • Detailed JOINs    : {join_details if join_details else 'None'}")
        print(f" • JOIN Keyword Casing: {join_keyword_casings if join_keyword_casings else 'None'}")
        print(f" • Foreign Keys      : {foreign_keys if foreign_keys else 'None'}")
        print(f" • Constraints       : {constraints if constraints else 'None'}")

        print("\n[AST Tree Output (repr)]:\n")
        print(repr(ast))
    except sqlglot.errors.ParseError as e:
        print("\n[AST ParseError Output]:\n")
        for err in e.errors:
            print(f" • Line {err['line']}, Col {err['col']}: {err['description']} (near '{err['highlight']}')")


def main():
    print_ast("1. COMPLEX POSTGRESQL QUERY", "postgres", POSTGRES_COMPLEX_SQL)
    print("\n" + "#" * 70 + "\n")
    print_ast("2. COMPLEX SNOWFLAKE QUERY", "snowflake", SNOWFLAKE_COMPLEX_SQL)
    print("\n" + "#" * 70 + "\n")
    print_ast("3. DDL QUERY WITH CONSTRAINTS", "postgres", CREATE_TABLE_CONSTRAINTS_SQL)
    print("\n" + "#" * 70 + "\n")
    print_ast("4. QUERY WITH SYNTAX ERROR", "postgres", SYNTAX_ERROR_SQL)


if __name__ == "__main__":
    main()

