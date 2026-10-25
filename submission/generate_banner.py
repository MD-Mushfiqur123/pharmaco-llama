"""
Pharmaco-Llama Official 1200x630 Dark Mode Submission Banner Generator
Uses Python Pillow (PIL) to generate a high-contrast clinical HUD banner.
"""

import os
from PIL import Image, ImageDraw, ImageFont

def generate_banner():
    width = 1200
    height = 630
    
    # 1. Base Gradient Canvas (Obsidian to Deep Clinical Navy)
    img = Image.new("RGB", (width, height), color="#0A0F1D")
    draw = ImageDraw.Draw(img)
    
    # Draw soft background gradient
    for y in range(height):
        ratio = y / height
        r = int(10 * (1 - ratio) + 15 * ratio)
        g = int(15 * (1 - ratio) + 23 * ratio)
        b = int(29 * (1 - ratio) + 42 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # Draw subtle clinical grid lines
    grid_color = (25, 35, 55)
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
    # Corner Accents (Cyan HUD brackets)
    accent_color = (6, 182, 212)
    bracket_len = 30
    bracket_width = 3
    
    # Top-Left
    draw.line([(40, 40), (40 + bracket_len, 40)], fill=accent_color, width=bracket_width)
    draw.line([(40, 40), (40, 40 + bracket_len)], fill=accent_color, width=bracket_width)
    # Top-Right
    draw.line([(width - 40, 40), (width - 40 - bracket_len, 40)], fill=accent_color, width=bracket_width)
    draw.line([(width - 40, 40), (width - 40, 40 + bracket_len)], fill=accent_color, width=bracket_width)
    # Bottom-Left
    draw.line([(40, height - 40), (40 + bracket_len, height - 40)], fill=accent_color, width=bracket_width)
    draw.line([(40, height - 40), (40, height - 40 - bracket_len)], fill=accent_color, width=bracket_width)
    # Bottom-Right
    draw.line([(width - 40, height - 40), (width - 40 - bracket_len, height - 40)], fill=accent_color, width=bracket_width)
    draw.line([(width - 40, height - 40), (width - 40, height - 40 - bracket_len)], fill=accent_color, width=bracket_width)

    # Badges (Top Bar)
    # Meta Hackathon Tag
    draw.rounded_rectangle([(60, 60), (320, 95)], radius=6, fill=(30, 41, 59), outline=(59, 130, 246), width=1)
    # Live FDA Tag
    draw.rounded_rectangle([(340, 60), (560, 95)], radius=6, fill=(6, 78, 59), outline=(16, 185, 129), width=1)
    # NIH Certified Tag
    draw.rounded_rectangle([(580, 60), (840, 95)], radius=6, fill=(30, 27, 75), outline=(139, 92, 246), width=1)

    try:
        font_large = ImageFont.truetype("arial.ttf", 64)
        font_title = ImageFont.truetype("arialbd.ttf", 72)
        font_sub = ImageFont.truetype("arial.ttf", 26)
        font_badge = ImageFont.truetype("arialbd.ttf", 14)
        font_mono = ImageFont.truetype("cour.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_mono = ImageFont.load_default()

    # Draw Badge Text
    draw.text((80, 70), "META $1M GLOBAL HACKATHON", fill=(96, 165, 250), font=font_badge)
    draw.text((360, 70), "OPENFDA LIVE CONNECTED", fill=(52, 211, 153), font=font_badge)
    draw.text((600, 70), "NIH-CERTIFIED SCHOLAR", fill=(196, 181, 253), font=font_badge)

    # Main Title
    draw.text((60, 140), "PHARMACO-LLAMA", fill=(255, 255, 255), font=font_title)
    
    # Glowing Accent Bar under title
    draw.line([(60, 230), (520, 230)], fill=(6, 182, 212), width=5)
    
    # Subtitle
    draw.text(
        (60, 250),
        "Autonomous Clinical Pharmacology & Polypharmacy Safety Auditor",
        fill=(148, 163, 184),
        font=font_sub
    )

    # Value Proposition Callouts
    draw.text(
        (60, 310),
        "Bridges Prescription Computer Vision with Live US FDA Black Box Warnings & Pharmacokinetics.",
        fill=(203, 213, 225),
        font=font_sub
    )

    # Feature Grid Box (Right side visualization)
    box_x = 720
    box_y = 140
    box_w = 420
    box_h = 420
    
    draw.rounded_rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], radius=16, fill=(17, 24, 39), outline=(55, 65, 81), width=2)
    draw.text((box_x + 24, box_y + 24), "CLINICAL TELEMETRY HUD", fill=(6, 182, 212), font=font_badge)
    
    # Simulated Hazard Dial
    draw.text((box_x + 24, box_y + 60), "POLYPHARMACY HAZARD INDEX:", fill=(156, 163, 175), font=font_mono)
    draw.text((box_x + 24, box_y + 90), "94 / 100", fill=(239, 68, 68), font=font_title)
    draw.text((box_x + 24, box_y + 175), "[CRITICAL FATAL WARNING]", fill=(248, 113, 113), font=font_badge)
    
    # Feature Bullet Points
    bullets = [
        "• Meta Llama 3.2 Vision: Prescription OCR",
        "• Live US OpenFDA 21 CFR 201.57 Query",
        "• 1-Compartment PK Clearance Cp(t) Curves",
        "• CYP450 Enzyme Blockade Triage",
        "• Automated Safe Drug Substitution Plan"
    ]
    
    for i, b in enumerate(bullets):
        draw.text((box_x + 24, box_y + 220 + (i * 32)), b, fill=(209, 213, 219), font=font_mono)

    # Footer Metadata
    draw.text(
        (60, 560),
        "Creator: Md Mushfiqur Rahim • The Sacred /truth Law • 100% Verifiable OpenFDA Reality",
        fill=(100, 116, 139),
        font=font_mono
    )

    out_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "banner_1200x630.png")
    img.save(out_path, format="PNG")
    print(f"Banner generated successfully: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    generate_banner()
