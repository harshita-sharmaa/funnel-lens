"""Build a synthetic product-usage database in SQLite.

Two tables: users and events. The product is a made-up team task app. Each
new user can verify their email, create a first project and invite a teammate,
then comes back (or not) in the weeks after signup. The data is simulated with
a fixed seed. Two patterns are built in for the analysis to find: Android users
get stuck before creating a project, and users who invite a teammate keep
coming back far more often.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 11
N_USERS = 8000
SIGNUP_START, SIGNUP_END = "2026-01-05", "2026-06-28"
DATA_END = "2026-07-26"  # last day of event data
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "product.db"

PLATFORMS = {
    # platform: share of signups, P(verify email), P(create project | verified), P(invite | created)
    "Web": (0.45, 0.86, 0.72, 0.36),
    "iOS": (0.30, 0.84, 0.70, 0.34),
    "Android": (0.25, 0.83, 0.44, 0.33),
}
# Chance of being active in week 1 after signup, and how fast that fades each week
RETENTION = {
    "invited": (0.78, 0.96),
    "created": (0.42, 0.90),
    "neither": (0.10, 0.75),
}
MAX_WEEKS = 12

SCHEMA = """
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL,
    platform    TEXT NOT NULL
);

CREATE TABLE events (
    event_id   INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    event_name TEXT NOT NULL,
    event_date TEXT NOT NULL
);

CREATE INDEX idx_events_user ON events(user_id, event_name);
"""


def main():
    rng = np.random.default_rng(SEED)
    names = list(PLATFORMS)
    shares = [PLATFORMS[p][0] for p in names]

    signup_days = pd.date_range(SIGNUP_START, SIGNUP_END, freq="D")
    users = pd.DataFrame(
        {
            "user_id": np.arange(1, N_USERS + 1),
            "signup_date": np.sort(rng.choice(signup_days, size=N_USERS)),
            "platform": rng.choice(names, size=N_USERS, p=shares),
        }
    )

    p_verify = users["platform"].map(lambda p: PLATFORMS[p][1]).to_numpy()
    p_create = users["platform"].map(lambda p: PLATFORMS[p][2]).to_numpy()
    p_invite = users["platform"].map(lambda p: PLATFORMS[p][3]).to_numpy()

    verified = rng.random(N_USERS) < p_verify
    created = verified & (rng.random(N_USERS) < p_create)
    invited = created & (rng.random(N_USERS) < p_invite)

    # Days after signup that each step happens. Most invites land in week one.
    verify_day = rng.integers(0, 2, N_USERS)
    create_day = verify_day + rng.integers(0, 4, N_USERS)
    invite_day = create_day + np.where(rng.random(N_USERS) < 0.8, rng.integers(0, 3, N_USERS),
                                       rng.integers(7, 21, N_USERS))

    signup = users["signup_date"]
    steps = [
        ("signed_up", np.ones(N_USERS, dtype=bool), np.zeros(N_USERS, dtype=int)),
        ("verified_email", verified, verify_day),
        ("created_project", created, create_day),
        ("invited_teammate", invited, invite_day),
    ]
    frames = []
    for name, mask, day in steps:
        frames.append(pd.DataFrame({
            "user_id": users.loc[mask, "user_id"],
            "event_name": name,
            "event_date": signup[mask] + pd.to_timedelta(day[mask], unit="D"),
        }))

    # Weekly return visits, driven by how far the user got in onboarding
    group = np.where(invited, "invited", np.where(created, "created", "neither"))
    start = np.array([RETENTION[g][0] for g in group])
    fade = np.array([RETENTION[g][1] for g in group])
    for week in range(1, MAX_WEEKS + 1):
        active = rng.random(N_USERS) < start * fade ** (week - 1)
        day = 7 * week + rng.integers(0, 7, N_USERS)
        frames.append(pd.DataFrame({
            "user_id": users.loc[active, "user_id"],
            "event_name": "session",
            "event_date": signup[active] + pd.to_timedelta(day[active], unit="D"),
        }))

    events = pd.concat(frames, ignore_index=True)
    events = events[events["event_date"] <= pd.Timestamp(DATA_END)]
    events = events.sort_values(["event_date", "user_id"]).reset_index(drop=True)
    events.insert(0, "event_id", np.arange(1, len(events) + 1))

    users["signup_date"] = users["signup_date"].dt.strftime("%Y-%m-%d")
    events["event_date"] = events["event_date"].dt.strftime("%Y-%m-%d")

    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    users.to_sql("users", con, if_exists="append", index=False)
    events.to_sql("events", con, if_exists="append", index=False)
    con.commit()
    con.close()
    print(f"Wrote {len(users):,} users and {len(events):,} events to {DB_PATH}")


if __name__ == "__main__":
    main()
