"""Generate a synthetic e-commerce product catalog for the search demo.

Outputs (into demo/data/):
  - products_bulk.ndjson : Elasticsearch _bulk format
  - products.csv         : for Cassandra COPY
Stdlib only — no pip installs needed.
"""
import json, csv, random, os, math

random.seed(42)
N = 5000
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)

CATEGORIES = {
    "laptops": (["UltraBook", "ProBook", "GameMaster", "AirLite", "WorkStation"],
                ["14-inch", "15.6-inch", "16-inch OLED", "13.3-inch touchscreen"],
                ["Intel Core i7", "AMD Ryzen 9", "Intel Core i5", "Apple M3"],
                (450, 3500)),
    "smartphones": (["Galaxy", "Pixel Pro", "Xperia", "Nova", "RedMagic"],
                    ["128GB", "256GB", "512GB", "1TB"],
                    ["5G dual-SIM", "AMOLED 120Hz", "titanium frame", "foldable display"],
                    (200, 1800)),
    "headphones": (["SoundCore", "QuietComfort", "StudioPro", "BassBoost", "AirPods-style"],
                   ["wireless", "noise cancelling", "over-ear", "in-ear sport"],
                   ["Bluetooth 5.3", "40h battery", "hi-res audio", "low-latency gaming"],
                   (25, 550)),
    "cameras": (["AlphaShot", "EOS-Line", "LumixPro", "ActionCam", "InstaView"],
                ["mirrorless", "DSLR", "action camera", "instant film"],
                ["24MP full-frame", "4K 60fps video", "waterproof 10m", "optical zoom 30x"],
                (150, 4200)),
    "coffee machines": (["EspressoMaster", "BrewPerfect", "MokaPro", "ColdDrip", "BaristaOne"],
                        ["automatic", "semi-automatic", "manual lever", "capsule"],
                        ["15-bar pump", "built-in grinder", "milk frother", "thermal carafe"],
                        (40, 1200)),
    "running shoes": (["CloudRunner", "SpeedForm", "TrailGrip", "MarathonX", "FlexStep"],
                      ["men's", "women's", "unisex"],
                      ["carbon plate", "breathable mesh", "waterproof gore-tex", "extra cushioning"],
                      (35, 280)),
}
BRANDS_BY_CAT = {
    "laptops": ["Dell", "Asus", "Lenovo", "Apple", "HP", "MSI"],
    "smartphones": ["Samsung", "Apple", "Xiaomi", "Sony", "Google", "Oppo"],
    "headphones": ["Sony", "Bose", "JBL", "Anker", "Sennheiser", "Apple"],
    "cameras": ["Canon", "Nikon", "Sony", "Fujifilm", "GoPro", "Panasonic"],
    "coffee machines": ["DeLonghi", "Breville", "Philips", "Nespresso", "Gaggia"],
    "running shoes": ["Nike", "Adidas", "Asics", "New Balance", "Hoka", "Brooks"],
}
ADJ = ["premium", "budget-friendly", "professional", "compact", "lightweight",
       "ergonomic", "durable", "stylish", "high-performance", "energy-efficient"]
TYPO_TARGETS = {}  # keep track for fuzzy-search demo talking points

rows = []
for pid in range(1, N + 1):
    cat = random.choice(list(CATEGORIES))
    names, variants, feats, (lo, hi) = CATEGORIES[cat]
    brand = random.choice(BRANDS_BY_CAT[cat])
    name = f"{brand} {random.choice(names)} {random.randint(100, 999)}"
    variant = random.choice(variants)
    feat = random.sample(feats, k=2)
    adj = random.choice(ADJ)
    desc = (f"The {name} is a {adj} {cat[:-1] if cat.endswith('s') else cat} "
            f"({variant}) featuring {feat[0]} and {feat[1]}. "
            f"Ideal for {random.choice(['everyday use', 'professionals', 'students', 'travel', 'home and office'])}.")
    price = round(random.uniform(lo, hi), 2)
    rating = round(min(5.0, max(1.0, random.gauss(4.0, 0.6))), 1)
    stock = random.randint(0, 500)
    reviews = int(abs(random.gauss(200, 250)))
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
    })

# Elasticsearch bulk file
with open(os.path.join(OUT, "products_bulk.ndjson"), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps({"index": {"_index": "products", "_id": r["product_id"]}}) + "\n")
        f.write(json.dumps(r) + "\n")

# Cassandra CSV (column order must match COPY statement)
cols = ["product_id", "category", "price", "name", "brand", "description", "rating", "stock", "review_count"]
with open(os.path.join(OUT, "products.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for r in rows:
        w.writerow([r[c] for c in cols])

print(f"Generated {len(rows)} products -> {os.path.abspath(OUT)}")
print("Sample:", json.dumps(rows[0], indent=2))
