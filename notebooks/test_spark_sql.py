# test_spark_sql.py
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# 1. Valid SQL (RULE-001 passed)
spark.sql("SELECT * FROM customer_table")

# 2. Invalid SQL (RULE-001 casing violation: select/from)
spark.sql("select * from customer_table")

# 3. Invalid SQL with descriptive naming violation (RULE-002 check via LLM: alias is cust)
query_var = "SELECT name AS cust FROM customer_table ORDER BY cust_id"
spark.sql(query_var)

# 4. Dynamic query using variable assignment and f-string (with lowercase 'select')
tbl = "orders"
query_fstring = f"select order_id, amt FROM {tbl}"
spark.sql(query_fstring)

# 5. Dynamic query using format() (with lowercase 'where')
query_format = "SELECT * FROM sales where region = '{}'".format("North")
spark.sql(query_format)

# 6. Dynamic query built conditionally (Demonstrating AST static limit)
# Note: Static AST will only resolve the initial variable content
query_conditional = "SELECT txn_id, dt FROM transactions"
if True:
    query_conditional += " WHERE amt > 100"
spark.sql(query_conditional)

# 7. Complex SQL Query (CTEs, JOINs, WINDOW functions with lowercase 'over', 'partition by')
complex_query = """
WITH user_activity AS (
    SELECT 
        user_id,
        action,
        timestamp,
        ROW_NUMBER() over (partition by user_id ORDER BY timestamp DESC) as rn
    FROM events
)
SELECT 
    u.user_id,
    u.name,
    a.action
FROM users u
LEFT JOIN user_activity a ON u.user_id = a.user_id
WHERE a.rn = 1
"""
spark.sql(complex_query)
# 8. Query with multiple cryptic short forms (RULE-002 check: cust, amt, qty, dt)
spark.sql("SELECT cust_id as cust, txn_amt as amt, order_qty as qty, txn_dt as dt FROM orders")
