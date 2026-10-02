from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ASSET_DIR = Path.home() / "AppData" / "Local" / "Temp" / "vaep_track_report_assets"


def main() -> None:
    episodes = pd.read_csv(PROCESSED / "episode_manifest.csv")
    annotations = pd.read_csv(PROCESSED / "gegenpressing_annotation_manifest.csv")
    match_summary = (
        episodes.groupby("match_id")
        .agg(
            candidates=("candidate_id", "size"),
            strict_valid=("strict_valid", "sum"),
        )
    )
    pilot = annotations[
        annotations["pilot_selected"].astype(str).str.lower().eq("true")
        & annotations["is_gegenpressing"].notna()
    ].copy()

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    order = ["J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WPY", "J03WQQ", "J03WR9"]
    chart = match_summary.loc[order]
    x = range(len(chart))
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    ax.bar(
        [i - 0.18 for i in x],
        chart["candidates"],
        width=0.36,
        label="Kandidat",
        color="#8FAADC",
    )
    ax.bar(
        [i + 0.18 for i in x],
        chart["strict_valid"],
        width=0.36,
        label="Valid ketat",
        color="#2F75B5",
    )
    ax.set_xticks(list(x), order)
    ax.set_ylabel("Jumlah episode")
    ax.set_title("Kandidat transisi dan episode valid per pertandingan")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False, ncols=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "episode_quantity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    counts = (
        pilot["is_gegenpressing"]
        .astype(int)
        .value_counts()
        .reindex([-1, 0, 1], fill_value=0)
    )
    labels = ["Ragu", "Bukan", "Gegenpressing"]
    colors = ["#F4B183", "#A5A5A5", "#70AD47"]
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    bars = ax.bar(labels, counts.values, color=colors, width=0.58)
    for bar, value in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.35,
            str(value),
            ha="center",
            fontsize=10,
        )
    ax.set_ylim(0, max(counts.values) + 4)
    ax.set_ylabel("Jumlah sampel")
    ax.set_title("Distribusi anotasi pilot")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "pilot_annotation.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(ASSET_DIR)


if __name__ == "__main__":
    main()
