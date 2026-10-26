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

Kudzaishe Chikowore — FitFindr

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

**Why whole tokens and not a substring test.** I counted. A plain substring test for `S` matches 16 listings, and 6 of those are wrong: every shoe (`US 7`, `US 8`, `US 8.5`, `US 9`) and both `XL (oversized)` tops. For `L` it matches 13, and 4 are wrong: `W30 L30` jeans and three XLs. Whole-token matching drops all 10 of those. It returns *more* for `M` (18 instead of 14) only because one-size items now count, and I decided that on purpose: a one-size bag fits anyone who asked for a size M.

**What this search is bad at, and I'm not going to pretend otherwise.** It's a keyword match with no idea what words mean. "vintage" appears in 29 of the 40 listings, so a query that leans on it barely narrows anything. `'vintage graphic tee under $30'` returns 10 results, and a belt and a bucket hat are in them because they match "vintage". When scores tie, the cheaper listing wins, which is why the $18 Y2K baby tee beats the $19 band tee for that query. "tee" won't match "t-shirt", and "sneakers" only matches "sneaker" because of a crude plural strip.

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

**1. I asked Claude to test the fit card, and the first result was a false pass.**
I had it run `create_fit_card` three times on the same item (the 2003 tour
graphic tee) with the same outfit, to check that the captions vary. Three
captions came back identical word for word. That isn't the tool. It's the
starter's cache (`CACHE_ENABLED` in `config.py`) handing back the first
answer.

Re-run with `AI201_CACHE=0`, the three captions were different, but two of
them opened with the same sentence: "Found my new favorite concert tee even
though I definitely wasn't at this show in 2003." So "the captions are
different" is too weak a bar, because two cards can differ and still read the
same. I took that into account when writing my fit-card criterion. The lesson
I'm taking from project 1 still holds: a result from an AI isn't a
measurement until I know what produced it.

**2. I asked it to review my README against the code, and the README was the
part that was wrong.** The grader checks the code against what the README
claims, so I had Claude check the Planning Loop section line by line against
`agent.py`. The README said `parse_query` strips filler words like "looking
for" and "in". It doesn't: `parse_query("90s track jacket in size M")` returns
the description `"90s track jacket in"`. The words are dropped later, by the
`STOPWORDS` set in `tools.py::search_listings`.

What I changed: the README, not the code. The behavior was fine. The sentence
describing it was wrong, and changing working code to match a wrong sentence
would have been backwards. The same review caught a number I'd been told
earlier, that "vintage" appears in 36 of the 40 listings. Recounted, it's 29.

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

Run with `python run_eval.py --label before`: 9 scenarios, 5 tries each, cache off, temperature 0.9, 80 model calls. Evidence file: `results/run_2026-10-25_2231_before.md`. Each try was marked PASS or FAIL by `score_run.py`, which applies each criterion's wording literally. I committed it with `scenarios.py` *before* the first run, so the rules couldn't drift to fit the results.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item is first result / outfit names its title | 5 of 5 / 4 of 5 | PASS / PASS | PASS / PASS | PASS / PASS | PASS / PASS | PASS / PASS | MET (5/5 and 5/5) |
| 4. Fit card follows the caption rules | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Empty wardrobe invents no owned clothes | 4 of 5 | FAIL | PASS | FAIL | PASS | PASS | MISSED (3/5) |

Criterion 4's Try N is the first run of the Nth query (graphic tee, track jacket, slip dress, platform sneakers, denim jacket). I fixed that mapping in `scenarios.py` before running. Across all 25 fit cards produced, 24 passed. The one failure was slip dress try 5, which isn't a counted try. It's covered under Diagnoses.

**A mistake in my own measurement, caught before I called anything.** The first time I scored this run, criterion 2 came out **0 of 5**. That can't be right for a path with no model call, so I read the raw log. Every try had stopped correctly at step 2. The scorer checked whether the text "suggest_outfit" appeared anywhere in the trace, and my branch's own trace note says "stopping before suggest_outfit". I changed the check to look for a trace *step* named `suggest_outfit` (commit `88b8144`). The agent and the criterion didn't change; the measurement did.

**Real output from one try per criterion**, all from `results/run_2026-10-25_2231_before.md`, produced by `run_eval.py::main` running `agent.py::run_agent`:

Criterion 1, try 1, `'vintage graphic tee under $30'`: completed, fit card from `tools.py::create_fit_card`:

```
Found this little butterfly tee and I'm obsessed with the pastel colors. Got it for $18.00 on depop and the fit is genuinely so flattering. Going to style it with baggy jeans and chunky sneakers for running errands today. #y2kstyle #babytee #thrifted
```

Criterion 2, try 1, `'designer ballgown size XXS under $5'`: the message from `agent.py::explain_empty`, and the trace stops at step 2:

```
- stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5. None of the 40 listings mention those words at all, so changing the price or size won't help. Try a different item type (tops, bottoms, outerwear, shoes, accessories) or a style word like 'vintage', '90s', 'y2k' or 'denim'.
- selected_item: (none)
- search_results: 0

[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit
```

