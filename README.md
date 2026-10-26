# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

You type what you're thrifting for in plain words, such as `'vintage graphic tee under $30, size M'`. FitFindr pulls the price ceiling and size out of the query and searches 40 secondhand listings from Depop, thredUp and Poshmark for the best keyword match. If it finds one, it asks the model for one or two outfits that pair the item with pieces from your saved wardrobe, then writes a short caption you could post with it. If nothing matches, it stops before the model calls and tells you which filter blocked the search and what to change.



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

**What the data holds (Milestone 1).** 40 listings in `data/listings.json`.
Each has `id`, `title`, `description`, `category` (tops, bottoms, outerwear,
shoes, accessories), `style_tags` (list), `size`, `condition`, `price` (float),
`colors` (list), `brand` (str or None, and None for most), `platform` (depop,
thredUp, poshmark). Sizes are not one format: letter sizes (`M`, `S/M`,
`L/XL`, `XL (oversized)`), waists (`W28`, `W30 L30`), shoes (`US 8`, `US 8.5`)
and one-size items (`One Size`, `One Size (adjustable)`). A wardrobe is
`{"items": [...]}`, each item with `id`, `name`, `category`, `colors`,
`style_tags`, `notes`. The empty wardrobe is `{"items": []}`.

### `search_listings`

- **What it does:** Filters the 40 listings by price ceiling and size, scores the rest by how many query keywords appear in each listing, and returns the best matches first. It makes no model call.
- **Inputs:** `description` (str): keywords such as `"vintage graphic tee"`. `size` (str or None): a size such as `"M"`, `"W30"` or `"8"`, or None to skip size filtering. `max_price` (float or None): inclusive price ceiling, or None to skip price filtering.
- **Returns:** A `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) whole listing dicts, highest score first, with ties going to the lower price. Each dict has the same fields as the data: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Scoring: a keyword found in the title, a style tag or the category counts 2; one found only in the description, colors or brand counts 1. A listing that scores 0 is dropped.
  - **Size matching rule:** the listing's size and the requested size are both split into lowercase tokens on spaces, `/`, `(` and `)`, and a listing matches if it shares a whole token with the request. So `M` matches `S/M`, `M` and `M/L`, but not `XL`, `W30 L30` or `US 9`. `8` matches `US 8` but not `US 8.5`. A listing whose size contains "one size" matches any requested size.
- **When it has nothing:** It returns an empty list `[]`, never None and never an exception. An empty or stopword-only `description` also returns `[]`.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, naming pieces from the user's wardrobe by their `name`.
- **Inputs:** `new_item` (dict): one listing dict. `wardrobe` (dict): `{"items": [wardrobe item dicts]}`, where `items` may be empty.
- **Returns:** A non-empty `str` of 2 to 6 short lines of plain text: one or two outfit ideas, each naming the wardrobe pieces it uses.
- **When it has nothing:** If `wardrobe["items"]` is empty (or missing), it asks for general styling advice for the item instead, with no wardrobe pieces named, and still returns a non-empty `str`. If the model sends back blank text, it returns a fixed fallback sentence: `"Style the <title> with simple basics in neutral colors and let it be the focus."`

### `create_fit_card`

- **What it does:** Asks the model for a short caption someone would post about the find.
- **Inputs:** `outfit` (str): the text `suggest_outfit` returned. `new_item` (dict): the same listing dict.
- **Returns:** A `str` caption of 2 to 4 sentences in a casual first-person voice, mentioning the item's price and platform once each, with at most 3 hashtags at the end. The brand is mentioned only when the listing has one.
- **When it has nothing:** If `outfit` is empty or only whitespace, it makes no model call and returns `"No fit card: there was no outfit suggestion for <title> to write about."`

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that says which filter blocked the search and what to change (raise the price, drop the size, or use other words), and stop. `suggest_outfit` and `create_fit_card` are not called and `session["fit_card"]` stays None. Otherwise, take the first result as `session["selected_item"]` and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. The price comes from `under $30`, `below 30`, `less than $30`, `max $30`, `up to $30` or a bare `$30`. The size comes from `size M` or `size 8.5`. Both are cut out of the query and what's left becomes the description. Filler words like "looking", "for", "a" and "in" stay in the description and are dropped by `search_listings` before scoring.

**Empty-search message:** `agent.py::explain_empty` re-runs the search with one filter removed at a time to find the blocker. If no listing contains the words at all, it says so and suggests item types and style words that exist. If the price was the blocker, it gives the cheapest price that would match. If the size was, it lists the sizes that would match.

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` → *branch* → `selected_item` → `outfit_suggestion` → `fit_card`. Each tool reads its inputs out of the session, not from the previous call's return value.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query** (example wardrobe)

```
$ python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1:
Y2K Baby Tee — Butterfly Print
Baggy straight-leg jeans, dark wash
Chunky white sneakers
Black crossbody bag

Outfit 2:
Y2K Baby Tee — Butterfly Print
Wide-leg khaki trousers
Brown leather belt
Black combat boots

  Fit card: Found this little butterfly tee and I'm obsessed with the pastel print. It was only $18.00 on depop and the fit is so snatched. Perfect for throwing on with baggy jeans or slouchy trousers. #y2kstyle #babytee #thriftedfashion

0 model calls this session, 2 served from cache
```

**The empty-search branch**

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched 'designer ballgown' in size XXS under $5. None of the 40 listings mention those words at all, so changing the price or size won't help. Try a different item type (tops, bottoms, outerwear, shoes, accessories) or a style word like 'vintage', '90s', 'y2k' or 'denim'.

0 model calls this session
```

**The three tools, tested one at a time**

`search_listings`, a matching search and the empty case:

```
$ python -c "from tools import search_listings; print([(l['id'], l['title'], l['size'], l['price']) for l in search_listings('graphic tee', size='M', max_price=30)]); print(search_listings('designer ballgown', size='XXS', max_price=5))"
[('lst_002', 'Y2K Baby Tee — Butterfly Print', 'S/M', 18.0), ('lst_017', 'Mesh Long-Sleeve Top — Black', 'S/M', 15.0)]
[]
```

`suggest_outfit` with the example wardrobe:

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1:
Vintage Levi's 501 Jeans — Medium Wash
White ribbed tank top
Chunky white sneakers
Black crossbody bag

Outfit 2:
Vintage Levi's 501 Jeans — Medium Wash
Oversized grey crewneck sweatshirt
Brown leather belt
Black combat boots
```

`create_fit_card` with an outfit, then with an empty outfit:

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0])); print(create_fit_card('', load_listings()[0]))"
Found these vintage Levi's 501s and the fade at the knees is just so good. Tossed them on with some fresh white sneakers for that effortless everyday look. Scoring these for $38.00 on depop totally made my week. #levis #vintage #denim
No fit card: there was no outfit suggestion for Vintage Levi's 501 Jeans — Medium Wash to write about.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
