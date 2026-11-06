"""Build the phone dashboard (camper_phone.yaml) from the desktop one (camper.yaml).

Phone layout (2026-10-18): no badge bar. The home page is a grid of big tiles made
from the desktop home view's badges (same icon, colors, live text, tap actions and
orange "on" highlight). Every other page is a subview with a back arrow to the tiles.
Since 2026-10-25 it's laid out for an 8" tablet in landscape (about 960x600): the home
page is a "sections" view - header + a full-width 6-across tile grid on top, then the
rest of the desktop home cards in two columns (people/weather, temperature).

Run after any change to camper.yaml:
  docker exec homeassistant python3 /config/dashboards/make_phone_dashboard.py
"""
import re
import yaml

SRC = "/config/dashboards/camper.yaml"
DST = "/config/dashboards/camper_phone.yaml"
DESK = "/lovelace-camper/"
PHONE = "/lovelace-phone/"
HOME = PHONE + "home"
SHOP_PAGES = {"cereal", "dog-food", "little-debbie", "dawn", "sealant", "laundry",
              "paper-towels", "toilet-paper"}

TILE_STYLE = """ha-card {
  --primary-text-color: #2B2A28 !important;
  --secondary-text-color: #6B6558 !important;
  opacity: 1 !important;
  background: #FFFFFF !important;
  border-radius: 18px !important;
  border: 1px solid #E3D9C7 !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.25) !important;
  padding: 12px 6px !important;
}
ha-tile-icon { --tile-icon-size: 56px; --mdc-icon-size: 36px; }
ha-card [slot=primary] { color: #2B2A28 !important; font-size: 18px !important; font-weight: 700 !important; white-space: normal !important; line-height: 1.15 !important; }
ha-card [slot=secondary] { color: #6B6558 !important; font-size: 15px !important; font-weight: 600 !important; white-space: normal !important; }
"""


def relink(obj):
    """Point desktop navigation paths at the phone dashboard."""
    if isinstance(obj, dict):
        return {k: relink(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [relink(v) for v in obj]
    if isinstance(obj, str):
        return obj.replace(DESK + "camper", HOME).replace(DESK, PHONE)
    return obj


def badge_highlight(badge):
    """Turn a badge's card_mod highlight (.badge / .label / .content) into tile CSS."""
    style = ((badge.get("card_mod") or {}).get("style") or "")
    if ".badge" not in style or "outline" in style:
        return ""
    style = style.replace(".badge {", "ha-card {")
    style = style.replace(".label, .content {", "ha-card [slot=primary], ha-card [slot=secondary] {")
    # Drop the icon color rules but keep icon animations (the spinning ceiling fan)
    return re.sub(r"\n?\s*ha-state-icon \{(?![^}]*animation)[^}]*\}", "", style)


def card_weight(card):
    """Rough height of a card: 1 + all the cards nested inside it."""
    kids = card.get("cards") or ([card["card"]] if isinstance(card.get("card"), dict) else [])
    return 1 + sum(card_weight(k) for k in kids)


def two_columns(cards):
    """Masonry-style split into 2 sections (each card goes to the shorter column, order kept).
    At ~960 px the masonry view makes 3 narrow columns that squeeze wide cards like the
    thermostat panel; 2 sections of full-width cards are bigger and easier to read."""
    cols, h = [[], []], [0, 0]
    # The fixed beach background and the page title take no room in a column, so they and
    # the first real card all start the left column (title on top, like the desktop).
    lead = 2 if cards and cards[0].get("type") == "markdown" and not str(cards[0].get("content", "")).strip() else 1
    for n, c in enumerate(cards):
        i = 0 if h[0] <= h[1] else 1
        cols[i].append(dict(c, grid_options={"columns": "full"}))
        h[i] += 0 if n < lead else card_weight(c)
    return [{"type": "grid", "cards": col} for col in cols if col]


def is_titled(card, title):
    """True if the card (or a title card directly inside it) has this title."""
    return card.get("title") == title or any(
        k.get("title") == title for k in card.get("cards") or [] if isinstance(k, dict))


def tile(badge):
    card = {"type": "custom:mushroom-template-card",
            "primary": badge.get("label", ""),
            "secondary": badge.get("content", ""),
            "icon": badge.get("icon", ""),
            "icon_color": badge.get("icon_color", ""),
            "layout": "vertical",
            "multiline_secondary": True,
            "fill_container": True}
    for k in ("tap_action", "hold_action", "double_tap_action"):
        if k in badge:
            card[k] = badge[k]
    style = TILE_STYLE + badge_highlight(badge)
    if len(badge.get("label", "")) > 10:  # long single words ("Dehumidifier") don't fit at 18px
        style += "ha-card [slot=primary] { font-size: 15px !important; }\n"
    card["card_mod"] = {"style": style}
    return card


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def str_rep(dumper, s):
    if "\n" in s:
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", s)


Dumper.add_representer(str, str_rep)


def main():
    desk = yaml.safe_load(open(SRC))
    views = desk["views"]
    home = views[0]

    tiles = [tile(b) for b in home.get("badges", []) if b.get("label") != "Home"]
    # The tablet has no Shortcuts card (the user asked 2026-10-25); the desktop keeps it.
    home_cards = [c for c in home.get("cards", []) if not is_titled(c, "Shortcuts")]
    # full width: background, header, tile grid; below it the rest of the desktop home
    # split into two columns (first half / second half of the remaining cards)
    grid = {"type": "grid", "columns": 6, "square": False, "cards": tiles}
    full = {"columns": "full"}  # sections make cards half width by default
    home_cards = [dict(c, grid_options=full) for c in home_cards]
    grid["grid_options"] = full
    rest = home_cards[2:]
    half = (len(rest) + 1) // 2
    phone_home = {"title": "🚐 Camper", "path": "home", "icon": "mdi:rv-truck",
                  "type": "sections", "max_columns": 2,
                  "sections": [{"type": "grid", "column_span": 2, "cards": home_cards[:2] + [grid]},
                               {"type": "grid", "cards": rest[:half]},
                               {"type": "grid", "cards": rest[half:]}]}

    phone_views = [phone_home]
    for v in views[1:]:
        v = dict(v)
        v.pop("badges", None)
        v.pop("visible", None)
        v["subview"] = True
        v["back_path"] = PHONE + "shopping" if v.get("path") in SHOP_PAGES else HOME
        if v.get("type") in (None, "masonry") and v.get("cards"):
            v["type"] = "sections"
            v["max_columns"] = 2
            v["sections"] = two_columns(v.pop("cards"))
        phone_views.append(v)

    out = {k: v for k, v in desk.items() if k != "views"}
    out["title"] = "📱 Camper Phone"
    out["views"] = phone_views
    out = relink(out)

    with open(DST, "w") as f:
        f.write("# GENERATED by make_phone_dashboard.py from camper.yaml - do not edit here.\n"
                "# Change camper.yaml, then re-run the script.\n")
        yaml.dump(out, f, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=4096)
    print(f"wrote {DST}: {len(tiles)} tiles, {len(phone_views)} views")


main()
