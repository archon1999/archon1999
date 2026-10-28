"""Refresh public KEP counters; retain the last verified snapshot on API failure."""
import json
from pathlib import Path
import re
import sys
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

URL='https://kep.uz/api/landing-page-statistics'
ROOT=Path(__file__).resolve().parents[1]
KEYS=('users','problems','competitions','attempts')

def validate(payload):
    values={}
    for key in KEYS:
        value=payload[key]['value']
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=10**12:
            raise ValueError(f'Invalid public counter: {key}')
        values[key]=value
    if values['users']==0 or values['problems']==0:raise ValueError('Empty platform snapshot')
    return values

def fetch():
    request=Request(URL,headers={'User-Agent':'archon1999-public-profile/1.0','Accept':'application/json'})
    with urlopen(request,timeout=20) as response:return json.load(response)

def refresh(root=ROOT,fetcher=fetch,now=None):
    now=now or datetime.now(timezone.utc)
    try:
        values=validate(fetcher());day=now.astimezone(ZoneInfo('Asia/Tashkent')).date().isoformat()
        sources={}
        for theme in ('dark','light'):
            path=root/'assets'/f'kep-overview-{theme}.svg'
            source=path.read_text(encoding='utf-8')
            for key,value in {**{f'metric-{key}':f'{value:,}' for key,value in values.items()},'snapshot-date':day}.items():
                source,count=re.subn(r'(<text\b[^>]*\bid="'+re.escape(key)+r'"[^>]*>)[^<]*(</text>)',lambda match:match[1]+value+match[2],source)
                if count!=1:raise ValueError(f'Missing or duplicate metric slot: {key}')
            ET.fromstring(source);sources[path]=source
        data={'source':URL,'observedUtc':now.astimezone(timezone.utc).isoformat(),'displayDate':day,'timezone':'Asia/Tashkent','metrics':values,'scope':{'users':'registered users','problems':'visible problems','competitions':'contests','attempts':'submitted solutions'}}
        sources[root/'data/products.json']=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    except Exception as error:
        print(f'::warning::KEP snapshot retained: {type(error).__name__}: {error}')
        return False
    for path,source in sources.items():
        path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(source,encoding='utf-8');temporary.replace(path)
    print(f'Updated KEP public counters for {day}.')
    return True

if __name__=='__main__':refresh()
