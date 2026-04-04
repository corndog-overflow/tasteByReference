from pathlib import Path


BASE_DIR     = Path(__file__).resolve().parent
BASE_DIR2     = Path(__file__).resolve().parent.parent

OUTPUT_DIR   = str(BASE_DIR / "raw")
VISITED_FILE = str(BASE_DIR / "visited_urls.txt")
DB_NAME      = str(BASE_DIR2 / "ui" / "recipes.db")

CRAWL_DELAY = (3.5, 7.5)

SEEDS = [
    "https://downshiftology.com/recipes/",   
    "https://cooking.nytimes.com/recipes/1027656-baked-creole-tetrazzini",
    "https://www.bonappetit.com/recipes",
    "https://www.foodnetwork.com/recipes",
    "https://www.allrecipes.com/recipes",
    "https://www.bbcgoodfood.com/recipes",
    "https://www.simplyrecipes.com/recipes",
    "https://www.seriouseats.com/recipes",
    "https://www.delish.com/cooking"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

URL_BLOCKLIST    = {"login", "signin", "signup", "register", "logout",
                    "cart", "checkout", "account", "admin", "search"}
TERMINAL         = {"recipes", "collection", "collections", "ideas"}
SKIP_PREFIXES    = ("mailto:", "javascript:", "tel:", "#")
SKIP_EXTENSIONS  = {".jpg", ".jpeg", ".png", ".gif", ".svg",
                    ".pdf", ".mp4", ".zip", ".ico", ".webp"}

RECIPE_URL_SIGNALS = ("recipe", "easy", "dish", "dinner",
                      "lunch", "breakfast", "appetizer", "dessert")
RECIPE_STRONG_KW   = ["tablespoon", "teaspoon", "cup", "preheat",
                       "simmer", "whisk", "bake", "stir", "chop"]
RECIPE_GENERIC_KW  = ["ingredients", "instructions", "prep time",
                       "cook time", "servings"]
