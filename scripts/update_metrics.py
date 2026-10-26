"""Build self-hosted profile charts from GitHub and Codeforces public APIs.

Only public original repositories are enumerated. Contribution calendars can
include restricted/private contribution COUNTS exposed by GitHub; no private
repository names, files, messages, or URLs are collected.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
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
   contributionCalendar {totalContributions weeks {contributionDays {date contributionCount weekday}}}
  }
 }
}"""
PALETTES = {
 "dark": dict(bg="#0B1019", surface="#101925", line="#263A48", text="#E9F0ED", muted="#829DAD", accent="#ACDCD8", cream="#E2D19E", faint="#152631"),
 "light": dict(bg="#F8FAF5", surface="#EEF3ED", line="#CFDDD7", text="#24404A", muted="#6B8792", accent="#387E86", cream="#AE914E", faint="#E4EEE8"),
}

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
<defs><linearGradient id="accent"><stop stop-color="{p['cream']}"/><stop offset="1" stop-color="{p['accent']}"/></linearGradient><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{p['accent']}" stop-opacity=".25"/><stop offset="1" stop-color="{p['accent']}" stop-opacity="0"/></linearGradient></defs>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="10" fill="{p['bg']}" stroke="{p['line']}"/>
<path d="M25 1h{width-50}" stroke="url(#accent)" opacity=".6"/>
<g font-family="Arial,Helvetica,sans-serif" fill="{p['text']}">{body}</g></svg>'''

def overview(d,p):
    body=text(26,34,"GitHub / by the numbers",17,weight=500)+text(26,56,"A rolling year of building.",10,p["muted"])
    labels=[("CONTRIBUTIONS",d["contributions"]),("PUBLIC REPOSITORIES",d["repositories"]),("REPOSITORY STARS",d["stars"]),("FOLLOWERS",d["followers"])]
    for i,(label,value) in enumerate(labels):
        x=26+(i%2)*239;y=92+(i//2)*78
        body+=text(x,y,label,8,p["muted"])+text(x,y+35,f"{value:,}",32,p["accent"])
    body+=f'<path d="M26 231h448" stroke="{p["line"]}"/>'
    body+=text(26,251,f'{d["activeDays"]} active days  /  API snapshot {d["updatedUtc"]}',9,p["muted"])
    return svg(500,270,"GitHub statistics",f'{d["contributions"]} contributions, {d["repositories"]} public original repositories, {d["stars"]} repository stars and {d["followers"]} followers. Contribution counts can include private activity.',body,p)

def language_chart(d,p):
    pairs=list(d["languages"].items());top=pairs[:5];remaining=sum(v for _,v in pairs[5:])
    if remaining: top.append(("Other",remaining))
    total=sum(v for _,v in top)
    if total<=0: raise ValueError("No language bytes available")
    colors=[p["accent"],p["cream"],"#6F9FAE","#557A98","#8C9CA8",p["line"]]
    body=text(26,34,"Languages / public source",17,weight=500)+text(26,56,"Repository bytes, not skill percentages.",10,p["muted"])
    radius=61;circ=2*math.pi*radius;offset=0
    body+=f'<circle cx="112" cy="151" r="{radius}" fill="none" stroke="{p["faint"]}" stroke-width="18"/>'
    for i,(name,value) in enumerate(top):
        length=value/total*circ
        body+=f'<circle cx="112" cy="151" r="{radius}" fill="none" stroke="{colors[i]}" stroke-width="18" stroke-dasharray="{max(0,length-2):.2f} {circ:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 112 151)"/>'
        offset+=length
        y=98+i*25
        body+=f'<rect x="225" y="{y-7}" width="6" height="6" rx="1" fill="{colors[i]}"/>'
        body+=text(241,y,name,11,p["text"])+text(472,y,f'{value/total:.1%}',10,p["muted"],"end")
    body+=text(112,148,"LANGUAGES",8,p["muted"],"middle")+text(112,169,str(len(pairs)),22,p["text"],"middle")
    body+=text(26,251,"Original public repos · archived repos excluded",9,p["muted"])
    return svg(500,270,"Programming languages",", ".join(f'{n}: {v/total:.1%}' for n,v in top)+". GitHub language bytes from public original non-archived repositories.",body,p)

def activity_chart(d,p):
    weeks=defaultdict(int)
    for day in d["days"]:
        date=datetime.fromisoformat(day["date"]).date();year,week,_=date.isocalendar()
        weeks[(year,week)]+=day["contributionCount"]
    values=list(weeks.values());maximum=max(max(values),1)
    x0,y0,w,h=42,90,916,136
    points=[(x0+i*w/max(1,len(values)-1),y0+h-v/maximum*h) for i,v in enumerate(values)]
    path="M"+" L".join(f"{x:.2f} {y:.2f}" for x,y in points)
    body=text(30,35,"Contribution activity",18,weight=500)+text(30,58,"Weekly contributions · last 12 months",11,p["muted"])
    body+=text(965,37,f'{d["contributions"]:,} contributions',13,p["accent"],"end")
    for i in range(4):
        y=y0+i*h/3;body+=f'<path d="M{x0} {y:.2f}h{w}" stroke="{p["line"]}" stroke-dasharray="3 6" opacity=".65"/>'
    body+=f'<path d="{path} L{x0+w} {y0+h} L{x0} {y0+h} Z" fill="url(#area)"/>'
    body+=f'<path d="{path}" fill="none" stroke="url(#accent)" stroke-width="2.5" stroke-linejoin="round"/>'
    for i in [0,len(points)-1]:
        x,y=points[i];body+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{p["accent"]}"/>'
    body+=text(42,249,d["days"][0]["date"],9,p["muted"])+text(958,249,d["days"][-1]["date"],9,p["muted"],"end")
    body+=text(30,282,"GitHub counts can include private activity. No private repository details are collected.",9,p["muted"])
    return svg(1000,300,"Contribution activity by week","Rolling year of weekly contribution counts reported by GitHub. Counts can include private activity. Updated "+d["updatedUtc"],body,p)

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
    body+=text(965,36,f'Master · peak {peak}',13,p["accent"],"end")
    for rating,label in [(1200,"Pupil"),(1400,"Specialist"),(1600,"Expert"),(1900,"Candidate Master"),(2100,"Master")]:
        y=223-(rating-floor)/(ceiling-floor)*139
        body+=f'<path d="M42 {y:.2f}h916" stroke="{p["line"]}" stroke-dasharray="3 6"/>'
        body+=text(48,y-5,str(rating)+" / "+label,7,p["muted"])
    body+=f'<path d="{path} L958 225 L42 225 Z" fill="url(#area)"/><path d="{path}" fill="none" stroke="url(#accent)" stroke-width="2.5" stroke-linejoin="round"/>'
    for x,y in points: body+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{p["bg"]}" stroke="{p["accent"]}" stroke-width="1.5"/>'
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
    if not d["days"] or d["repositories"]<1: raise ValueError("Incomplete metrics; refusing to replace existing charts")
    for theme,palette in PALETTES.items():
        for name,render in [("github-stats",overview),("languages",language_chart),("activity",activity_chart),("codeforces",codeforces_chart)]:
            result=render(d,palette)
            if result: (ROOT/"assets"/f"{name}-{theme}.svg").write_text(result,encoding="utf-8")
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f'Updated profile charts: {d["repositories"]} public original repositories, {d["contributions"]} contribution counts, {len(ratings)} rated Codeforces contests.')

if __name__=="__main__": main()
