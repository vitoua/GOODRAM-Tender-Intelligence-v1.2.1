import hashlib,httpx
from app.config import settings
CACHE={}
async def one(value,target):
 if not value or not settings.libretranslate_url:return value
 key=(hashlib.sha256(value.encode()).hexdigest(),target)
 if key in CACHE:return CACHE[key]
 data={'q':value,'source':'auto','target':target,'format':'text'}
 if settings.libretranslate_api_key:data['api_key']=settings.libretranslate_api_key
 try:
  async with httpx.AsyncClient(timeout=25) as c:r=await c.post(settings.libretranslate_url.rstrip('/')+'/translate',data=data);r.raise_for_status();out=r.json()['translatedText']
  CACHE[key]=out;return out
 except:return value
async def ensure(items,lang):
 for x in items:
  if lang not in x.translations:x.translations[lang]={'title':await one(x.title,lang),'description':await one(x.description,lang)}
