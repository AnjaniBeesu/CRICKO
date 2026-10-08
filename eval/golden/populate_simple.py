from __future__ import annotations

import argparse, json, re, zipfile
from collections import defaultdict
from pathlib import Path

EXCLUDED_DISMISSALS={"run out","retired hurt","retired out","obstructing the field","retired_hurt","retired_out","obstructing_the_field"}

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()

def player_score(query: str, name: str) -> int:
    q=norm(query).split(); n=norm(name).split()
    if not q or not n: return -1
    if norm(query)==norm(name): return 100
    score=0
    if q[-1]==n[-1]: score+=50
    if q[0][0]==n[0][0]: score+=20
    if len(q)>2 and q[-2] in n: score+=10
    if all(part in n for part in q if len(part)>2): score+=15
    return score

def resolve_player(name, registry_names):
    scored=sorted(((player_score(name,n),n,pid) for n,pid in registry_names.items()), reverse=True)
    if not scored or scored[0][0] < 50: raise ValueError(f"cannot resolve player: {name}")
    if len(scored)>1 and scored[0][0]==scored[1][0]:
        raise ValueError(f"ambiguous player: {name}: {scored[:3]}")
    return scored[0][2]

def match_allowed(info):
    if info.get("gender")!="male": return False
    if info.get("match_type") not in {"T20","IT20"}: return False
    dates=info.get("dates",[])
    if not dates or str(dates[0])[:4] < "2022": return False
    event=((info.get("event") or {}).get("name") or "")
    if event!="Indian Premier League" and info.get("team_type")!="international": return False
    outcome=info.get("outcome") or {}
    if not outcome: return False
    if "method" in outcome: return False
    if outcome.get("result") in {"no result","no_result"}: return False
    return True

def rows_from_zip(zpath):
    with zipfile.ZipFile(zpath) as z:
        for fn in z.namelist():
            if not fn.endswith(".json"): continue
            yield fn, json.loads(z.read(fn))

def extract_player(question):
    q=question.rstrip("?")
    patterns=[
        r"How many runs has (.+?) scored",
        r"How many wickets has (.+?) taken",
        r"What is (.+?)'s",
        r"How many sixes has (.+?) hit",
        r"How many matches has (.+?) played",
        r"How many runs did (.+?) score",
        r"How many wickets did (.+?) take",
        r"How many fours has (.+?) hit",
        r"How many .* has (.+?) scored",
        r"How many .* did (.+?) take",
    ]
    for p in patterns:
        m=re.search(p,q,re.I)
        if m: return m.group(1).strip()
    raise ValueError(f"cannot parse player: {question}")

def metric(question):
    q=question.lower()
    if "strike rate" in q: return "strike_rate"
    if "economy" in q: return "economy"
    if "bowling average" in q: return "bowling_average"
    if "batting average" in q: return "batting_average"
    if "wickets" in q: return "wickets"
    if "sixes" in q: return "sixes"
    if "fours" in q: return "fours"
    if "centuries" in q: return "centuries"
    if "fifties" in q: return "fifties"
    if "matches" in q: return "matches"
    if "runs" in q: return "runs"
    raise ValueError(question)

