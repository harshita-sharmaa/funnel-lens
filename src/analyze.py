"""Run the SQL in sql/ against the product database and publish results.

Writes one CSV per query plus two charts to outputs/, and prints a summary
with the size of the Android onboarding opportunity.
"""
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "product.db"
SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "outputs"

PLATFORM_COLORS = {"Web": "#2a78d6", "iOS": "#0ca30c", "Android": "#d03b3b"}
BLUE, INK, MUTED, GRID, SURFACE = "#2a78d6", "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c3c2b7",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "text.color": INK,
        "axes.labelcolor": "#52514e",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "font.size": 10,
    }
)


def run_query(con, filename):
    return pd.read_sql_query((SQL_DIR / filename).read_text(), con)


def chart_funnel(funnel):
    steps = ["Signed up", "Verified email", "Created project", "Invited teammate"]
    cols = ["verified_pct_of_signups", "created_pct_of_signups", "invited_pct_of_signups"]
    platforms = funnel[funnel["platform"] != "All"]
    x = np.arange(len(steps))
    width = 0.26
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for i, (_, row) in enumerate(platforms.iterrows()):
        values = [100.0] + [row[c] for c in cols]
        bars = ax.bar(x + (i - 1) * width, values, width, label=row["platform"],
                      color=PLATFORM_COLORS[row["platform"]])
        ax.bar_label(bars, labels=[f"{v:.0f}" for v in values], padding=2, color=INK, fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(steps)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 112)
    ax.set_ylabel("% of signups reaching the step")
    ax.set_title("Onboarding funnel by platform: Android drops at project creation")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "funnel_by_platform.png", dpi=160)
    plt.close(fig)


def chart_activation(activation):
    labels = activation["first_week_group"].str.slice(3)
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    bars = ax.barh(labels, activation["week4_retention_pct"],
                   color=[BLUE, "#9dbfe8", "#c3c2b7"], height=0.55)
    ax.bar_label(bars, labels=[f"{v:.0f}%  ({s:.0f}% of users)" for v, s in
                               zip(activation["week4_retention_pct"], activation["share_of_users_pct"])],
                 padding=5, color=INK)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Still active in week 4 (%)")
    ax.set_title("Week-4 retention by what users did in their first 7 days")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "retention_by_first_week.png", dpi=160)
    plt.close(fig)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    funnel = run_query(con, "01_funnel.sql")
    cohorts = run_query(con, "02_cohort_retention.sql")
    activation = run_query(con, "03_activation.sql")
    con.close()

    funnel.to_csv(OUT_DIR / "funnel.csv", index=False)
    cohorts.to_csv(OUT_DIR / "cohort_retention.csv", index=False)
    activation.to_csv(OUT_DIR / "activation.csv", index=False)

    chart_funnel(funnel)
    chart_activation(activation)

    # Opportunity size: Android users who would create a project if Android
    # converted from verified to created at the same rate as Web
    by_platform = funnel.set_index("platform")
    android, web = by_platform.loc["Android"], by_platform.loc["Web"]
    extra = android["verified"] * web["verify_to_create_conv"] / 100 - android["created_project"]
    total_created = by_platform.loc["All", "created_project"]

    print(funnel.to_string(index=False))
    print()
    print(cohorts.to_string(index=False))
    print()
    print(activation.to_string(index=False))
    print(f"\nAndroid verified-to-created conversion: {android['verify_to_create_conv']:.1f}% "
          f"vs {web['verify_to_create_conv']:.1f}% on Web")
    print(f"Closing that gap adds about {extra:,.0f} users who create a project "
          f"(+{100 * extra / total_created:.1f}% on today's {total_created:,.0f})")
    print(f"Outputs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
