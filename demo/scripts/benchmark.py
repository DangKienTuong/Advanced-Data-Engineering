"""Quantitative Benchmark Suite for CO5173 Final Project (Elasticsearch 8.15 vs. Cassandra 5.0).

Measures server-side and client-side query execution latencies (mean, p50, p95 in ms)
across 11 core query patterns on the 50,000-product catalog, plus a scalability stress
test comparing N = 5,000 vs. 25,000 vs. 50,000 rows.
"""
import json
import os
import statistics
import subprocess
import time
import urllib.request

ES_URL = "http://localhost:9200/products/_search"
WARMUP = 5
ITERATIONS = 25


def percentile(sorted_vals, pct):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def bench_es(name, payload_dict):
    body = json.dumps(payload_dict).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    # Warmup
    for _ in range(WARMUP):
        req = urllib.request.Request(ES_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            resp.read()

    client_times = []
    engine_times = []
    hits_count = 0
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        req = urllib.request.Request(ES_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        t1 = time.perf_counter()
        client_times.append((t1 - t0) * 1000.0)
        engine_times.append(float(data.get("took", 0.0)))
        hits_count = data.get("hits", {}).get("total", {}).get("value", 0)

    client_times.sort()
    return {
        "name": name,
        "engine": "Elasticsearch 8.15",
        "hits": hits_count,
        "mean_ms": round(statistics.mean(client_times), 2),
        "p50_ms": round(percentile(client_times, 50), 2),
        "p95_ms": round(percentile(client_times, 95), 2),
        "server_took_ms": round(statistics.mean(engine_times), 2),
    }


def bench_cassandra_batch(queries):
    """Run multiple CQL queries inside a single Python script inside the de-cassandra container
    using cqlsh's bundled cassandra-driver for accurate sub-millisecond driver timing!
    """
    driver_script = """
import sys, glob, time, json, statistics
for z in glob.glob('/opt/cassandra/lib/*.zip'):
    sys.path.insert(0, z)
sys.path.insert(0, '/opt/cassandra/lib/cassandra-driver-internal-only-3.29.0.zip/cassandra-driver-3.29.0')
from cassandra.cluster import Cluster

cluster = Cluster(['127.0.0.1'])
session = cluster.connect('shop')

queries = json.loads('''__QUERIES_JSON__''')
warmup = __WARMUP__
iters = __ITERS__

def pct(vals, p):
    k = (len(vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return vals[f] if f == c else vals[f] * (c - k) + vals[c] * (k - f)

results = []
for q in queries:
    cql = q['cql']
    for _ in range(warmup):
        list(session.execute(cql))
    times = []
    rows_n = 0
    for _ in range(iters):
        t0 = time.perf_counter()
        r = list(session.execute(cql))
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)
        rows_n = len(r)
    times.sort()
    results.append({
        'name': q['name'],
        'engine': 'Cassandra 5.0',
        'hits': rows_n,
        'mean_ms': round(statistics.mean(times), 2),
        'p50_ms': round(pct(times, 50), 2),
        'p95_ms': round(pct(times, 95), 2),
    })

print("BENCH_JSON_START:" + json.dumps(results))
cluster.shutdown()
"""
    script_filled = (
        driver_script.replace("__QUERIES_JSON__", json.dumps(queries))
        .replace("__WARMUP__", str(WARMUP))
        .replace("__ITERS__", str(ITERATIONS))
    )
    cmd = ["docker", "exec", "de-cassandra", "python3", "-c", script_filled]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    for line in proc.stdout.splitlines():
        if line.startswith("BENCH_JSON_START:"):
            return json.loads(line.split("BENCH_JSON_START:", 1)[1])
    raise RuntimeError(f"Failed to parse Cassandra benchmark output: {proc.stdout}\n{proc.stderr}")


def run_scaling_benchmark():
    """Measure Cassandra Partition Key, SAI, and ALLOW FILTERING across N = 5K, 25K, 50K rows."""
    scale_script = """
import sys, glob, time, json, statistics
for z in glob.glob('/opt/cassandra/lib/*.zip'):
    sys.path.insert(0, z)
sys.path.insert(0, '/opt/cassandra/lib/cassandra-driver-internal-only-3.29.0.zip/cassandra-driver-3.29.0')
from cassandra.cluster import Cluster

cluster = Cluster(['127.0.0.1'])
session = cluster.connect('shop')

# Fetch up to 50,000 rows from products_by_category
all_rows = list(session.execute("SELECT product_id, category, price, name, brand, description, rating, stock, review_count FROM products_by_category LIMIT 50000"))

session.execute("DROP TABLE IF EXISTS shop.bench_scale")
session.execute('''
CREATE TABLE shop.bench_scale (
  category text, price decimal, product_id int, name text, brand text,
  description text, rating float, stock int, review_count int,
  PRIMARY KEY ((category), price, product_id)
) WITH CLUSTERING ORDER BY (price ASC, product_id ASC)
''')
session.execute("CREATE CUSTOM INDEX idx_bench_brand ON shop.bench_scale (brand) USING 'StorageAttachedIndex'")

insert_stmt = session.prepare("INSERT INTO shop.bench_scale (category, price, product_id, name, brand, description, rating, stock, review_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")

scales = [5000, 25000, 50000]
out = {}
loaded = 0
for target in scales:
    batch_rows = all_rows[loaded:target]
    for r in batch_rows:
        session.execute(insert_stmt, (r.category, r.price, r.product_id, r.name, r.brand, r.description, r.rating, r.stock, r.review_count))
    loaded = target

    queries = {
        'partition_key': "SELECT name, price FROM shop.bench_scale WHERE category='laptops' LIMIT 5",
        'sai_brand': "SELECT name, category, price FROM shop.bench_scale WHERE brand='Sony' LIMIT 5",
        'allow_filtering': "SELECT name, stock FROM shop.bench_scale WHERE stock = -1 ALLOW FILTERING",
    }
    scale_res = {}
    for k, cql in queries.items():
        for _ in range(3):
            list(session.execute(cql))
        ts = []
        for _ in range(12):
            t0 = time.perf_counter()
            list(session.execute(cql))
            t1 = time.perf_counter()
            ts.append((t1 - t0) * 1000.0)
        ts.sort()
        scale_res[k] = round(statistics.median(ts), 2)
    out[str(target)] = scale_res

session.execute("DROP TABLE IF EXISTS shop.bench_scale")
print("SCALE_JSON_START:" + json.dumps(out))
cluster.shutdown()
"""
    cmd = ["docker", "exec", "de-cassandra", "python3", "-c", scale_script]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    for line in proc.stdout.splitlines():
        if line.startswith("SCALE_JSON_START:"):
            return json.loads(line.split("SCALE_JSON_START:", 1)[1])
    raise RuntimeError(f"Failed scaling benchmark: {proc.stdout}\n{proc.stderr}")


def main():
    print("======================================================================")
    print("CO5173 Benchmark Suite: Elasticsearch 8.15 vs. Apache Cassandra 5.0")
    print(f"Dataset: N = 50,000 products | Warmup = {WARMUP} | Iterations = {ITERATIONS}")
    print("======================================================================\n")

    es_workloads = [
        ("ES 1. Full-Text BM25 (match)", {
            "size": 5,
            "query": {"match": {"description": "lightweight laptop for travel"}},
            "_source": ["name", "category", "price", "rating"]
        }),
        ("ES 2. Fuzzy Multi-Match (AUTO)", {
            "size": 5,
            "query": {"multi_match": {"query": "lapptop wireles", "fields": ["name^2", "description"], "fuzziness": "AUTO"}},
            "_source": ["name", "category", "price"]
        }),
        ("ES 3. Edge N-Gram Autocomplete", {
            "size": 5,
            "query": {"match": {"name.autocomplete": "sams"}},
            "_source": ["name", "brand", "category"]
        }),
        ("ES 4. Bool + Cached Bitset Filters", {
            "size": 5,
            "query": {"bool": {
                "must": [{"match": {"description": "noise cancelling"}}],
                "filter": [
                    {"term": {"category": "headphones"}},
                    {"range": {"price": {"lte": 100}}},
                    {"range": {"rating": {"gte": 4.0}}}
                ]
            }},
            "_source": ["name", "price", "rating"]
        }),
        ("ES 5. Faceted Aggregations (50K docs)", {
            "size": 0,
            "aggs": {"by_category": {
                "terms": {"field": "category"},
                "aggs": {"avg_price": {"avg": {"field": "price"}}, "max_rating": {"max": {"field": "rating"}}}
            }}
        }),
        ("ES 6. Hybrid Search (BM25 + HNSW kNN)", {
            "size": 5,
            "query": {"match": {"description": {"query": "portable travel", "boost": 0.5}}},
            "knn": {
                "field": "embedding",
                "query_vector": [0.64, 0.54, 0.09, 0.09, 0.50, 0.18, 0.0, 0.0],
                "k": 10,
                "num_candidates": 50,
                "boost": 0.5
            },
            "_source": ["name", "category", "price"]
        }),
    ]

    es_results = []
    for title, payload in es_workloads:
        res = bench_es(title, payload)
        es_results.append(res)
        print(f"[ES]  {res['name']:<38} | mean={res['mean_ms']:>6.2f} ms | p50={res['p50_ms']:>6.2f} ms | p95={res['p95_ms']:>6.2f} ms | engine={res['server_took_ms']:>5.2f} ms | hits={res['hits']}")

    cass_queries = [
        {"name": "CQL 1. Partition Key Lookup O(1)", "cql": "SELECT name, price, rating FROM shop.products_by_category WHERE category='laptops' LIMIT 5"},
        {"name": "CQL 2. Partition + Clustering Range", "cql": "SELECT name, price FROM shop.products_by_category WHERE category='laptops' AND price>=500 AND price<=800 LIMIT 5"},
        {"name": "CQL 3. SAI Equality (brand='Sony')", "cql": "SELECT name, category, price FROM shop.products_by_category WHERE brand='Sony' LIMIT 5"},
        {"name": "CQL 4. Partition + SAI Numeric Range", "cql": "SELECT name, rating, price FROM shop.products_by_category WHERE category='laptops' AND rating>=4.8 LIMIT 5"},
        {"name": "CQL 5. SAI Vector Search (ANN OF)", "cql": "SELECT name, category, price FROM shop.products_by_category WHERE category='laptops' ORDER BY embedding ANN OF [0.64, 0.54, 0.09, 0.09, 0.50, 0.18, 0.0, 0.0] LIMIT 5"},
        {"name": "CQL 6. ALLOW FILTERING (50K Full Scan)", "cql": "SELECT name, category, stock, review_count FROM shop.products_by_category WHERE stock = 500 AND review_count > 650 LIMIT 5 ALLOW FILTERING"},
    ]

    print("")
    cass_results = bench_cassandra_batch(cass_queries)
    for res in cass_results:
        print(f"[CQL] {res['name']:<38} | mean={res['mean_ms']:>6.2f} ms | p50={res['p50_ms']:>6.2f} ms | p95={res['p95_ms']:>6.2f} ms | rows={res['hits']}")

    print("\nRunning Scalability Stress Test (N = 5,000 -> 25,000 -> 50,000 rows)...")
    scale_results = run_scaling_benchmark()
    for n_str, metrics in scale_results.items():
        print(f"  N = {int(n_str):>6,} | Partition Key: {metrics['partition_key']:>6.2f} ms | SAI Brand: {metrics['sai_brand']:>6.2f} ms | ALLOW FILTERING (Full Scan): {metrics['allow_filtering']:>7.2f} ms")

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"elasticsearch": es_results, "cassandra": cass_results, "scaling": scale_results}, f, indent=2)
    print(f"\nSaved full benchmark results -> {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
