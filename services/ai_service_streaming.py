# -*- coding: utf-8 -*-
"""AI Service with Streaming Support"""
import asyncio
import aiohttp
import json
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class AIServiceStreaming:
    """AI Service with streaming support for faster responses"""

    @staticmethod
    def _build_system_prompt(interpretation_type: str) -> str:
        """Yorum türüne göre system prompt döndür"""
        base = (
            "Sen bir astroloji yorumlama motorusun. "
            "Verilen hesaplama verisini yorumlarsın. "
            "KESİN KURAL: Gezegen isimleri (Mars, Venüs, Satürn, Jüpiter, Merkür, Uranüs, Neptün, Plüton, Ay, Güneş), "
            "burç isimleri (Koç, Boğa, İkizler, Yengeç, Aslan, Başak, Terazi, Akrep, Yay, Oğlak, Kova, Balık), "
            "ev numaraları (1. ev, 7. ev vb.), açı adları (kare, karşıt, üçgen, kavuşum), "
            "ve teknik terimler (transit, natal, ascendant, Chiron, Dasha, Navamsa, Firdaria, retrograd) "
            "çıktıda HİÇBİR KOŞULDA geçmez. "
            "Tavsiye vermezsin. Yönlendirmezsin. Sadece enerjiyi ve etkiyi tanımlarsın."
        )
        if interpretation_type == "daily":
            return (
                base + " "
                "EKLEME KISITLAMA: YALNIZCA bugünkü gezegen pozisyonları ile doğum haritası arasındaki "
                "aktif etkileşimleri yorumlarsın. Dönem analizi, karakter yorumu, uzun vade YASAK."
            )
        return base

    @staticmethod
    async def call_provider_streaming(
        session: aiohttp.ClientSession,
        provider: dict,
        prompt: str,
        max_tokens: int = 2048,
        timeout: int = 60,
        temperature: float = 0.3,
        interpretation_type: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        Streaming ile provider'a çağrı yap - chunk chunk yanıt al

        Yields:
            str: Her chunk'tan gelen metin parçası
        """
        base_url = provider['base_url'].rstrip('/')
        api_key = provider['api_key']
        model = provider.get('model', 'deepseek-chat')
        name = provider.get('name', 'Bilinmeyen')

        url = f"{base_url}/chat/completions" if not base_url.endswith('/chat/completions') else base_url

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": AIServiceStreaming._build_system_prompt(interpretation_type)},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"[AI] ❌ {name} hata {resp.status}: {error_text[:200]}")
                    raise Exception(f"HTTP {resp.status}: {error_text[:200]}")

                logger.info(f"[AI] 🚀 {name} streaming başladı")

                # Server-Sent Events (SSE) formatında gelir
                async for line in resp.content:
                    line = line.decode('utf-8').strip()

                    if not line:
                        continue

                    # SSE format: "data: {...}"
                    if line.startswith("data: "):
                        line = line[6:]  # "data: " prefix'ini kaldır

                    # Stream bitiş sinyali
                    if line == "[DONE]":
                        logger.info(f"[AI] ✅ {name} streaming tamamlandı")
                        break

                    try:
                        chunk_data = json.loads(line)
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield content

                    except json.JSONDecodeError:
                        # Bazen boş veya hatalı line'lar olabilir
                        continue

        except asyncio.TimeoutError:
            logger.warning(f"[AI] ⏰ {name} timeout ({timeout}s)")
            raise
        except Exception as e:
            logger.warning(f"[AI] ❌ {name} exception: {str(e)[:100]}")
            raise

    @staticmethod
    async def call_provider_with_streaming(
        session: aiohttp.ClientSession,
        provider: dict,
        prompt: str,
        max_tokens: int = 2048,
        timeout: int = 60,
        temperature: float = 0.3
    ) -> dict:
        """
        Streaming kullanarak yanıtı topla ve döndür
        (Mevcut API uyumluluğu için - tüm yanıtı birleştirip döner)
        """
        name = provider.get('name', 'Bilinmeyen')
        full_response = []

        try:
            async for chunk in AIServiceStreaming.call_provider_streaming(
                session, provider, prompt, max_tokens, timeout, temperature
            ):
                full_response.append(chunk)

            content = ''.join(full_response)

            if not content:
                logger.warning(f"[AI] ❌ {name} boş yanıt döndü")
                return {"success": False, "error": f"{name}: boş yanıt", "provider": name}

            logger.info(f"[AI] ✅ {name} başarılı (len={len(content)})")
            return {
                "success": True,
                "interpretation": content,
                "provider": name
            }

        except Exception as e:
            logger.warning(f"[AI] ❌ {name} hata: {str(e)[:100]}")
            return {"success": False, "error": f"{name}: {str(e)[:100]}", "provider": name}


# ============================================================
# KULLANIM ÖRNEKLERİ
# ============================================================

async def example_streaming_usage():
    """Örnek 1: Chunk chunk yazdırma (gerçek zamanlı)"""
    async with aiohttp.ClientSession() as session:
        provider = {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "api_key": "your-api-key",
            "model": "deepseek-chat"
        }

        prompt = "Astroloji hakkında kısa bir açıklama yaz."

        print("🚀 Streaming yanıt:")
        async for chunk in AIServiceStreaming.call_provider_streaming(
            session, provider, prompt
        ):
            print(chunk, end='', flush=True)  # Gerçek zamanlı yazdır
        print("\n✅ Tamamlandı")


async def example_backward_compatible():
    """Örnek 2: Mevcut API ile uyumlu (tüm yanıtı döner)"""
    async with aiohttp.ClientSession() as session:
        provider = {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "api_key": "your-api-key",
            "model": "deepseek-chat"
        }

        prompt = "Astroloji hakkında kısa bir açıklama yaz."

        result = await AIServiceStreaming.call_provider_with_streaming(
            session, provider, prompt
        )

        if result["success"]:
            print("✅ Yanıt:", result["interpretation"][:200])
        else:
            print("❌ Hata:", result["error"])
