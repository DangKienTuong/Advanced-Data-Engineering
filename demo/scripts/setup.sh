#!/usr/bin/env bash
# One-shot setup: start containers, generate 50,000 products, create schemas, load data, and flush SSTables.
# Run from the demo/ folder:  bash scripts/setup.sh
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

echo "=== [1/7] Generating synthetic product data (50,000 products + 8D semantic vectors) ==="
python scripts/generate_data.py --count 50000

echo "=== [2/7] Starting Docker containers (Elasticsearch 8.15 + Cassandra 5.0 + Kibana) ==="
docker compose up -d

echo "=== [3/7] Waiting for Elasticsearch to be healthy ==="
until curl -s http://localhost:9200/_cluster/health | grep -qE '"status":"(green|yellow)"'; do
  printf '.'; sleep 5
done
echo " ES ready!"

echo "=== [4/7] Creating 'products' index with custom analyzers + HNSW vector index ==="
curl -s -X DELETE http://localhost:9200/products > /dev/null 2>&1 || true
curl -s -X PUT http://localhost:9200/products \
  -H 'Content-Type: application/json' \
  --data-binary @es/index_mapping.json
echo ""

echo "=== [5/7] Bulk-loading 50,000 products into Elasticsearch (5 chunks x 10,000) ==="
for chunk in data/products_bulk_*.ndjson; do
  printf "  Loading %s -> " "$chunk"
  curl -s -X POST "http://localhost:9200/_bulk" \
    -H 'Content-Type: application/x-ndjson' \
    --data-binary @"$chunk" | python -c "import sys,json; d=json.load(sys.stdin); print('errors:', d['errors'], '| items:', len(d['items']))"
done
curl -s -X POST "http://localhost:9200/products/_refresh" > /dev/null
curl -s "http://localhost:9200/products/_count?pretty"

echo "=== [6/7] Waiting for Cassandra 5.0, then creating schema + loading 50,000 rows ==="
until docker exec de-cassandra cqlsh -e 'describe cluster' > /dev/null 2>&1; do
  printf '.'; sleep 10
done
echo " Cassandra ready!"
docker exec de-cassandra cqlsh -e "DROP TABLE IF EXISTS shop.products_by_category;" > /dev/null 2>&1 || true
docker exec de-cassandra cqlsh -f /demo-cql/schema.cql
docker exec de-cassandra cqlsh -f /demo-cql/load.cql

echo "=== [7/7] Flushing Cassandra Memtable to on-disk SSTables & building SAI indexes ==="
docker exec de-cassandra nodetool flush shop products_by_category
docker exec de-cassandra cqlsh -e "SELECT count(*) FROM shop.products_by_category;"

echo ""
echo "=== DONE! ==="
echo "Elasticsearch: http://localhost:9200   | Kibana: http://localhost:5601"
echo "Cassandra:     docker exec -it de-cassandra cqlsh"
echo "Next: bash scripts/demo_elasticsearch.sh  |  bash scripts/demo_cassandra.sh  |  python scripts/benchmark.py"
