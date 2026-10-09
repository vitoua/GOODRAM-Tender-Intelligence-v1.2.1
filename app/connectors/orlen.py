from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from app.core import Tender
from app.filters import keywords
async def fetch(countries,published_from,min_eur):
 url='https://connect.orlen.pl/servlet/HomeServlet'
 async with httpx.AsyncClient(timeout=45,follow_redirects=True) as c:r=await c.get(url);r.raise_for_status()
 s=BeautifulSoup(r.text,'html.parser');out=[];terms=[k.casefold() for k in keywords(['pl','en'])]
 for a in s.select('a[href]'):
  text=' '.join((a.parent or a).get_text(' ',strip=True).split());title=' '.join(a.get_text(' ',strip=True).split())
  if title and any(k in text.casefold() for k in terms):
   href=str(httpx.URL(url).join(a.get('href','')));rid=str(abs(hash(href)));out.append(Tender('orlen:'+rid,'orlen','POL',title,'Grupa ORLEN',published=datetime.now(),url=href,description=text,procurement_id=rid))
 return list({x.id:x for x in out}.values()),{'scanned':len(s.select('a[href]')),'final':len(out)}
