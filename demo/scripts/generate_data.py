"""Generate a synthetic e-commerce product catalog (default: 50,000 products) for the search demo.

Outputs (into demo/data/):
  - products_bulk_1.ndjson .. products_bulk_5.ndjson : Chunked Elasticsearch _bulk format (10k docs/chunk)
  - products_bulk.ndjson                             : Combined Elasticsearch _bulk format
  - products.csv                                     : For Cassandra COPY (includes 8D semantic vector)
Stdlib only — no pip installs needed.
"""
import argparse
import csv
import glob
import json
import math
import os
import random

parser = argparse.ArgumentParser(description="Generate synthetic e-commerce catalog")
parser.add_argument("--count", type=int, default=50000, help="Number of products to generate (default: 50000)")
parser.add_argument("--chunk-size", type=int, default=10000, help="Docs per ES bulk chunk (default: 10000)")
args = parser.parse_args()

random.seed(42)
N = args.count
CHUNK_SIZE = args.chunk_size
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)

CATEGORIES = {
    "laptops": (
        ["UltraBook", "ProBook", "GameMaster", "AirLite", "WorkStation", "ThinkBook", "ZenBook", "BladePro"],
        ["14-inch", "15.6-inch", "16-inch OLED", "13.3-inch touchscreen", "17-inch Mini-LED", "14.5-inch 2.8K"],
        ["Intel Core i7", "AMD Ryzen 9", "Intel Core i5", "Apple M3", "Intel Core Ultra 9", "Snapdragon X Elite", "RTX 4070 GPU", "32GB LPDDR5X RAM"],
        (450, 3500),
    ),
    "smartphones": (
        ["Galaxy", "Pixel Pro", "Xperia", "Nova", "RedMagic", "UltraPhone", "FoldMax", "NoteEdge"],
        ["128GB", "256GB", "512GB", "1TB", "256GB Unlocked", "512GB Titanium"],
        ["5G dual-SIM", "AMOLED 120Hz", "titanium frame", "foldable display", "periscope 5x zoom", "5000mAh silicon battery", "wireless fast charging", "IP68 waterproof rating"],
        (200, 1800),
    ),
    "headphones": (
        ["SoundCore", "QuietComfort", "StudioPro", "BassBoost", "AirPods-style", "SonicWave", "PulseANC", "AcoustiMax"],
        ["wireless", "noise cancelling", "over-ear", "in-ear sport", "open-back studio", "true wireless earbuds"],
        ["Bluetooth 5.3", "40h battery", "hi-res audio", "low-latency gaming", "adaptive ANC", "multipoint pairing", "LDAC lossless codec", "spatial 3D audio"],
        (25, 550),
    ),
    "cameras": (
        ["AlphaShot", "EOS-Line", "LumixPro", "ActionCam", "InstaView", "CineMaster", "CyberShot", "RangeFinder"],
        ["mirrorless", "DSLR", "action camera", "instant film", "full-frame cinema", "compact vlog camera"],
        ["24MP full-frame", "4K 60fps video", "waterproof 10m", "optical zoom 30x", "5-axis IBIS stabilization", "8K RAW recording", "dual SD card slots", "weather-sealed magnesium body"],
        (150, 4200),
    ),
    "coffee machines": (
        ["EspressoMaster", "BrewPerfect", "MokaPro", "ColdDrip", "BaristaOne", "CremaPlus", "CafeRistretto", "LatteArt"],
        ["automatic", "semi-automatic", "manual lever", "capsule", "dual-boiler", "bean-to-cup"],
        ["15-bar pump", "built-in grinder", "milk frother", "thermal carafe", "PID temperature control", "conical burr grinder", "pre-infusion system", "stainless steel portafilter"],
        (40, 1200),
    ),
    "running shoes": (
        ["CloudRunner", "SpeedForm", "TrailGrip", "MarathonX", "FlexStep", "AeroStride", "NitroPace", "UltraCushion"],
        ["men's", "women's", "unisex", "wide-fit", "all-terrain", "track racing"],
        ["carbon plate", "breathable mesh", "waterproof gore-tex", "extra cushioning", "vibram outsole", "dual-density foam", "reflective heel tab", "lightweight knit upper"],
        (35, 280),
    ),
}

