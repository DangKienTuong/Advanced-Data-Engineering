USE shop;
TRACING OFF;
TRUNCATE products_by_category;
COPY products_by_category (product_id, category, price, name, brand, description, rating, stock, review_count, embedding)
FROM '/demo-data/products.csv' WITH HEADER = FALSE AND NUMPROCESSES = 4 AND CHUNKSIZE = 500 AND MAXBATCHSIZE = 5;
