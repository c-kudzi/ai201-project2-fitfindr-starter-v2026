# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** For a matching query the search half can't fail: parsing
is a regex and `search_listings` is a keyword match over a fixed file, so it
returns the same listing every time. The risk is the two model calls. On the
free tier I get 15 requests a minute, and until unit 4 nothing in `run_agent`
catches `ModelUnavailable`, so one failed call ends the whole run with no fit
card. 5 of 5 would be claiming the model never fails, which I can't promise.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** Nothing on this path is random. Parsing, searching and
writing the message (`agent.py::explain_empty`) are all plain code, and the
run makes 0 model calls, so the same query gives the same result every time.
Anything less than 5 of 5 here would be a bug in my branch, not bad luck.

---

## 3. The item search found is the item the outfit is built around

Given the query `'vintage graphic tee under $30, size M'`, after each run
`session["selected_item"]["id"]` is the same as
`session["search_results"][0]["id"]` in 5 of 5 tries, and
`session["outfit_suggestion"]` contains the selected item's full `title` word
for word in at least 4 of 5 tries.

**Why this target:** The first half is code: the loop copies the first search
result into the session and nothing else writes to it, so 5 of 5. The second
half is how I can see the item actually *reached* `suggest_outfit`: if the
model had the right listing, it names it. In my tests both outfits started with
the full title, but my prompt never tells the model to repeat it, so it may
shorten it to "the baby tee" some of the time. That's why it's 4 of 5 and not
5.

---

## 4. The fit card follows the caption rules

With the cache off, run each of these five queries once:
`'vintage graphic tee under $30'`, `'90s track jacket in size M'`,
`'silk slip dress in midi length under $40'`, `'platform sneakers size 8'`,
`'denim jacket under $50'`. Each picks a different item. A fit card passes if
all four hold:

- it contains the item's price as a number (`18`, `45`, `30`, `48` or `42`),
- it contains the platform name, ignoring case,
- it has 2 to 4 sentences, not counting the hashtags,
- it has at most 3 hashtags.

Target: at least 4 of the 5 fit cards pass.

**Why this target:** These rules are all in the prompt for
`tools.py::create_fit_card`, but a prompt is a request, not a guarantee. The
model writes freely at temperature 0.9 and sometimes ignores a length or
hashtag limit. I'm not grading whether the caption sounds good, because two
people would score that differently. I picked these four because anyone can
count them. I didn't pick "the cards are all different": when I ran the same
item three times, two cards opened with the same sentence, but these five
items are all different, so that check would almost always pass and prove
nothing.

---

## 5. With an empty wardrobe, the outfit doesn't invent clothes I own

Run `python app.py ask 'denim jacket under $50' --empty-wardrobe` five times
with the cache off. It passes if the run returns a fit card **and** the outfit
suggestion contains none of the 10 item names from the example wardrobe
(`data/wardrobe_schema.json`), word for word. Target: at least 4 of 5.

**Why this target:** `suggest_outfit` switches to a different prompt when the
wardrobe is empty, and that path is easy to forget, because every normal test
uses the example wardrobe. The danger is the model writing "pair it with your
black combat boots" to someone who owns nothing. I'm not asking for 5 of 5
because some example wardrobe names are ordinary phrases. In one test the
model, with no wardrobe, suggested "chunky black sneakers", which is one word
away from "Chunky white sneakers". So a pass can miss by luck, and a fail can
happen without the model inventing anything.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
