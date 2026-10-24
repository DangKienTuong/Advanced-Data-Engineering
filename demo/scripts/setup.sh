#!/usr/bin/env bash
# One-shot setup: start containers, generate data, create schemas, load data.
# Run from the demo/ folder:  bash scripts/setup.sh
set -e
cd "$(dirname "$0")/.."

echo "=== [1/6] Generating synthetic product data (5,000 products) ==="
python scripts/generate_data.py

echo "=== [2/6] Starting Docker containers (Elasticsearch + Cassandra + Kibana) ==="
docker compose up -d

echo "=== [3/6] Waiting for Elasticsearch to be healthy ==="
until curl -s http://localhost:9200/_cluster/health | grep -qE '"status":"(green|yellow)"'; do
  printf '.'; sleep 5
done
echo " ES ready!"

echo "=== [4/6] Creating 'products' index with custom analyzers ==="
curl -s -X DELETE http://localhost:9200/products > /dev/null 2>&1 || true
curl -s -X PUT http://localhost:9200/products \
  -H 'Content-Type: application/json' \
  --data-binary @es/index_mapping.json
echo ""

echo "=== [5/6] Bulk-loading 5,000 products into Elasticsearch ==="
curl -s -X POST "http://localhost:9200/_bulk?refresh=true" \
  -H 'Content-Type: application/x-ndjson' \
  --data-binary @data/products_bulk.ndjson | python -c "import sys,json; d=json.load(sys.stdin); print('errors:', d['errors'], '| items:', len(d['items']))"

echo "=== [6/6] Waiting for Cassandra, then creating schema + loading data ==="
until docker exec de-cassandra cqlsh -e 'describe cluster' > /dev/null 2>&1; do
  printf '.'; sleep 10
done
echo " Cassandra ready!"
docker exec de-cassandra cqlsh -f /demo-cql/schema.cql
docker exec de-cassandra cqlsh -f /demo-cql/load.cql
docker exec de-cassandra cqlsh -e "SELECT count(*) FROM shop.products_by_category;"

echo ""
echo "=== DONE! ==="
echo "Elasticsearch: http://localhost:9200   | Kibana: http://localhost:5601"
echo "Cassandra:     docker exec -it de-cassandra cqlsh"
echo "Next: bash scripts/demo_elasticsearch.sh  and  bash scripts/demo_cassandra.sh"
