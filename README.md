# Search Techniques in Modern Database Systems
### Elasticsearch 8.15 & Apache Cassandra 5.0 — Data Engineering (CO5173) Final Project
**HCMUT — VNU-HCM | Semester 261 (Academic Year 2026–2027)**
- **Supervisor:** Assoc. Prof. Trần Minh Quang (`quangtran@hcmut.edu.vn`)
- **Students:** Đặng Kiến Tường (2670391) — Đặng Minh Quân (2670358)

---

## Project Overview

This repository contains the complete theoretical analysis, LaTeX Beamer presentation (`slides/main.pdf`), reproducible Docker stack (`demo/docker-compose.yml`), 50,000-product synthetic dataset with 8D semantic vectors, 20 guided live demo queries, and an automated latency & scalability benchmark suite (`demo/scripts/benchmark.py`) comparing **Elasticsearch 8.15.3** and **Apache Cassandra 5.0**.

### Key Highlights
1. **Deep Storage & Indexing Internals:**
   - **Elasticsearch 8.15:** Apache Lucene Inverted Index, Finite State Transducers (FST), Roaring Bitmap filter caches, Columnar `doc_values`, Block K-D (BKD) Trees, and Multi-Layer **HNSW** Vector Graphs.
   - **Apache Cassandra 5.0:** Masterless Consistent-Hashing Ring (`Murmur3Partitioner`), Append-Only **LSM-Trees** (CommitLog, SkipList Memtable, Immutable SSTables, Bloom Filters), and **Storage-Attached Indexes (SAI)** (Byte-Ordered Tries, BKD-Trees, and **JVector/DiskANN** Vector Graphs).
2. **Mathematical & Empirical Verification:**
   - Exact manual verification of multi-term **Okapi BM25** scoring (demonstrating $k_1 = 1.2$ term-frequency saturation and $b = 0.75$ document-length normalization) against Elasticsearch's `explain: true` API over $N = 50,000$ documents.
   - Authentic post-`nodetool flush` Cassandra `TRACING ON` execution merging on-disk SSTables (`Data.db`, `Filter.db`, `Index.db`, and `SAI` `.db` components).
3. **2026 Research Frontier — Dense Vector & Hybrid Search:**
   - Demonstrates **Hybrid Search (Lexical BM25 + HNSW Cosine kNN)** in Elasticsearch 8.15 and **SAI Vector Search (`ORDER BY embedding ANN OF ...`)** in Cassandra 5.0 across 50,000 8-dimensional product embeddings.

---

## Repository Structure
```
Final Project/
├── slides/
│   ├── main.tex                      LaTeX Beamer source (HCMUT template, 41 pages / 34 content slides)
│   ├── references.bib                Academic bibliography (BM25, LSM-Tree, HNSW, DiskANN, RRF, etc.)
│   └── main.pdf                      ← THE COMPILED PRESENTATION
├── demo/
│   ├── docker-compose.yml            ES 8.15.3 + Cassandra 5.0 + Kibana 8.15.3
│   ├── scripts/
│   │   ├── generate_data.py          50,000 synthetic products + variable-length text + 8D semantic vectors
│   │   ├── setup.sh                  One-shot: generate 50K + start Docker + bulk load + nodetool flush
│   │   ├── demo_elasticsearch.sh     10 guided live queries (BM25, Fuzzy, N-Gram, Bool, Aggs, Explain, Hybrid kNN)
│   │   ├── demo_cassandra.sh         10 guided live queries (Partition, Clustering, SAI, Vector ANN, SSTable inspect)
│   │   └── benchmark.py              Automated latency benchmark (mean/p50/p95) & scaling test (5K -> 25K -> 50K)
│   ├── es/index_mapping.json         Custom analyzers (stemming, edge n-grams) + HNSW dense_vector (cosine)
│   ├── cassandra/schema.cql          Query-first table + 3 SAI indexes (Trie brand, BKD rating, JVector embedding)
│   └── data/                         Generated 50,000-product CSV/NDJSON & benchmark_results.json
└── docs/
    └── DEMO_GUIDE.md                 ← Step-by-step live presentation script & Q&A talking points
```

---

## Quantitative Benchmark Summary ($N = 50,000$ Products)

Measured via `python demo/scripts/benchmark.py` (5 warmup + 25 timed iterations per workload):

| Engine | Workload Pattern ($N = 50,000$) | Mean (ms) | Median $p_{50}$ (ms) | Tail $p_{95}$ (ms) |
| :--- | :--- | :---: | :---: | :---: |
| **Cassandra 5.0** | 1. Partition Key Lookup $\Theta(1)$ | 1.74 | **1.70** | 2.00 |
| **Cassandra 5.0** | 2. Partition + Clustering Range | 2.87 | **2.31** | 6.92 |
| **Cassandra 5.0** | 3. SAI Equality (`brand='Sony'`) | 4.00 | **3.84** | 5.36 |
| **Cassandra 5.0** | 4. Partition + SAI BKD Range | 4.43 | **4.40** | 5.81 |
| **Cassandra 5.0** | 5. SAI Vector Search (`ANN OF`) | 9.33 | **8.31** | 10.36 |
| **Cassandra 5.0** | 6. `ALLOW FILTERING` (50K Full Scan Anti-Pattern) | 124.67 | **115.88** | 192.23 |
| **Elasticsearch 8.15** | 1. Faceted Aggregations (`doc_values`, 50K docs) | 7.21 *(1.00 engine)* | **7.03** | 10.01 |
| **Elasticsearch 8.15** | 2. Edge N-Gram Autocomplete | 7.29 *(1.48 engine)* | **7.18** | 8.39 |
| **Elasticsearch 8.15** | 3. Compound `bool` + 3 Cached Bitsets | 9.16 *(2.72 engine)* | **8.23** | 12.77 |
| **Elasticsearch 8.15** | 4. Full-Text BM25 (`match`) | 9.66 *(3.24 engine)* | **9.29** | 12.25 |
| **Elasticsearch 8.15** | 5. Hybrid Search (BM25 + HNSW kNN) | 12.60 *(4.72 engine)* | **10.55** | 18.26 |
| **Elasticsearch 8.15** | 6. Fuzzy Multi-Match (`fuzziness: AUTO`) | 13.82 *(7.52 engine)* | **12.93** | 19.94 |

---

## Quick Start

```bash
cd demo
bash scripts/setup.sh                  # Generates 50,000 products, loads ES + Cassandra, flushes SSTables
bash scripts/demo_elasticsearch.sh     # 10 guided Elasticsearch 8.15 live queries
bash scripts/demo_cassandra.sh         # 10 guided Cassandra 5.0 live queries
python scripts/benchmark.py            # Quantitative latency & scaling benchmark suite
```
Full walkthrough with presentation talking points: [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

## Rebuilding the Slides
The PDF is pre-compiled at [slides/main.pdf](slides/main.pdf). To rebuild after edits (uses Docker, no local LaTeX needed):
```bash
cd slides
docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/work" -w /work texlive/texlive:latest \
  sh -c "pdflatex -interaction=nonstopmode main.tex && bibtex main || true && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex"
```
