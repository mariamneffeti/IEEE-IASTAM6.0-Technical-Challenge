"""Render a reproducible two-orbit heuristic telemetry plot as SVG."""
from pathlib import Path
from simulation.satellite_sim import Satellite
from simulation.baseline import heuristic_agent


def main():
    sat = Satellite(seed=42)
    rows = []
    for _ in range(2 * sat.cfg.orbit_period_s):
        sat.step(heuristic_agent(sat))
        tel = sat.get_telemetry()
        rows.append((tel["time_step"], tel["battery_soc"] * 100,
                     tel["temperature_c"], tel["sunlit"]))

    width, height = 900, 430
    left, right, top, bottom = 74, 24, 36, 55
    plot_w, plot_h = width - left - right, height - top - bottom
    n = len(rows)

    def point(index, value, low, high):
        x = left + plot_w * index / (n - 1)
        y = top + plot_h * (high - value) / (high - low)
        return x, y

    def polyline(column, low, high, color):
        coords = []
        for i, row in enumerate(rows):
            x, y = point(i, row[column], low, high)
            coords.append(f"{x:.2f},{y:.2f}")
        return f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(coords)}"/>'

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#222}.grid{stroke:#ddd;stroke-width:1}</style>',
           '<text x="450" y="22" text-anchor="middle" font-size="16">ASTRA baseline telemetry (seed 42, two orbits)</text>']
    for pct in (30, 50, 70, 90, 100):
        y = point(0, pct, 0, 100)[1]
        svg += [f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>',
                f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11">{pct}</text>']
    for temp in (0, 10, 20, 30, 40, 50):
        y = point(0, temp, 0, 50)[1]
        svg.append(f'<text x="{width-right+8}" y="{y+4:.1f}" font-size="11">{temp}</text>')
    for tick in range(0, 10801, 1800):
        x = left + plot_w * tick / (n - 1)
        svg += [f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}"/>',
                f'<text x="{x:.1f}" y="{height-bottom+20}" text-anchor="middle" font-size="11">{tick}</text>']
    # Mark sunlit/eclipsed spans from configured orbit durations.
    for i, row in enumerate(rows):
        if row[3] and (i == 0 or not rows[i-1][3]):
            start = i
            j = i
            while j + 1 < n and rows[j+1][3]:
                j += 1
            x0 = left + plot_w * start / (n - 1)
            x1 = left + plot_w * j / (n - 1)
            svg.append(f'<rect x="{x0:.1f}" y="{top}" width="{x1-x0:.1f}" height="{plot_h}" fill="#ffd166" opacity="0.12"/>')
    svg += [polyline(1, 0, 100, '#1464a5'), polyline(2, 0, 50, '#d1495b'),
            f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#222"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#222"/>',
            f'<text x="{left}" y="{height-12}" font-size="12">Mission time (s)</text>',
            f'<text transform="translate(16 {top+plot_h/2}) rotate(-90)" text-anchor="middle" font-size="12">Battery SoC (%)</text>',
            f'<text transform="translate({width-8} {top+plot_h/2}) rotate(90)" text-anchor="middle" font-size="12">Chip temperature (°C)</text>',
            '<line x1="300" y1="414" x2="330" y2="414" stroke="#1464a5" stroke-width="2"/><text x="336" y="418" font-size="11">Battery SoC</text>',
            '<line x1="435" y1="414" x2="465" y2="414" stroke="#d1495b" stroke-width="2"/><text x="471" y="418" font-size="11">Chip temperature</text>',
            '<rect x="580" y="407" width="14" height="12" fill="#ffd166" opacity="0.4"/><text x="600" y="418" font-size="11">Sunlit interval</text>',
            '</svg>']
    output = Path(__file__).resolve().parents[1] / "results" / "figures" / "orbit_telemetry.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg), encoding="utf-8")
    # Write a small vector PDF using only built-in PDF drawing operators so
    # the figure can be included by pdflatex without an SVG conversion tool.
    pdf_commands = ["q", "1 1 1 rg 0 0 900 430 re f", "0 0 0 RG 0 0 0 rg"]

    def pdf_line(x0, y0, x1, y1, color=(0.85, 0.85, 0.85), line_width=1):
        r, g, b = color
        pdf_commands.append(f"{r} {g} {b} RG {line_width} w {x0:.2f} {430-y0:.2f} m {x1:.2f} {430-y1:.2f} l S")

    def pdf_text(x, y, value, size=10):
        safe = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        pdf_commands.append(f"BT /F1 {size} Tf {x:.2f} {430-y:.2f} Td ({safe}) Tj ET")

    for pct in (30, 50, 70, 90, 100):
        y = point(0, pct, 0, 100)[1]
        pdf_line(left, y, width-right, y)
        pdf_text(left-28, y+4, str(pct), 10)
    for temp in (0, 10, 20, 30, 40, 50):
        y = point(0, temp, 0, 50)[1]
        pdf_text(width-right+8, y+4, str(temp), 10)
    for tick in range(0, 10801, 1800):
        x = left + plot_w * tick / (n - 1)
        pdf_line(x, top, x, height-bottom)
        pdf_text(x-12, height-bottom+20, str(tick), 9)
    pdf_line(left, top+plot_h, width-right, top+plot_h, (0.1, 0.1, 0.1))
    pdf_line(left, top, left, top+plot_h, (0.1, 0.1, 0.1))
    for column, low, high, color in ((1, 0, 100, (0.078, 0.392, 0.647)),
                                     (2, 0, 50, (0.82, 0.286, 0.357))):
        prior = point(0, rows[0][column], low, high)
        for i, row in enumerate(rows[1:], 1):
            current = point(i, row[column], low, high)
            pdf_line(*prior, *current, color, 1.1)
            prior = current
    pdf_text(270, 20, "ASTRA baseline telemetry (seed 42, two orbits)", 15)
    pdf_text(74, 418, "Mission time (s)", 11)
    pdf_text(300, 414, "Battery SoC (%)", 10)
    pdf_text(465, 414, "Chip temperature (deg C)", 10)
    pdf_commands.append("Q")
    content = "\n".join(pdf_commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 900 430] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_num, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_num} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    pdf_path = output.with_suffix(".pdf")
    pdf_path.write_bytes(pdf)
    print(f"Wrote {output}")
    print(f"Wrote {pdf_path}")
    print(f"SoC range: {min(r[1] for r in rows):.2f}%–{max(r[1] for r in rows):.2f}%")
    print(f"Temperature range: {min(r[2] for r in rows):.2f}–{max(r[2] for r in rows):.2f} °C")


if __name__ == "__main__":
    main()
