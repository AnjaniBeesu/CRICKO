from __future__ import annotations

import argparse, json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.reference.stats_reference import Ball

PLAYER_IDS = {
    "A001": "Virat Kohli",
    "A002": "Jasprit Bumrah",
    "A003": "Rohit Sharma",
    "A004": "AB de Villiers",
    "A005": "MS Dhoni",
    "A006": "Jasprit Bumrah",
    "A007": "Suryakumar Yadav",
    "A008": "Rashid Khan",
    "A009": "Hardik Pandya",
    "A010": "Shubman Gill",
    "A011": "Virat Kohli",
    "A012": "Arshdeep Singh",
    "A013": "Babar Azam",
    "A014": "Rohit Sharma",
    "A015": "Kuldeep Yadav",
    "A017": "Yuzvendra Chahal",
    "A018": "Jasprit Bumrah",
    "A019": "Virat Kohli",
    "A020": "Shikhar Dhawan",
}

def load_aliases(path: str) -> dict[str, str]:
    return json.loads(Path(path).read_text())

def metric_for(question: str) -> str:
    q=question.lower()
    for needle,metric in [
        ("strike rate","strike_rate"),("economy","economy"),("bowling average","bowling_average"),
        ("batting average","batting_average"),("wickets","wickets"),("sixes","sixes"),
        ("fours","fours"),("centuries","centuries"),("fifties","fifties"),("matches","matches"),("runs","runs")
    ]:
        if needle in q: return metric
    raise ValueError(question)

def calculate(rows: list[dict], pid: str, metric: str, season: str|None):
    balls=[]
    match_ids=set()
    innings_seen=set()
    for r in rows:
        if season and str(r["date"])[:4] != season: continue
        if r["batter_id"] != pid and r["bowler_id"] != pid: continue
        b=Ball(
            match_id=r["match_id"], innings=r["innings"], over=r["over"],
            legal_delivery=r["legal_delivery"], batter_id=r["batter_id"],
            bowler_id=r["bowler_id"], batter_runs=r["batter_runs"],
            total_runs=r["total_runs"], bowler_runs=r["total_runs"] - r["bye_runs"] - r["legbye_runs"] - r["penalty_runs"],
            batter_faced=r["batter_faced"], batter_dismissed=r["batter_dismissed"],
            bowler_credited_wicket=r["bowler_credited_wicket"],
            dismissal_kind=r["dismissal_kind"])
        balls.append(b); match_ids.add(r["match_id"])
        if r["batter_id"]==pid: innings_seen.add((r["match_id"],r["innings"]))
    runs=sum(b.batter_runs for b in balls if b.batter_id==pid)
    batballs=sum(1 for b in balls if b.batter_id==pid and b.batter_faced and b.legal_delivery)
    fours=sum(1 for b in balls if b.batter_id==pid and b.batter_runs==4)
    sixes=sum(1 for b in balls if b.batter_id==pid and b.batter_runs==6)
    dismissals=sum(1 for b in balls if b.batter_id==pid and b.batter_dismissed)
    bowlballs=sum(1 for b in balls if b.bowler_id==pid and b.legal_delivery)
    bowlruns=sum(b.bowler_runs for b in balls if b.bowler_id==pid)
    wickets=sum(1 for b in balls if b.bowler_id==pid and b.bowler_credited_wicket)
    if metric=="runs": return runs
    if metric=="matches": return len(match_ids)
    if metric=="fours": return fours
    if metric=="sixes": return sixes
    if metric=="wickets": return wickets
    if metric=="strike_rate": return round(100*runs/batballs,2) if batballs else None
    if metric=="economy": return round(6*bowlruns/bowlballs,2) if bowlballs else None
    if metric=="bowling_average": return round(bowlruns/wickets,2) if wickets else None
    if metric=="batting_average": return round(runs/dismissals,2) if dismissals else None
    raise ValueError(metric)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--golden",required=True)
    ap.add_argument("--normalized",action="append",required=True)
    ap.add_argument("--player-map",required=True)
    args=ap.parse_args()
    aliases=load_aliases(args.player_map)
    rows=[]
    for p in args.normalized:
        rows.extend(json.loads(x) for x in Path(p).read_text().splitlines() if x.strip())
    by_comp=defaultdict(list)
    for r in rows: by_comp[r["competition"]].append(r)
    golden=[json.loads(x) for x in Path(args.golden).read_text().splitlines() if x.strip()]
    checked=0
    for case in golden:
        if case["block"]!="A" or case["expected_result"]["status"]!="VERIFIED_BY_INDEPENDENT_REFERENCE":
            continue
        expected=case["expected_result"]["values"]["value"]
        pid=aliases.get(case["id"])
        if not pid:
            raise SystemExit(f"no normalized player id for {case['id']}")
        season=None
        q=case["question"]
        import re
        m=re.search(r"\b(?:IPL|T20I)\s+(20\d{2})\b",q,re.I)
        if m: season=m.group(1)
        value=calculate(rows,pid,metric_for(q),season)
        if value != expected:
            raise SystemExit(f"MISMATCH {case['id']}: generator={expected} normalized-reference={value}")
        checked+=1
    print(f"checked={checked}; all deterministic golden values match normalized reference")

if __name__=="__main__": main()
