"""
build_video.py — Creates an animated narrated slideshow video (.mp4)
using moviepy + PIL. No audio (TTS not available), uses animated text
overlays, smooth slide transitions, and project content.

Run: python build_video.py
Output: assets/CarbonIntelligencePlatform_Demo.mp4
Duration: ~90 seconds
"""

import os, sys, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip, VideoClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip, TextClip
)

W, H     = 1280, 720
FPS      = 24
FADE_DUR = 0.5   # seconds per cross-fade

# ── Colours (RGB tuples for PIL) ──────────────────────────────────────────────
C_DARK_GREEN  = (26,  71,  42)
C_MID_GREEN   = (45, 106,  79)
C_LIGHT_GREEN = (82, 183, 136)
C_WHITE       = (255, 255, 255)
C_AMBER       = (133, 100,   4)
C_LIGHT_BG    = (247, 248, 250)
C_DARK_TEXT   = (31,  35,  40)
C_MUTED       = (87,  96, 106)
C_LIGHT_CARD  = (240, 249, 240)
C_YELLOW_BG   = (255, 243, 205)


def load_font(size=24, bold=False):
    """Load system font with graceful fallback to default."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    if bold:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/Arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ] + candidates
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
    draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
    draw.ellipse([x0, y0, x0+2*radius, y0+2*radius], fill=fill)
    draw.ellipse([x1-2*radius, y0, x1, y0+2*radius], fill=fill)
    draw.ellipse([x0, y1-2*radius, x0+2*radius, y1], fill=fill)
    draw.ellipse([x1-2*radius, y1-2*radius, x1, y1], fill=fill)


def wrap_text(draw, text, font, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines, line = [], []
    for word in words:
        test = " ".join(line + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and line:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    return lines


def make_slide_image(draw_fn):
    """Call draw_fn(img, draw) and return numpy array."""
    img  = Image.new("RGB", (W, H), C_LIGHT_BG)
    draw = ImageDraw.Draw(img)
    draw_fn(img, draw)
    return np.array(img)


# ── Slide drawing functions ────────────────────────────────────────────────────

def draw_header(draw, subtitle=""):
    draw.rectangle([0, 0, W, 52], fill=C_DARK_GREEN)
    font = load_font(14)
    draw.text((16, 16), "🌿  Enterprise Carbon Intelligence & Net-Zero Planning Platform", font=font, fill=C_LIGHT_GREEN)
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font)
        draw.text((W - bbox[2] + bbox[0] - 20, 16), subtitle, font=font, fill=C_WHITE)


def draw_footer(draw):
    draw.rectangle([0, H-36, W, H], fill=C_DARK_GREEN)
    font = load_font(12)
    text = "IBM SkillsBuild Capstone 2026  ·  Agentic AI  ·  GHG Protocol Aligned"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((x, H-24), text, font=font, fill=C_LIGHT_GREEN)


def draw_title_band(draw, title, y=70):
    font_title = load_font(30, bold=True)
    draw.text((40, y), title, font=font_title, fill=C_DARK_GREEN)
    draw.rectangle([40, y+46, W-40, y+49], fill=C_MID_GREEN)


def draw_bullets(draw, bullets, x, y, w, font_size=15, title=None, title_color=C_MID_GREEN):
    font_b = load_font(font_size, bold=True)
    font_r = load_font(font_size)
    if title:
        draw.text((x, y), title, font=font_b, fill=title_color)
        y += font_size + 12
    for bullet in bullets:
        lines = wrap_text(draw, bullet, font_r, w)
        for i, line in enumerate(lines):
            prefix = "  •  " if i == 0 else "      "
            draw.text((x, y), prefix + line, font=font_r, fill=C_DARK_TEXT)
            y += font_size + 5
        y += 4
    return y


# ─── Slide 1 — Title ──────────────────────────────────────────────────────────
def slide_title(img, draw):
    img.paste(Image.new("RGB", (W, H), C_DARK_GREEN))
    draw = ImageDraw.Draw(img)
    # Accent band
    draw.rectangle([0, 260, W, 420], fill=C_MID_GREEN)
    # Title
    f1 = load_font(46, bold=True)
    f2 = load_font(20)
    f3 = load_font(15)
    t1 = "Enterprise Carbon Intelligence"
    t2 = "& Net-Zero Planning Platform"
    bbox1 = draw.textbbox((0,0), t1, font=f1)
    bbox2 = draw.textbbox((0,0), t2, font=f1)
    draw.text(((W-(bbox1[2]-bbox1[0]))//2, 275), t1, font=f1, fill=C_WHITE)
    draw.text(((W-(bbox2[2]-bbox2[0]))//2, 335), t2, font=f1, fill=C_LIGHT_GREEN)
    sub = "Agentic AI  ·  RAG  ·  Multi-Agent  ·  Human-in-the-Loop  ·  GHG Protocol"
    bsub = draw.textbbox((0,0), sub, font=f2)
    draw.text(((W-(bsub[2]-bsub[0]))//2, 435), sub, font=f2, fill=C_WHITE)
    cap = "IBM SkillsBuild Academic Program — Gartner Capstone 2026"
    bcap = draw.textbbox((0,0), cap, font=f3)
    draw.text(((W-(bcap[2]-bcap[0]))//2, 490), cap, font=f3, fill=C_LIGHT_GREEN)
    # Footer
    draw_footer(draw)


# ─── Slide 2 — Problem ────────────────────────────────────────────────────────
def slide_problem(img, draw):
    draw_header(draw, "Problem Statement")
    draw_footer(draw)
    draw_title_band(draw, "The Challenge — Why This Platform?")
    bullets = [
        "Organizations emit CO2 across electricity, fuel, travel, waste & procurement",
        "Measuring emissions alone does NOT show which interventions work best",
        "Finance teams lack ROI data for decarbonization investments",
        "Sustainability reports are manual, slow and siloed across business units",
        "Gap: No tool bridges accounting → strategy → simulation → boardroom roadmap",
    ]
    draw_bullets(draw, bullets, 40, 145, W-80, font_size=17)
    # Solution banner
    draw_rounded_rect(draw, (40, 530, W-40, 600), 8, (212, 237, 218))
    draw.text((60, 546), "✅  Solution: Agentic AI transforms activity data → prioritized, "
              "cost-ranked, human-approved roadmaps.", font=load_font(15, bold=True), fill=C_DARK_GREEN)


# ─── Slide 3 — Architecture ───────────────────────────────────────────────────
def slide_architecture(img, draw):
    draw_header(draw, "System Architecture")
    draw_footer(draw)
    draw_title_band(draw, "Multi-Agent Pipeline")

    fb = load_font(13, bold=True)
    fr = load_font(12)

    # Supervisor box
    draw_rounded_rect(draw, (480, 135, 800, 178), 6, C_DARK_GREEN)
    draw.text((510, 148), "Ω  Supervisor Agent", font=fb, fill=C_WHITE)

    # Agent row 1
    agents1 = ["1. Carbon Accounting", "2. Emissions Analysis", "3. Reduction Strategy"]
    for i, a in enumerate(agents1):
        x = 60 + i * 270
        draw_rounded_rect(draw, (x, 215, x+240, 265), 5, C_MID_GREEN)
        draw.text((x+10, 231), a, font=fb, fill=C_WHITE)

    # Agent row 2
    agents2 = ["4. Scenario Simulation", "5. Cost & Feasibility", "6. ESG Roadmap"]
    for i, a in enumerate(agents2):
        x = 60 + i * 270
        draw_rounded_rect(draw, (x, 305, x+240, 355), 5, C_MID_GREEN)
        draw.text((x+10, 321), a, font=fb, fill=C_WHITE)

    # Right column
    right = [("Tools (5)", C_LIGHT_GREEN), ("RAG + Gemini", C_LIGHT_GREEN),
             ("HITL Gate", C_AMBER), ("Export", (40, 167, 69))]
    for i, (label, clr) in enumerate(right):
        y = 215 + i * 62
        draw_rounded_rect(draw, (900, y, 1090, y+48), 5, clr)
        draw.text((915, y+14), label, font=fb, fill=C_WHITE)

    # Flow label
    flow = "User → Supervisor → 6 Agents → Tools + RAG → Validation → HITL → Approved Export"
    bbox = draw.textbbox((0,0), flow, font=fr)
    draw.text(((W-(bbox[2]-bbox[0]))//2, 430), flow, font=load_font(13, bold=True), fill=C_MID_GREEN)

    # Tech stack
    draw.rectangle([40, 475, W-40, 520], fill=(240, 249, 240))
    draw.text((60, 488), "Stack:  Python 3.15  ·  Streamlit  ·  LangChain  ·  Gemini 1.5 Pro  ·  "
              "InMemoryVectorStore  ·  SQLite  ·  Plotly", font=fr, fill=C_DARK_TEXT)


# ─── Slide 4 — Test Results ───────────────────────────────────────────────────
def slide_tests(img, draw):
    draw_header(draw, "Test Results")
    draw_footer(draw)
    draw_title_band(draw, "Agent Correctness — 34/34 Tests Passing (100%)")

    kpis = [("34", "Total"), ("34", "Passed ✅"), ("0", "Failed"), ("100%", "Pass Rate")]
    for i, (val, lbl) in enumerate(kpis):
        x = 40 + i * 300
        clr = (212, 237, 218) if lbl != "Failed" else (248, 215, 218)
        draw_rounded_rect(draw, (x, 145, x+270, 235), 8, clr)
        draw.text((x+90, 158), val, font=load_font(38, bold=True), fill=C_DARK_GREEN)
        draw.text((x+80, 208), lbl, font=load_font(13), fill=C_MUTED)

    sections = [
        ("Section 1 — Tools Layer",         "12 tests  ·  math, ranking, scenarios, scoring"),
        ("Section 2 — Input Validators",     "5 tests   ·  TC-03, TC-04, scope, empty rows"),
        ("Section 3 — Agent Pipeline",       "7 tests   ·  TC-01, TC-02, TC-05, empty input"),
        ("Section 4 — HITL Gate",            "4 tests   ·  approve, reject, blocked, audit trail"),
        ("Section 5 — RAG Degradation",      "4 tests   ·  TC-06, TC-07, sources, fallback"),
        ("Section 6 — Database Schema",      "2 tests   ·  6 tables created, FK enforcement"),
    ]
    fb = load_font(14, bold=True)
    fr = load_font(13)
    for i, (sec, desc) in enumerate(sections):
        y = 265 + i * 52
        bg = C_WHITE if i % 2 == 0 else C_LIGHT_CARD
        draw.rectangle([40, y, W-40, y+46], fill=bg)
        draw.text((55, y+14), f"✅  {sec}", font=fb, fill=C_DARK_GREEN)
        draw.text((580, y+16), desc, font=fr, fill=C_MUTED)


# ─── Slide 5 — HITL Gate ─────────────────────────────────────────────────────
def slide_hitl(img, draw):
    draw_header(draw, "Human-in-the-Loop")
    draw_footer(draw)
    draw_title_band(draw, "HITL Safety Gate — Responsible AI Control")

    fb = load_font(15, bold=True)
    fr = load_font(14)

    steps = [
        ("1", "ESG Roadmap Agent generates roadmap", C_MID_GREEN),
        ("2", "Status = AWAITING_APPROVAL  |  export_ready = False", C_AMBER),
        ("3", "Human reviewer enters name + optional notes in Streamlit", C_MID_GREEN),
        ("4", "APPROVE → Status = APPROVED → export_ready = True", (40, 167, 69)),
        ("5", "REJECT  → Status = REJECTED → pipeline must restart", (220, 53, 69)),
        ("6", "Approved-by + timestamp recorded in exported document", C_MID_GREEN),
    ]
    for i, (num, text, clr) in enumerate(steps):
        y = 148 + i * 65
        draw_rounded_rect(draw, (40, y, W-40, y+56), 8, C_LIGHT_CARD)
        draw_rounded_rect(draw, (40, y, 80, y+56), 8, clr)
        draw.text((53, y+16), num, font=fb, fill=C_WHITE)
        draw.text((100, y+17), text, font=fr, fill=C_DARK_TEXT)

    # Warning banner
    draw_rounded_rect(draw, (40, 558, W-40, 628), 8, C_YELLOW_BG)
    draw.text((60, 571), "⚠️  Responsible AI:", font=fb, fill=C_AMBER)
    draw.text((60, 596), "AI-generated sustainability commitments cannot be exported without human validation.",
              font=load_font(13), fill=C_AMBER)


# ─── Slide 6 — Thank You ─────────────────────────────────────────────────────
def slide_thankyou(img, draw):
    img.paste(Image.new("RGB", (W, H), C_DARK_GREEN))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 270, W, 420], fill=C_MID_GREEN)
    f1 = load_font(54, bold=True)
    f2 = load_font(20)
    f3 = load_font(14)
    t = "Thank You"
    bbox = draw.textbbox((0,0), t, font=f1)
    draw.text(((W-(bbox[2]-bbox[0]))//2, 280), t, font=f1, fill=C_WHITE)
    sub = "Enterprise Carbon Intelligence & Net-Zero Planning Platform"
    bsub = draw.textbbox((0,0), sub, font=f2)
    draw.text(((W-(bsub[2]-bsub[0]))//2, 355), sub, font=f2, fill=C_LIGHT_GREEN)
    # Quick start box
    draw_rounded_rect(draw, (100, 440, W-100, 500), 8, C_LIGHT_GREEN)
    qs = "pip install -r requirements.txt  →  copy .env.example .env  →  streamlit run app.py"
    bqs = draw.textbbox((0,0), qs, font=f3)
    draw.text(((W-(bqs[2]-bqs[0]))//2, 459), qs, font=f3, fill=C_DARK_GREEN)
    # Stats
    stats = "34/34 Tests Passing  ·  100% Pass Rate  ·  All Capstone Guidelines Met  ·  30 Project Files"
    bst = draw.textbbox((0,0), stats, font=f3)
    draw.text(((W-(bst[2]-bst[0]))//2, 530), stats, font=f3, fill=C_LIGHT_GREEN)
    draw_footer(draw)


# ── Build slides list ─────────────────────────────────────────────────────────
SLIDES = [
    (slide_title,        5.0),
    (slide_problem,      7.0),
    (slide_architecture, 8.0),
    (slide_tests,        8.0),
    (slide_hitl,         7.0),
    (slide_thankyou,     5.0),
]


def make_clip(draw_fn, duration):
    """Render one slide to a static ImageClip with fade-in / fade-out."""
    frame = make_slide_image(draw_fn)
    clip  = ImageClip(frame, duration=duration)
    return clip.fadein(FADE_DUR).fadeout(FADE_DUR)


print("Rendering slides...")
clips = []
for i, (fn, dur) in enumerate(SLIDES):
    print(f"  Slide {i+1}/{len(SLIDES)}: {fn.__name__}  ({dur}s)")
    clips.append(make_clip(fn, dur))

print("Concatenating...")
video = concatenate_videoclips(clips, method="compose")

os.makedirs("assets", exist_ok=True)
out_path = "assets/CarbonIntelligencePlatform_Demo.mp4"
print(f"Writing {out_path}  ({video.duration:.0f}s @ {FPS}fps)...")
video.write_videofile(out_path, fps=FPS, codec="libx264",
                      audio=False, verbose=False, logger=None)
print(f"✅  Saved: {out_path}")
