USE shop;
COPY products_by_category (product_id, category, price, name, brand, description, rating, stock, review_count)
FROM '/demo-data/products.csv' WITH HEADER = FALSE;