BRANDS_BY_CAT = {
    "laptops": ["Dell", "Asus", "Lenovo", "Apple", "HP", "MSI", "Acer", "Razer"],
    "smartphones": ["Samsung", "Apple", "Xiaomi", "Sony", "Google", "Oppo", "OnePlus", "Nothing"],
    "headphones": ["Sony", "Bose", "JBL", "Anker", "Sennheiser", "Apple", "Audio-Technica", "Beyerdynamic"],
    "cameras": ["Canon", "Nikon", "Sony", "Fujifilm", "GoPro", "Panasonic", "Leica", "OM-System"],
    "coffee machines": ["DeLonghi", "Breville", "Philips", "Nespresso", "Gaggia", "Krups", "Jura", "Rancilio"],
    "running shoes": ["Nike", "Adidas", "Asics", "New Balance", "Hoka", "Brooks", "Saucony", "Salomon"],
}

ADJ = [
    "premium", "budget-friendly", "professional", "compact", "lightweight",
    "ergonomic", "durable", "stylish", "high-performance", "energy-efficient",
    "ultra-thin", "rugged", "versatile", "next-generation",
]

USE_CASES = [
    "everyday use", "professionals", "students", "travel", "home and office",
    "remote work and business trips", "content creators", "outdoor adventures",
    "competitive gaming and streaming", "minimalist commuters",
]

EXTRA_CLAUSES = [
    "Designed with precision engineering for long-lasting reliability.",
    "Backed by a 2-year international warranty and rapid customer support.",
    "Includes fast USB-C charging cable and protective travel pouch.",
    "Engineered for ultra-quiet operation and low power consumption.",
    "Tested under extreme conditions to guarantee consistent performance.",
    "Features intuitive controls and seamless smart-device connectivity.",
    "Highly rated by industry reviewers for exceptional value and build quality.",
    "Compact footprint makes it easy to pack in carry-on luggage for travel.",
]

# 8D semantic axes:
# [0: portability, 1: compute_power, 2: audio_fidelity, 3: imaging_pro,
#  4: battery_life, 5: durability_waterproof, 6: barista_brew, 7: athletic_run]
BASE_VECTORS = {
    "laptops":         [0.65, 0.90, 0.15, 0.15, 0.65, 0.15, 0.00, 0.00],
    "smartphones":     [0.90, 0.65, 0.30, 0.60, 0.75, 0.45, 0.00, 0.05],
    "headphones":      [0.80, 0.10, 0.95, 0.00, 0.70, 0.30, 0.00, 0.25],
    "cameras":         [0.55, 0.35, 0.15, 0.95, 0.50, 0.60, 0.00, 0.10],
    "coffee machines": [0.10, 0.10, 0.00, 0.00, 0.00, 0.35, 0.98, 0.00],
    "running shoes":   [0.75, 0.00, 0.00, 0.00, 0.00, 0.65, 0.00, 0.98],
}


def compute_embedding(cat, adj, feats, use_case, desc):
    vec = list(BASE_VECTORS[cat])
    text_lower = desc.lower()
    if "lightweight" in text_lower or "compact" in text_lower or "travel" in text_lower or "ultra-thin" in text_lower:
        vec[0] += 0.35
    if "ryzen" in text_lower or "core" in text_lower or "m3" in text_lower or "rtx" in text_lower or "high-performance" in text_lower:
        vec[1] += 0.30
    if "noise cancelling" in text_lower or "hi-res" in text_lower or "audio" in text_lower or "anc" in text_lower:
        vec[2] += 0.30
    if "4k" in text_lower or "8k" in text_lower or "full-frame" in text_lower or "zoom" in text_lower:
        vec[3] += 0.30
    if "battery" in text_lower or "energy-efficient" in text_lower:
        vec[4] += 0.30
    if "waterproof" in text_lower or "gore-tex" in text_lower or "durable" in text_lower or "rugged" in text_lower or "ip68" in text_lower:
        vec[5] += 0.40
    if "grinder" in text_lower or "espresso" in text_lower or "frother" in text_lower or "pump" in text_lower:
        vec[6] += 0.30
    if "carbon plate" in text_lower or "marathon" in text_lower or "trail" in text_lower or "cushioning" in text_lower:
        vec[7] += 0.30

    # Add tiny deterministic jitter so every product has a realistic position
    for i in range(8):
        vec[i] = max(0.0, vec[i] + random.uniform(-0.04, 0.04))

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 4) for x in vec]


