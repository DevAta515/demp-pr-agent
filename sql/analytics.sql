-- Advanced Analytics Queries (CTEs & Window Functions)

-- 1. Customer Retention & Repeat Purchase Analysis using CTE
WITH UserOrderCounts AS (
    SELECT 
        user_id,
        COUNT(order_id) AS order_count,
        MIN(created_at) AS first_order_date,
        MAX(created_at) AS last_order_date
    FROM orders
    GROUP BY user_id
)
SELECT 
    CASE 
        WHEN order_count = 1 THEN 'One-time Customer'
        WHEN order_count BETWEEN 2 AND 5 THEN 'Repeat Customer'
        ELSE 'Loyal Customer'
    END AS customer_segment,
    COUNT(user_id) AS total_customers,
    ROUND(AVG(order_count), 2) AS avg_orders_per_customer
FROM UserOrderCounts
GROUP BY customer_segment
ORDER BY total_customers DESC;

-- 2. User Spending Rank and Running Total using Window Functions
SELECT 
    user_id,
    order_id,
    created_at,
    total_amount,
    SUM(total_amount) OVER (
        PARTITION BY user_id 
        ORDER BY created_at
    ) AS running_total_spent,
    DENSE_RANK() OVER (
        ORDER BY total_amount DESC
    ) AS highest_order_rank
FROM orders
WHERE status = 'completed';

-- 3. Month-over-Month Revenue Growth Percentage
WITH MonthlySales AS (
    SELECT 
        DATE_TRUNC('month', created_at) AS sales_month,
        SUM(total_amount) AS total_sales
    FROM orders
    WHERE status = 'completed'
    GROUP BY DATE_TRUNC('month', created_at)
)
SELECT 
    sales_month,
    total_sales,
    LAG(total_sales, 1) OVER (ORDER BY sales_month) AS previous_month_sales,
    ROUND(
        (total_sales - LAG(total_sales, 1) OVER (ORDER BY sales_month)) 
        / NULLIF(LAG(total_sales, 1) OVER (ORDER BY sales_month), 0) * 100, 
        2
    ) AS mom_growth_percentage
FROM MonthlySales
ORDER BY sales_month DESC;

-- 4. Cohort Retention Analysis by User Signup Month
WITH UserCohorts AS (
    SELECT 
        user_id,
        DATE_TRUNC('month', created_at) AS cohort_month
    FROM users
),
UserActivity AS (
    SELECT 
        o.user_id,
        c.cohort_month,
        DATE_TRUNC('month', o.created_at) AS activity_month,
        (EXTRACT(YEAR FROM o.created_at) - EXTRACT(YEAR FROM c.cohort_month)) * 12 + 
        (EXTRACT(MONTH FROM o.created_at) - EXTRACT(MONTH FROM c.cohort_month)) AS month_number
    FROM orders o
    JOIN UserCohorts c ON o.user_id = c.user_id
    WHERE o.status = 'completed'
)
SELECT 
    cohort_month,
    month_number,
    COUNT(DISTINCT user_id) AS active_users
FROM UserActivity
GROUP BY cohort_month, month_number
ORDER BY cohort_month ASC, month_number ASC;
