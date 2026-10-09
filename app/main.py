from datetime import datetime,timedelta
from io import BytesIO
import asyncio,json,uuid
from pathlib import Path
from fastapi import FastAPI,Form,Request,HTTPException
from fastapi.responses import JSONResponse,StreamingResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.core import store,active,analytics
from app.sources import COUNTRIES,SOURCES
from app.i18n import tr
from app.translate import ensure
app=FastAPI(version='1.2.1');app.mount('/static',StaticFiles(directory='app/static'),name='static');tpl=Jinja2Templates(directory='app/templates');JOB={'running':False,'id':None,'progress':0,'message':'','error':''};LOCK=asyncio.Lock()
def lang(r):return r.cookies.get('lang') or settings.app_language
def ctx(r,x=None):return {'request':r,'lang':lang(r),'t':tr(lang(r)),**(x or {})}
def default_date():return (datetime.now()-timedelta(days=30)).date().isoformat()
def filtered(q='',country='',source='',active_only=1):return [x for x in store.data.values() if (not active_only or active(x)) and (not country or x.country==country) and (not source or x.source==source) and (not q or q.casefold() in (x.title+x.buyer+x.description+' '.join(x.cpv)).casefold())]
@app.get('/health')
def health():return {'status':'ok','version':'1.2.1','job':JOB,'tenders':len(store.data)}
@app.get('/lang/{code}')
def language(code,request:Request):
 r=RedirectResponse(request.headers.get('referer') or '/',303);r.set_cookie('lang',code if code in ('pl','uk','en','es') else 'pl');return r
@app.get('/')
async def home(request:Request,q:str='',country:str='',source:str='',active_only:int=1):
 items=sorted(filtered(q,country,source,active_only),key=lambda x:x.deadline or datetime.max);await ensure(items,lang(request));return tpl.TemplateResponse('index.html',ctx(request,{'rows':items,'runs':store.runs,'countries':COUNTRIES,'sources':SOURCES,'default_date':default_date(),'q':q,'country':country,'source':source,'last_update':store.last_update}))
async def execute(job,selected,sources,start,min_value):
 async with LOCK:
  JOB.update(running=True,id=job,progress=2,message='Rozpoczynanie...',error='');plan=[]
  if 'ted' in sources and any(c not in ('UKR','TUR') for c in selected):plan.append(('ted',[c for c in selected if c not in ('UKR','TUR')]))
  if 'prozorro' in sources and 'UKR' in selected:plan.append(('prozorro',['UKR']))
  if 'germany' in sources and 'DEU' in selected:plan.append(('germany',['DEU']))
  if 'orlen' in sources and 'POL' in selected:plan.append(('orlen',['POL']))
  if 'junta' in sources and 'ESP' in selected:plan.append(('junta',['ESP']))
  if 'ekap' in sources and 'TUR' in selected:plan.append(('turkey',['TUR']))
  results=[]
  for i,(name,scope) in enumerate(plan,1):
   JOB.update(progress=int((i-1)/max(1,len(plan))*90)+5,message=f'Pobieranie: {name.upper()}')
   try:module=__import__('app.connectors.'+name,fromlist=['fetch']);items,stats=await asyncio.wait_for(module.fetch(scope,start,min_value),150);results.append(('ekap' if name=='turkey' else name,items,None,stats))
   except Exception as e:results.append(('ekap' if name=='turkey' else name,[],e,{}))
  store.replace(results);JOB.update(running=False,progress=100,message='Aktualizacja zakończona')
@app.post('/refresh/start')
async def start(countries:list[str]=Form(default=[]),sources:list[str]=Form(default=[]),min_value_eur:float=Form(0),published_from:str=Form(default='')):
 if JOB['running']:return JSONResponse({'ok':False,'message':'Aktualizacja jest już uruchomiona.'},409)
 if not countries or not sources:return JSONResponse({'ok':False,'message':'Wybierz kraj i źródło.'},400)
 job=str(uuid.uuid4());asyncio.create_task(execute(job,countries,sources,datetime.fromisoformat(published_from or default_date()),min_value_eur));return {'ok':True,'job':job}
@app.get('/refresh/status')
def status():return {**JOB,'runs':store.runs,'count':len(store.data)}
@app.get('/tenders/{tid:path}')
async def detail(tid,request:Request,view:str='translated'):
 x=store.data.get(tid)
 if not x:raise HTTPException(404)
 await ensure([x],lang(request));return tpl.TemplateResponse('detail.html',ctx(request,{'x':x,'view':view}))
@app.get('/analytics')
def analytical(request:Request):return tpl.TemplateResponse('analytics.html',ctx(request,{'data':analytics(list(store.data.values())),'count':len(store.data)}))
@app.get('/export.xlsx')
def export():
 from openpyxl import Workbook
 wb=Workbook();ws=wb.active;ws.append(['Źródło','Kraj','Numer','Nazwa','Zamawiający','Publikacja','Termin','Wartość','Waluta','EUR','CPV','Link'])
 for x in store.data.values():ws.append([x.source,x.country,x.procurement_id,x.title,x.buyer,x.published,x.deadline,x.value,x.currency,x.value_eur,', '.join(x.cpv),x.url])
 ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions;out=BytesIO();wb.save(out);out.seek(0);return StreamingResponse(out,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="GOODRAM-Tender-Intelligence-v1.2.1.xlsx"'})
