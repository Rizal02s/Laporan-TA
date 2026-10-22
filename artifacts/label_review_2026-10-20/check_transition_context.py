from pathlib import Path
import pickle
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
a = pd.read_csv(ROOT / "data/processed/gegenpressing_annotation_manifest.csv")
contexts = pickle.load((OUT / "contexts.pkl").open("rb"))
records = []
for match, rows in a.groupby("match_id"):
    t = pd.read_csv(ROOT / f"data/sportec_idsse/{match}_tracking.csv",
                    usecols=["period_id", "frame_id", "ball_state", "ball_owning_team_id"])
    t = t.sort_values(["period_id", "frame_id"]).reset_index(drop=True)
    for _, r in rows.iterrows():
        idx = t.index[(t.period_id == r.period_id) & (t.frame_id == r.loss_frame)][0]
        prev = t.iloc[max(0, idx-50):idx]
        prev = prev[prev.period_id == r.period_id]
        c = contexts[int(r.annotation_order)]
        dead = c["window"].ball_state.ne("alive").to_numpy()
        records.append({
            "annotation_order": int(r.annotation_order),
            "dead_frames_before_2s": int(prev.ball_state.ne("alive").sum()),
            "previous_frame_state": prev.iloc[-1].ball_state if len(prev) else "",
            "first_dead_after_s": float(c["relative_times"][np.flatnonzero(dead)[0]]) if dead.any() else np.nan,
        })
    print("Context", match, flush=True)
pd.DataFrame(records).to_csv(OUT / "transition_context.csv", index=False, encoding="utf-8-sig")
