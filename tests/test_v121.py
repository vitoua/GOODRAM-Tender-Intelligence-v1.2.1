from app.main import app
from app.filters import relevant
from app.sources import SOURCES
assert app.version=='1.2.1'
assert 'base' not in SOURCES and 'ekap' in SOURCES
assert relevant('prozorro',['30230000'],'')
assert not relevant('prozorro',['09123000'],'Природний газ')
assert {'/refresh/start','/refresh/status','/lang/{code}','/export.xlsx'}<={r.path for r in app.routes}
print('v1.2.1 tests ok')
