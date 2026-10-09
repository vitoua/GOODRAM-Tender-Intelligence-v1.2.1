from datetime import datetime
import httpx
from app.core import Tender
from app.filters import codes,keywords,relevant
from app.fx import eur
URL='https://api.ted.europa.eu/v3/notices/search';FIELDS=['publication-number','notice-title','buyer-name','buyer-country','publication-date','deadline','description-proc','classification-cpv','total-value','total-value-cur']
def first(v):
 if isinstance(v,dict):return first(v.get('eng') or v.get('pol') or next(iter(v.values()),''))
 if isinstance(v,list):return first(v[0]) if v else ''
 return str(v or '')
def dt(v):
 try:return datetime.fromisoformat(first(v)[:10])
 except:return None
async def fetch(countries,published_from,min_eur):
 cut=published_from.strftime('%Y%m%d');q='('+' OR '.join(f'classification-cpv={x}' for x in codes('ted'))+') AND publication-date>='+cut;p={'query':q,'fields':FIELDS,'page':1,'limit':250,'scope':'ACTIVE','paginationMode':'PAGE_NUMBER','onlyLatestVersions':True}
 async with httpx.AsyncClient(timeout=60) as c:r=await c.post(URL,json=p);r.raise_for_status();raw=r.json().get('notices',[])
 out=[]
 for x in raw:
  co=first(x.get('buyer-country'))[:3].upper();ddl=dt(x.get('deadline'));pub=dt(x.get('publication-date'));cpv=[first(z) for z in x.get('classification-cpv',[])];title=first(x.get('notice-title'));desc=first(x.get('description-proc'))
  if co not in countries or not ddl or ddl<datetime.now() or not pub or pub<published_from or not relevant('ted',cpv,title+' '+desc):continue
  try:val=float(first(x.get('total-value')))
  except:val=None
  cur=first(x.get('total-value-cur')) or 'EUR';ve=await eur(val,cur)
  if min_eur>0 and (ve is None or ve<min_eur):continue
  n=first(x.get('publication-number'));out.append(Tender('ted:'+n,'ted',co,title,first(x.get('buyer-name')),val,cur,ddl,pub,url=f'https://ted.europa.eu/en/notice/-/detail/{n}',description=desc,procurement_id=n,cpv=cpv,value_eur=ve))
 return out,{'scanned':len(raw),'final':len(out)}
