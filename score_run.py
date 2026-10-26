#!/usr/bin/env python3
"""
Mark every try in a run log PASS or FAIL against criteria.md. ← UNIT 4

    python score_run.py results/run_..._before.md

run_eval.py leaves the verdicts blank on purpose. This applies each criterion
exactly as criteria.md words it, so the marking is the same for the before and
after runs and anyone can re-run it. It reads only the run log; it never calls
the agent or the model.

How each criterion is read, decided before the first run:

  1. PASS if the try didn't crash, didn't stop early, and has a fit card.
  2. PASS if it stopped early, the trace has no suggest_outfit step, there is
     no fit card, and the message names a change (a price to raise, a size to
     drop, or different words to try).
  3. Two checks. ID: the first search result's title in the trace is the
     selected item's title (the trace prints titles, and the note names the
     selected id). TITLE: the outfit suggestion contains the selected item's
     full title, ignoring case only — a dash written differently is a miss,
     because the criterion says "word for word".
     MET needs ID in 5 of 5 and TITLE in at least 4 of 5.
  4. Try N is the FIRST run of the Nth criterion-4 scenario. A card passes if
     it contains the price as a whole number ("18" for $18.0), the platform
     ignoring case, 2 to 4 sentences once hashtags are removed, and at most 3
     hashtags. MET needs 4 of 5.
  5. PASS if there is a fit card and the outfit contains none of the 10
     example wardrobe item names, ignoring case. MET needs 4 of 5.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.data_loader import get_example_wardrobe  # noqa: E402

TARGETS = {1: 4, 2: 5, 4: 4, 5: 4}  # criterion 3 has two targets, handled below


def parse(path: Path) -> list[dict]:
    """Every try in the log, with the scenario it belongs to."""
    text = path.read_text(encoding="utf-8")
    body = text.split("## What actually happened", 1)[1]
    tries = []
    for section in re.split(r"\n### ", body)[1:]:
        name = section.split("\n", 1)[0].strip()
        for number, chunk in re.findall(r"\*\*Try (\d+)\*\*\n(.*?)(?=\n\*\*Try \d+\*\*|\Z)", section, re.S):
            blocks = dict(re.findall(r"\n(Outfit suggestion|Fit card|Trace|Crashed):\n\n```\n(.*?)\n```", "\n" + chunk, re.S))
            stopped = re.search(r"- stopped early: (.*)", chunk)
            item = re.search(r"- selected_item: (.*?) \(\$([\d.]+), (\w+)\)", chunk)
            tries.append({
                "scenario": name,
                "try": int(number),
                "crashed": "Crashed" in blocks or chunk.lstrip().startswith("Crashed"),
                "stopped": bool(stopped) and stopped.group(1).startswith("yes"),
                "message": stopped.group(1) if stopped else "",
                "title": item.group(1) if item else None,
                "price": float(item.group(2)) if item else None,
                "platform": item.group(3) if item else None,
                "outfit": blocks.get("Outfit suggestion", ""),
                "card": blocks.get("Fit card", ""),
                "trace": blocks.get("Trace", ""),
            })
    return tries


def sentences(card: str) -> int:
    text = re.sub(r"#\w+", "", card).strip()
    return len([s for s in re.split(r"(?<=[.!?])\s+", text) if re.search(r"[A-Za-z]", s)])


def card_checks(t: dict) -> dict:
    price = f"{t['price']:g}"
    return {
        "price": bool(re.search(rf"(?<![\d.]){re.escape(price)}(?!\d)", t["card"])),
        "platform": t["platform"].lower() in t["card"].lower(),
        "sentences": 2 <= sentences(t["card"]) <= 4,
        "hashtags": len(re.findall(r"#\w+", t["card"])) <= 3,
    }


def main(path: Path) -> None:
    tries = parse(path)
    by = lambda prefix: [t for t in tries if t["scenario"].startswith(prefix)]
    mark = lambda ok: "PASS" if ok else "FAIL"
    rows = []

    c1 = [not t["crashed"] and not t["stopped"] and bool(t["card"]) for t in by("matching query completes")]
    rows.append(("1. Matching query completes all three tools", "4 of 5", c1, sum(c1) >= TARGETS[1]))

    c2 = [
        # A *step* named suggest_outfit, not the words anywhere: the branch's
        # own note reads "stopping before suggest_outfit".
        t["stopped"] and not re.search(r"^\[\d+\] suggest_outfit", t["trace"], re.M) and not t["card"]
        and bool(re.search(r"raise your max price|drop the size|drop both|Try a different", t["message"]))
        for t in by("impossible query stops early")
    ]
    rows.append(("2. Impossible query stops before suggest_outfit", "5 of 5", c2, sum(c2) >= TARGETS[2]))

    c3 = by("selected item reaches suggest_outfit")
    ids = [bool(t["title"]) and bool(re.search(rf"out: \d+ items: {re.escape(t['title'])}(,|$| …)", t["trace"], re.M)) for t in c3]
    titles = [bool(t["title"]) and t["title"].lower() in t["outfit"].lower() for t in c3]
    cells3 = [f"{mark(a)} / {mark(b)}" for a, b in zip(ids, titles)]
    rows.append(("3. Selected item is first result / outfit names its title", "5 of 5 / 4 of 5", cells3,
                 sum(ids) == 5 and sum(titles) >= 4, (sum(ids), sum(titles))))

    c4_runs = by("fit card rules")
    firsts = [t for t in c4_runs if t["try"] == 1]
    c4 = [bool(t["card"]) and all(card_checks(t).values()) for t in firsts]
    rows.append(("4. Fit card follows the caption rules", "4 of 5", c4, sum(c4) >= TARGETS[4]))

    names = [w["name"].lower() for w in get_example_wardrobe()["items"]]
    c5 = [bool(t["card"]) and not any(n in t["outfit"].lower() for n in names) for t in by("empty wardrobe")]
    rows.append(("5. Empty wardrobe invents no owned clothes", "4 of 5", c5, sum(c5) >= TARGETS[5]))

    print(f"Scored {path}\n")
    print("| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for row in rows:
        label, target, cells, met = row[:4]
        cells = [c if isinstance(c, str) else mark(c) for c in cells]
        if len(row) == 5:
            count = f"{row[4][0]}/5 and {row[4][1]}/5"
        else:
            count = f"{sum(c == 'PASS' for c in cells)}/5"
        print(f"| {label} | {target} | {' | '.join(cells)} | {'MET' if met else 'MISSED'} ({count}) |")

    print("\nCriterion 4, every card (only Try 1 of each query counts above):")
    for t in c4_runs:
        checks = card_checks(t) if t["card"] else {"card": False}
        failed = [k for k, ok in checks.items() if not ok]
        print(f"  {t['scenario'][17:]:<18} try {t['try']}: {'PASS' if not failed else 'FAIL — ' + ', '.join(failed)}"
              f"  ({sentences(t['card'])} sentences)" if t["card"] else "  (no card)")
    print(f"  all runs: {sum(1 for t in c4_runs if t['card'] and all(card_checks(t).values()))}/{len(c4_runs)} cards pass")

    print("\nCriterion 3 misses and criterion 5 misses, with the evidence:")
    for t, a, b in zip(c3, ids, titles):
        if not (a and b):
            print(f"  c3 try {t['try']}: id={'ok' if a else 'MISS'} title={'ok' if b else 'MISS'} — selected {t['title']!r}")
    for t in by("empty wardrobe"):
        hits = [n for n in names if n in t["outfit"].lower()]
        if hits or not t["card"]:
            print(f"  c5 try {t['try']}: {'no fit card' if not t['card'] else 'names ' + ', '.join(hits)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python score_run.py results/run_<stamp>_<label>.md")
    main(Path(sys.argv[1]))
