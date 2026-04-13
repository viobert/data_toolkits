"""
Shared plotting and CSV helpers for dataset_statistic.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any, Callable


def counter_to_rows(counter: Counter) -> list[dict[str, Any]]:
    total = sum(counter.values())
    if total == 0:
        return []

    rows: list[dict[str, Any]] = []
    for category, count in counter.most_common():
        ratio = count / total
        rows.append(
            {
                "category": str(category),
                "count": int(count),
                "ratio": ratio,
                "percentage": ratio * 100.0,
            }
        )
    return rows


def save_distribution_csv(rows: list[dict[str, Any]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "count", "ratio", "percentage"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "category": row["category"],
                    "count": row["count"],
                    "ratio": f"{row['ratio']:.8f}",
                    "percentage": f"{row['percentage']:.4f}",
                }
            )


def _make_autopct(values: list[int]) -> Callable[[float], str]:
    total = sum(values)

    def _autopct(pct: float) -> str:
        if total == 0:
            return "0\n(0.0%)"
        count = int(round(pct * total / 100.0))
        return f"{count}\n({pct:.1f}%)"

    return _autopct


def _build_legend_labels(labels: list[str], counts: list[int]) -> list[str]:
    total = sum(counts)
    legend_labels: list[str] = []
    for label, count in zip(labels, counts):
        pct = 0.0 if total <= 0 else count / total * 100.0
        legend_labels.append(f"{label}: {count} ({pct:.1f}%)")
    return legend_labels


def save_pie_chart(rows: list[dict[str, Any]], title: str, output_png: Path, dpi: int = 160) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError(
            "matplotlib is required for pie chart export. "
            "Please fix your matplotlib/numpy environment first."
        ) from exc

    if not rows:
        raise ValueError("No rows to plot.")

    # Match project-level chart style for readability and consistency.
    plt.style.use("seaborn-v0_8-whitegrid")

    labels = [str(row["category"]) for row in rows]
    counts = [int(row["count"]) for row in rows]
    total = sum(counts)

    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % cmap.N) for i in range(len(labels))]

    plot_counts = counts
    plot_colors = colors
    center_note: str | None = None

    if total <= 0:
        plot_counts = [1]
        plot_colors = ["#D9D9D9"]
        center_note = "No data"

    # Increase canvas width and use tight bbox to avoid clipped legends.
    fig, ax = plt.subplots(figsize=(13.0, 8.0))
    wedges, _, _ = ax.pie(
        plot_counts,
        labels=None,
        colors=plot_colors,
        startangle=90,
        counterclock=False,
        autopct=_make_autopct(counts),
        pctdistance=0.72,
        wedgeprops={"linewidth": 1.0, "edgecolor": "white"},
        textprops={"fontsize": 9},
    )

    autotexts = ax.texts[-len(plot_counts) :]
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(8.5)
        autotext.set_weight("bold")

    if center_note is not None:
        ax.text(0, 0, center_note, ha="center", va="center", fontsize=12, color="#4D4D4D")

    legend_labels = _build_legend_labels(labels, counts)
    legend_handles = wedges if total > 0 else [wedges[0]] * len(legend_labels)
    ax.legend(
        legend_handles,
        legend_labels,
        title="Legend",
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        fontsize=9,
        title_fontsize=10,
        frameon=True,
    )

    ax.set_title(title)
    ax.axis("equal")
    fig.tight_layout()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=max(180, dpi), bbox_inches="tight")
    plt.close(fig)
