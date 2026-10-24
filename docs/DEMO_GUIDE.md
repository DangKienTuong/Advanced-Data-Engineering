# DEMO GUIDE — Search Techniques in Modern Database Systems
### Elasticsearch & Cassandra | Data Engineering (CO5173) Final Project

This is your step-by-step script for the live demo (presentation part C).
Everything runs in Docker — nothing else to install.

---

## 0. Requirements
- Docker Desktop running (check: `docker info`)
- ~4 GB free RAM for the containers
- A bash shell (Git Bash on Windows works; all commands below assume it)

## 1. One-time setup (do this BEFORE presentation day, takes ~5-10 min)

```bash
cd "C:/Users/ASUS/Documents/Master/Data Engineering/Final Project/demo"
bash scripts/setup.sh
```

This will:
1. Generate 5,000 synthetic e-commerce products (`data/`)
2. Start 3 containers: **Elasticsearch 8.15**, **Cassandra 5.0**, **Kibana**
3. Create the ES `products` index (custom analyzers: English stemming, edge n-grams for autocomplete)
4. Bulk-load all 5,000 products into Elasticsearch
5. Create the Cassandra `shop.products_by_category` table + 2 SAI indexes, load the same data

**Verify** everything is up:
```bash
curl -s http://localhost:9200/_cat/indices?v          # products index, 5000 docs
docker exec de-cassandra cqlsh -e "SELECT count(*) FROM shop.products_by_category;"
```

> On presentation day, if the laptop was rebooted: `docker compose up -d` (data persists
> inside the containers as long as you don't `docker compose down -v`). If containers were
> removed, just re-run `setup.sh`.

## 2. Live demo — Elasticsearch (≈4 min)

```bash
bash scripts/demo_elasticsearch.sh
```
The script pauses after each query (press Enter to advance). Run one query alone with
`bash scripts/demo_elasticsearch.sh 3`.

What each demo shows + what to SAY:

- **Demo 1 — Full-text search (BM25):** "Query: *lightweight laptop for travel*. Note no product contains that exact sentence — ES tokenizes, stems, and ranks by BM25 relevance (`_score` field)."
- **Demo 2 — Fuzzy search:** "I typed *lapptop wireles* with typos. Levenshtein automata over the FST term dictionary still find matches. This is impossible in plain SQL/CQL."
- **Demo 3 — Autocomplete:** "Typing just *sams* → Samsung products. Edge n-grams index every prefix at WRITE time, so search-as-you-type is a cheap exact lookup."
- **Demo 4 — Bool + filters:** "must = scored full-text; filter = cached, non-scored structured predicates (category, price, rating). This mix is THE e-commerce search pattern."
- **Demo 5 — Aggregations:** "Facet counts + avg price per category in one round-trip — powered by doc_values (columnar storage), not the inverted index."
- **Demo 6 — function_score:** "Relevance tuning: boost by rating and review count. Search engineering = controlling ranking, not just matching."
- **Demo 7 — Highlighting:** "ES returns WHY it matched — highlighted fragments."
- **Demo 8 — Explain API:** "Full BM25 score breakdown: IDF × TF saturation × field-length norm. Good Q&A ammunition."
- **Demo 9 — Analyzer API:** "How 'The professional cameras are featuring...' becomes tokens: lowercased, stopwords out, 'cameras'→'camera' (stemming)."

Optional eye-candy: open **Kibana** at http://localhost:5601 → Dev Tools, paste any query.

## 3. Live demo — Cassandra (≈4 min)

```bash
bash scripts/demo_cassandra.sh
```

- **Demo 1 — Partition key query:** "WHERE category='laptops' → hash(partition key) → ONE node, ONE partition. O(1) routing regardless of cluster size. This is why Cassandra scales linearly."
- **Demo 2 — Clustering range:** "Price is a clustering column → rows stored sorted on disk → range scan is a sequential read inside one partition."
- **Demo 3 — SAI on brand:** "Cassandra 5.0's Storage-Attached Indexes: trie-based index attached to each SSTable. Much better than old 2i."
- **Demo 4 — SAI numeric range:** "SAI supports range predicates (rating >= 4.5) combined with the partition key."
- **Demo 5 — The refusal:** "Filtering on a non-indexed column → Cassandra REFUSES. It won't let you accidentally scan the cluster. This error is a feature!"
- **Demo 6 — ALLOW FILTERING:** "You can force it... on 5,000 rows it's fine, on 5 billion it's an outage."
- **Demo 7 — No LIKE:** "No full-text, no relevance ranking — this fails. Exactly the gap Elasticsearch fills."
- **Demo 8 — TRACING:** "The actual internal read path: coordinator, SSTable reads, merge, latency in µs."

## 4. The punchline (transition back to slides)

> "Cassandra answers *known queries* over massive data with predictable low latency.
> Elasticsearch answers *unknown, user-typed queries* with relevance ranking.
> Real architectures (Netflix, Discord, eBay) use both: Cassandra as source of truth,
> Elasticsearch as the search index, synced via CDC/dual writes."

## 5. Teardown after the presentation

```bash
docker compose down        # keep data
docker compose down -v     # remove everything
```

## 6. Troubleshooting

- **ES container exits immediately:** usually RAM. In Docker Desktop → Settings → Resources, give it ≥ 4 GB.
- **`curl: connection refused`:** ES needs ~30-60 s to boot. `docker logs de-elasticsearch --tail 20`.
- **Cassandra "Unavailable" / cqlsh fails:** Cassandra 5 takes 1-3 min to boot. `docker logs de-cassandra --tail 20`, wait for "Startup complete".
- **COPY fails from cqlsh:** re-run `docker exec de-cassandra cqlsh -f /demo-cql/load.cql`.
- **Port conflict (9200/9042/5601 in use):** edit the left side of the port mappings in `docker-compose.yml`.
