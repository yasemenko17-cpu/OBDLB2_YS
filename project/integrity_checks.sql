-- check: fk: Замовлення, що посилаються на неіснуючого клієнта
SELECT o.id FROM "orders" o LEFT JOIN "customer" c ON o.customer_id = c.id WHERE c.id IS NULL;

-- check: fk: Товари з неіснуючими категоріями
SELECT p.id FROM "product" p LEFT JOIN "category" c ON p.category_id = c.id WHERE c.id IS NULL;

-- check: dup: Дублікати клієнтів за електронною поштою
SELECT email FROM "customer" GROUP BY email HAVING count(*) > 1;

-- check: rule: Товари з від'ємною або нульовою ціною
SELECT id FROM "product" WHERE price <= 0;

-- check: rule: Позиції замовлення з нульовою чи від'ємною кількістю
SELECT orders_id, item_no FROM "order_item" WHERE quantity <= 0;

-- check: rule: Товари на складі з від'ємною кількістю
SELECT warehouse_id, stock_id FROM "stock" WHERE quantity < 0;