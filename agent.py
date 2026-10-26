"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from mcp_client import MCPError, call_tool
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── the MCP tool ──────────────────────────────────────────────────────────────

def search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]:
    """search_listings, called through the MCP server in mcp_server.py."""
    return call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE = re.compile(
    r"(?:under|below|less than|max|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)|\$(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE = re.compile(r"\bsize\s+([a-z0-9][a-z0-9./]*)", re.IGNORECASE)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language, by regex.

    "vintage graphic tee under $30, size M"
        → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    Anything not found comes back as None. Whatever's left after the price and
    size are cut out is the description; search_listings drops filler words.
    """
    rest = query

    max_price = None
    price = _PRICE.search(rest)
    if price:
        max_price = float(price.group(1) or price.group(2))
        rest = rest[: price.start()] + " " + rest[price.end():]

    size = None
    size_match = _SIZE.search(rest)
    if size_match:
        size = size_match.group(1).rstrip(".").upper()
        rest = rest[: size_match.start()] + " " + rest[size_match.end():]

    description = " ".join(re.sub(r"[^\w'\- ]", " ", rest).split())
    return {"description": description, "size": size, "max_price": max_price}


def explain_empty(parsed: dict) -> str:
    """
    Say why a search came back empty and what to change.

    It re-runs the search with one filter removed at a time, so the message
    can say which filter was the blocker rather than just "no results".
    """
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    asked = f"'{description}'"
    if size:
        asked += f" in size {size}"
    if max_price is not None:
        asked += f" under ${max_price:g}"

    keyword_only = search_listings(description)
    if not keyword_only:
        return (
            f"No listings matched {asked}. None of the 40 listings mention those "
            "words at all, so changing the price or size won't help. Try a "
            "different item type (tops, bottoms, outerwear, shoes, accessories) "
            "or a style word like 'vintage', '90s', 'y2k' or 'denim'."
        )

    tips = []
    if max_price is not None and search_listings(description, size, None):
        cheapest = min(l["price"] for l in search_listings(description, size, None))
        tips.append(f"raise your max price to at least ${cheapest:g}")
    if size and search_listings(description, None, max_price):
        sizes = sorted({l["size"] for l in search_listings(description, None, max_price)})
        tips.append(f"drop the size (sizes that match: {', '.join(sizes[:5])})")
    if not tips:
        tips.append("drop both the size and the price limit")

    return f"No listings matched {asked}. To find something, " + " or ".join(tips) + "."


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    iterations = 0
    next_step = "parse"

    while next_step != "done":
        iterations += 1
        trace.check_iterations(iterations)

        if next_step == "parse":
            session["parsed"] = parse_query(session["query"])
            trace.step("parse_query", inputs=session["query"], returned=str(session["parsed"]))
            next_step = "search"

        elif next_step == "search":
            parsed = session["parsed"]
            try:
                session["search_results"] = search_listings(
                    parsed["description"], parsed["size"], parsed["max_price"]
                )
            except MCPError as exc:
                session["error"] = (
                    "The listing search couldn't run, because the MCP search server "
                    "failed, so nothing was searched. Run `python mcp_client.py` to "
                    f"check the server starts, then ask again. Details: {exc}"
                )
                trace.step("search_listings (via MCP)", inputs=str(parsed),
                           returned="MCPError", note="search failed, stopping")
                next_step = "done"
                continue
            # The branch: nothing found means stop here, with a message that
            # says what to change. suggest_outfit never sees an empty result.
            if not session["search_results"]:
                session["error"] = explain_empty(session["parsed"])
                trace.step("search_listings (via MCP)", inputs=str(parsed),
                           returned=session["search_results"],
                           note="branch: empty, stopping before suggest_outfit")
                next_step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                trace.step("search_listings (via MCP)", inputs=str(parsed),
                           returned=session["search_results"],
                           note=f"branch: {len(session['search_results'])} found, "
                                f"selected {session['selected_item']['id']}")
                next_step = "suggest"

        elif next_step in ("suggest", "fit_card"):
            # Both model calls fail the same way: a bad key, no network, or a
            # model name that doesn't resolve. Stop with what was found so far.
            try:
                if next_step == "suggest":
                    session["outfit_suggestion"] = suggest_outfit(
                        session["selected_item"], session["wardrobe"]
                    )
                    trace.step("suggest_outfit",
                               inputs=str({"new_item": session["selected_item"]["id"],
                                       "wardrobe_items": len(session["wardrobe"].get("items") or [])}),
                               returned=session["outfit_suggestion"])
                    next_step = "fit_card"
                else:
                    session["fit_card"] = create_fit_card(
                        session["outfit_suggestion"], session["selected_item"]
                    )
                    trace.step("create_fit_card",
                               inputs=str({"new_item": session["selected_item"]["id"],
                                       "outfit": session["outfit_suggestion"]}),
                               returned=session["fit_card"])
                    next_step = "done"
            except ModelUnavailable as exc:
                item = session["selected_item"]
                session["error"] = (
                    f"Found {item['title']} (${item['price']:g} on {item['platform']}), "
                    f"but couldn't reach the model to "
                    f"{'suggest an outfit' if next_step == 'suggest' else 'write the fit card'}. "
                    f"{exc}"
                )
                trace.step(next_step == "suggest" and "suggest_outfit" or "create_fit_card",
                           returned="ModelUnavailable", note="model unreachable, stopping")
                next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
