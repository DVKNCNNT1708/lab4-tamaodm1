import json
from urllib.request import Request, urlopen

def get(url, headers=None):
    req = Request(url, headers=headers or {})
    with urlopen(req) as resp:
        return json.load(resp)

def post(url, data, headers=None):
    b = json.dumps(data).encode('utf-8')
    hdrs = {'Content-Type': 'application/json'}
    if headers:
        hdrs.update(headers)
    req = Request(url, data=b, headers=hdrs, method='POST')
    with urlopen(req) as resp:
        return json.load(resp)


if __name__ == '__main__':
    base = 'http://127.0.0.1:4010'
    print('== /health ==')
    print(json.dumps(get(base + '/health'), indent=2))

    print('\n== /ingest POST ==')
    payload = {
        'sourceType':'camera',
        'detectionId':'d-1',
        'detectionType':'PERSON',
        'confidence':0.95,
        'cameraId':'CAM-01',
        'occurredAt':'2026-06-01T10:00:00+00:00'
    }
    print(json.dumps(post(base + '/ingest', payload, headers={'Authorization':'Bearer local-dev-token'}), indent=2))

    print('\n== /analytics/summary ==')
    qs = '?fromDate=2026-06-01T00:00:00&toDate=2026-06-30T23:59:59'
    print(json.dumps(get(base + '/analytics/summary' + qs, headers={'Authorization':'Bearer local-dev-token'}), indent=2))

    print('\n== /dashboard ==')
    print(json.dumps(get(base + '/dashboard', headers={'Authorization':'Bearer local-dev-token'}), indent=2))