# Clean old chunk files if any
for old_chunk in glob.glob(os.path.join(OUT, "products_bulk_*.ndjson")):
    os.remove(old_chunk)

rows = []
cat_list = list(CATEGORIES.keys())

for pid in range(1, N + 1):
    cat = random.choice(cat_list)
    names, variants, feats, (lo, hi) = CATEGORIES[cat]
    brand = random.choice(BRANDS_BY_CAT[cat])
    model_name = random.choice(names)
    name = f"{brand} {model_name} {random.randint(100, 999)}"
    variant = random.choice(variants)

    # Variable number of features (1 to 3) + optional extra clauses -> variable document length |D|
    num_feats = random.choice([1, 2, 2, 3])
    feat = random.sample(feats, k=num_feats)
    adj = random.choice(ADJ)
    use_case = random.choice(USE_CASES)
    singular_cat = cat[:-1] if cat.endswith("s") else cat

    if num_feats == 1:
        feat_str = feat[0]
    elif num_feats == 2:
        feat_str = f"{feat[0]} and {feat[1]}"
    else:
        feat_str = f"{feat[0]}, {feat[1]}, and {feat[2]}"

    desc = (
        f"The {name} is a {adj} {singular_cat} ({variant}) "
        f"featuring {feat_str}. Ideal for {use_case}."
    )

    # Vary document length and natural term repetition
    style_roll = random.random()
    if style_roll < 0.30:
        # Short concise description (~14-18 tokens)
        pass
    elif style_roll < 0.75:
        # Medium description (~24-30 tokens)
        desc += " " + random.choice(EXTRA_CLAUSES)
    else:
        # Detailed description (~34-44 tokens), occasionally reinforcing key terms
        extra1, extra2 = random.sample(EXTRA_CLAUSES, k=2)
        reinforce = f"This {adj} {singular_cat} excels in {use_case}." if random.random() < 0.5 else extra2
        desc += f" {extra1} {reinforce}"

    price = round(random.uniform(lo, hi), 2)
    rating = round(min(5.0, max(1.0, random.gauss(4.0, 0.6))), 1)
    stock = random.randint(0, 500)
    reviews = int(abs(random.gauss(200, 250)))
    embedding = compute_embedding(cat, adj, feat, use_case, desc)

    rows.append({
        "product_id": pid,
        "name": name,
        "category": cat,
        "brand": brand,
        "description": desc,
        "price": price,
        "rating": rating,
        "stock": stock,
        "review_count": reviews,
        "embedding": embedding,
    })

# Write combined Elasticsearch bulk file and chunked files (for fast curl ingestion)
bulk_path = os.path.join(OUT, "products_bulk.ndjson")
with open(bulk_path, "w", encoding="utf-8") as full_f:
    for chunk_idx in range(0, len(rows), CHUNK_SIZE):
        chunk_num = (chunk_idx // CHUNK_SIZE) + 1
        chunk_path = os.path.join(OUT, f"products_bulk_{chunk_num}.ndjson")
        with open(chunk_path, "w", encoding="utf-8") as chunk_f:
            for r in rows[chunk_idx: chunk_idx + CHUNK_SIZE]:
                meta_line = json.dumps({"index": {"_index": "products", "_id": r["product_id"]}}) + "\n"
                doc_line = json.dumps(r) + "\n"
                full_f.write(meta_line)
                full_f.write(doc_line)
                chunk_f.write(meta_line)
                chunk_f.write(doc_line)

# Write Cassandra CSV (column order must match COPY statement in load.cql)
cols = ["product_id", "category", "price", "name", "brand", "description", "rating", "stock", "review_count", "embedding"]
with open(os.path.join(OUT, "products.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for r in rows:
        row_vals = [r[c] if c != "embedding" else json.dumps(r[c]) for c in cols]
        w.writerow(row_vals)

num_chunks = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE
print(f"Generated {len(rows):,} products ({num_chunks} bulk chunks) -> {os.path.abspath(OUT)}")
print("Sample:", json.dumps(rows[0], indent=2))
