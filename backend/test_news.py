import httpx, asyncio

API_KEY = '3b12860071d04603848cf0fb3bc62815'
URL = 'https://newsapi.org/v2/everything'

async def test():
    async with httpx.AsyncClient() as client:
        # Test 1: current query style (long boolean with city name)
        q1 = 'Toronto AND (real estate OR housing market OR mortgage OR condo OR rent OR zoning)'
        r1 = await client.get(URL, params={
            'q': q1, 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': 10, 'apiKey': API_KEY
        }, timeout=20)
        d1 = r1.json()
        print('=== Query 1: Toronto basic ===')
        print(f'Status: {d1.get("status")}, Total: {d1.get("totalResults")}')
        for a in d1.get('articles', [])[:5]:
            print(' -', (a.get('title','') or '')[:90])

        # Test 2: simpler keyword-only
        q2 = 'Toronto housing market'
        r2 = await client.get(URL, params={
            'q': q2, 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': 10, 'apiKey': API_KEY
        }, timeout=20)
        d2 = r2.json()
        print()
        print('=== Query 2: Toronto housing market ===')
        print(f'Status: {d2.get("status")}, Total: {d2.get("totalResults")}')
        for a in d2.get('articles', [])[:5]:
            print(' -', (a.get('title','') or '')[:90])

        # Test 3: Bank of Canada macro
        q3 = 'Bank of Canada interest rate housing'
        r3 = await client.get(URL, params={
            'q': q3, 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': 10, 'apiKey': API_KEY
        }, timeout=20)
        d3 = r3.json()
        print()
        print('=== Query 3: Bank of Canada ===')
        print(f'Status: {d3.get("status")}, Total: {d3.get("totalResults")}')
        for a in d3.get('articles', [])[:5]:
            print(' -', (a.get('title','') or '')[:90])

        # Test 4: Canadian real estate
        q4 = 'Canadian real estate market 2025'
        r4 = await client.get(URL, params={
            'q': q4, 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': 10, 'apiKey': API_KEY
        }, timeout=20)
        d4 = r4.json()
        print()
        print('=== Query 4: Canadian real estate ===')
        print(f'Status: {d4.get("status")}, Total: {d4.get("totalResults")}')
        for a in d4.get('articles', [])[:5]:
            print(' -', (a.get('title','') or '')[:90])

        # Test 5: Calgary housing
        q5 = 'Calgary housing market OR Calgary real estate'
        r5 = await client.get(URL, params={
            'q': q5, 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': 10, 'apiKey': API_KEY
        }, timeout=20)
        d5 = r5.json()
        print()
        print('=== Query 5: Calgary housing ===')
        print(f'Status: {d5.get("status")}, Total: {d5.get("totalResults")}')
        for a in d5.get('articles', [])[:5]:
            print(' -', (a.get('title','') or '')[:90])

asyncio.run(test())
