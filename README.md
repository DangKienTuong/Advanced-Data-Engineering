# Search Techniques in Modern Database Systems
### Elasticsearch & Cassandra — Data Engineering (CO5173) Final Project
**HCMUT — VNU-HCM | Semester 261**

## Contents
```
Final Project/
├── slides/              LaTeX source (HCMUT template) + compiled PDF
│   └── main.pdf         ← THE PRESENTATION
├── demo/
│   ├── docker-compose.yml       ES 8.15 + Cassandra 5.0 + Kibana
│   ├── scripts/
│   │   ├── generate_data.py     5,000 synthetic e-commerce products
│   │   ├── setup.sh             one-shot: start + schema + load
│   │   ├── demo_elasticsearch.sh  9 guided live queries
│   │   └── demo_cassandra.sh      8 guided live queries
│   ├── es/index_mapping.json    custom analyzers (stemming, edge n-grams)
│   ├── cassandra/schema.cql     query-first table + SAI indexes
│   └── data/                    generated (git-ignorable)
└── docs/
    └── DEMO_GUIDE.md    ← step-by-step presentation script
```

## Quick start
```bash
cd demo
bash scripts/setup.sh                  # ~5-10 min first time (image pulls)
bash scripts/demo_elasticsearch.sh     # guided ES demo
bash scripts/demo_cassandra.sh         # guided Cassandra demo
```
Full walkthrough with talking points: `docs/DEMO_GUIDE.md`.

## Rebuilding the slides
The PDF is pre-compiled. To rebuild after edits (uses Docker, no local LaTeX needed):
```bash
cd slides
docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/work" -w /work texlive/texlive:latest \
  sh -c "pdflatex -interaction=nonstopmode main.tex && bibtex main || true && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex"
```
