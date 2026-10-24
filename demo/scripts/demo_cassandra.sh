#!/usr/bin/env bash
# Cassandra demo: shows query-first modeling, partition-key lookups, SAI, Vector ANN,
# on-disk SSTable inspection, and WHY full-text search is not Cassandra's game (ALLOW FILTERING).
# Usage: bash scripts/demo_cassandra.sh      (or with a number 1..10 to run one demo)
export MSYS_NO_PATHCONV=1
CQL() { docker exec de-cassandra cqlsh -e "$1"; }
run() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ] || return 0
  echo ""; echo "============================================================"
  echo "DEMO $1: $2"; echo "============================================================"
  echo "CMD> $3"; echo ""
  eval "$4"
  read -r -p "--- press Enter for next demo ---" _ 2>/dev/null || true
}
ONLY=$1

run 1 "Partition-key query — THE Cassandra access pattern (O(1) single partition)" \
  "SELECT name, price, rating FROM shop.products_by_category WHERE category='laptops' LIMIT 5;" \
  "CQL \"SELECT name, price, rating FROM shop.products_by_category WHERE category='laptops' LIMIT 5;\""

run 2 "Partition + clustering column range (price between 500-800, sorted on disk)" \
  "SELECT name, price FROM shop.products_by_category WHERE category='laptops' AND price>=500 AND price<=800 LIMIT 5;" \
  "CQL \"SELECT name, price FROM shop.products_by_category WHERE category='laptops' AND price>=500 AND price<=800 LIMIT 5;\""

run 3 "SAI equality index on brand (Cassandra 5.0 Byte-Ordered Trie)" \
  "SELECT name, category, price FROM shop.products_by_category WHERE brand='Sony' LIMIT 5;" \
  "CQL \"SELECT name, category, price FROM shop.products_by_category WHERE brand='Sony' LIMIT 5;\""

run 4 "SAI numeric range + partition (BKD-Tree: rating >= 4.8 laptops)" \
  "SELECT name, rating, price FROM shop.products_by_category WHERE category='laptops' AND rating>=4.8 LIMIT 5;" \
  "CQL \"SELECT name, rating, price FROM shop.products_by_category WHERE category='laptops' AND rating>=4.8 LIMIT 5;\""

run 5 "The ANTI-PATTERN: filtering without index -> Cassandra refuses to protect SLA" \
  "SELECT name FROM shop.products_by_category WHERE stock > 100 LIMIT 5;" \
  "CQL \"SELECT name FROM shop.products_by_category WHERE stock > 100 LIMIT 5;\""

run 6 "ALLOW FILTERING = full 50,000-row scan across SSTables (dangerous at scale!)" \
  "SELECT name, category, stock, review_count FROM shop.products_by_category WHERE stock = 500 AND review_count > 650 LIMIT 5 ALLOW FILTERING;" \
  "CQL \"SELECT name, category, stock, review_count FROM shop.products_by_category WHERE stock = 500 AND review_count > 650 LIMIT 5 ALLOW FILTERING;\""

run 7 "No LIKE / no relevance ranking — substring search is rejected" \
  "SELECT name FROM shop.products_by_category WHERE description LIKE '%laptop%' LIMIT 3;" \
  "CQL \"SELECT name FROM shop.products_by_category WHERE description LIKE '%laptop%' LIMIT 3;\""

run 8 "TRACING ON — inspect internal read path (Coordinator, Bloom filter, SSTable merge)" \
  "TRACING ON; SELECT name, price FROM shop.products_by_category WHERE category='cameras' AND price >= 1000 AND price <= 1500 LIMIT 3; TRACING OFF;" \
  "CQL \"TRACING ON; SELECT name, price FROM shop.products_by_category WHERE category='cameras' AND price >= 1000 AND price <= 1500 LIMIT 3; TRACING OFF;\""

run 9 "Cassandra 5.0 Vector Search — SAI JVector ANN (Cosine Similarity over 50,000 rows)" \
  "SELECT name, category, price, similarity_cosine(embedding, [0.64, 0.54, 0.09, 0.09, 0.50, 0.18, 0.0, 0.0]) AS sem_score FROM shop.products_by_category WHERE category='laptops' ORDER BY embedding ANN OF [0.64, 0.54, 0.09, 0.09, 0.50, 0.18, 0.0, 0.0] LIMIT 5;" \
  "CQL \"SELECT name, category, price, similarity_cosine(embedding, [0.64, 0.54, 0.09, 0.09, 0.50, 0.18, 0.0, 0.0]) AS sem_score FROM shop.products_by_category WHERE category='laptops' ORDER BY embedding ANN OF [0.64, 0.54, 0.09, 0.09, 0.50, 0.18, 0.0, 0.0] LIMIT 5;\""

run 10 "On-Disk SSTable & SAI File Inspection (Data.db, Filter.db, Index.db, SAI components)" \
  "nodetool tablestats shop.products_by_category && ls -lh /var/lib/cassandra/data/shop/products_by_category-*" \
  "docker exec de-cassandra sh -c 'nodetool tablestats shop.products_by_category | head -n 28 && echo \"--- Physical SSTable & SAI Files on Disk ---\" && ls -lh /var/lib/cassandra/data/shop/products_by_category-*/*'"

echo ""; echo "=== Cassandra demo complete (10/10) ==="
echo "Takeaway: Cassandra = O(1) key-based & partitioned SAI retrieval at scale; Elasticsearch = relevance-ranked full-text & hybrid search."