Criterion 3, try 1, `'vintage graphic tee under $30, size M'`: the first search result is the selected item (lst_002), and the same id goes into `suggest_outfit`, which names it word for word:

```
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)

[2] search_listings (via MCP)
      out: 10 items: Y2K Baby Tee — Butterfly Print, Leather Belt — Brown, Braided, Bucket Hat — Reversible, Brown Plaid … +7 more
      →    branch: 10 found, selected lst_002
[3] suggest_outfit
      in:  {'new_item': 'lst_002', 'wardrobe_items': 10}

Outfit suggestion:
Outfit 1:
Y2K Baby Tee — Butterfly Print
Baggy straight-leg jeans, dark wash
...
```

Criterion 4, try 2 (track jacket, $45.0 on poshmark): price `45`, platform `poshmark`, 3 sentences, 3 hashtags:

```
Found this vintage Champion track jacket and it is officially my new favorite layering piece. Tossed it on with baggy denim and chunky sneakers for the ultimate 90s athletic vibe. Score of the century for $45.00 on poshmark. #vintage #streetwear #champion
```

Criterion 5, try 1 (a FAIL), `'denim jacket under $50'` with the empty wardrobe, outfit from `tools.py::suggest_outfit`:

```
Pair the cropped jacket with a simple white ribbed tank top and black high-waisted wide-leg trousers.
Add chunky black loafers and a minimal leather shoulder bag to complete the look.
Alternatively, layer it over a black maxi slip dress with worn-in white canvas sneakers.
This Wrangler piece is a classic vintage find, though forty-two dollars is a bit steep for Poshmark.
```

"white ribbed tank top" is the example wardrobe's "White ribbed tank top", word for word.

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
| 1 | Matching query completes all three tools | 4 of 5 | MET (5/5) | All five tries returned a fit card with no error and no crash. |
| 2 | Impossible query stops before suggest_outfit | 5 of 5 | MET (5/5) | All five stopped at step 2, with no `suggest_outfit` step, no fit card, and a message naming a change. This is plain code with 0 model calls, so 5/5 is what I expected. |
| 3 | Selected item is first result / outfit names its title | 5 of 5 / 4 of 5 | MET (5/5 and 5/5) | Both halves had to hold. The id half is code. The title half I expected to miss sometimes, but with a wardrobe the model always listed the item by its full title as the first line of each outfit. |
| 4 | Fit card follows the caption rules | 4 of 5 | MET (5/5) | The five counted cards each had the price, the platform, 3 sentences and 3 hashtags. |
| 5 | Empty wardrobe invents no owned clothes | 4 of 5 | MISSED (3/5) | Tries 1 and 3 both contained "white ribbed tank top", one of the 10 wardrobe names. 3 is under the target of 4, so it's a miss. |

**Arguing the opposite verdict on criterion 5.** Someone could say it should count as MET: neither failing outfit claims the user *owns* a tank top. Both say "pair it with a simple white ribbed tank top", which is advice to buy or borrow one. I'm keeping MISSED anyway, because the criterion I wrote counts name matches, not claims of ownership, and the count was 3. Whether the criterion measures the right thing is a separate question, discussed below. It doesn't change the verdict.

**Diagnoses**

**Criterion 5 missed: model output, caused by my own prompt.** Where: `tools.py::suggest_outfit`, the empty-wardrobe branch. Mechanism: with no wardrobe, my prompt asks the model to build outfits "using common basics anyone could pick up". The most common basic it reaches for is a ribbed tank. 3 of the 5 empty-wardrobe outfits paired the jacket with one (tries 1, 3 and 5), 2 of them in white, using the exact words of an item in my example wardrobe. The denim jacket listing never mentions a tank top (its description is about "structured shoulders" and being a "blank canvas"), so the phrase didn't come from the item. It came from asking for generic basics. The tool and the branch worked: no crash, non-empty advice, a fit card every time. The prompt pushed the model toward exactly the generic pieces a real wardrobe is likely to hold.

The criterion itself is blunt, and I said so in unit 3: some wardrobe names are ordinary phrases, so a match isn't proof the model invented ownership. That's still a real finding, because it means the empty-wardrobe advice reads like "the usual basics" rather than advice built around this specific item.

**A pattern outside the counted tries: the model sometimes writes prices as words.** Slip dress try 5 was the only fit card of 25 to fail a rule, because it said "Snagged it for thirty bucks on depop" with no number. Two empty-wardrobe outfits did the same ("forty-two dollars is a bit steep for Poshmark"). My `create_fit_card` prompt says "mention the price exactly once" and never says *how*. It costs nothing in this run, because try 5 isn't one of criterion 4's counted tries, but it's the same tool and the same kind of gap: a prompt that leaves the format to the model.

**On targets that were too easy.** I missed only one criterion, so I should say honestly where my targets were low. Criterion 4 at 4 of 5 passed 24 of 25 cards over the whole run, so I'd tighten it to 5 of 5. Criterion 3's title half (4 of 5) passed every time, because the wardrobe prompt makes the model list the item's full title as an outfit line. A stricter version would check the title in the fit card instead, which is written freely.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path:** 4 steps, with the MCP call at step 2. This was run with the build cache on, which is why it reports 0 model calls.

