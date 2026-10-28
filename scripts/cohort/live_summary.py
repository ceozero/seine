"""One summary line for a pool_fixture.py run: user H/s over the whole window and the last 300 s."""
import json
import sys

d = json.load(open(sys.argv[1]))
m, secs = sys.argv[2], float(sys.argv[3])
user = [s["elapsed"] for s in d["shares"] if s["eligible"] and s["user_work"] and s["elapsed"] < secs]
fee = sum(1 for s in d["shares"] if s["eligible"] and not s["user_work"] and s["elapsed"] < secs)
last = sum(1 for t in user if t >= secs - 300) / 300
print(f"{m} lifetime_user={len(user)/secs:.3f} last300_user={last:.3f} fee_shares={fee} "
      f"first_share={d['launch_to_first_share_seconds']} end={d['termination_reason']}")
