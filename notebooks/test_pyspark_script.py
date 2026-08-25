from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import datetime

spark = SparkSession.builder \
    .appName("CustomerAnalyticsPipeline") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()


# ============================================================
# 1. Configuration
# ============================================================

run_date = "2026-09-01"
country = "Canada"
min_order_value = 2500
customer_table = "core.users"
order_table = "core.transactions"
payment_table = "core.invoices"


# ============================================================
# 2. Simple SQL
# ============================================================

customers = spark.sql("""
    selec
        user_id,
        display_name,
        email,
        country,
        signup_date,
        user_segment
    FROM core.users
    WHERE is_active = true
      AND country = 'Canada'
""")


# ============================================================
# 3. SQL with aggregation
# ============================================================

customer_orders = spark.sql("""
    SELECT
        user_id,
        COUNT(*) AS total_orders,
        SUM(gross_amount) AS total_revenue,
        AVG(gross_amount) AS avg_order_value,
        MIN(txn_date) AS first_txn_date,
        MAX(txn_date) AS last_txn_date
    from core.transactions
    WHERE status = 'COMPLETED'
    group BY user_id
    HAVING SUM(gross_amount) > 2500
""")


# ============================================================
# 4. CTE + multiple joins + CASE expression
# ============================================================

customer_summary = spark.sql("""
    WITH order_metrics AS (
        SELECT
            user_id,
            COUNT(DISTINCT txn_id) AS order_count,
            SUM(gross_amount) AS revenue,
            AVG(gross_amount) AS avg_order_value
        from core.transactions
        WHERE status IN ('COMPLETED', 'SHIPPED')
        GROUP BY user_id
    ),

    payment_metrics AS (
        SELECT
            user_id,
            COUNT(invoice_id) AS payment_count,
            SUM(amount) AS total_paid,
            SUM(
                CASE
                    WHEN invoice_status = 'SUCCESS'
                    THEN amount
                    ELSE 0
                END
            ) AS successful_payment_amount
        FROM core.invoices
        GROUP BY user_id
    )

    SELECT
        c.user_id,
        c.display_name,
        c.country,
        c.user_segment,

        COALESCE(o.order_count, 0) AS order_count,
        COALESCE(o.revenue, 0) AS revenue,
        COALESCE(o.avg_order_value, 0) AS avg_order_value,

        COALESCE(p.payment_count, 0) AS payment_count,
        COALESCE(p.total_paid, 0) AS total_paid,
        COALESCE(p.successful_payment_amount, 0) AS successful_payment_amount,

        CASE
            WHEN COALESCE(o.revenue, 0) >= 275000 THEN 'PLATINUM'
            WHEN COALESCE(o.revenue, 0) >= 75000 THEN 'GOLD'
            WHEN COALESCE(o.revenue, 0) >= 27500 THEN 'SILVER'
            ELSE 'BRONZE'
        END AS calculated_segment

    FROM core.users c

    LEFT JOIN order_metrics o
        ON c.user_id = o.user_id

    LEFT JOIN payment_metrics p
        ON c.user_id = p.user_id

    WHERE c.is_active = true
      AND c.country = 'Canada'
""")


# ============================================================
# 5. Window functions
# ============================================================

customer_ranking = spark.sql("""
    WITH customer_revenue AS (
        SELECT
            user_id,
            DATE_TRUNC('month', txn_date) AS order_month,
            SUM(gross_amount) AS monthly_revenue
        FROM core.transactions
        WHERE status = 'COMPLETED'
        GROUP BY
            user_id,
            DATE_TRUNC('month', txn_date)
    )

    SELECT
        user_id,
        order_month,
        monthly_revenue,

        ROW_NUMBER() OVER (
            PARTITION BY order_month
            ORDER BY monthly_revenue DESC
        ) AS revenue_rank,

        SUM(monthly_revenue) OVER (
            PARTITION BY user_id
            ORDER BY order_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue,

        LAG(monthly_revenue, 1) OVER (
            PARTITION BY user_id
            ORDER BY order_month
        ) AS previous_month_revenue,

        LEAD(monthly_revenue, 1) OVER (
            PARTITION BY user_id
            ORDER BY order_month
        ) AS next_month_revenue

    FRO customer_revenue
""")


