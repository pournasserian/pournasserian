#!/usr/bin/env python3
"""Draw the README's badges as SVGs: transparent chips with a hairline border and the icon in the AP logo's colour.

shields.io can't do a transparent badge that reads well on both GitHub themes, so these are drawn here instead.
Each SVG carries its own light and dark colours behind a prefers-color-scheme query, so the README needs one
<img> per badge rather than a <picture> pair. Text is set in GitHub's own system font stack.

The project badges (stars, licence, NuGet version) fetch live numbers, which is why .github/workflows/heatmap.yml
runs this once a day; everything else is redrawn identically. Standard library only. Reads the GitHub token from
GITHUB_TOKEN; with no token it falls back to the gh CLI's login, which is convenient for a local run.

Icons live in scripts/icons: brand marks from Simple Icons 16.34.0 (CC0), the rest Feather-style outlines.

usage: python scripts/badges.py <output dir>
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.request

ICONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

# (file, icon, text). The file name is what the README links to.
STATIC = [
    ("location", "map-pin", "Toronto, Canada"),
    ("site", "ap", "pournasserian.com"),
    ("linkedin", "linkedin", "LinkedIn"),
    ("x", "x", "X"),
    ("rss", "rss", "RSS"),
    # AI & agents
    ("microsoft-agent-framework", "sparkle", "Microsoft Agent Framework"),
    ("mcp", "modelcontextprotocol", "MCP"),
    ("claude", "claude", "Claude"),
    ("azure-openai", "cloud", "Azure OpenAI"),
    ("azure-ai-foundry", "cloud", "Azure AI Foundry"),
    ("langchain", "langchain", "LangChain"),
    ("graphrag-neo4j", "neo4j", "GraphRAG on Neo4j"),
    ("pgvector", "postgresql", "pgvector"),
    ("python", "python", "Python"),
    # Platform
    ("csharp", "code", "C#"),
    ("dotnet", "dotnet", ".NET / ASP.NET Core"),
    ("blazor", "blazor", "Blazor"),
    ("signalr", "zap", "SignalR"),
    ("rabbitmq", "rabbitmq", "RabbitMQ"),
    ("redis", "redis", "Redis"),
    ("mongodb", "mongodb", "MongoDB"),
    ("sql-server", "database", "SQL Server"),
    ("mysql", "mysql", "MySQL"),
    ("azure-devops", "cloud", "Azure DevOps"),
    # Front end
    ("svelte", "svelte", "Svelte / SvelteKit"),
    ("angular", "angular", "Angular"),
    ("vue", "vuedotjs", "Vue"),
    ("tailwind-css", "tailwindcss", "Tailwind CSS"),
    ("bootstrap", "bootstrap", "Bootstrap"),
    ("astro", "astro", "Astro"),
    # IoT & embedded
    ("ble", "bluetooth", "BLE"),
    ("lora", "radio", "LoRa"),
    ("lte-m-nb-iot", "radio", "LTE-M / NB-IoT"),
    ("nordic-nrf9160", "nordicsemiconductor", "Nordic nRF9160"),
    ("zephyr-rtos", "cpu", "Zephyr RTOS"),
    ("micropython", "micropython", "MicroPython"),
    ("mqtt", "mqtt", "MQTT"),
    # Observability
    ("grafana", "grafana", "Grafana"),
    ("kibana", "kibana", "Kibana"),
    ("elasticsearch", "elasticsearch", "Elasticsearch"),
    ("application-insights", "activity", "Application Insights"),
    # Data & ML
    ("pytorch", "pytorch", "PyTorch"),
    ("scikit-learn", "scikitlearn", "scikit-learn"),
    ("r", "r", "R"),
    ("time-series-forecasting", "trending-up", "Time-series forecasting"),
]

NOW = "AI platform architecture · Four Seasons Hotels and Resorts"

PROJECTS = [
    dict(name="fluentcms", repo="fluentcms/FluentCMS", stars=True, nuget="FluentCMS.Web.Api", status="pre-1.0"),
    dict(name="yesvelte", repo="yesvelte/yesvelte", stars=True, status="pre-1.0"),
    dict(name="ubeac", repo="ubeac/api.ubeac.io", stars=False, status="retired service"),
]

# Same palette as the banner and the heatmap: the logo's accent blue on light, its periwinkle on dark.
THEMES = {
    "light": dict(accent="#1640ca", text="#3f4b61", muted="#5b677d", border="#d3d9e3"),
    "dark": dict(accent="#8ca8ff", text="#aab4c6", muted="#8792a7", border="#253046"),
}
FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif'

HEIGHT, PAD, ICON, GAP = 24, 8, 15, 6
TEXT_SIZE, LABEL_SIZE, TRACKING = 13, 10.5, 0.6

# Advance widths per 1000 em for U+0020..U+007E then U+00B7, the mean of Arial and Segoe UI. Text can't be
# measured inside an <img>, so widths are estimated from this and pinned with textLength, which absorbs the
# few per cent by which the reader's actual system font differs.
REGULAR = [276, 281, 374, 573, 548, 854, 734, 210, 317, 317, 403, 634, 247, 366, 247, 334, 548, 548, 548, 548, 548, 548,
           548, 548, 548, 548, 247, 247, 634, 634, 634, 502, 985, 656, 620, 671, 712, 586, 550, 732, 716, 272, 428, 624,
           513, 865, 735, 766, 614, 766, 660, 599, 567, 705, 644, 939, 628, 610, 591, 290, 328, 290, 577, 486, 301, 532,
           572, 481, 573, 540, 295, 573, 561, 232, 232, 499, 232, 847, 561, 571, 572, 573, 340, 462, 308, 561, 490, 722,
           479, 492, 476, 318, 250, 318, 634, 275]
BOLD = [276, 318, 456, 574, 556, 865, 719, 248, 333, 333, 412, 639, 260, 367, 260, 346, 556, 479, 556, 556, 566, 556, 557,
        546, 556, 557, 287, 287, 639, 639, 639, 527, 965, 697, 663, 672, 720, 592, 557, 738, 729, 285, 476, 667, 550, 879,
        745, 767, 626, 767, 672, 606, 581, 713, 654, 955, 643, 622, 599, 333, 341, 333, 639, 486, 311, 539, 607, 513, 607,
        544, 339, 607, 596, 270, 270, 541, 270, 887, 597, 604, 607, 607, 380, 494, 347, 597, 532, 767, 529, 532, 482, 361,
        279, 361, 639, 287]


def text_width(text, size, widths, tracking=0.0):
    advance = sum(widths[ord(c) - 32] if " " <= c <= "~" else widths[-1] for c in text)
    return advance * size / 1000 + tracking * (len(text) - 1)


def load_icon(name):
    with open(os.path.join(ICONS, f"{name}.svg"), encoding="utf-8") as fh:
        svg = fh.read()
    root, body = re.fullmatch(r"\s*(<svg[^>]*>)(.*)</svg>\s*", svg, re.S).groups()
    view_box = re.search(r'viewBox="([^"]+)"', root).group(1)
    return view_box, body, 'fill="none"' in root


def style(colours):
    return (f'.b{{fill:none;stroke:{colours["border"]}}}'
            f'.f{{fill:{colours["accent"]}}}'
            f'.s{{fill:none;stroke:{colours["accent"]};stroke-width:2;stroke-linecap:round;stroke-linejoin:round}}'
            f'text{{fill:{colours["text"]}}}.l{{fill:{colours["accent"]}}}.m{{fill:{colours["muted"]}}}')


def baseline(size):
    # Capitals are about 0.7 em tall, so this puts them on the chip's centre line.
    return f"{HEIGHT / 2 + 0.35 * size:.1f}"


def render(title, icon=None, label=None, value="", muted=False):
    """A chip reading [icon] [LABEL] value. Every part but the value is optional."""
    parts, x = [], PAD
    if icon:
        view_box, body, outline = load_icon(icon)
        parts.append(f'<svg class="{"s" if outline else "f"}" x="{x}" y="{(HEIGHT - ICON) / 2:g}" width="{ICON}" '
                     f'height="{ICON}" viewBox="{view_box}">{body}</svg>')
        x += ICON + GAP
    if label:
        label = label.upper()
        width = text_width(label, LABEL_SIZE, BOLD, TRACKING)
        parts.append(f'<text class="l" x="{x:g}" y="{baseline(LABEL_SIZE)}" textLength="{width:.1f}" lengthAdjust="spacingAndGlyphs">'
                     f'{html.escape(label)}</text>')
        x += width + GAP
    width = text_width(value, TEXT_SIZE, REGULAR)
    css_class = ' class="m"' if muted else ""
    parts.append(f'<text{css_class} x="{x:.1f}" y="{baseline(TEXT_SIZE)}" textLength="{width:.1f}" '
                 f'lengthAdjust="spacingAndGlyphs">{html.escape(value)}</text>')
    total = round(x + width + PAD)
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{HEIGHT}" viewBox="0 0 {total} {HEIGHT}" '
        f'role="img" aria-label="{html.escape(title)}">',
        f"<title>{html.escape(title)}</title>",
        f'<style>text{{font:{TEXT_SIZE}px {FONT}}}.l{{font-size:{LABEL_SIZE}px;font-weight:600}}'
        f'{style(THEMES["light"])}@media (prefers-color-scheme:dark){{{style(THEMES["dark"])}}}</style>',
        f'<rect class="b" x=".5" y=".5" width="{total - 1}" height="{HEIGHT - 1}" rx="3.5"/>',
        *parts,
        "</svg>\n",
    ])


def get_json(url, github=False):
    token = os.environ.get("GITHUB_TOKEN")
    if github and not token:
        result = subprocess.run(["gh", "api", url.removeprefix("https://api.github.com/")],
                                capture_output=True, text=True, encoding="utf-8", check=True)
        return json.loads(result.stdout)
    headers = {"User-Agent": "pournasserian/pournasserian badges"}
    if github:
        headers["Authorization"] = f"bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def metric(n):
    # The way shields.io abbreviated it: 950, 1.2k, 12k.
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n < 10000 else f"{round(n / 1000)}k"


def project_badges(project):
    repo = get_json(f"https://api.github.com/repos/{project['repo']}", github=True)
    name = project["name"]
    if project["stars"]:
        yield f"{name}-stars", render(f"{repo['stargazers_count']} GitHub stars", "github", "stars",
                                      metric(repo["stargazers_count"]))
    licence = (repo.get("license") or {}).get("spdx_id") or "none"
    yield f"{name}-license", render(f"License: {licence}", label="license", value=licence)
    if project.get("nuget"):
        versions = get_json(f"https://api.nuget.org/v3-flatcontainer/{project['nuget'].lower()}/index.json")["versions"]
        stable = [v for v in versions if "-" not in v]
        version = (stable or versions)[-1]
        yield f"{name}-nuget", render(f"NuGet version {version}", "nuget", "NuGet", f"v{version}")
    yield f"{name}-status", render(f"Status: {project['status']}", label="status", value=project["status"], muted=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    badges = [(name, render(text, icon, value=text)) for name, icon, text in STATIC]
    badges.append(("now", render(f"Now: {NOW}", label="now", value=NOW)))
    for project in PROJECTS:
        badges += project_badges(project)
    for name, svg in badges:
        with open(os.path.join(out_dir, f"{name}.svg"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
    print(f"wrote {len(badges)} badges to {out_dir}")


if __name__ == "__main__":
    main()
