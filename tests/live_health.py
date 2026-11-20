import sys
import httpx
url=sys.argv[1].rstrip('/')
response=httpx.get(url+'/health',timeout=60)
print('GET /health:',response.status_code, response.text[:200])
assert response.status_code==200, 'Backend health did not pass'
assert response.json()=={'status':'ok','database':'connected'}
response=httpx.get(url+'/api/demo/stats',timeout=60)
print('GET /api/demo/stats:',response.status_code)
assert response.status_code==200
data=response.json()
assert data['site']['is_demo'] and data['pageviews']>0
print('Public health and PostgreSQL demo aggregation: 2 passed; synthetic pageviews:',data['pageviews'])