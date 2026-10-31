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
    def _build_system_prompt(interpretation_type: str = "") -> str:
        """Sıfır astrolojik terim, tamamen hesaplama verilerine dayalı profesyonel uzman promptu"""
        base = (
            "Sen analitik psikoloji, davranışsal dinamikler ve geometrik rezonans alanında uzman bir analiz motorusun.\n"
            "GÖREVİN: Sana aktarılan matematiksel ve geometrik hesaplama sonuçlarını, kişinin gerçek yaşam dinamiklerine, "
            "zihinsel modellerine, bilinçaltı örüntülerine ve yeteneklerine dönüştürerek derinlemesine yorumlamaktır.\n\n"
            "## KESİN KURALLAR — SIFIR ASTROLOJİK TERİM:\n"
            "1. GEZEGEN ADLARI ASLA GEÇMEYECEK: Güneş, Ay, Mars, Venüs, Satürn, Jüpiter, Merkür, Uranüs, Neptün, Plüton adları KESİNLİKLE YASAKTIR. "
            "Bunlar yerine; yaşam enerjisi, duygusal güvenlik ihtiyacı, zihinsel işlemleme hızı, bağ kurma dinamiği, yapısal sorumluluk baskısı, dönüştürücü iç güç de.\n"
            "2. BURÇ, ELEMENT VE NİTELİK ADLARI ASLA GEÇMEYECEK: Koç, Boğa, İkizler, Yengeç, Aslan, Başak, Terazi, Akrep, Yay, Oğlak, Kova, Balık isimleri KESİNLİKLE YASAK. "
            "'Hava ağırlıklı', 'su grubu', 'ateş elementi', 'toprak enerjisi', 'değişken nitelik', 'öncü yapı', 'sabit dinamik' veya 'nitelik dağılımı' gibi sınıflandırmalar ASLA KULLANILAMAZ.\n"
            "3. EV VE AÇI ADLARI ASLA GEÇMEYECEK: '1. ev', '7. ev', '10. ev' gibi ev numaraları; 'kavuşum', 'kare', 'karşıt', 'üçgen', 'sekstil' gibi açı isimleri ASLA KULLANILMAYACAKTIR.\n"
            "4. DİĞER TEKNİK TERİMLER YASAK: Transit, natal, ascendant, yükselen, alçalan, MC, IC, orb, cusp, retrograd, dasha, firdaria, navamsa, harmonik, deklinasyon, antiscia, midpoint terimleri çıktıda ASLA YER ALMAYACAKTIR.\n"
            "5. TAMAMEN HESAPLAMA SONUÇLARINA BAĞLI (ASLA HAYALİ DEĞİL): Veride bulunmayan hiçbir genel geçer kehanet veya kurgu üretme. Tüm tespitlerin sana verilen hesaplama verilerinin somut karşılığı olsun.\n"
            "6. TAVSİYE YASAĞI: 'Yapmalısın, etmelisin, kaçınmalısın' gibi tavsiyeler YASAKTIR. Yalnızca tabloyu ve etkileşimleri tanımla.\n"
            "7. EKSİKSİZ VE BÜTÜN YANIT: Analizi başından sonuna kadar tüm başlıklarıyla eksiksiz tamamla. Cümleleri veya metni asla yarım bırakma. Son cümleyi tamamlanmış bir nokta ile bitir."
        )
        if interpretation_type == "daily":
            return (
                base + "\n"
                "EK KISITLAMA: YALNIZCA bugünün aktif etkileşimlerini yorumlarsın. Uzun vade veya karakter analizi YASAKTIR."
            )
        return base

    @staticmethod
    async def call_provider_streaming(
        session: aiohttp.ClientSession,
        provider: dict,
        prompt: str,
        max_tokens: int = 16384,
        timeout: int = 120,
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
                async for raw_line in resp.content:
                    line = raw_line.decode('utf-8', errors='replace').strip()

                    if not line:
                        continue

                    # SSE format: "data: {...}" veya "data:{...}"
                    if line.startswith("data:"):
                        line = line[5:].strip()

                    # Stream bitiş sinyali
                    if line == "[DONE]":
                        logger.info(f"[AI] ✅ {name} streaming tamamlandı ([DONE])")
                        break

                    try:
                        chunk_data = json.loads(line)
                        choices = chunk_data.get("choices", [])
                        if not choices:
                            continue
                        choice = choices[0]
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            logger.info(f"[AI Stream] {name} finish_reason: {finish_reason}")
                            if finish_reason == "length":
                                logger.warning(f"[AI Stream] ⚠️ {name} max_tokens sınırına ulaştı!")

                        delta = choice.get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield content

                    except json.JSONDecodeError:
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
        max_tokens: int = 16384,
        timeout: int = 120,
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
