# DEMO GUIDE — Search Techniques in Modern Database Systems
### Elasticsearch 8.15 & Apache Cassandra 5.0 | Data Engineering (CO5173) Final Project

This is your step-by-step script for the live demo (Presentation Part C).
Everything runs in Docker over a **50,000-product e-commerce catalog** with variable-length descriptions and 8-dimensional semantic embeddings.

---

## 0. Requirements
- Docker Desktop running (check: `docker info`)
- ~4 GB free RAM for the containers
- A bash shell (Git Bash on Windows works; `MSYS_NO_PATHCONV=1` is automatically set in the scripts)

## 1. One-time setup (do this BEFORE presentation day, takes ~1-2 min if images are cached)

```bash
cd "C:/Users/ASUS/Documents/Master/Data Engineering/Final Project/demo"
bash scripts/setup.sh
```

This will:
1. Generate **50,000 synthetic e-commerce products** (`data/products.csv` + 5 chunked `products_bulk_*.ndjson` files) with variable-length text ($|D| \in [12, 44]$ tokens) and 8D unit-normalized semantic vectors (`embedding`).
2. Start 3 containers: **Elasticsearch 8.15.3**, **Cassandra 5.0**, **Kibana 8.15.3**.
3. Create the ES `products` index (custom analyzers: English stemming, edge n-grams for autocomplete, and an 8D HNSW `dense_vector` index).
4. Bulk-load all 50,000 products into Elasticsearch in 5 chunks of 10,000.
5. Create the Cassandra `shop.products_by_category` table + **3 SAI indexes** (Trie on `brand`, BKD-tree on `rating`, and JVector ANN on `embedding`), load all 50,000 rows, and run `nodetool flush` so SSTable `.db` and `SAI` index files are materialized on disk.

**Verify** everything is up:
```bash
curl -s http://localhost:9200/_cat/indices?v          # products index, 50000 docs
docker exec de-cassandra cqlsh -e "SELECT count(*) FROM shop.products_by_category;"
```

---

## 2. Live demo — Elasticsearch 8.15 (10 Guided Queries)

```bash
bash scripts/demo_elasticsearch.sh
```
The script pauses after each query (press Enter to advance). Run a single query with `bash scripts/demo_elasticsearch.sh 10`.

What each demo shows + what to SAY:

- **Demo 1 — Full-text search (BM25 over 50,000 products):** "Query: *lightweight laptop for travel*. Over 10,000 documents match in ~3 ms; because our 50,000 products have variable-length descriptions ($|D|$ vs. $\text{avgdl} = 24.23$) and term frequencies, each result gets a distinct BM25 `_score` (`7.12`, `6.91`, `6.86`)."
- **Demo 2 — Fuzzy search (`lapptop wireles`):** "Both words have typos. Elasticsearch builds Levenshtein automata ($d \le 2$) intersected directly with the in-memory FST term dictionary, matching 8,280 laptops in ~7 ms."
- **Demo 3 — Autocomplete (`sams`):** "Edge n-grams index prefixes at write time, so typing `sams` is a 1.5 ms exact term lookup."
- **Demo 4 — Compound `bool` + cached bitset filters:** "`must` computes BM25 relevance; `filter` applies binary predicates (`category=headphones`, `price<=100`, `rating>=4.0`) cached as Roaring Bitmaps with zero scoring overhead."
- **Demo 5 — Faceted Aggregations (50,000 docs in 1.0 ms):** "Computes document counts, average price, and max rating across all 6 categories in 1.0 ms engine time using columnar `doc_values`."
- **Demo 6 — Relevance tuning (`function_score`):** "Combines lexical BM25 with business signals (`sqrt(rating)` and `log1p(review_count)`)."
- **Demo 7 — Highlighting:** "Returns `<em>` fragments explaining *why* a document matched."
- **Demo 8 — Explain API (`conical burr grinder`):** "Proves the exact BM25 math on doc `5212`: `conic` ($f=1 \rightarrow 3.80$) + `burr` ($f=1 \rightarrow 3.80$) + `grinder` ($f=2 \rightarrow 4.00$, showing $k_1=1.2$ TF saturation!) = `11.6021`."
- **Demo 9 — Analyzer API:** "Shows tokenization, stopword removal, and Porter stemming (`cameras` $\rightarrow$ `camera`, `housings` $\rightarrow$ `hous`)."
- **Demo 10 — Hybrid Search (BM25 + HNSW Dense Vector kNN):** "Combines lexical matching on `portable travel` with an 8D HNSW cosine similarity search on `embedding` (`MSI AirLite 586`, `Asus ThinkBook 970`)."

---

## 3. Live demo — Apache Cassandra 5.0 (10 Guided Queries)

```bash
bash scripts/demo_cassandra.sh
```

- **Demo 1 — Partition key query ($1.70\text{ ms}$):** "`WHERE category='laptops'` hashes via Murmur3 to ONE partition. $O(1)$ routing regardless of cluster size."
- **Demo 2 — Clustering range ($2.31\text{ ms}$):** "`price` is a clustering column sorted ascending on disk; range scan is a single contiguous disk slice."
- **Demo 3 — SAI equality on `brand` ($3.84\text{ ms}$):** "Cassandra 5.0 Storage-Attached Index using a memory-efficient Byte-Ordered Trie."
- **Demo 4 — Partition + SAI numeric range ($4.40\text{ ms}$):** "Intersects the `laptops` partition with the SAI BKD-tree on `rating >= 4.8`."
- **Demo 5 — Unindexed column refusal:** "Filtering on `stock > 100` is rejected by Cassandra to protect cluster SLAs from accidental full scans."
- **Demo 6 — `ALLOW FILTERING` on 50,000 rows ($115.88\text{ ms}$):** "Forcing a scan across all 50,000 rows on disk is **68x slower** than Partition Key lookup!"
- **Demo 7 — No `LIKE '%laptop%'`:** "Substring full-text search is rejected — the exact gap Elasticsearch fills."
- **Demo 8 — `TRACING ON` (Real SSTable Read Path):** "Because we ran `nodetool flush`, the trace shows Cassandra checking Bloom filters, looking up `Partition index found for sstable 4 & 5`, and merging data from 2 on-disk SSTables in 3.45 ms."
- **Demo 9 — Cassandra 5.0 SAI Vector Search (`ANN OF`):** "Uses JVector (DiskANN-inspired Vamana graph) attached to SSTables to find top-5 semantically similar laptops by cosine similarity in 8.31 ms."
- **Demo 10 — Physical SSTable & SAI File Inspection:** "Lists the actual files inside `/var/lib/cassandra/data/shop/products_by_category-*/`: `Data.db`, `Filter.db` (Bloom filter), `idx_brand+TermsData.db` (Trie), `idx_rating+BalancedTree.db` (BKD-Tree), and `idx_embedding+CompressedVectors.db` (JVector)."

---

## 4. Quantitative Benchmark Suite

```bash
python scripts/benchmark.py
```
Runs 5 warmup + 25 timed iterations across 12 workloads (6 ES + 6 Cassandra) plus a scalability stress test ($N = 5,000 \rightarrow 25,000 \rightarrow 50,000$ rows) and saves results to `data/benchmark_results.json`.
