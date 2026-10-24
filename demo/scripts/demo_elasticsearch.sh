#!/usr/bin/env bash
# Elasticsearch demo: run each query live during the presentation.
# Usage: bash scripts/demo_elasticsearch.sh          (runs all)
#        bash scripts/demo_elasticsearch.sh 3        (runs only demo #3)
ES=http://localhost:9200
run() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ] || return 0
  echo ""; echo "============================================================"
  echo "DEMO $1: $2"; echo "============================================================"
  shift 2; "$@"; echo ""; read -r -p "--- press Enter for next demo ---" _ 2>/dev/null || true
}
ONLY=$1

q() { curl -s -X POST "$ES/products/_search?pretty" -H 'Content-Type: application/json' -d "$1"; }

run 1 "Full-text search with relevance ranking (BM25)" \
  q '{
    "size": 3,
    "query": { "match": { "description": "lightweight laptop for travel" } },
    "_source": ["name", "category", "price", "rating"]
  }'

run 2 "Fuzzy search — typo tolerance ('lapptop wireles')" \
  q '{
    "size": 3,
    "query": { "multi_match": {
      "query": "lapptop wireles",
      "fields": ["name^2", "description"],
      "fuzziness": "AUTO"
    }},
    "_source": ["name", "category", "price"]
  }'

run 3 "Autocomplete / search-as-you-type (edge n-grams: 'sams')" \
  q '{
    "size": 5,
    "query": { "match": { "name.autocomplete": "sams" } },
    "_source": ["name", "brand", "category"]
  }'

run 4 "Boolean query + filters (headphones, under \$100, rating >= 4)" \
  q '{
    "size": 3,
    "query": { "bool": {
      "must":   [ { "match": { "description": "noise cancelling" } } ],
      "filter": [
        { "term":  { "category": "headphones" } },
        { "range": { "price":  { "lte": 100 } } },
        { "range": { "rating": { "gte": 4.0 } } }
      ]
    }},
    "_source": ["name", "price", "rating"]
  }'

run 5 "Aggregations — faceted navigation (count + avg price per category)" \
  q '{
    "size": 0,
    "aggs": { "by_category": {
      "terms": { "field": "category" },
      "aggs": {
        "avg_price": { "avg": { "field": "price" } },
        "max_rating": { "max": { "field": "rating" } }
      }
    }}
  }'

run 6 "Relevance tuning — function_score: boost by rating & review count" \
  q '{
    "size": 3,
    "query": { "function_score": {
      "query": { "match": { "description": "camera" } },
      "functions": [
        { "field_value_factor": { "field": "rating", "factor": 1.2, "modifier": "sqrt" } },
        { "field_value_factor": { "field": "review_count", "factor": 0.001, "modifier": "log1p" } }
      ],
      "boost_mode": "multiply"
    }},
    "_source": ["name", "rating", "review_count", "price"]
  }'

run 7 "Highlighting — show WHY a document matched" \
  q '{
    "size": 2,
    "query": { "match": { "description": "waterproof action camera" } },
    "_source": ["name"],
    "highlight": { "fields": { "description": {} } }
  }'

run 8 "Explain API — peek inside BM25 scoring" \
  curl -s -X POST "$ES/products/_search?pretty" -H 'Content-Type: application/json' -d '{
    "size": 1,
    "explain": true,
    "query": { "match": { "description": "espresso grinder" } },
    "_source": ["name"]
  }'

run 9 "Analyzer API — how text becomes tokens (stemming + stopwords)" \
  curl -s -X POST "$ES/products/_analyze?pretty" -H 'Content-Type: application/json' -d '{
    "analyzer": "english_custom",
    "text": "The professional cameras are featuring waterproof housings"
  }'

echo ""; echo "=== Elasticsearch demo complete ==="