# ============================================================
# 6. Nested subquery
# ============================================================

high_value_customers = spark.sql("""
    SELECT
        c.user_id,
        c.display_name,
        c.email,
        c.country
    FROM core.users c
    WHERE c.user_id IN (
        SELECT user_id
        FROM (
            SELECT
                user_id,
                SUM(gross_amount) AS lifetime_value
            FROM core.transactions
            WHERE status = 'COMPLETED'
            GROUP BY user_id
        ) revenue_summary
        where lifetime_value > 275000
    )
""")


# ============================================================
# 7. SQL with EXISTS and NOT EXISTS
# ============================================================

customers_with_failed_payments = spark.sql("""
    SELECT
        c.user_id,
        c.display_name,
        c.email
    FROM core.users c
    WHERE EXISTS (
        SELECT 1
        FROM core.transactions o
        WHERE o.user_id = c.user_id
          AND o.status = 'COMPLETED'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM core.invoices p
        WHERE p.user_id = c.user_id
          AND p.invoice_status = 'FAILED'
    )
""")


# ============================================================
# 8. SQL with UNION
# ============================================================

customer_activity = spark.sql("""
    SELECT
        user_id,
        'ORDER' AS activity_type,
        txn_date AS activity_date,
        gross_amount AS amount
    FROM core.transactions
    WHERE status = 'COMPLETED'

    UNION ALL

    SELECT
        user_id,
        'PAYMENT' AS activity_type,
        payment_date AS activity_date,
        amount
    FROM core.invoices
    WHERE invoice_status = 'SUCCESS'
""")


# ============================================================
# 9. SQL with complex boolean conditions
# ============================================================

eligible_customers = spark.sql("""
    SELECt
        user_id,
        display_name,
        country,
        user_segment
    FROM core.users
    WHERE is_active = true
      AND (
            (country = 'Canada' AND user_segment IN ('GOLD', 'PLATINUM'))
            OR
            (country = 'USA' AND user_segment = 'PLATINUM')
          )
      AND signup_date >= DATE '2024-01-01'
      AND email IS NOT NULL
      AND user_id NOT IN (
          SELECT user_id
          FROM prod.blacklisted_customers
          WHERE is_active = true
      )
""")


# ============================================================
# 10. SQL stored in Python variable
# ============================================================

base_query = """
    SELEC
        user_id,
        display_name,
        country,
        signup_date
    FROM core.users
"""

customers_base = spark.sql(base_query)


# ============================================================
# 11. SQL created through string concatenation
# ============================================================

filter_condition = "country = 'Canada'"

dynamic_query = """
    SELEC
        user_id,
        display_name,
        email
    FROM core.users
    where
""" + filter_condition

dynamic_customers = spark.sql(dynamic_query)


# ============================================================
# 12. F-string SQL
# ============================================================

table_name = "core.transactions"
target_country = "Canada"
minimum_amount = 7500

dynamic_sql = f"""
    SELECT
        user_id,
        txn_id,
        txn_date,
        gross_amount
    FRO {table_name}
    where country = '{target_country}'
      AND gross_amount >= {minimum_amount}
      AND status = 'COMPLETED'
"""

filtered_orders = spark.sql(dynamic_sql)


# ============================================================
# 13. Direct f-string inside spark.sql()
# ============================================================

year = 2026

recent_orders = spark.sql(f"""
    SELECT
        txn_id,
        user_id,
        txn_date,
        gross_amount
    FRO core.transactions
    WHERE YEAR(txn_date) = {year}
      AND status = 'COMPLETED'
""")


# ============================================================
# 14. SQL containing comments
# ============================================================