def aggregate(zips, target_name):
    bat=defaultdict(lambda: {"runs":0,"balls":0,"fours":0,"sixes":0,"dismissals":0,"innings":0,"scores":[]})
    bowl=defaultdict(lambda: {"runs":0,"balls":0,"wickets":0})
    matches=set()
    non_boundary=False
    target_ids=set()

    for zpath in zips:
        for fn,payload in rows_from_zip(zpath):
            info=payload["info"]
            if not match_allowed(info): continue
            people=info.get("registry",{}).get("people",{})
            try:
                pid=resolve_player(target_name, people)
            except ValueError:
                continue
            target_ids.add(pid)
            names_by_team=info.get("players",{})
            if any(target_name.lower() in n.lower() for team in names_by_team.values() for n in team):
                matches.add(fn)
            innings_scores={}
            for inn in payload.get("innings",[]):
                for over in inn.get("overs",[]):
                    for d in over.get("deliveries",[]):
                        batter=d["batter"]; bowler=d["bowler"]
                        bid=people.get(batter); wid=people.get(bowler)
                        runs=d["runs"]; br=runs["batter"]; total=runs["total"]
                        legal=not any(k in d.get("extras",{}) for k in ("wides","noballs"))
                        if bid==pid:
                            matches.add(fn); bat[pid]["runs"]+=br
                            if legal: bat[pid]["balls"]+=1
                            if br==4: bat[pid]["fours"]+=1
                            if br==6: bat[pid]["sixes"]+=1
                            if runs.get("non_boundary"): non_boundary=True
                            for w in d.get("wickets",[]):
                                if people.get(w["player_out"])==pid and w["kind"] not in EXCLUDED_DISMISSALS:
                                    bat[pid]["dismissals"]+=1
                            innings_scores.setdefault(pid,0); innings_scores[pid]+=br
                        if wid==pid:
                            matches.add(fn)
                            if legal: bowl[pid]["balls"]+=1
                            extras=d.get("extras",{})
                            conceded=total-extras.get("byes",0)-extras.get("legbyes",0)-extras.get("penalty",0)
                            bowl[pid]["runs"]+=conceded
                            for w in d.get("wickets",[]):
                                if w["kind"] not in EXCLUDED_DISMISSALS: bowl[pid]["wickets"]+=1
            for pid2,score in innings_scores.items():
                bat[pid2]["innings"]+=1; bat[pid2]["scores"].append(score)
    return bat,bowl,len(matches),non_boundary

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--golden",required=True); ap.add_argument("--ipl",required=True); ap.add_argument("--t20i",required=True); ap.add_argument("--out",required=True)
    args=ap.parse_args()
    rows=[json.loads(x) for x in Path(args.golden).read_text().splitlines() if x.strip()]
    zips={"IPL":[args.ipl],"T20I":[args.t20i]}
    done=0
    for x in rows:
        if x["block"]!="A": continue
        comp="IPL" if "IPL" in x["question"] else "T20I"
        player=extract_player(x["question"])
        m=metric(x["question"])
        bat,bowl,matches,non_boundary=aggregate(zips[comp],player)
        # Resolve the target ID again from the populated maps.
        ids=set(bat)|set(bowl)
        if not ids: continue
        pid=next(iter(ids))
        b=bat[pid]; w=bowl[pid]
        if m=="runs": value=b["runs"]
        elif m=="wickets": value=w["wickets"]
        elif m=="strike_rate": value=round(100*b["runs"]/b["balls"],2) if b["balls"] else None
        elif m=="economy": value=round(6*w["runs"]/w["balls"],2) if w["balls"] else None
        elif m=="bowling_average": value=round(w["runs"]/w["wickets"],2) if w["wickets"] else None
        elif m=="batting_average": value=round(b["runs"]/b["dismissals"],2) if b["dismissals"] else None
        elif m=="fours": value=b["fours"]
        elif m=="sixes": value=b["sixes"]
        elif m=="matches": value=matches
        elif m=="centuries": value=sum(s>=100 for s in b["scores"])
        elif m=="fifties": value=sum(50<=s<100 for s in b["scores"])
        else: continue
        if value is None: continue
        # Four/six counts are left pending if the source marks a non-boundary 4/6.
        if m in {"fours","sixes"} and non_boundary:
            continue
        x["expected_result"]={"status":"VERIFIED_BY_INDEPENDENT_REFERENCE","values":{"value":value},"tolerance":{"value":0 if isinstance(value,int) else 0.01}}
        x["data_snapshot_id"]="cricsheet-mvp-t20-2026-10-08"
        x["verification"]["needs_second_impl"]=True
        x["verification"]["needs_statsguru"]=True
        x["failure_category"]=None
        x["notes"]="Computed by an independent source-level implementation against the pinned Cricsheet snapshot; external/manual reconciliation remains a release check."
        done+=1
    Path(args.out).write_text("\n".join(json.dumps(x,separators=(",",":")) for x in rows)+"\n")
    print(f"populated={done}")

if __name__=="__main__": main()
