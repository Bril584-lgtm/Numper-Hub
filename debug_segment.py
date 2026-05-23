import asyncio
from curl_cffi.requests import AsyncSession

async def test():
    # Segment from tigerflare10.xyz (base64 obfuscated extension)
    url = "https://tigerflare10.xyz/file2/SUMXM8CzI4vH429D2w5JnmdH13bgPlQJCxxnNP7917D07RpU1YTu1CTwqjqH60efnr6FhSb1psZf3sQOPYQVOcOEUvJ2e7eOsJlxis3M~7ap7e4rPP3BGwDl8xOSbYeFEf6iR1Fl8209~5OUuE7qvMHa4eXHW~rI~TaNcZTuHE4=/NzIw/c2VnLTEtdjEtYTEuanBn"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    for ref in ["https://videostr.net/", "https://frostcomet5.pro/", ""]:
        origin = ref.rstrip("/") if ref else "https://tigerflare10.xyz"
        headers = {"User-Agent": ua}
        if ref:
            headers["Referer"] = ref
            headers["Origin"] = origin
        async with AsyncSession(impersonate="chrome120") as s:
            r = await s.get(url, headers=headers, allow_redirects=True, timeout=20)
        print(f"ref={ref[:35]:35s} status={r.status_code} size={len(r.content)} ct={r.headers.get('content-type','')[:25]}")

asyncio.run(test())
