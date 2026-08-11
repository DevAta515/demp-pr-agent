"""
SQLFluff Demo Script
Demonstrates linting SQL for casing/formatting violations and auto-fixing code.
"""

from sqlfluff.core import Linter, FluffConfig
import sqlfluff

# Sample messy SQL query with lowercase keywords, missing aliases, and formatting issues
MESSY_SQL = """
select u.user_id, u.first_name, u.email, count(o.id) as total_orders
from users u
left join orders o on u.user_id = o.user_id
where u.status = 'active' and u.created_at >= '2024-01-01'
group by 1, 2, 3
having count(o.id) > 5
order by total_orders desc
"""

def main():
    print("=" * 60)
    print(" 1. DEMO: LINTING SQL WITH SQLFLUFF")
    print("=" * 60)
    print("\n[Original Messy SQL]:")
    print(MESSY_SQL)

    # Configure Linter for Postgres dialect with Casing Rules (L010 = Keyword Casing, L030 = Capitalisation of function names)
    config = FluffConfig(overrides={"dialect": "postgres", "rules": "L010,L030"})
    linter = Linter(config=config)

    # Lint the SQL string
    result = linter.lint_string(MESSY_SQL)
    violations = result.get_violations()

    print(f"\n[Detected Violations ({len(violations)} found)]:")
    print("-" * 60)
    for v in violations:
        print(f" • Line {v.line_no:2d}, Col {v.line_pos:2d} | Rule [{v.rule_code()}]: {v.description}")

    print("\n" + "=" * 60)
    print(" 2. DEMO: AUTO-FIXING SQL WITH SQLFLUFF")
    print("=" * 60)

    # Fix casing and formatting automatically
    fixed_sql = sqlfluff.fix(MESSY_SQL, dialect="postgres")
    
    print("\n[Auto-Fixed SQL Result]:")
    print("-" * 60)
    print(fixed_sql)

if __name__ == "__main__":
    main()
