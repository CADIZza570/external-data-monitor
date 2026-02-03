-- 🦈 SEED PRODUCTION QUICK - SQL Directo
-- Ejecutar vía Railway shell: sqlite3 webhooks.db < seed_production_quick.sql

-- Insertar productos Columbus
INSERT OR REPLACE INTO products (product_id, name, sku, stock, price, cost_price, velocity_daily, total_sales_30d, category, shop, last_updated, last_sale_date)
VALUES
('WINTER-001', 'Chaqueta Térmica Winter Pro', 'JACKET-WINTER-01', 12, 189.99, 95.00, 3.2, 96, 'A', 'columbus-shop', datetime('now'), datetime('now', '-1 day')),
('WINTER-002', 'Boots Waterproof Premium', 'BOOTS-WP-01', 8, 159.99, 80.00, 2.8, 84, 'A', 'columbus-shop', datetime('now'), datetime('now', '-1 day')),
('WINTER-003', 'Guantes Térmicos Arctic', 'GLOVES-ARC-01', 25, 45.99, 18.00, 4.5, 135, 'A', 'columbus-shop', datetime('now'), datetime('now', '-1 day')),
('WINTER-004', 'Bufanda Lana Merino', 'SCARF-WOOL-01', 40, 39.99, 15.00, 1.8, 54, 'B', 'columbus-shop', datetime('now'), datetime('now', '-1 day')),
('WINTER-005', 'Gorro Térmico Fleece', 'HAT-FLEECE-01', 60, 29.99, 10.00, 2.1, 63, 'B', 'columbus-shop', datetime('now'), datetime('now', '-1 day'));

-- Verificar insert
SELECT 'Productos insertados:' as status, COUNT(*) as count FROM products WHERE shop='columbus-shop';
SELECT '✅ Seed completado - inventario total:', SUM(stock * cost_price) FROM products WHERE shop='columbus-shop';
