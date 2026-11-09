"""
Price estimate engine for Møbelsnekker I&W.

Pure Python (no Django imports) so it can be unit-tested and reused anywhere.
All rates are EXAMPLE values in NOK excluding VAT — adjust them with the
carpenter.  The public result is shown including 25 % VAT, as required for
consumer prices in Norway.
"""
from __future__ import annotations

from dataclasses import dataclass

VAT = 0.25
CURRENCY = "NOK"

# --------------------------------------------------------------------------
# Configuration — edit these numbers to change the calculator.
# --------------------------------------------------------------------------
# area: which surface the rate is applied to
#   "front" = width x height (cabinets, shelving, panels)
#   "top"   = width x depth  (tables, benches, shelves)
TYPES: dict[str, dict] = {
    "kitchen":      {"label": "Kitchen",             "rate": 8500,  "min": 36000, "area": "front", "depth_ref": 60, "dims": (360, 230, 60), "install": True,  "img": "p04_kitchen.jpg"},
    "wardrobe":     {"label": "Wardrobe",            "rate": 6500,  "min": 11000, "area": "front", "depth_ref": 60, "dims": (200, 240, 60), "install": True,  "img": "p06_wardrobe.jpg"},
    "bookshelf":    {"label": "Bookshelf / TV wall", "rate": 4200,  "min": 7000,  "area": "front", "depth_ref": 35, "dims": (300, 240, 35), "install": True,  "img": "p02_tvwall.jpg"},
    "sideboard":    {"label": "Sideboard / cabinet", "rate": 9500,  "min": 6500,  "area": "front", "depth_ref": 45, "dims": (180, 75, 45),  "install": False, "img": "p09_sideboard.jpg"},
    "dining_table": {"label": "Dining table",        "rate": 9000,  "min": 9500,  "area": "top",   "depth_ref": None, "dims": (200, 75, 90), "install": False, "img": "p11_dining.jpg"},
    "coffee_table": {"label": "Coffee / side table", "rate": 10500, "min": 4500,  "area": "top",   "depth_ref": None, "dims": (110, 45, 60), "install": False, "img": "cut_stool.png"},
    "bench":        {"label": "Bench / window seat", "rate": 7000,  "min": 5000,  "area": "top",   "depth_ref": None, "dims": (180, 45, 40), "install": True,  "img": "p11_dining.jpg"},
    "wall_panel":   {"label": "Wall panelling",      "rate": 2600,  "min": 5500,  "area": "front", "depth_ref": None, "dims": (300, 250, 2), "install": True,  "img": "p12_wallpanel.jpg"},
    "shelf":        {"label": "Wall shelf",          "rate": 3800,  "min": 2000,  "area": "top",   "depth_ref": None, "dims": (100, 30, 25), "install": True,  "img": "p13_wallshelf.jpg"},
}

MATERIALS: dict[str, dict] = {
    "chipboard":    {"label": "Laminated chipboard", "mult": 0.75, "swatch": "#e9e4da"},
    "mdf_painted":  {"label": "MDF, painted",        "mult": 1.00, "swatch": "#f2f1ec"},
    "solid_pine":   {"label": "Solid pine",          "mult": 1.05, "swatch": "#e6c99a"},
    "birch_ply":    {"label": "Birch plywood",       "mult": 1.10, "swatch": "#ead8b7"},
    "oak_veneer":   {"label": "Oak veneer",          "mult": 1.25, "swatch": "#d2b48a"},
    "solid_oak":    {"label": "Solid oak",           "mult": 1.65, "swatch": "#b98a55"},
    "solid_walnut": {"label": "Solid walnut",        "mult": 2.20, "swatch": "#6b4630"},
}

FINISHES: dict[str, dict] = {
    "oil":     {"label": "Natural oil / wax",       "mult": 1.00},
    "lacquer": {"label": "Matt lacquer",            "mult": 1.06},
    "paint":   {"label": "Painted, any NCS colour", "mult": 1.12},
    "raw":     {"label": "Untreated",               "mult": 0.95},
}

