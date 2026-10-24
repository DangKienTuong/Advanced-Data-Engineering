#!/usr/bin/env bash
# Cassandra demo: shows query-first modeling, partition-key lookups, SAI, and
# WHY full-text search is not Cassandra's game (ALLOW FILTERING anti-pattern).
# Usage: bash scripts/demo_cassandra.sh      (or with a number to run one demo)
CQL() { docker exec de-cassandra cqlsh -e "$1"; }
run() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ] || return 0
  echo ""; echo "============================================================"
  echo "DEMO $1: $2"; echo "============================================================"
  echo "CQL> $3"; echo ""
  CQL "$3"
  read -r -p "--- press Enter for next demo ---" _ 2>/dev/null || true
}
ONLY=$1

run 1 "Partition-key query — THE Cassandra access pattern (fast: 1 partition)" \
  "SELECT name, price, rating FROM shop.products_by_category WHERE category='laptops' LIMIT 5;"

run 2 "Partition + clustering column range (price between 500-800, still 1 partition)" \
  "SELECT name, price FROM shop.products_by_category WHERE category='laptops' AND price>=500 AND price<=800 LIMIT 5;"

run 3 "SAI index on brand (Cassandra 5.0 Storage-Attached Index)" \
  "SELECT name, category, price FROM shop.products_by_category WHERE brand='Sony' LIMIT 5;"

run 4 "SAI numeric range + partition (rating >= 4.5 laptops)" \
  "SELECT name, rating, price FROM shop.products_by_category WHERE category='laptops' AND rating>=4.5 LIMIT 5;"

run 5 "The ANTI-PATTERN: filtering without index -> Cassandra refuses" \
  "SELECT name FROM shop.products_by_category WHERE stock > 100 LIMIT 5;"

run 6 "ALLOW FILTERING = full cluster scan (works, but dangerous at scale)" \
  "SELECT name, stock FROM shop.products_by_category WHERE stock > 100 LIMIT 5 ALLOW FILTERING;"

run 7 "No LIKE / no relevance ranking — text search is equality-only on SAI" \
  "SELECT name FROM shop.products_by_category WHERE description LIKE '%laptop%' LIMIT 3;"

run 8 "TRACING ON — see the internal read path (coordinator, SSTables, latency)" \
  "TRACING ON; SELECT name FROM shop.products_by_category WHERE category='cameras' LIMIT 3; TRACING OFF;"

echo ""; echo "=== Cassandra demo complete ==="
echo "Takeaway: Cassandra = O(1) key-based retrieval at scale; Elasticsearch = relevance-ranked full-text search."
echo "Real systems often combine them (ES as search index over a Cassandra source of truth)."
