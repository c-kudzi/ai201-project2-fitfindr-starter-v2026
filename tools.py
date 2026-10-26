"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that say nothing about the item. Matching on these would score every
# listing, so they're dropped before scoring.
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to", "my",
    "i", "im", "i'm", "me", "want", "looking", "need", "some", "something",
    "any", "find", "please", "size", "under", "below", "less", "than", "max",
    "up", "price", "length", "style",
}


def _words(text: str) -> list[str]:
    """Lowercase word tokens, keeping things like '90s' and 'y2k' whole."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _stem(word: str) -> str:
    """Crude plural strip, so 'sneakers' matches 'sneaker' and 'jeans' 'jean'."""
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _size_tokens(size: str) -> set[str]:
    return {t for t in re.split(r"[\s/()]+", size.lower()) if t}


def _size_matches(listing_size: str, wanted: str) -> bool:
    """Whole-token match, so 'M' matches 'S/M' but not 'XL', and 'S' not 'US 9'."""
    if "one size" in listing_size.lower():
        return True
    return bool(_size_tokens(listing_size) & _size_tokens(wanted))


def _score(listing: dict, keywords: set[str]) -> int:
    """2 per keyword in title, style tags or category; 1 if only in description, colors or brand."""
    strong = {_stem(w) for w in _words(
        " ".join([listing["title"], listing["category"], *listing["style_tags"]])
    )}
    weak = {_stem(w) for w in _words(
        " ".join([listing["description"], *listing["colors"], listing["brand"] or ""])
    )}
    score = 0
    for word in keywords:
        if word in strong:
            score += 2
        elif word in weak:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = {_stem(w) for w in _words(description or "") if w not in STOPWORDS}
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(listing["size"], size):
            continue
        score = _score(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        system = (
            "You are a thrift stylist. The user has no saved wardrobe, so give "
            "general styling advice. Do not pretend they own anything. Plain "
            "text, no markdown, 2 to 6 short lines."
        )
        prompt = (
            f"The user is considering this thrifted item:\n{item_text}\n\n"
            "Suggest one or two outfits built around it, using common basics "
            "anyone could pick up (describe them by type and color)."
        )
    else:
        owned = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])}; "
            f"style: {', '.join(w['style_tags'])})"
            for w in items
        )
        system = (
            "You are a thrift stylist. Build outfits only from the new item plus "
            "pieces the user already owns, and name each owned piece exactly as "
            "it is written in their wardrobe list. Plain text, no markdown, "
            "2 to 6 short lines."
        )
        prompt = (
            f"The user is considering this thrifted item:\n{item_text}\n\n"
            f"Their wardrobe:\n{owned}\n\n"
            "Suggest one or two outfits that pair the new item with pieces from "
            "the wardrobe."
        )

    response = generate(prompt, system=system).strip()
    if not response:
        return (
            f"Style the {new_item['title']} with simple basics in neutral colors "
            "and let it be the focus."
        )
    return response


def _describe_item(item: dict) -> str:
    """The listing as prompt text. Leaves out brand when there isn't one."""
    lines = [
        f"Title: {item['title']}",
        f"Category: {item['category']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Size: {item['size']}",
        f"Condition: {item['condition']}",
        f"Price: ${item['price']:.2f} on {item['platform']}",
        f"Description: {item['description']}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            f"No fit card: there was no outfit suggestion for "
            f"{new_item.get('title', 'this item')} to write about."
        )

    system = (
        "You write captions people post with their thrift finds. Casual, first "
        "person, specific about the vibe. 2 to 4 sentences. Mention the price "
        "and the platform exactly once each. At most 3 hashtags, at the end. "
        "Only mention a brand if one is given. No quotation marks around the "
        "caption, no preamble."
    )
    prompt = (
        f"The find:\n{_describe_item(new_item)}\n\n"
        f"How I'm wearing it:\n{outfit.strip()}\n\n"
        "Write the caption."
    )
    return generate(prompt, system=system).strip()