```
$ python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Leather Belt — Brown, Braided, Bucket Hat — Reversible, Brown Plaid … +7 more
      →    branch: 10 found, selected lst_002
[3] suggest_outfit
      in:  {'new_item': 'lst_002', 'wardrobe_items': 10}
      out: Outfit 1: Y2K Baby Tee — Butterfly Print Baggy straight-leg jeans, dark wash Chunky white sneakers Black cross…
[4] create_fit_card
      in:  {'new_item': 'lst_002', 'outfit': 'Outfit 1:\nY2K Baby Tee — Butterfly Print\nBaggy straight-leg jeans, dark w…
      out: Found this little butterfly tee and I'm obsessed with the pastel print. It was only $18.00 on depop and the fi…

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

**Empty search:** 2 steps. It stops at the branch, and nothing after search runs.

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

  No listings matched 'designer ballgown' in size XXS under $5. None of the 40 listings mention those words at all, so changing the price or size won't help. Try a different item type (tops, bottoms, outerwear, shoes, accessories) or a style word like 'vintage', '90s', 'y2k' or 'denim'.

0 model calls this session
```

### The three failure modes, triggered on purpose

I triggered each one before writing any handler and recorded what the agent did.

**1. Empty search** (`'designer ballgown size XXS under $5'`). This was already handled in unit 3, and the message is shown above. It stops at step 2, makes 0 model calls, and `fit_card` stays None. No change needed.

**2. Empty wardrobe** (`python app.py ask 'denim jacket under $50' --empty-wardrobe`, cache off). This was already handled in unit 3: `suggest_outfit` switches to a general-advice prompt. No crash and no empty string:

```
(running with an empty wardrobe)

  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

  Outfit:   Pair the cropped jacket with a simple white ribbed tank and high-waisted black wide-leg trousers.
Throw on a pair of classic canvas sneakers and a canvas tote bag to finish the look.
Alternatively, layer it over a black slip dress with chunky black boots for a high-low mix.

  Fit card: Finally found the perfect cropped vintage denim jacket to throw over literally everything. Snagged this Wrangler piece for $42.00 on poshmark and the structured shoulders are unreal. It is such a good blank canvas for layering through every season. #thrifted #denimstyle #poshfinds
```

Note that it suggests "a simple white ribbed tank", which is one of my example wardrobe's item names word for word, "White ribbed tank top", minus "top". Criterion 5 checks for exactly this kind of overlap.

**3. Model unavailable** (one character of the key changed, on a query I hadn't asked before, `'corduroy pants under $40'`). **Before the handler**, `run_agent` raised `ModelUnavailable` and the only thing that caught it was the catch-all at the bottom of `app.py`:

```
ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

That isn't a stack trace, but it threw the whole session away. The user never learned that the search had worked and found something, and `run_eval.py` would have logged the run as CRASHED. **I added a handler in `agent.py::run_agent`** that catches `ModelUnavailable` around both model calls, keeps the session, and stops with what it has:

```
[1] parse_query
      in:  corduroy pants under $40
      out: {'description': 'corduroy pants', 'size': None, 'max_price': 40.0}
[2] search_listings (via MCP)
      in:  {'description': 'corduroy pants', 'size': None, 'max_price': 40.0}
      out: 2 items: Corduroy Wide-Leg Pants — Rust, Low-Rise Cargo Pants — Khaki
      →    branch: 2 found, selected lst_005
[3] suggest_outfit
      out: ModelUnavailable
      →    model unreachable, stopping

  Found Corduroy Wide-Leg Pants — Rust ($32 on depop), but couldn't reach the model to suggest an outfit. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

I changed the key for that one command only, through the `GEMINI_API_KEY` environment variable, which `load_dotenv` doesn't override. `.env` itself was never edited, so there was nothing to put back.

**A fourth one the MCP move created: the MCP server failing.** Moving search onto MCP added a way to fail that didn't exist before. I forced it by pointing `mcp_client.SERVER` at a file that doesn't exist. The handler catches `MCPError` and stops at step 2 with: *"The listing search couldn't run, because the MCP search server failed, so nothing was searched. Run `python mcp_client.py` to check the server starts, then ask again."*

**On the MCP move:** `search_listings` is now registered in `mcp_server.py`, with a description written for an agent that can't see my code: what each input means, the size-matching rule, prices in US dollars, and that an empty list `[]` is the "nothing found" answer, not an error. In `agent.py`, a small `search_listings` wrapper calls `mcp_client.call_tool("search_listings", ...)`. Every search the agent makes goes through it, including the re-searches `explain_empty` does to build its message. The tool's code in `tools.py` is unchanged. Nothing behaved differently: `call_tool(...) == search_listings(...)` came back `True` for a matching query, the empty query returned `[]` through MCP too, and both example runs printed the same output as in unit 3. Each MCP call starts a server process, which cost about 0.34 s per call on my machine.

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
