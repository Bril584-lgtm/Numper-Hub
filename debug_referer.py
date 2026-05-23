import asyncio
from curl_cffi.requests import AsyncSession

async def test():
    url = "https://frostcomet5.pro/file2/SUMXM8CzI4vH429D2w5JnmdH13bgPlQJCxxnNP7917D07RpU1YTu1CTwqjqH60efnr6FhSb1psZf3sQOPYQVOcOEUvJ2e7eOsJlxis3M~7ap7e4rPP3BGwDl8xOSbYeFEf6iR1Fl8209~5OUuE7qvMHa4eXHW~rI~TaNcZTuHE4=/NzIw/aW5kZXgubTN1OA==.m3u8"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    for ref in ["https://videostr.net/", "https://vidlink.pro/", "https://frostcomet5.pro/"]:
        headers = {"Referer": ref, "Origin": ref.rstrip("/"), "User-Agent": ua}
        async with AsyncSession(impersonate="chrome120") as s:
            r = await s.get(url, headers=headers, allow_redirects=True, timeout=15)
        ct = r.headers.get("content-type", "")
        print(f"ref={ref[:30]:30s}  status={r.status_code}  ct={ct[:30]}")
        if r.status_code == 200:
            print("  First 150:", r.text[:150])

asyncio.run(test())
