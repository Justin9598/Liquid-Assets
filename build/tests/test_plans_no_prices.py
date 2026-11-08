"""Plan 12 section 6: plans are public, so no plan file may carry a price. Fails on an `S$<number>` amount, or on a
`Price (S$)` Markdown table column that holds values. The words "price" and the column name alone are fine."""
import re
from pathlib import Path

PLANS = Path(__file__).resolve().parents[2] / "plans"
AMOUNT = re.compile(r"S\$\s?\d")


def _cells(line):
    """Split a Markdown table row on unescaped pipes."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _price_column_values(text):
    found = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|") or "price (s$)" not in line.casefold():
            continue
        head = [c.casefold() for c in _cells(line)]
        cols = [k for k, c in enumerate(head) if c == "price (s$)"]       # a header cell, not a `Price (S$)` mention
        if not cols:
            continue
        col = cols[0]
        for row in lines[i + 2:]:                       # skip the header and the separator row
            if not row.lstrip().startswith("|"):
                break
            cells = _cells(row)
            if col < len(cells) and cells[col] not in ("", "-", "n/a"):
                found.append(f"{row.strip()[:60]}")
    return found


def test_plans_carry_no_prices():
    problems = []
    for p in sorted(PLANS.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if AMOUNT.search(line):
                problems.append(f"{p.relative_to(PLANS)}:{n}: S$ amount")
        for v in _price_column_values(text):
            problems.append(f"{p.relative_to(PLANS)}: Price (S$) column has a value: {v}")
    assert not problems, "prices in plans:\n" + "\n".join(problems)


def test_the_check_itself_catches_prices():
    assert AMOUNT.search("paid  for it")
    table = "| Name | Price (S$) |\n|---|---|\n| A | 12 |\n"
    assert _price_column_values(table)
    assert not _price_column_values("| Name | Price (S$) |\n|---|---|\n| A |  |\n")
