# km-poster-generator

> [English](README.md) · [中文](README_zh.md)

Atian beige journal style · knowledge-graph poster generator. Data-driven: edit one JSON to reproduce the same 3:4 Xiaohongshu promo long image — fixed layout, fixed character IP, fixed decorations.

![preview](assets/preview.jpg)

## Effect

Outputs a ~1080×1440 (3:4) PNG, fixed to include:

- Top big title + English-style subtitle + tag bubbles
- Cartoon girl IP character × 5 (same character, different poses, 3D Pixar style)
- 2×2 color-block category cards (progress bar + highlight words)
- Bottom black "Key Takeaways" summary area
- Bottom three action cards
- Journal-style decorations: tape, stickers, dividers, shadows

## Quick Start

```bash
# Clone
git clone https://github.com/qianqiuwanzi/km-poster-generator.git
cd km-poster-generator

# Install deps
pip install playwright
playwright install chromium

# Edit content
# Edit content.json (field reference below)

# Generate poster
python generate.py

# Output at output/poster.png
```

## content.json Field Reference

| Field | Description | Example |
|------|------|------|
| `title` | Top big title | `"Give AI long-term memory"` |
| `subtitle` | Subtitle (emoji supported) | `"IQ can't hide — make AI stop forgetting in 7 seconds"` |
| `tags` | 4 tags (emoji + word) | `["🧠 AI memory system", "⚡ cognitive architecture"]` |
| `intro` | Intro bubble (`<strong>` `<em>` `<br>` supported) | `"<strong>Ordinary AI</strong> only has short-term memory..."` |
| `b1`~`b4` | Four color-block cards | See sub-fields below |
| `sum` | Bottom key-takeaways black area | `{label, main, sub}` |
| `a1`~`a3` | Bottom three action cards | `{title, item1, item2, highlight}` |
| `footer` | Footer text | `"🧠 Knowledge graph · David Media"` |

### Color-block card sub-fields (b1~b4)

| Sub-field | Description |
|--------|------|
| `title` | Card title (emoji + text) |
| `item1` / `item2` | Two lines of description |
| `barlabel` | Progress bar label |
| `bar` | Progress value 0~100 |
| `barcolor` | Progress bar color (`#2C2C2C` dark / `#E85A9C` pink alternating) |
| `highlight` | Highlight quote |
| `b4` only | `m1/m1l` `m2/m2l` `m3/m3l` (three metrics: value + label) |

**Note**: only change the **values** in the JSON, not the keys or structure.

## Rendering Notes

`generate.py` embeds an adaptive render pipeline:

1. Playwright opens the filled HTML
2. Compress child element margin / padding / gap proportionally so content height ≈ 1400px (font size unchanged)
3. Explicit 20px gaps between 2×2 color blocks / key takeaways / bottom three cards
4. Viewport height follows the poster's real bottom-right position (prevents bottom crop)
5. Precise `bounding_box` clip (with shadow margin), zero cropping

## Directory Structure

```
km-poster-generator/
├── SKILL.md              # Skill flow definition + field reference
├── README.md             # This file
├── content.json          # Example copy (IQ can't hide)
├── content.schema.json   # JSON Schema validation
├── generate.py           # Generator (fill copy + render)
├── template.html         # Placeholder template (54 {{...}})
├── assets/
│   └── characters/       # 5 transparent cutout characters (_rb.png)
├── tests/                # Basic render + Schema tests
└── tools/                # Debug scripts
```

## Debug Tools

```bash
# Diagnose render height issues
python tools/debug_height.py

# Diagnose each section
python tools/debug_sections.py
```

## License

MIT