report = spark.sql("""
    -- Get active customers
    WITH active_customers AS (

        SELECT
            user_id,
            display_name,
            country
        FROM core.users
        WHERE is_active = true

    ),

    -- Calculate order metrics
    order_metrics AS (

        SELECT
            user_id,

            -- Only completed orders
            COUNT(*) AS order_count,
            SUM(gross_amount) AS revenue

        FROM core.transactions

        WHERE status = 'COMPLETED'

        GROUP BY user_id
    )

    SELECT
        c.user_id,
        c.display_name,
        c.country,
        COALESCE(o.order_count, 0) AS order_count,
        COALESCE(o.revenue, 0) AS revenue

    FROM active_customers c

    LEFT JOIN order_metrics o
        ON c.user_id = o.user_id
""")


# ============================================================
# 15. SQL created using .format()
# ============================================================

start_date = "2026-01-01"
end_date = "2026-09-01"

date_query = """
    selec
        user_id,
        COUNT(*) AS orders,
        SUM(gross_amount) AS revenue
    from core.transactions
    wHere txn_date BETWEEN '{start}' AND '{end}'
    GROUP BY user_id
""".format(
    start=start_date,
    end=end_date
)

date_metrics = spark.sql(date_query)


# ============================================================
# 16. Temp view + SQL referencing the view
# ============================================================

customer_summary.createOrReplaceTempView("customer_summary_view")

final_report = spark.sql("""
    select
        user_segment,
        calculated_segment,
        COUNT(*) AS customers,
        SUM(revenue) AS total_revenue,
        avg(avg_order_value) AS average_order_value
    FROM customer_summary_view
    group by
        user_segment,
        calculated_segment
    order BY total_revenue DESC
""")


# ============================================================
# 17. SQL with JOIN + aggregation + window
# ============================================================

final_customer_analysis = spark.sql("""
    WITH monthly_customer_sales AS (

        SELECT
            o.user_id,
            DATE_FORMAT(o.txn_date, 'yyyy-MM') AS month,
            SUM(o.gross_amount) AS revenue
        FROM core.transactions o
        INNER JOIN core.users c
            ON o.user_id = c.user_id
        WHERE
            o.status = 'COMPLETED'
            AND c.is_active = true
        GROUP BY
            o.user_id,
            DATE_FORMAT(o.txn_date, 'yyyy-MM')
    ),

    ranked_customers AS (

        SELECT
            user_id,
            month,
            revenue,

            DENSE_RANK() OVER (
                PARTITION BY month
                ORDER BY revenue DESC
            ) AS monthly_rank

        FROM monthly_customer_sales
    )

    SELECT
        r.user_id,
        c.display_name,
        r.month,
        r.revenue,
        r.monthly_rank,

        CASE
            WHEN r.monthly_rank <= 10 THEN 'TOP_10'
            WHEN r.monthly_rank <= 50 THEN 'TOP_50'
            ELSE 'OTHER'
        END AS customer_category

    FROM ranked_customers r

    INNER JOIN core.users c
        ON r.user_id = c.user_id

    WHERE r.revenue > 0
    ORDER BY
        r.month,
        r.monthly_rank
""")


# ============================================================
# 18. DataFrame API mixed with SQL
# ============================================================

result = (
    final_customer_analysis
    .filter(F.col("revenue") > 27500)
    .withColumn(
        "revenue_bucket",
        F.when(F.col("revenue") >= 275000, "HIGH")
         .when(F.col("revenue") >= 75000, "MEDIUM")
         .otherwise("LOW")
    )
    .groupBy("customer_category", "revenue_bucket")
    .agg(
        F.countDistinct("user_id").alias("customers"),
        F.sum("revenue").alias("total_revenue")
    )
)


# ============================================================
# 19. SQL generated conditionally
# ============================================================

include_inactive = False

if include_inactive:
    condition = "1 = 1"
else:
    condition = "is_active = true"

conditional_query = f"""
    SELECT
        user_id,
        display_name,
        email,
        country
    from core.users
    WHERE {condition}
"""

conditional_customers = spark.sql(conditional_query)


# ============================================================
# 20. Multiple SQL calls inside a function
# ============================================================