COMPLEXITY: dict[str, dict] = {
    "simple":   {"label": "Simple",   "hint": "Straight lines, standard sizes",              "mult": 1.00},
    "standard": {"label": "Standard", "hint": "Niches, mix of open and closed parts",         "mult": 1.15},
    "complex":  {"label": "Complex",  "hint": "Sloped ceiling, curves, inlays, marquetry",    "mult": 1.35},
}

HARDWARE: dict[str, dict] = {
    "standard": {"label": "Standard hinges & runners", "per_unit": 0},
    "premium":  {"label": "Blum soft-close / push-to-open", "per_unit": 350},
}

EXTRAS: dict[str, dict] = {
    "drawers":     {"label": "Drawers",          "price": 1100, "max": 40},
    "doors":       {"label": "Doors",            "price": 550,  "max": 40},
    "glass_doors": {"label": "Glass doors",      "price": 1400, "max": 20},
    "led":         {"label": "LED light strips", "price": 2200, "max": 20},
}

DELIVERY: dict[str, dict] = {
    "pickup":    {"label": "Pick-up at the workshop", "price": 0},
    "oslo":      {"label": "Oslo",                    "price": 900},
    "akershus":  {"label": "Akershus",                "price": 1500},
    "ostlandet": {"label": "Rest of Østlandet",       "price": 3200},
}

INSTALL_PCT = 0.12          # of production cost
INSTALL_MIN = 2500
DRAWINGS_PRICE = 1200       # free when the project is big enough
DRAWINGS_FREE_FROM = 20000
FLOOR_PRICE = 200           # per floor without elevator (from 2nd floor)
RUSH_PCT = 0.20
RANGE_LOW, RANGE_HIGH = 0.90, 1.15

LIMITS = {"width": (10, 800), "height": (2, 300), "depth": (2, 120)}


class EstimateError(ValueError):
    pass


@dataclass
class Line:
    label: str
    amount: int  # NOK excl. VAT

    def as_dict(self):
        return {"label": self.label, "amount": self.amount}


def _choice(data, key, table, default):
    value = data.get(key) or default
    if value not in table:
        raise EstimateError(f"Unknown {key}: {value!r}")
    return value


def _num(data, key, default, lo, hi, cast=float):
    raw = data.get(key, default)
    if raw in (None, ""):
        raw = default
    try:
        val = cast(raw)
    except (TypeError, ValueError):
        raise EstimateError(f"{key} must be a number")
    return max(lo, min(hi, val))


def _bool(data, key, default=False):
    v = data.get(key, default)
    if isinstance(v, str):
        return v.lower() in ("1", "true", "on", "yes")
    return bool(v)


def _round(n, step=100):
    return int(round(n / step) * step)


