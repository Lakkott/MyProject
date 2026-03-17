"""
Flask web app for the Sales Intelligence Dashboard.
Generates the dashboard on demand and serves it as an image.
"""

import io
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import numpy as np
from collections import defaultdict
from flask import Flask, send_file, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Sales Intelligence Dashboard</title>
  <style>
    body { margin: 0; background: #0d0d1a; display: flex; flex-direction: column;
           align-items: center; justify-content: center; min-height: 100vh; }
    h1   { color: #e8c547; font-family: monospace; margin-bottom: 16px; }
    img  { max-width: 100%; border: 1px solid #2a2a40; }
  </style>
</head>
<body>
  <h1>Sales Intelligence Dashboard</h1>
  <img src="/dashboard.png" alt="Sales Dashboard">
</body>
</html>
"""

def load_sales_data(filepath="sample_sales_data.csv"):
    sales_data = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sales_data.append({
                "id":      int(row["id"]),
                "name":    row["name"],
                "region":  row["region"],
                "product": row["product"],
                "sales":   int(row["sales"]),
                "units":   int(row["units"]),
                "date":    row["date"],
            })
    return sales_data


def build_dashboard():
    sales_data = load_sales_data()

    product_totals = defaultdict(lambda: {"revenue": 0, "units": 0})
    for r in sales_data:
        product_totals[r["product"]]["revenue"] += r["sales"]
        product_totals[r["product"]]["units"]   += r["units"]

    product_names   = list(product_totals.keys())
    product_revenue = [product_totals[p]["revenue"] for p in product_names]
    product_units   = [product_totals[p]["units"]   for p in product_names]

    region_totals = defaultdict(int)
    for r in sales_data:
        region_totals[r["region"]] += r["sales"]
    region_items   = sorted(region_totals.items(), key=lambda x: x[1], reverse=True)
    region_names   = [x[0] for x in region_items]
    region_revenue = [x[1] for x in region_items]

    month_totals = defaultdict(int)
    month_labels = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
    for r in sales_data:
        mo = r["date"][5:7]
        month_totals[mo] += r["sales"]
    sorted_months   = sorted(month_totals.keys())
    months          = [month_labels[m] for m in sorted_months]
    monthly_revenue = [month_totals[m] for m in sorted_months]

    total_revenue  = sum(r["sales"] for r in sales_data)
    total_units    = sum(r["units"] for r in sales_data)
    avg_sale       = total_revenue / len(sales_data)
    top_region     = region_names[0]
    top_region_rev = region_revenue[0]

    COLORS = ["#e8c547", "#f0a05a", "#e87070", "#9b8fe8"]
    BG     = "#0d0d1a"
    PANEL  = "#141428"
    BORDER = "#2a2a40"
    TEXT   = "#f0ece0"
    MUTED  = "#8a8a9a"
    GOLD   = "#e8c547"
    PURPLE = "#9b8fe8"

    def style_ax(ax, title=""):
        ax.set_facecolor(PANEL)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        if title:
            ax.set_title(title, color=MUTED, fontsize=9, fontweight="normal",
                         loc="left", pad=10, fontfamily="monospace")

    fig = plt.figure(figsize=(18, 14), facecolor=BG)
    fig.patch.set_facecolor(BG)
    gs = gridspec.GridSpec(4, 3, figure=fig,
                           hspace=0.55, wspace=0.35,
                           top=0.88, bottom=0.07,
                           left=0.06, right=0.97)

    fig.text(0.06, 0.95, "Sales Intelligence",
             color=TEXT, fontsize=28, fontweight="bold", va="top")
    fig.text(0.06, 0.905,
             f"Q1–Q2  ·  2024  ·  {len(sales_data)} transactions  ·  {len(region_names)} regions",
             color=MUTED, fontsize=11, va="top", fontfamily="monospace")
    fig.text(0.97, 0.95, f"${total_revenue:,}",
             color=GOLD, fontsize=28, fontweight="bold", va="top", ha="right")
    fig.text(0.97, 0.905, "total revenue",
             color=MUTED, fontsize=10, va="top", ha="right", fontfamily="monospace")

    kpis = [
        ("Total Revenue", f"${total_revenue:,}", f"across {len(sales_data)} sales"),
        ("Units Sold",    str(total_units),        f"avg {total_units/len(sales_data):.1f} / sale"),
        ("Avg Sale",      f"${avg_sale:,.0f}",     "per transaction"),
        ("Top Region",    top_region,               f"${top_region_rev:,} revenue"),
    ]
    for (label, value, sub), (x, y, w, h) in zip(kpis,
            [(0.06 + i * 0.235, 0.845, 0.20, 0.055) for i in range(4)]):
        ax_kpi = fig.add_axes([x, y, w, h])
        ax_kpi.set_facecolor(PANEL)
        ax_kpi.set_xticks([]); ax_kpi.set_yticks([])
        for sp in ax_kpi.spines.values():
            sp.set_edgecolor(BORDER); sp.set_linewidth(0.8)
        ax_kpi.text(0.05, 0.85, label.upper(), transform=ax_kpi.transAxes,
                    color=MUTED, fontsize=7.5, fontfamily="monospace", va="top")
        ax_kpi.text(0.05, 0.45, value, transform=ax_kpi.transAxes,
                    color=TEXT, fontsize=18, fontweight="bold", va="top")
        ax_kpi.text(0.05, 0.02, sub, transform=ax_kpi.transAxes,
                    color=GOLD, fontsize=8, va="bottom", fontfamily="monospace")

    ax_trend = fig.add_subplot(gs[0, :2])
    style_ax(ax_trend, "MONTHLY REVENUE TREND")
    ax_trend.plot(months, monthly_revenue, color=GOLD, linewidth=2.5,
                  marker="o", markersize=7, markerfacecolor=GOLD, zorder=3)
    ax_trend.fill_between(months, monthly_revenue, alpha=0.12, color=GOLD)
    ax_trend.set_ylim(0, max(monthly_revenue) * 1.25)
    ax_trend.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
    ax_trend.grid(axis="y", color=BORDER, linewidth=0.6, linestyle="--")
    ax_trend.set_axisbelow(True)
    for x, y in zip(months, monthly_revenue):
        ax_trend.annotate(f"${y:,}", (x, y), textcoords="offset points",
                          xytext=(0, 10), ha="center", color=TEXT, fontsize=9,
                          fontfamily="monospace")

    ax_region = fig.add_subplot(gs[0, 2])
    style_ax(ax_region, "REVENUE BY REGION")
    bars = ax_region.barh(region_names, region_revenue, color=PURPLE,
                          height=0.55, edgecolor="none")
    ax_region.set_xlim(0, max(region_revenue) * 1.2)
    ax_region.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:.1f}k"))
    ax_region.grid(axis="x", color=BORDER, linewidth=0.6, linestyle="--")
    ax_region.set_axisbelow(True)
    ax_region.tick_params(axis="y", colors=TEXT)
    for bar, val in zip(bars, region_revenue):
        ax_region.text(val + 30, bar.get_y() + bar.get_height() / 2,
                       f"${val:,}", va="center", color=TEXT, fontsize=9,
                       fontfamily="monospace")

    ax_prod = fig.add_subplot(gs[1, :2])
    style_ax(ax_prod, "REVENUE BY PRODUCT")
    x_pos = np.arange(len(product_names))
    colors_used = COLORS[:len(product_names)]
    bars2 = ax_prod.bar(x_pos, product_revenue, color=colors_used,
                        width=0.5, edgecolor="none")
    ax_prod.set_xticks(x_pos)
    ax_prod.set_xticklabels(product_names, color=TEXT, fontsize=10)
    ax_prod.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:.1f}k"))
    ax_prod.grid(axis="y", color=BORDER, linewidth=0.6, linestyle="--")
    ax_prod.set_axisbelow(True)
    for bar, val in zip(bars2, product_revenue):
        ax_prod.text(bar.get_x() + bar.get_width() / 2, val + 60,
                     f"${val:,}", ha="center", color=TEXT, fontsize=9,
                     fontfamily="monospace")

    ax_pie = fig.add_subplot(gs[1, 2])
    style_ax(ax_pie, "REVENUE SHARE")
    wedges, texts, autotexts = ax_pie.pie(
        product_revenue, labels=product_names, colors=colors_used,
        autopct="%1.0f%%", startangle=140,
        wedgeprops={"edgecolor": BG, "linewidth": 2}, pctdistance=0.75)
    for t in texts:
        t.set_color(TEXT); t.set_fontsize(9)
    for at in autotexts:
        at.set_color(BG); at.set_fontsize(8); at.set_fontweight("bold")
    ax_pie.add_patch(plt.Circle((0, 0), 0.45, color=PANEL))

    ax_units = fig.add_subplot(gs[2, :2])
    style_ax(ax_units, "UNITS SOLD BY PRODUCT")
    bars3 = ax_units.bar(x_pos, product_units, color=colors_used, width=0.5, edgecolor="none")
    ax_units.set_xticks(x_pos)
    ax_units.set_xticklabels(product_names, color=TEXT, fontsize=10)
    ax_units.grid(axis="y", color=BORDER, linewidth=0.6, linestyle="--")
    ax_units.set_axisbelow(True)
    for bar, val in zip(bars3, product_units):
        ax_units.text(bar.get_x() + bar.get_width() / 2, val + 0.2,
                      str(val), ha="center", color=TEXT, fontsize=10,
                      fontfamily="monospace")

    top_product = product_names[product_revenue.index(max(product_revenue))]
    top_pct     = max(product_revenue) / total_revenue * 100
    low_product = product_names[product_revenue.index(min(product_revenue))]
    low_rev_per_unit = min(product_revenue) / product_units[product_revenue.index(min(product_revenue))]
    top_month   = months[monthly_revenue.index(max(monthly_revenue))]

    ax_insight = fig.add_subplot(gs[2, 2])
    ax_insight.set_facecolor("#14200d")
    for sp in ax_insight.spines.values():
        sp.set_edgecolor(GOLD); sp.set_linewidth(0.6); sp.set_alpha(0.4)
    ax_insight.set_xticks([]); ax_insight.set_yticks([])
    ax_insight.text(0.05, 0.96, "KEY INSIGHTS", transform=ax_insight.transAxes,
                    color=GOLD, fontsize=8, fontfamily="monospace", va="top")
    insights = [
        (">>", f"{top_product}s drive {top_pct:.0f}% of all revenue."),
        (">>", f"Regions balanced; {top_region} leads by ${top_region_rev - region_revenue[1]:,}."),
        (">>", f"{top_month} strongest month — ${max(monthly_revenue):,}."),
        (">>", f"{low_product} lowest rev/unit at ~${low_rev_per_unit:.0f}."),
    ]
    for i, (icon, txt) in enumerate(insights):
        y_pos = 0.78 - i * 0.21
        ax_insight.text(0.04, y_pos, icon, transform=ax_insight.transAxes,
                        fontsize=13, va="top")
        ax_insight.text(0.18, y_pos, txt, transform=ax_insight.transAxes,
                        color="#c8c4b0", fontsize=8.5, va="top", wrap=True)

    ax_lb = fig.add_subplot(gs[3, :])
    ax_lb.set_facecolor(PANEL)
    for sp in ax_lb.spines.values():
        sp.set_edgecolor(BORDER); sp.set_linewidth(0.8)
    ax_lb.set_xticks([]); ax_lb.set_yticks([])
    ax_lb.text(0.01, 0.95, "SALES REP LEADERBOARD", transform=ax_lb.transAxes,
               color=MUTED, fontsize=8, fontfamily="monospace", va="top")
    ranked = sorted(sales_data, key=lambda r: r["sales"], reverse=True)
    medals = ["#1", "#2", "#3"]
    cols   = ["#", "NAME", "REGION", "PRODUCT", "REVENUE", "UNITS"]
    col_x  = [0.01, 0.06, 0.25, 0.38, 0.52, 0.65]
    for ci, (col, cx) in enumerate(zip(cols, col_x)):
        ax_lb.text(cx, 0.82, col, transform=ax_lb.transAxes,
                   color=MUTED, fontsize=7.5, fontfamily="monospace", va="top")
    for i, rep in enumerate(ranked):
        y = 0.62 - i * 0.13
        medal = medals[i] if i < 3 else f"#{i+1}"
        if i == 0:
            rect = FancyBboxPatch((0.0, y - 0.08), 1.0, 0.14,
                                   transform=ax_lb.transAxes, clip_on=False,
                                   boxstyle="round,pad=0.01",
                                   facecolor=GOLD, alpha=0.07, edgecolor="none")
            ax_lb.add_patch(rect)
        vals = [medal, rep["name"], rep["region"], rep["product"],
                f"${rep['sales']:,}", str(rep["units"])]
        for ci, (val, cx) in enumerate(zip(vals, col_x)):
            color = GOLD if (i < 3 and ci == 0) else (TEXT if ci in [1, 4] else MUTED)
            ax_lb.text(cx, y, val, transform=ax_lb.transAxes,
                       color=color, fontsize=9,
                       fontfamily=("monospace" if ci in [0, 4, 5] else "sans-serif"),
                       va="center")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    buf.seek(0)
    return buf


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/dashboard.png")
def dashboard():
    buf = build_dashboard()
    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