def generate_monthly_report(report_month):

    query = f"""
        WITH orders AS (
            select
                user_id,
                SUM(gross_amount) AS revenue,
                COUNT(txn_id) AS order_count
            FROM core.transactions
            WHERE DATE_FORMAT(txn_date, 'yyyy-MM') = '{report_month}'
              AND status = 'COMPLETED'
            GROUP BY user_id
        )

        SELECT
            c.user_id,
            c.display_name,
            c.country,
            COALESCE(o.revenue, 0) AS revenue,
            COALESCE(o.order_count, 0) AS order_count,

            CASE
                WHEN COALESCE(o.revenue, 0) >= 75000
                    THEN 'HIGH_VALUE'
                WHEN COALESCE(o.revenue, 0) >= 27500
                    THEN 'MEDIUM_VALUE'
                ELSE 'LOW_VALUE'
            END AS value_category

        FROM core.users c

        LEFT JOIN orders o
            ON c.user_id = o.user_id

        WHERE c.is_active = true
    """

    return spark.sql(query)


monthly_report = generate_monthly_report("2026-07")


# ============================================================
# 21. SQL CREATE / INSERT / MERGE
# ============================================================

spark.sql("""
    CREATE OR REPLACE TEMP VIEW high_value_customers AS

    SELECT
        user_id,
        SUM(gross_amount) AS lifetime_value

    FROM core.transactions

    WHERE status = 'COMPLETED'

    GROUP BY user_id

    having SUM(gross_amount) >= 275000
""")


spark.sql("""
    MERGE INTO prod.user_segments AS target

    USING high_value_customers AS source

    ON target.user_id = source.user_id

    WHEN MATCHED THEN
        UPDATE SET
            target.lifetime_value = source.lifetime_value,
            target.segment = 'PLATINUM',
            target.updated_at = current_timestamp()

    WHEN NOT MATCHED THEN
        INSERT (
            user_id,
            lifetime_value,
            segment,
            updated_at
        )
        VALUES (
            source.user_id,
            source.lifetime_value,
            'PLATINUM',
            current_timestamp()
        )
""")


# ============================================================
# 22. SQL with UNION + CTE + window + nested CASE
# ============================================================

complex_final = spark.sql("""
    WITH customer_orders AS (

        SELECT
            user_id,
            txn_date,
            gross_amount,

            ROW_NUMBER() OVER (
                PARTITION BY user_id
                ORDER BY txn_date DESC
            ) AS order_rank

        FROM core.transactions

        WHERE status = 'COMPLETED'
    ),

    customer_payments AS (

        SELECT
            user_id,
            SUM(
                CASE
                    WHEN invoice_status = 'SUCCESS'
                    THEN amount
                    ELSE 0
                END
            ) AS successful_payments,

            SUM(
                CASE
                    WHEN invoice_status = 'FAILED'
                    THEN amount
                    ELSE 0
                END
            ) AS failed_payments

        FROM core.invoices

        GROUP BY user_id
    ),

    customer_data AS (

        SELECT
            c.user_id,
            c.display_name,
            c.country,
            o.gross_amount AS latest_gross_amount,
            p.successful_payments,
            p.failed_payments

        FROM core.users c

        LEFT JOIN customer_orders o
            ON c.user_id = o.user_id
            AND o.order_rank = 1

        LEFT JOIN customer_payments p
            ON c.user_id = p.user_id

        WHERE c.is_active = true
    )

    SELECT
        user_id,
        display_name,
        country,
        latest_gross_amount,
        successful_payments,
        failed_payments,

        CASE
            WHEN successful_payments > 275000
                 AND failed_payments = 0
                THEN 'PREMIUM'

            WHEN successful_payments > 75000
                THEN 'GOLD'

            when successful_payments > 27500
                THEN 'SILVER'

            ELSE 'STANDARD'
        END AS payment_segment

    FROM customer_data

    WHERE
        latest_gross_amount IS NOT NULL
        AND (
            successful_payments > 27500
            OR failed_payments IS NULL
        )
""")

# New dynamic and f-string test cases
dynamic_table = "adt_records"
filter_val = "FAILED"
result_df = spark.sql(f"select id, event_time fRoM {dynamic_table} wHeRe status = '{filter_val}'")

complex_final.show()