from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 app_language:str='pl';libretranslate_url:str='';libretranslate_api_key:str='';apify_api_token:str=''
 model_config=SettingsConfigDict(env_file='.env',extra='ignore')
settings=Settings()
