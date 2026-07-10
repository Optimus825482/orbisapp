# -*- coding: utf-8 -*-
"""
AI Provider Streaming vs Non-Streaming Benchmark
Streaming kullanmanın hız avantajını gösterir
"""
import asyncio
import aiohttp
import json
import os
import sys
import time
from typing import Tuple, Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_providers():
    """Firestore'dan veya env'den provider'ları al"""
    providers = []
    try:
        from services.firebase_service import firebase_service
        db = firebase_service.db
        if db:
            doc = db.collection("config").document("ai_settings").get()
            if doc.exists:
                data = doc.to_dict()
                provs = data.get("providers", [])
                active = data.get("active_provider", "")
                for p in provs:
                    providers.append(dict(
                        name=p.get("name", "?"),
                        base_url=p.get("base_url", ""),
                        api_key=p.get("api_key", ""),
                        model=p.get("model", ""),
                        active=(p.get("name") == active),
                    ))
    except Exception as e:
        print("[WARN] Firestore: %s" % e)

    if not providers:
        print("[INFO] env fallback")
        if os.getenv("DEEPSEEK_API_KEY"):
            providers.append(dict(
                name="DEEPSEEK(env)",
                base_url="https://api.deepseek.com",
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                model="deepseek-chat",
                active=True
            ))
    return providers


