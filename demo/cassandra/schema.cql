-- Cassandra schema for the search-techniques demo (Cassandra 5.0, SAI indexes)
CREATE KEYSPACE IF NOT EXISTS shop
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE shop;

-- Query-first design: table partitioned by category, clustered by price
-- -> supports "browse category sorted/filtered by price" natively (no index needed)
CREATE TABLE IF NOT EXISTS products_by_category (
  category     text,
  price        decimal,
  product_id   int,
  name         text,
  brand        text,
  description  text,
  rating       float,
  stock        int,
  review_count int,
  PRIMARY KEY ((category), price, product_id)
) WITH CLUSTERING ORDER BY (price ASC, product_id ASC);

-- SAI (Storage-Attached Index, new in Cassandra 5.0): secondary filtering
CREATE CUSTOM INDEX IF NOT EXISTS idx_brand  ON products_by_category (brand)  USING 'StorageAttachedIndex';
CREATE CUSTOM INDEX IF NOT EXISTS idx_rating ON products_by_category (rating) USING 'StorageAttachedIndex';
