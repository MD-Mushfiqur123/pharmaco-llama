"""
Pharmaco-Llama: Minimalist White Swiss Clinical Banner Generator (1200x630)
Follows banner-design skill: Minimalist aesthetic, Apple/Swiss typography, disciplined grid alignment,
clean white porcelain palette, high-contrast typography, and floating clinical telemetry card.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

def render_minimal_white_banner():
    width = 1200
    height = 630

    # 1. Base Porcelain White Canvas
    img = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Subtle minimal dot grid (Swiss design system)
    dot_color = (241, 245, 249) # Slate 100
    for x in range(40, width, 32):
        for y in range(40, height, 32):
            draw.point((x, y), fill=dot_color)

    # Outer fine border (Card border)
    border_color = (226, 232, 240) # Slate 200
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=border_color, width=1)

    # 2. Typography Setup (Segoe UI & Segoe UI Bold)
    font_path_bold = "C:/Windows/Fonts/segoeuib.ttf"
    font_path_reg = "C:/Windows/Fonts/segoeui.ttf"
    font_path_semi = "C:/Windows/Fonts/seguisb.ttf"
    font_path_mono = "C:/Windows/Fonts/cour.ttf"

    try:
        font_hero = ImageFont.truetype(font_path_bold, 62)
        font_sub = ImageFont.truetype(font_path_semi, 22)
        font_body = ImageFont.truetype(font_path_reg, 16)
        font_badge = ImageFont.truetype(font_path_bold, 12)
        font_card_title = ImageFont.truetype(font_path_bold, 13)
        font_card_score = ImageFont.truetype(font_path_bold, 54)
        font_card_mono = ImageFont.truetype(font_path_mono, 13)
    except Exception:
        font_hero = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_card_title = ImageFont.load_default()
        font_card_score = ImageFont.load_default()
        font_card_mono = ImageFont.load_default()

    # 3. Left Column Content (Grid aligned: x = 70px)
    left_x = 70

    # Top Badges Row
    # Badge 1: Meta $1M Global Hackathon
    b1_x1, b1_y1 = left_x, 65
    b1_w, b1_h = 240, 28
    draw.rounded_rectangle([(b1_x1, b1_y1), (b1_x1 + b1_w, b1_y1 + b1_h)], radius=6, fill="#EFF6FF", outline="#BFDBFE", width=1)
    draw.text((b1_x1 + 14, b1_y1 + 6), "META $1M GLOBAL HACKATHON", fill="#1D4ED8", font=font_badge)

    # Badge 2: OpenFDA Live
    b2_x1 = b1_x1 + b1_w + 12
    b2_w = 175
    draw.rounded_rectangle([(b2_x1, b1_y1), (b2_x1 + b2_w, b1_y1 + b1_h)], radius=6, fill="#ECFDF5", outline="#A7F3D0", width=1)
    draw.text((b2_x1 + 14, b1_y1 + 6), "OPENFDA LIVE CONNECTED", fill="#047857", font=font_badge)

    # Hero Headline
    hero_y = 125
    draw.text((left_x, hero_y), "Pharmaco-Llama", fill="#0F172A", font=font_hero)
    
    # Minimal Cyan/Blue Accent Underline (Short, disciplined)
    draw.line([(left_x, hero_y + 82), (left_x + 90, hero_y + 82)], fill="#0284C7", width=4)

    # Subtitle
    sub_y = hero_y + 102
    draw.text((left_x, sub_y), "Autonomous Clinical Pharmacology & Polypharmacy Auditor", fill="#334155", font=font_sub)

    # Explanatory Paragraph (Multi-line cleanly aligned)
    body_y = sub_y + 44
    line1 = "Eradicating fatal drug-drug interactions through multimodal prescription"
    line2 = "vision, live US OpenFDA Black Box Warnings, and 1-compartment"
    line3 = "CYP450 pharmacokinetic clearance simulation."
    draw.text((left_x, body_y), line1, fill="#64748B", font=font_body)
    draw.text((left_x, body_y + 24), line2, fill="#64748B", font=font_body)
    draw.text((left_x, body_y + 48), line3, fill="#64748B", font=font_body)

    # Feature List / Pillars
    pillar_y = body_y + 92
    pillars = [
        "• Meta Llama 3.2 Vision: Handwritten Rx & Multi-Pill Label OCR",
        "• Federal Ground Truth: 21 CFR 201.57 Verbatim Boxed Warnings",
        "• Real Biophysical Simulation: Area Under the Curve (AUC) & Half-Life"
    ]
    for i, p in enumerate(pillars):
        draw.text((left_x, pillar_y + (i * 26)), p, fill="#475569", font=font_body)

    # Footnote / Credential Line
    foot_y = 540
    foot_text = "Lead Architect: Md Mushfiqur Rahim  •  US NIH-Certified in Clinical Pharmacology  •  The Sacred /truth Law"
    draw.text((left_x, foot_y), foot_text, fill="#94A3B8", font=font_body)

    # 4. Right Column: Floating Minimalist Clinical Decision Card
    card_x = 730
    card_y = 65
    card_w = 400
    card_h = 500

    # Soft Card Drop Shadow (multi-layer blur simulation)
    shadow_color = (230, 236, 245)
    for offset in range(8, 0, -2):
        draw.rounded_rectangle(
            [(card_x + offset, card_y + offset), (card_x + card_w + offset, card_y + card_h + offset)],
            radius=16,
            fill=shadow_color
        )

    # White Card Body with crisp outline
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill="#FFFFFF", outline="#E2E8F0", width=1)

    # Card Top Header
    draw.text((card_x + 28, card_y + 26), "CLINICAL RISK TELEMETRY", fill="#64748B", font=font_card_title)
    
    # Status Pill (Critical Red)
    pill_w = 110
    draw.rounded_rectangle([(card_x + card_w - pill_w - 28, card_y + 22), (card_x + card_w - 28, card_y + 46)], radius=6, fill="#FEF2F2", outline="#FECACA", width=1)
    draw.text((card_x + card_w - pill_w - 18, card_y + 27), "CRITICAL RISK", fill="#DC2626", font=font_badge)

    # Divider Line
    draw.line([(card_x + 28, card_y + 60), (card_x + card_w - 28, card_y + 60)], fill="#F1F5F9", width=1)

    # Hazard Score Gauge Display
    draw.text((card_x + 28, card_y + 78), "Polypharmacy Hazard Index", fill="#94A3B8", font=font_body)
    draw.text((card_x + 28, card_y + 102), "94", fill="#DC2626", font=font_card_score)
    draw.text((card_x + 104, card_y + 130), "/ 100", fill="#94A3B8", font=font_sub)

    # Hazard Bar Indicator
    bar_x = card_x + 28
    bar_y = card_y + 172
    bar_w = card_w - 56
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + 8)], radius=4, fill="#FEE2E2")
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + int(bar_w * 0.94), bar_y + 8)], radius=4, fill="#EF4444")

    # Conflict Card Inside
    conf_y = card_y + 198
    draw.rounded_rectangle([(bar_x, conf_y), (bar_x + bar_w, conf_y + 88)], radius=10, fill="#F8FAFC", outline="#E2E8F0", width=1)
    draw.text((bar_x + 16, conf_y + 14), "Lethal Interaction Identified:", fill="#1E293B", font=font_card_title)
    draw.text((bar_x + 16, conf_y + 36), "Warfarin 5mg  +  Omeprazole 20mg", fill="#DC2626", font=font_sub)
    draw.text((bar_x + 16, conf_y + 62), "CYP2C19 blockade -> 4.2x Bleeding Hazard", fill="#64748B", font=font_body)

    # Pharmacokinetic Plasma Curve Chart Simulation (Mini Sparkline)
    chart_y = conf_y + 106
    draw.text((bar_x, chart_y), "Pharmacokinetic Plasma Clearance Cp(t)", fill="#64748B", font=font_card_title)

    # Draw Chart Axes
    axis_x0 = bar_x
    axis_y0 = chart_y + 84
    axis_x1 = bar_x + bar_w
    axis_y1 = chart_y + 24
    draw.line([(axis_x0, axis_y0), (axis_x1, axis_y0)], fill="#CBD5E1", width=1)

    # Plot Baseline Curve (Green)
    points_baseline = []
    points_inhibited = []
    num_pts = 10
    base_data = [0, 8.5, 7.2, 5.8, 4.2, 2.9, 1.8, 1.1, 0.6, 0.3]
    inh_data = [0, 9.8, 9.2, 8.5, 7.6, 6.8, 5.9, 4.8, 3.9, 3.1]

    for idx in range(num_pts):
        px = axis_x0 + int((idx / (num_pts - 1)) * bar_w)
        py_base = axis_y0 - int((base_data[idx] / 11.0) * 55)
        py_inh = axis_y0 - int((inh_data[idx] / 11.0) * 55)
        points_baseline.append((px, py_base))
        points_inhibited.append((px, py_inh))

    # Draw lines
    draw.line(points_baseline, fill="#059669", width=2)
    draw.line(points_inhibited, fill="#DC2626", width=2)

    # Legend for chart
    draw.text((bar_x, axis_y0 + 8), "Green: Baseline t1/2 (40h)", fill="#059669", font=font_badge)
    draw.text((bar_x + 160, axis_y0 + 8), "Red: Inhibited t1/2 (88.5h)", fill="#DC2626", font=font_badge)

    # Save Output Banner
    out_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "banner_1200x630.png")
    img.save(out_path, format="PNG", quality=95)
    print(f"Minimalist White Banner generated successfully: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    render_minimal_white_banner()
