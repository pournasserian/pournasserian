#!/usr/bin/env python3
"""Draw the GitHub contribution calendar as two SVGs, dark and light, in the pournasserian.com palette.

Run once a day by .github/workflows/heatmap.yml. Standard library only. Reads the GitHub token from
GITHUB_TOKEN (the workflow's default token is enough); with no token it falls back to the gh CLI's login,
which is convenient for a local run.

usage: python scripts/heatmap.py <github login> <output dir>
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.request

QUERY = """query($login: String!) {
  user(login: $login) { contributionsCollection { contributionCalendar {
    totalContributions
    weeks { contributionDays { date contributionCount contributionLevel } }
  } } }
}"""

# Same colours as the banner: periwinkle on dark, accent blue on light.
THEMES = {
    "dark": dict(cells=["#161d2b", "#2a3f7d", "#4660b5", "#6d88e6", "#8ca8ff"], text="#8792a7", title="#e7ebf3"),
    "light": dict(cells=["#e6eaf1", "#c5d0f4", "#8ca8ff", "#4a6be0", "#1640ca"], text="#5b677d", title="#0e1626"),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
CELL, GAP, LEFT, TOP = 11, 3, 34, 24


def fetch_calendar(login):
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
        headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "pournasserian/pournasserian heatmap"}
        with urllib.request.urlopen(urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers), timeout=60) as response:
            payload = json.load(response)
    else:
        result = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={login}"],
                                capture_output=True, text=True, encoding="utf-8", check=True)
        payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render(calendar, theme):
    colours = THEMES[theme]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    width = LEFT + len(weeks) * (CELL + GAP) + 8
    height = TOP + 7 * (CELL + GAP) + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{total} contributions in the last year">',
        f'<style>text{{font:10px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;fill:{colours["text"]}}}'
        f'.t{{font-size:12px;font-weight:600;fill:{colours["title"]}}}</style>',
    ]
    last_month = None
    for column, week in enumerate(weeks):
        x = LEFT + column * (CELL + GAP)
        for day in week["contributionDays"]:
            date = datetime.date.fromisoformat(day["date"])
            y = TOP + (date.isoweekday() % 7) * (CELL + GAP)  # Sunday on the top row, as on GitHub
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{colours["cells"][LEVEL[day["contributionLevel"]]]}"/>')
        first = datetime.date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and first.day <= 7 and column < len(weeks) - 2:
            out.append(f'<text x="{x}" y="{TOP - 8}">{first.strftime("%b")}</text>')
        last_month = first.month
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        out.append(f'<text x="0" y="{TOP + row * (CELL + GAP) + 9}">{label}</text>')
    legend_y = height - 14
    legend_x = width - 8 - 5 * (CELL + GAP) - 50
    out.append(f'<text x="{LEFT}" y="{legend_y + 9}" class="t">{total:,} contributions in the last year</text>')
    out.append(f'<text x="{legend_x - 28}" y="{legend_y + 9}">Less</text>')
    out += [f'<rect x="{legend_x + i * (CELL + GAP)}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{colour}"/>'
            for i, colour in enumerate(colours["cells"])]
    out.append(f'<text x="{legend_x + 5 * (CELL + GAP) + 2}" y="{legend_y + 9}">More</text>')
    out.append("</svg>\n")
    return "\n".join(out)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    login, out_dir = sys.argv[1:3]
    calendar = fetch_calendar(login)
    for theme in THEMES:
        path = os.path.join(out_dir, f"heatmap-{theme}.svg")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render(calendar, theme))
        print(f"wrote {path}")
    print(f"{calendar['totalContributions']} contributions across {len(calendar['weeks'])} weeks")


if __name__ == "__main__":
    main()
