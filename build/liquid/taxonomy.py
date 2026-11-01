"""Fixed vocabulary of the site: categories, subcategories and ordering (Plan 01 section 4)."""
from __future__ import annotations

# (key, name, vessel) in top-shelf order
CATEGORIES = [
    ("sake", "Sake", "sake"),
    ("makgeolli", "Makgeolli", "makgeolli"),
    ("liqueur", "Liqueur", "liqueur"),
    ("beer", "Beer", "beer"),
    ("wine", "Wine", "wine"),
    ("spirits", "Spirits", "spirits"),
    ("cocktails", "Cocktails", "cocktail"),
]
CATEGORY_NAMES = {k: n for k, n, _ in CATEGORIES}

# Core.Category value -> top-level category key (Plan 01 section 8)
CORE_TO_CATEGORY = {
    "Sake": "sake", "Craft Sake": "sake", "Makgeolli": "makgeolli",
    "Umeshu": "liqueur", "Liqueur": "liqueur", "Beer": "beer", "Wine": "wine",
    "Whisky": "spirits", "Shochu": "spirits", "Soju": "spirits", "Spirit": "spirits",
    "Cocktail": "cocktails",
}

# Native names (Plan 01 section 4.1 table, 4.2 and 4.3 fallback label)
SAKE_NATIVE = {
    "Junmai Daiginjo": "純米大吟醸", "Junmai Ginjo": "純米吟醸", "Tokubetsu Junmai": "特別純米",
    "Junmai": "純米", "Daiginjo": "大吟醸", "Ginjo": "吟醸", "Tokubetsu Honjozo": "特別本醸造",
    "Honjozo": "本醸造", "Futsushu": "普通酒", "Craft Sake": "クラフトサケ", "Ungraded": "日本酒",
}
FALLBACK_NATIVE = {"makgeolli": "막걸리"}
# Native names of liqueur kinds (Plan 01 section 4.3)
LIQUEUR_NATIVE = {"Umeshu": "梅酒", "Yuzushu": "柚子酒"}

# Default sake grade order if the ledger's validation list can't be read (Plan 01 section 4.1)
DEFAULT_SAKE_GRADES = ["Junmai Daiginjo", "Junmai Ginjo", "Tokubetsu Junmai", "Junmai", "Daiginjo",
                       "Ginjo", "Tokubetsu Honjozo", "Honjozo", "Futsushu"]

# Valid Other Detail.Type values per category (Plan 01 sections 4.3 - 4.7, 10.1)
TYPE_VALUES = {
    # kinds of liqueur, for Core.Category = Liqueur (Plan 01 section 4.3)
    "liqueur": ["Yuzushu", "Fruit liqueur", "Herbal", "Cream", "Coffee & tea"],
    # flavour/base of umeshu rows: a card fact, not a subcategory
    "umeshu": ["Classic", "Fruit Blend", "Tea", "Sake-based", "Brandy-based", "Aged", "Other"],
    "beer": ["Lager", "Pilsner", "Pale Ale", "IPA", "Wheat", "Stout/Porter", "Sour", "Saison", "Specialty"],
    "cocktails": ["Highball", "Sour", "Martini", "Old Fashioned", "Spritz", "Other"],
    "spirit": ["Gin", "Brandy", "Rum", "Vodka", "Tequila", "Baijiu"],
}

# Fixed leading order inside Spirits (Plan 01 section 4.6)
SPIRIT_FIRST = ["Whisky", "Gin", "Brandy"]

# Display names for the single fallback bottle of each category (Plan 01 section 4: "named after the category")
FALLBACK_NAME = {
    "makgeolli": "Makgeolli", "liqueur": "Liqueur", "beer": "Beer", "wine": "Wine",
    "spirits": "Spirit", "cocktails": "Cocktail", "sake": "Sake",
}

PREFECTURES = [
    "Hokkaido", "Aomori", "Iwate", "Miyagi", "Akita", "Yamagata", "Fukushima", "Ibaraki", "Tochigi",
    "Gunma", "Saitama", "Chiba", "Tokyo", "Kanagawa", "Niigata", "Toyama", "Ishikawa", "Fukui",
    "Yamanashi", "Nagano", "Gifu", "Shizuoka", "Aichi", "Mie", "Shiga", "Kyoto", "Osaka", "Hyogo",
    "Nara", "Wakayama", "Tottori", "Shimane", "Okayama", "Hiroshima", "Yamaguchi", "Tokushima",
    "Kagawa", "Ehime", "Kochi", "Fukuoka", "Saga", "Nagasaki", "Kumamoto", "Oita", "Miyazaki",
    "Kagoshima", "Okinawa",
]

# Core.Category values that are spirit sub-bottles by themselves
SPIRIT_CORE_SUBS = {"Whisky": "Whisky", "Shochu": "Shochu", "Soju": "Soju"}

# "Other {category}" bottle names where plain lower-casing would read badly (Plan 01 section 4 shared rule)
OTHER_NAME = {"liqueur": "Other liqueurs"}