async def test_non_streaming(
    session: aiohttp.ClientSession,
    provider: dict,
    prompt: str,
    max_tokens: int = 256,
    timeout: int = 60
) -> Tuple[bool, float, str, Optional[str], Optional[float]]:
    """
    ❌ NON-STREAMING: Tüm yanıtı bekler (eski yöntem)

    Returns:
        (success, total_time, content, error, time_to_first_token)
    """
    url = provider["base_url"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    payload = dict(
        model=provider["model"],
        messages=[dict(role="user", content=prompt)],
        max_tokens=max_tokens,
        temperature=0.3,
        stream=False  # ❌ Streaming kapalı
    )
    headers = {
        "Authorization": "Bearer " + provider["api_key"],
        "Content-Type": "application/json"
    }

    start = time.time()
    try:
        async with session.post(
            url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()  # ⏰ Tüm yanıtı bekle
                elapsed = time.time() - start

                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                finish = data.get("choices", [{}])[0].get("finish_reason", "?")

                if not content:
                    return (False, elapsed, "", f"Boş yanıt (finish={finish})", None)

                # Non-streaming'de TTFT = total time (ilk token = son token)
                return (True, elapsed, content, None, elapsed)
            else:
                elapsed = time.time() - start
                error_text = await resp.text()
                return (False, elapsed, "", f"HTTP {resp.status}: {error_text[:100]}", None)

    except asyncio.TimeoutError:
        return (False, timeout, "", "TIMEOUT", None)
    except Exception as e:
        return (False, time.time() - start, "", str(e)[:100], None)


async def test_streaming(
    session: aiohttp.ClientSession,
    provider: dict,
    prompt: str,
    max_tokens: int = 256,
    timeout: int = 60
) -> Tuple[bool, float, str, Optional[str], Optional[float]]:
    """
    ✅ STREAMING: Chunk chunk alır (yeni yöntem)

    Returns:
        (success, total_time, content, error, time_to_first_token)
    """
    url = provider["base_url"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    payload = dict(
        model=provider["model"],
        messages=[dict(role="user", content=prompt)],
        max_tokens=max_tokens,
        temperature=0.3,
        stream=True  # ✅ Streaming açık
    )
    headers = {
        "Authorization": "Bearer " + provider["api_key"],
        "Content-Type": "application/json"
    }

    start = time.time()
    first_chunk_time = None
    chunks = []

    try:
        async with session.post(
            url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status != 200:
                elapsed = time.time() - start
                error_text = await resp.text()
                return (False, elapsed, "", f"HTTP {resp.status}: {error_text[:100]}", None)

            # Server-Sent Events (SSE) formatında gelir
            async for line in resp.content:
                line = line.decode('utf-8').strip()

                if not line or not line.startswith("data: "):
                    continue

                line = line[6:]  # "data: " prefix'ini kaldır

                if line == "[DONE]":
                    break

                try:
                    chunk_data = json.loads(line)
                    delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")

                    if content:
                        if first_chunk_time is None:
                            first_chunk_time = time.time() - start  # ⚡ İlk token süresi
                        chunks.append(content)

                except json.JSONDecodeError:
                    continue

            elapsed = time.time() - start
            full_content = ''.join(chunks)

            if not full_content:
                return (False, elapsed, "", "Boş yanıt", first_chunk_time)

            return (True, elapsed, full_content, None, first_chunk_time)

    except asyncio.TimeoutError:
        return (False, timeout, "", "TIMEOUT", first_chunk_time)
    except Exception as e:
        return (False, time.time() - start, "", str(e)[:100], first_chunk_time)


async def benchmark_comparison(prompt_type: str = "simple"):
    """Streaming vs Non-Streaming karşılaştırması"""
    providers = get_providers()
    if not providers:
        print("❌ Provider bulunamadı!")
        return

    # Prompt hazırlama
    if prompt_type == "real":
        # Gerçek astroloji prompt'u (uzun yanıt)
        astro_json = json.dumps({
            "natal_planet_positions": {
                "Sun": {"sign": "Ikizler", "house": 10, "degree": 80.14},
                "Moon": {"sign": "Kova", "house": 5, "degree": 311.72}
            }
        })
        prompt = f"""User: ERKAN ERDEM
## DOĞUM HARİTASI ANALİZİ
Yukarıdaki verileri kullanarak kısa bir analiz yap (maksimum 500 kelime).

Data: {astro_json}

## KURALLAR
- Sade Türkçe kullan
- Doğrudan ifadeler
- Maksimum 500 kelime"""
        max_tok = 2048  # 4096'dan düşürüldü
        timeout = 60     # 120'den düşürüldü
    else:
        prompt = "Astroloji nedir? Kısa açıkla."
        max_tok = 256
        timeout = 30

    print("\n" + "=" * 90)
    print("🔬 AI PROVIDER STREAMING vs NON-STREAMING BENCHMARK")
    print("=" * 90)
    print(f"Mode: {prompt_type} | max_tokens={max_tok} | timeout={timeout}s")
    print(f"Prompt size: {len(prompt)} bytes")
    print(f"Providers: {len(providers)}\n")

    async with aiohttp.ClientSession() as session:
        for p in providers:
            print(f"\n{'─' * 90}")
            print(f"🤖 Provider: {p['name']} | Model: {p['model']}")
            print(f"{'─' * 90}")

            # Test 1: Non-Streaming
            print("\n❌ Test 1: NON-STREAMING (eski yöntem - tüm yanıtı bekler)")
            success1, time1, content1, err1, ttft1 = await test_non_streaming(
                session, p, prompt, max_tok, timeout
            )

            if success1:
                print(f"   ✅ Başarılı")
                print(f"   ⏱️  Toplam süre: {time1:.2f}s")
                print(f"   📏 Yanıt uzunluğu: {len(content1)} karakter")
                print(f"   🔍 İlk 100 karakter: {content1[:100]}...")
            else:
                print(f"   ❌ HATA: {err1}")
                print(f"   ⏱️  Geçen süre: {time1:.2f}s")

            # Bekleme (rate limit için)
            await asyncio.sleep(2)

            # Test 2: Streaming
            print("\n✅ Test 2: STREAMING (yeni yöntem - chunk chunk alır)")
            success2, time2, content2, err2, ttft2 = await test_streaming(
                session, p, prompt, max_tok, timeout
            )

            if success2:
                print(f"   ✅ Başarılı")
                print(f"   ⚡ İlk token süresi (TTFT): {ttft2:.2f}s")
                print(f"   ⏱️  Toplam süre: {time2:.2f}s")
                print(f"   📏 Yanıt uzunluğu: {len(content2)} karakter")
                print(f"   🔍 İlk 100 karakter: {content2[:100]}...")
            else:
                print(f"   ❌ HATA: {err2}")
                print(f"   ⏱️  Geçen süre: {time2:.2f}s")
                if ttft2:
                    print(f"   ⚡ İlk token süresi: {ttft2:.2f}s")

            # Karşılaştırma
            if success1 and success2:
                print(f"\n📊 KARŞILAŞTIRMA:")
                print(f"   • Non-Streaming toplam: {time1:.2f}s")
                print(f"   • Streaming toplam: {time2:.2f}s")
                print(f"   • Streaming TTFT (ilk token): {ttft2:.2f}s ⚡")

                improvement = ((time1 - time2) / time1) * 100
                ttft_improvement = ((time1 - ttft2) / time1) * 100

                print(f"\n   🎯 SONUÇ:")
                print(f"   • Toplam süre farkı: {improvement:+.1f}%")
                print(f"   • İlk token TTFT farkı: {ttft_improvement:+.1f}% ⚡")
                print(f"   • Kullanıcı {ttft2:.1f} saniye sonra yanıt görmeye başlar!")

    print("\n" + "=" * 90)
    print("✅ Benchmark tamamlandı")
    print("=" * 90)


if __name__ == "__main__":
    prompt_type = sys.argv[1] if len(sys.argv) > 1 else "simple"
    asyncio.run(benchmark_comparison(prompt_type))