def estimate(data: dict) -> dict:
    """Return a full estimate for the given calculator input (dict-like)."""
    t_key = _choice(data, "type", TYPES, "wardrobe")
    t = TYPES[t_key]
    dw, dh, dd = t["dims"]
    w = _num(data, "width", dw, *LIMITS["width"])
    h = _num(data, "height", dh, *LIMITS["height"])
    d = _num(data, "depth", dd, *LIMITS["depth"])

    material = _choice(data, "material", MATERIALS, "oak_veneer")
    finish = _choice(data, "finish", FINISHES, "oil")
    complexity = _choice(data, "complexity", COMPLEXITY, "standard")
    hardware = _choice(data, "hardware", HARDWARE, "standard")
    delivery = _choice(data, "delivery", DELIVERY, "oslo")

    counts = {k: int(_num(data, k, 0, 0, v["max"], cast=float)) for k, v in EXTRAS.items()}
    floor = int(_num(data, "floor", 1, 0, 30, cast=float))
    elevator = _bool(data, "elevator", False)
    install = _bool(data, "installation", t["install"])
    drawings = _bool(data, "drawings", False)
    rush = _bool(data, "rush", False)

    # --- production -------------------------------------------------------
    area = (w / 100) * ((h if t["area"] == "front" else d) / 100)
    depth_factor = 1.0
    if t["depth_ref"]:
        depth_factor = max(0.8, min(1.5, 1 + 0.6 * (d / t["depth_ref"] - 1)))

    base = area * t["rate"] * depth_factor
    m = MATERIALS[material]["mult"]
    f = FINISHES[finish]["mult"]
    c = COMPLEXITY[complexity]["mult"]

    lines: list[Line] = []
    body = base * m * f * c
    if body < t["min"]:
        body = t["min"]
    lines.append(Line(f'{t["label"]} · {w:g}×{h:g}×{d:g} cm · {MATERIALS[material]["label"]}', _round(body)))

    extras_total = 0
    for k, n in counts.items():
        if n:
            amt = n * EXTRAS[k]["price"] * (m if k != "led" else 1)
            extras_total += amt
            lines.append(Line(f'{EXTRAS[k]["label"]} × {n}', _round(amt)))
    hw_units = counts["drawers"] + counts["doors"] + counts["glass_doors"]
    if HARDWARE[hardware]["per_unit"] and hw_units:
        amt = hw_units * HARDWARE[hardware]["per_unit"]
        extras_total += amt
        lines.append(Line(f'{HARDWARE[hardware]["label"]} × {hw_units}', _round(amt)))

    production = body + extras_total
    if rush:
        amt = production * RUSH_PCT
        lines.append(Line("Express production (+20 %)", _round(amt)))
        production += amt

    # --- services ---------------------------------------------------------
    services = 0
    if install:
        amt = max(INSTALL_MIN, production * INSTALL_PCT)
        services += amt
        lines.append(Line("Installation on site", _round(amt)))
    if drawings:
        amt = 0 if production >= DRAWINGS_FREE_FROM else DRAWINGS_PRICE
        services += amt
        lines.append(Line("Technical drawings" + (" (free)" if amt == 0 else ""), _round(amt)))
    dl = DELIVERY[delivery]["price"]
    if dl:
        services += dl
        lines.append(Line(f'Delivery · {DELIVERY[delivery]["label"]}', dl))
        if not elevator and floor > 1:
            amt = (floor - 1) * FLOOR_PRICE
            services += amt
            lines.append(Line(f"Carrying to floor {floor} (no elevator)", amt))

    subtotal = _round(production + services)
    vat = _round(subtotal * VAT)
    total = subtotal + vat

    weeks = 2 + production / 25000
    if rush:
        weeks *= 0.6
    weeks_lo = max(1, int(round(weeks)))
    weeks_hi = weeks_lo + (1 if weeks < 4 else 2)

    return {
        "input": {
            "type": t_key, "width": w, "height": h, "depth": d,
            "material": material, "finish": finish, "complexity": complexity,
            "hardware": hardware, "delivery": delivery, "floor": floor,
            "elevator": elevator, "installation": install, "drawings": drawings,
            "rush": rush, **counts,
        },
        "title": t["label"],
        "lines": [l.as_dict() for l in lines],
        "subtotal": subtotal,
        "vat": vat,
        "total": total,
        "low": _round(total * RANGE_LOW, 500),
        "high": _round(total * RANGE_HIGH, 500),
        "currency": CURRENCY,
        "lead_time_weeks": [weeks_lo, weeks_hi],
        "area_m2": round(area, 2),
    }


def options() -> dict:
    """Everything the front-end needs to render the calculator."""
    return {
        "types": {k: {"label": v["label"], "dims": v["dims"], "area": v["area"],
                      "install": v["install"], "img": v["img"],
                      "from": _round(v["min"] * (1 + VAT), 100)} for k, v in TYPES.items()},
        "materials": {k: {"label": v["label"], "swatch": v["swatch"]} for k, v in MATERIALS.items()},
        "finishes": {k: {"label": v["label"]} for k, v in FINISHES.items()},
        "complexity": {k: {"label": v["label"], "hint": v["hint"]} for k, v in COMPLEXITY.items()},
        "hardware": {k: {"label": v["label"]} for k, v in HARDWARE.items()},
        "extras": {k: {"label": v["label"], "max": v["max"]} for k, v in EXTRAS.items()},
        "delivery": {k: {"label": v["label"]} for k, v in DELIVERY.items()},
        "limits": LIMITS,
    }
