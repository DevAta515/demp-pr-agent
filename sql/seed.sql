-- Initial Seed Data for Testing and Development

-- Insert Categories
INSERT INTO categories (category_id, name, description) VALUES
(1, 'Electronics', 'Gadgets, devices, and electronic accessories'),
(2, 'Apparel', 'Clothing, footwear, and wearable fashion items'),
(3, 'Home & Kitchen', 'Home appliances, cookware, and living space essentials')
ON CONFLICT (category_id) DO NOTHING;

-- Insert Users
INSERT INTO users (user_id, username, email, password_hash, is_active) VALUES
(1, 'alice_smith', 'alice@example.com', '$2b$12$eImiTXuWVxfM37uY4JANjO98S/r6.kG0q8oJ', TRUE),
(2, 'bob_jones', 'bob@example.com', '$2b$12$k8Y09.XN1eM9u.kU8oM4Y.72y3J94O7s6nS', TRUE),
(3, 'charlie_brown', 'charlie@example.com', '$2b$12$L9p17xM0O7K2.nJ4p6M8u.11x0P8R5u1m', FALSE)
ON CONFLICT (user_id) DO NOTHING;

-- Insert Products
INSERT INTO products (product_id, category_id, name, description, price, stock_quantity) VALUES
(1, 1, 'Wireless Headphones', 'Noise-canceling over-ear bluetooth headphones', 149.99, 25),
(2, 1, 'Smart Watch v2', 'Fitness tracker with heart rate monitor and GPS', 199.50, 5),
(3, 2, 'Cotton Hoodie', 'Premium heavyweight fleece pullover hoodie', 49.99, 50),
(4, 3, 'Espresso Machine', 'Compact stainless steel espresso and cappuccino maker', 129.00, 3)
ON CONFLICT (product_id) DO NOTHING;

-- Insert Orders
INSERT INTO orders (order_id, user_id, total_amount, status, created_at) VALUES
(101, 1, 199.98, 'completed', NOW() - INTERVAL '10 days'),
(102, 2, 199.50, 'completed', NOW() - INTERVAL '5 days'),
(103, 1, 49.99, 'pending', NOW() - INTERVAL '1 day')
ON CONFLICT (order_id) DO NOTHING;

-- Insert Order Items
INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price) VALUES
(1, 101, 1, 1, 149.99),
(2, 101, 3, 1, 49.99),
(3, 102, 2, 1, 199.50),
(4, 103, 3, 1, 49.99)
ON CONFLICT (order_item_id) DO NOTHING;

-- Insert Reviews
INSERT INTO reviews (review_id, product_id, user_id, rating, comment) VALUES
(1, 1, 1, 5, 'Great sound quality and battery life!'),
(2, 2, 2, 4, 'Very helpful for workout tracking.'),
(3, 3, 1, 5, 'Super soft and comfortable fit.')
ON CONFLICT (review_id) DO NOTHING;
