from datetime import datetime
import httpx
from app.core import Tender
from app.filters import relevant
from app.fx import eur
B='https://public-api.prozorro.gov.ua/api/2.5/tenders'
def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).replace(tzinfo=None)
 except:return None
async def fetch(countries,published_from,min_eur,limit=1500):
 out=[];offset=None;seen=0;stats={'scanned':0,'after_date':0,'active_deadline':0,'relevant':0,'final':0}
 async with httpx.AsyncClient(timeout=50,headers={'User-Agent':'GOODRAM-Tender-Intelligence/1.2.1'}) as c:
  while seen<limit:
   p={'limit':100,'descending':1};
   if offset:p['offset']=offset
   r=await c.get(B,params=p);r.raise_for_status();body=r.json();page=body.get('data',[])
   if not page:break
   for row in page:
    if seen>=limit:break
    seen+=1;stats['scanned']+=1
    d=await c.get(f"{B}/{row['id']}");d.raise_for_status();x=d.json().get('data',{});pub=dt(x.get('dateCreated') or x.get('dateModified'))
    if pub and pub<published_from:continue
    stats['after_date']+=1;ddl=dt((x.get('tenderPeriod') or {}).get('endDate'))
    if not ddl or ddl<datetime.now():continue
    stats['active_deadline']+=1;items=x.get('items',[]);cpv=[i.get('classification',{}).get('id','') for i in items];text=' '.join([x.get('title',''),x.get('description','')]+[i.get('description','') for i in items])
    if not relevant('prozorro',cpv,text):continue
    stats['relevant']+=1;val=(x.get('value') or {}).get('amount');cur=(x.get('value') or {}).get('currency','UAH');ve=await eur(val,cur)
    if min_eur>0 and (ve is None or ve<min_eur):continue
    n=x.get('tenderID',row['id']);out.append(Tender('prozorro:'+n,'prozorro','UKR',x.get('title') or n,(x.get('procuringEntity') or {}).get('name',''),val,cur,ddl,pub,url=f'https://prozorro.gov.ua/tender/{n}',description=x.get('description',''),procurement_id=n,cpv=cpv,value_eur=ve))
   offset=(body.get('next_page') or {}).get('offset')
   if not offset:break
 stats['final']=len(out);return out,stats
