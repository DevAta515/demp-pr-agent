-- Common Database Queries

-- 1. Fetch user profile with total order counts and total spending
SELECT 
    u.user_id,
    u.username,
    u.email,
    COUNT(o.order_id) AS total_orders,
    COALESCE(SUM(o.total_amount), 0.00) AS total_spent
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
GROUP BY u.user_id, u.username, u.email
ORDER BY total_spent DESC;

-- 2. Find top 5 selling products by revenue with category details
SELECT 
    p.product_id,
    p.name AS product_name,
    c.name AS category_name,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.quantity * oi.unit_price) AS total_revenue
FROM products p
LEFT JOIN categories c ON p.category_id = c.category_id
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name, c.name
ORDER BY total_revenue DESC
LIMIT 5;

-- 3. Get monthly revenue breakdown
SELECT 
    DATE_TRUNC('month', created_at) AS month,
    COUNT(order_id) AS order_count,
    SUM(total_amount) AS monthly_revenue,
    AVG(total_amount) AS average_order_value
FROM orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;

-- 4. Recent pending orders with user contact info
SELECT 
    o.order_id,
    u.username,
    u.email,
    o.total_amount,
    o.created_at
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'pending'
ORDER BY o.created_at ASC;

-- 5. Products low on stock (less than 10 units remaining)
SELECT 
    p.product_id,
    p.name AS product_name,
    c.name AS category_name,
    p.stock_quantity,
    p.price
FROM products p
LEFT JOIN categories c ON p.category_id = c.category_id
WHERE p.stock_quantity < 10
ORDER BY p.stock_quantity ASC;
