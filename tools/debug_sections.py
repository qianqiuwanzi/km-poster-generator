#!python3
"""debug_sections.py — 打印 poster 各区块的渲染高度。

用于开发时快速检查各 section 的高度分布，帮助定位布局溢出问题。

用法:
    python tools/debug_sections.py
"""

from playwright.sync_api import sync_playwright
import pathlib

SKILL = pathlib.Path(__file__).resolve().parent.parent
HTML_FILE = SKILL / "poster_build.html"

SELECTORS = [
    ".scroll-header", ".tags-area", ".character-area", ".intro-bubble",
    ".blocks-grid", ".block-card", ".bottom-area", ".action-row", ".footer",
]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1100, "height": 1480})
    pg.goto("file://" + str(HTML_FILE))
    pg.wait_for_timeout(1800)
    for sel in SELECTORS:
        n = pg.evaluate("document.querySelectorAll('%s').length" % sel)
        h = pg.evaluate(
            "(document.querySelector('%s')||{getBoundingClientRect:function(){return{height:0}}}).getBoundingClientRect().height" % sel
        ) if n else 0
        print(f"{sel:30s}  count={n}  h={round(h)}")
    b.close()
