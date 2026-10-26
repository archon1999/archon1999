"""Build GitHub contribution calendars and Codeforces charts from public APIs.

Only public original repositories are enumerated. Contribution calendars can
include restricted/private contribution COUNTS exposed by GitHub; no private
repository names, files, messages, or URLs are collected.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOGIN = "archon1999"
QUERY = """query($login:String!, $cursor:String) {
 user(login:$login) {
  login name url createdAt followers {totalCount}
  repositories(first:100,after:$cursor,privacy:PUBLIC,ownerAffiliations:[OWNER],isFork:false) {
   totalCount pageInfo {hasNextPage endCursor}
   nodes {name url isArchived stargazerCount forkCount
    languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}
  }
  contributionsCollection {
   startedAt endedAt totalCommitContributions totalIssueContributions
   totalPullRequestContributions totalPullRequestReviewContributions
   restrictedContributionsCount
   contributionCalendar {totalContributions weeks {contributionDays {date contributionCount contributionLevel weekday}}}
  }
 }
}"""
PALETTES = {
 "dark": dict(bg="#0d1117", line="#30363d", text="#e6edf3", muted="#8b949e", accent="#3fb950", purple="#a371f7", levels=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]),
 "light": dict(bg="#ffffff", line="#d1d9e0", text="#1f2328", muted="#59636e", accent="#1a7f37", purple="#8250df", levels=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
}
LEVELS = {name: i for i, name in enumerate(["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"])}

def request_json(url, payload=None, token=None):
    headers={"Accept":"application/vnd.github+json", "User-Agent":"archon1999-profile-charts"}
    if token: headers["Authorization"]="Bearer "+token
    data=json.dumps(payload).encode() if payload else None
    if data: headers["Content-Type"]="application/json"
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers),timeout=35) as response:
        return json.load(response)

def fetch_github():
    token=os.environ.get("GITHUB_TOKEN")
    if not token: raise RuntimeError("GITHUB_TOKEN is required for a refresh")
    first=None; repositories=[]; cursor=None
    while True:
        response=request_json("https://api.github.com/graphql",{"query":QUERY,"variables":{"login":LOGIN,"cursor":cursor}},token)
        if response.get("errors"): raise RuntimeError("GitHub GraphQL request failed: "+str(response["errors"]))
        user=response["data"]["user"]
        if not user or user["login"].lower()!=LOGIN: raise ValueError("Unexpected GitHub user")
        if first is None: first=user
        repositories.extend(user["repositories"]["nodes"])
        page=user["repositories"]["pageInfo"]
        if not page["hasNextPage"]: break
        cursor=page["endCursor"]
    first["repositories"]["nodes"]=repositories
    return first

def metric_data(user, ratings, ratings_updated):
    repos=user["repositories"]["nodes"]
    collection=user["contributionsCollection"]
    days=[day for week in collection["contributionCalendar"]["weeks"] for day in week["contributionDays"]]
    languages=defaultdict(int)
    for repo in repos:
        if repo["isArchived"]: continue
        for edge in repo["languages"]["edges"]: languages[edge["node"]["name"]]+=edge["size"]
    return {
        "login":LOGIN,"updatedUtc":datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "repositoryScope":"Public original owned repositories; language bytes exclude archived repositories",
        "contributionScope":"GitHub contribution counts may include restricted/private activity counts; no private repository details",
        "repositories":user["repositories"]["totalCount"],"followers":user["followers"]["totalCount"],
        "stars":sum(r["stargazerCount"] for r in repos),
        "contributions":collection["contributionCalendar"]["totalContributions"],
        "commits":collection["totalCommitContributions"],"pullRequests":collection["totalPullRequestContributions"],
        "activeDays":sum(d["contributionCount"]>0 for d in days),
        "days":days,"languages":dict(sorted(languages.items(),key=lambda x:-x[1])),
        "ratings":ratings,"ratingsUpdatedUtc":ratings_updated,
    }

def text(x,y,value,size=12,color=None,anchor=None,weight=None):
    attrs=f'x="{x}" y="{y}" font-size="{size}"'
    if color: attrs+=f' fill="{color}"'
    if anchor: attrs+=f' text-anchor="{anchor}"'
    if weight: attrs+=f' font-weight="{weight}"'
    return f'<text {attrs}>{escape(str(value))}</text>'

def svg(width,height,title,description,body,p):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{p['purple']}" stop-opacity=".16"/><stop offset="1" stop-color="{p['purple']}" stop-opacity="0"/></linearGradient></defs>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="6" fill="{p['bg']}" stroke="{p['line']}"/>
<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" fill="{p['text']}">{body}</g></svg>'''

def activity_chart(d,p):
    days=d["days"]
    first=datetime.fromisoformat(days[0]["date"]).date()
    start=first-timedelta(days=int(days[0]["weekday"]))
    body=text(30,36,f'{d["contributions"]:,} contributions in the last year',18,weight=600)
    body+=text(970,36,f'{d["activeDays"]} active days',12,p["muted"],"end")
    x0,y0,step,size=61,78,17,13
    months=set()
    for day in days:
        date=datetime.fromisoformat(day["date"]).date()
        week=(date-start).days//7
        x=x0+week*step; y=y0+int(day["weekday"])*step
        month=(date.year,date.month)
        if month not in months:
            # A partial first month needs room before the next month label.
            if week>1 or date.day<24:
                body+=text(x,65,date.strftime("%b"),10,p["muted"])
            months.add(month)
        level=LEVELS[day["contributionLevel"]]
        count=day["contributionCount"]
        label=f'{count} contributions on {day["date"]}'
        body+=f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{p["levels"][level]}" stroke="{p["line"]}" stroke-opacity=".2"><title>{escape(label)}</title></rect>'
    for weekday,label in [(1,"Mon"),(3,"Wed"),(5,"Fri")]:
        body+=text(27,y0+weekday*step+10,label,10,p["muted"])
    body+=text(30,224,"Contribution levels reported by GitHub",10,p["muted"])
    body+=text(797,224,"Less",10,p["muted"])
    for i,color in enumerate(p["levels"]):
        body+=f'<rect x="{827+i*18}" y="213" width="13" height="13" rx="2" fill="{color}"/>'
    body+=text(928,224,"More",10,p["muted"])
    body+=text(30,253,f'GitHub API · {days[0]["date"]} – {days[-1]["date"]} · includes restricted activity counts',10,p["muted"])
    return svg(1000,275,"GitHub contribution calendar",f'{d["contributions"]} contributions and {d["activeDays"]} active days. Daily cells use GitHub contribution levels. Updated {d["updatedUtc"]}.',body,p)

def codeforces_chart(d,p):
    ratings=d["ratings"]
    if not ratings: return None
    first=ratings[0]["ratingUpdateTimeSeconds"];last=ratings[-1]["ratingUpdateTimeSeconds"]
    floor=min(900,math.floor(min(r["newRating"] for r in ratings)/100)*100-100)
    ceiling=max(2400,math.ceil(max(r["newRating"] for r in ratings)/100)*100+100)
    points=[(42+(r["ratingUpdateTimeSeconds"]-first)/max(1,last-first)*916,223-(r["newRating"]-floor)/(ceiling-floor)*139) for r in ratings]
    path="M"+" L".join(f"{x:.2f} {y:.2f}" for x,y in points)
    peak=max(r["newRating"] for r in ratings);current=ratings[-1]["newRating"]
    body=text(30,35,"Odminbey / Codeforces",18,weight=500)+text(30,58,"Rated contest history",11,p["muted"])
    body+=text(965,36,f'Master · peak {peak}',13,p["purple"],"end")
    for rating,label in [(1200,"Pupil"),(1400,"Specialist"),(1600,"Expert"),(1900,"Candidate Master"),(2100,"Master")]:
        y=223-(rating-floor)/(ceiling-floor)*139
        body+=f'<path d="M42 {y:.2f}h916" stroke="{p["line"]}" stroke-dasharray="3 6"/>'
        body+=text(48,y-5,str(rating)+" / "+label,7,p["muted"])
    body+=f'<path d="{path} L958 225 L42 225 Z" fill="url(#area)"/><path d="{path}" fill="none" stroke="{p["purple"]}" stroke-width="2.5" stroke-linejoin="round"/>'
    for x,y in points: body+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{p["bg"]}" stroke="{p["purple"]}" stroke-width="1.5"/>'
    body+=text(42,250,datetime.fromtimestamp(first,timezone.utc).strftime("%b %Y"),9,p["muted"])+text(958,250,datetime.fromtimestamp(last,timezone.utc).strftime("%b %Y"),9,p["muted"],"end")
    body+=text(30,282,f'{len(ratings)} rated contests · current {current} · source: Codeforces API · checked {d["ratingsUpdatedUtc"]}',9,p["muted"])
    return svg(1000,300,"Codeforces rating history",f'Odminbey: peak rating {peak}, current {current}, {len(ratings)} rated contests. Official Codeforces rating data.',body,p)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--source",type=Path);parser.add_argument("--codeforces-source",type=Path);args=parser.parse_args()
    user=json.loads(args.source.read_text(encoding="utf-8-sig"))["data"]["user"] if args.source else fetch_github()
    target=ROOT/"data"/"metrics.json";old=json.loads(target.read_text()) if target.exists() else {}
    ratings=old.get("ratings",[])
    ratings_updated=old.get("ratingsUpdatedUtc",old.get("updatedUtc",""))
    try:
        response=json.loads(args.codeforces_source.read_text()) if args.codeforces_source else request_json("https://codeforces.com/api/user.rating?handle=Odminbey")
        if response.get("status")!="OK" or not response.get("result"): raise ValueError("Invalid Codeforces response")
        ratings=[{k:r[k] for k in ["contestId","ratingUpdateTimeSeconds","newRating"]} for r in response["result"]]
        ratings_updated=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        if not ratings: raise RuntimeError("No Codeforces data available")
        print("Codeforces API unavailable; retaining the last successful rating history.")
    d=metric_data(user,ratings,ratings_updated)
    if not d["days"] or d["repositories"]<1 or any(day.get("contributionLevel") not in LEVELS for day in d["days"]): raise ValueError("Incomplete metrics; refusing to replace existing charts")
    for theme,palette in PALETTES.items():
        for name,render in [("activity",activity_chart),("codeforces",codeforces_chart)]:
            result=render(d,palette)
            if result: (ROOT/"assets"/f"{name}-{theme}.svg").write_text(result,encoding="utf-8")
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f'Updated profile charts: {d["repositories"]} public original repositories, {d["contributions"]} contribution counts, {len(ratings)} rated Codeforces contests.')

if __name__=="__main__": main()
