"""Read-only label screening; never writes the source annotations."""
from pathlib import Path
import hashlib
import json
import sys
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.idsse_episode_dataset import load_match
from src.gegenpressing_annotation import compute_annotation_context, plot_annotation_context, _draw_pitch

OUT = Path(__file__).resolve().parent
(OUT / "panels").mkdir(exist_ok=True)
SOURCE = ROOT / "data/processed/gegenpressing_annotation_manifest.csv"
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
a = pd.read_csv(SOURCE)
contexts, records, event_records = {}, [], []
for match_id, rows in a.groupby("match_id"):
    print("Checking", match_id, flush=True)
    tracking, events = load_match(ROOT / "data/sportec_idsse", match_id)
    events["event_seconds"] = pd.to_timedelta(events.timestamp).dt.total_seconds()
    for _, row in rows.iterrows():
        c = compute_annotation_context(row, tracking, events)
        order = int(row.annotation_order)
        contexts[order] = c
        w, m = c["window"], c["metrics"]
        times = c["relative_times"]
        start = pd.Timedelta(row.loss_timestamp).total_seconds()
        ev = events[(events.period_id == row.period_id) &
                    events.event_seconds.between(start - 2, start + 2)].copy()
        for _, event in ev.iterrows():
            event_records.append({
                "annotation_order": order, "candidate_id": row.candidate_id,
                "relative_time_s": round(event.event_seconds - start, 3),
                **{k: event.get(k) for k in ["event_type", "team_id", "player_id", "set_piece_type", "result", "ball_state"]},
            })
        # Distinguish relative approach from the player's own motion toward ball.
        lp, bp = c["losing_positions"], c["ball_positions"]
        pv = np.gradient(lp, 1/25, axis=0)
        toball = bp[:, None, :] - lp
        dist = np.linalg.norm(toball, axis=2)
        own_approach = np.sum(pv * toball / np.maximum(dist[:, :, None], 1e-9), axis=2)
        first = np.flatnonzero(m.total_pressers.to_numpy() > 0)
        rec = {
            "annotation_order": order, "candidate_id": row.candidate_id,
            "label_original": int(row.is_gegenpressing),
            "notes_original": row.annotation_notes,
            **c["summary"].to_dict(),
            "first_cue_s": float(times[first[0]]) if len(first) else np.nan,
            "distance_at_0_m": float(dist[0].min()),
            "distance_at_2_m": float(dist[-1].min()),
            "max_own_approach_within_10m_mps": float(np.max(own_approach[dist <= 10])) if (dist <= 10).any() else np.nan,
            "dead_frames": int(w.ball_state.ne("alive").sum()),
            "frames": len(w),
            "ball_z_max_raw": pd.to_numeric(w.ball_z, errors="coerce").max(),
            "ball_xy_displacement_m": float(np.linalg.norm(bp[-1] - bp[0])),
        }
        if rec["max_total_pressers"] == 0:
            rec["screening"] = "prioritas_tanpa_cue_bola"
        elif rec["pressure_duration_s"] < .4:
            rec["screening"] = "prioritas_cue_singkat"
        elif rec["label_original"] != 1:
            rec["screening"] = "review_label_negatif_atau_ragu"
        else:
            rec["screening"] = "belum_ditinjau_visual"
        records.append(rec)
    del tracking

df = pd.DataFrame(records).sort_values("annotation_order")
df.to_csv(OUT / "screening_264.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(event_records).to_csv(OUT / "event_context.csv", index=False, encoding="utf-8-sig")
with (OUT / "contexts.pkl").open("wb") as stream:
    pickle.dump(contexts, stream)

selected = df[(df.label_original != 1) | (df.pressure_duration_s < .4)]
selected.to_csv(OUT / "review_priority.csv", index=False, encoding="utf-8-sig")
for _, row in selected.iterrows():
    if row.max_total_pressers == 0 or row.pressure_duration_s < .4:
        c = contexts[int(row.annotation_order)]
        fig = plot_annotation_context(c)
        fig.savefig(OUT / "panels" / f"{int(row.annotation_order):03d}.png", dpi=105, bbox_inches="tight")
        plt.close(fig)

orders = selected.annotation_order.tolist()
for page in range(0, len(orders), 6):
    fig, axes = plt.subplots(3, 2, figsize=(15, 14))
    for ax, order in zip(axes.flat, orders[page:page+6]):
        c = contexts[order]
        _draw_pitch(ax, c["config"])
        for pos, color in [(c["losing_positions"], "#cc3344"), (c["opponent_positions"], "#2266cc")]:
            for j in range(pos.shape[1]):
                ax.plot(pos[:, j, 0], pos[:, j, 1], c=color, lw=1, alpha=.75)
                ax.scatter(*pos[0, j], facecolors="none", edgecolors=color, s=28)
                ax.scatter(*pos[-1, j], c=color, s=23)
        bp = c["ball_positions"]
        ax.plot(bp[:, 0], bp[:, 1], c="black", lw=1.7)
        for t in [0, 1, 2]:
            i = np.argmin(np.abs(c["relative_times"] - t))
            ax.scatter(*bp[i], c="black", marker="*", s=60)
            ax.annotate(f"b{t}", bp[i], xytext=(4, 5), textcoords="offset points", fontsize=8)
        ax.set_title(f"#{order} | {c['candidate']['candidate_id']}", fontsize=11)
    for ax in list(axes.flat)[len(orders[page:page+6]):]:
        ax.axis("off")
    fig.suptitle("Lintasan 0–2 detik | Merah: tim kehilangan bola; biru: lawan\nLingkaran kosong: awal; titik penuh: akhir. Label awal dan outcome disembunyikan.", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(OUT / "panels" / f"sheet_{page//6+1:02d}.png", dpi=115)
    plt.close(fig)

assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
(OUT / "provenance.json").write_text(json.dumps({
    "source": str(SOURCE), "sha256": source_hash,
    "records_screened": len(df), "priority_records": len(selected),
    "source_labels_modified": False,
    "method": "Fresh pressure cues from tracking; triage only, not automatic ground truth. No model or quick-regain outcome used for screening.",
}, indent=2), encoding="utf-8")
print("DONE", len(df), "screened;", len(selected), "priority", flush=True)
