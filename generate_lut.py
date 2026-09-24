import os
import colorsys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LUT_DIR = os.path.join(SCRIPT_DIR, "assets", "luts")
os.makedirs(LUT_DIR, exist_ok=True)
LUT_PATH = os.path.join(LUT_DIR, "tropical_cinematic.cube")
SIZE = 33

def s_curve(x):
    # Filmic S-curve: deepens rich tones without crushing shadows
    return x * x * (3.0 - 2.0 * x) * 0.35 + x * 0.65

def generate():
    lines = []
    lines.append('TITLE "Tropical_Cinematic_Vibes"\n')
    lines.append(f'LUT_3D_SIZE {SIZE}\n')

    vals = [i / (SIZE - 1) for i in range(SIZE)]

    for b_val in vals:
        for g_val in vals:
            for r_val in vals:
                # 1. Apply gentle film S-curve
                r = s_curve(r_val)
                g = s_curve(g_val)
                b = s_curve(b_val)
                
                # 2. Convert to HSV for targeted grading
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                
                # Boost saturation moderately (+15%)
                s = min(1.0, s * 1.15)
                
                # Tropical lush greens (Hue between 65 deg and 160 deg -> 0.18 to 0.44)
                if 0.18 <= h <= 0.44:
                    # Slightly deepen yellow-greens toward emerald
                    dist = abs(h - 0.30)
                    shift = max(0.0, 1.0 - dist / 0.15)
                    h = min(1.0, h + 0.025 * shift)
                    s = min(1.0, s * 1.12)
                
                # Convert back to RGB
                ro, go, bo = colorsys.hsv_to_rgb(h, s, v)
                
                # 3. Add warm golden sunlight to highlights (v > 0.65)
                if v > 0.65:
                    w = ((v - 0.65) / 0.35) * 0.035
                    ro = min(1.0, ro + w * 1.0)
                    go = min(1.0, go + w * 0.7)
                    bo = max(0.0, bo - w * 0.2)
                    
                lines.append(f"{ro:.6f} {go:.6f} {bo:.6f}\n")

    with open(LUT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[SUCCESS] Wrote {len(lines)} lines to {LUT_PATH}")

if __name__ == "__main__":
    generate()
