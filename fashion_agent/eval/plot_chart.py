"""Generate a clean grouped bar chart from summary.csv for the thesis slide.

Output: results/ablation_chart.png (1920x1080, white bg, slide-ready).
Reads results/summary.csv. Run from anywhere with matplotlib installed.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


HERE = Path(__file__).parent
CSV_PATH = HERE / "results" / "summary.csv"
OUT_PATH = HERE / "results" / "ablation_chart.png"

# Slide palette
COLORS = {
    "Hit@1": "#3B82F6",   # blue
    "Hit@3": "#10B981",   # emerald — highlight metric
    "Hit@6": "#A78BFA",   # violet
    "MRR":   "#F59E0B",   # amber
}

METRICS = ["Hit@1", "Hit@3", "Hit@6", "MRR"]


def load_summary() -> list[dict]:
    rows = []
    with CSV_PATH.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "variant": r["variant"],
                "Hit@1": float(r["Hit@1"]),
                "Hit@3": float(r["Hit@3"]),
                "Hit@6": float(r["Hit@6"]),
                "MRR":   float(r["MRR"]),
            })
    return rows


def main() -> None:
    data = load_summary()
    variants = [r["variant"] for r in data]
    n_variants = len(variants)
    n_metrics = len(METRICS)

    fig, ax = plt.subplots(figsize=(14, 7), dpi=160)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bar_width = 0.18
    group_centers = list(range(n_variants))

    for m_idx, metric in enumerate(METRICS):
        offsets = [c + (m_idx - (n_metrics - 1) / 2) * bar_width for c in group_centers]
        values = [r[metric] for r in data]
        bars = ax.bar(
            offsets, values, width=bar_width,
            color=COLORS[metric], edgecolor="white", linewidth=0.5,
            label=metric,
        )
        # value labels on top of every bar (including 0)
        for x, v in zip(offsets, values):
            label_y = max(v, 0) + 0.018
            label_text = f"{v:.2f}" if v > 0 else "0.00"
            ax.text(x, label_y, label_text, ha="center", va="bottom",
                    fontsize=10, color="#1F2937", fontweight="bold")

    # styling
    ax.set_xticks(group_centers)
    ax.set_xticklabels(variants, fontsize=12, color="#111827")
    ax.set_ylabel("Score (0 - 1)", fontsize=12, color="#374151")
    ax.set_ylim(0, 0.95)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
    ax.tick_params(axis="y", labelsize=10, colors="#6B7280")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#D1D5DB")
    ax.spines["left"].set_color("#D1D5DB")

    # title + subtitle (drawn as text for fine control)
    fig.text(0.07, 0.945, "Retrieval Ablation — Hit@K & MRR",
             fontsize=18, fontweight="bold", color="#111827")
    fig.text(0.07, 0.905,
             "N = 24 user-observed cart-adds | Top-K=10 retrieved | query expansion OFF for fair compare",
             fontsize=11, color="#6B7280")

    # legend
    legend_handles = [Patch(facecolor=COLORS[m], label=m) for m in METRICS]
    ax.legend(handles=legend_handles, loc="upper left",
              frameon=False, fontsize=11, ncol=4,
              bbox_to_anchor=(0.0, 1.02))

    # subtle annotation arrow pointing to Full Hybrid as the production system
    full_idx = next((i for i, v in enumerate(variants) if "Full" in v), None)
    if full_idx is not None:
        ax.annotate(
            "Production",
            xy=(full_idx, 0.78),
            xytext=(full_idx - 0.45, 0.88),
            fontsize=11, color="#059669", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#059669", lw=1.5),
        )

    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(OUT_PATH, dpi=160, facecolor="white", bbox_inches="tight")
    print(f"Chart saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
