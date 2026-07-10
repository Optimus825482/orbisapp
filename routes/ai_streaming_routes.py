# -*- coding: utf-8 -*-
"""
AI Streaming Routes - Server-Sent Events (SSE) ile gerçek zamanlı AI yanıtları
"""
import asyncio
import json
import logging
from flask import Blueprint, request, Response, stream_with_context
from services.ai_service_streaming import AIServiceStreaming
from services.firebase_service import firebase_service
import aiohttp

logger = logging.getLogger(__name__)

ai_streaming_bp = Blueprint('ai_streaming', __name__, url_prefix='/api/ai')


def get_active_provider():
    """Firestore'dan aktif provider'ı al"""
    try:
        db = firebase_service.db
        if not db:
            raise Exception("Firestore bağlantısı yok")

        doc = db.collection("config").document("ai_settings").get()
        if not doc.exists:
            raise Exception("ai_settings bulunamadı")

        data = doc.to_dict()
        providers = data.get("providers", [])
        active_name = data.get("active_provider", "")

        for p in providers:
            if p.get("name") == active_name:
                return {
                    "name": p.get("name"),
                    "base_url": p.get("base_url"),
                    "api_key": p.get("api_key"),
                    "model": p.get("model", "deepseek-chat")
                }

        # Fallback: İlk provider'ı kullan
        if providers:
            p = providers[0]
            return {
                "name": p.get("name"),
                "base_url": p.get("base_url"),
                "api_key": p.get("api_key"),
                "model": p.get("model", "deepseek-chat")
            }

        raise Exception("Hiç provider bulunamadı")

    except Exception as e:
        logger.error(f"Provider alma hatası: {str(e)}")
        raise


@ai_streaming_bp.route('/interpret-stream', methods=['POST'])
def interpret_stream():
    """
    Streaming ile AI yorumu - Server-Sent Events (SSE)

    Request body:
    {
        "natal_data": {...},
        "interpretation_type": "character|compatibility|...",
        "user_name": "ERKAN ERDEM"
    }

    Response: SSE stream
    data: {"type": "chunk", "content": "..."}
    data: {"type": "done", "total_tokens": 1234}
    data: {"type": "error", "message": "..."}
    """
    try:
        data = request.get_json()
        natal_data = data.get('natal_data')
        interpretation_type = data.get('interpretation_type', 'character')
        user_name = data.get('user_name', 'Kullanıcı')

        if not natal_data:
            return Response(
                f'data: {json.dumps({"type": "error", "message": "natal_data gerekli"})}\n\n',
                mimetype='text/event-stream'
            )

        # Prompt oluştur
        prompt = build_astro_prompt(natal_data, interpretation_type, user_name)

        # Provider al
        try:
            provider = get_active_provider()
        except Exception as e:
            return Response(
                f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n',
                mimetype='text/event-stream'
            )

        # SSE stream generator
        def generate():
            """SSE formatında chunk chunk gönder"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                async def stream_response():
                    async with aiohttp.ClientSession() as session:
                        chunk_count = 0
                        total_chars = 0

                        async for chunk in AIServiceStreaming.call_provider_streaming(
                            session=session,
                            provider=provider,
                            prompt=prompt,
                            max_tokens=2048,  # 4096'dan düşürüldü
                            timeout=60        # 120'den düşürüldü
                        ):
                            chunk_count += 1
                            total_chars += len(chunk)

                            # SSE format: "data: {...}\n\n"
                            yield f'data: {json.dumps({"type": "chunk", "content": chunk})}\n\n'

                        # Son mesaj
                        yield f'data: {json.dumps({"type": "done", "chunks": chunk_count, "total_chars": total_chars})}\n\n'

                # Async generator'ı çalıştır
                for item in loop.run_until_complete(collect_stream(stream_response())):
                    yield item

            except asyncio.TimeoutError:
                yield f'data: {json.dumps({"type": "error", "message": "Timeout - yanıt çok uzun sürdü"})}\n\n'
            except Exception as e:
                logger.error(f"Streaming hatası: {str(e)}")
                yield f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n'
            finally:
                loop.close()

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Nginx buffering'i kapat
                'Connection': 'keep-alive'
            }
        )

    except Exception as e:
        logger.error(f"Endpoint hatası: {str(e)}")
        return Response(
            f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n',
            mimetype='text/event-stream'
        )


async def collect_stream(async_gen):
    """Async generator'ı sync generator'a dönüştür"""
    items = []
    async for item in async_gen:
        items.append(item)
    return items


def build_astro_prompt(natal_data, interpretation_type, user_name):
    """Astroloji prompt'u oluştur"""
    # natal_data'yı JSON string'e çevir
    natal_json = json.dumps(natal_data, ensure_ascii=False)

    if interpretation_type == "character":
        prompt = f"""User: {user_name}
## DOĞUM HARİTASI VE KARAKTER ANALİZİ
Aşağıdaki doğum haritası verilerini kullanarak kapsamlı bir karakter analizi yap.

Şu başlıkları detaylıca işle:
1. Dış dünyaya yansıyan kimlik (Yükselen burç)
2. Duygusal yapı ve iç dünya (Ay burcu)
3. Temel karakter ve ego (Güneş burcu)
4. İletişim ve düşünce tarzı
5. Sevgi dili ve ilişki yaklaşımı

Data: {natal_json}

## KESİN KURALLAR
### 1. YASAK TERİMLER (ASLA KULLANMA)
- Gezegen isimleri, burç isimleri, ev numaraları, açı isimleri, teknik terimler
### 2. DİL VE ÜSLUP
- Sade, anlaşılır Türkçe
- Doğrudan ve net ifadeler
- Kişisel ve samimi ton
### 3. UZUNLUK
- 500-800 kelime arası (kısa ve öz)
"""
    else:
        # Diğer interpretation türleri için farklı prompt'lar
        prompt = f"User: {user_name}\nData: {natal_json}\n\nKısa bir astroloji yorumu yap (maksimum 500 kelime)."

    return prompt


# ============================================================
# ÖRNEK KULLANIM - Test için
# ============================================================
if __name__ == "__main__":
    """
    Test için örnek Flask app

    Çalıştır:
        python routes/ai_streaming_routes.py

    Test et:
        curl -X POST http://localhost:5001/api/ai/interpret-stream \
             -H "Content-Type: application/json" \
             -d '{"natal_data": {...}, "user_name": "Test"}'
    """
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(ai_streaming_bp)

    print("🚀 AI Streaming Test Server başlatılıyor...")
    print("📍 Endpoint: http://localhost:5001/api/ai/interpret-stream")
    print("\n✅ Hazır! Test için curl komutu kullanabilirsiniz.")

    app.run(host='0.0.0.0', port=5001, debug=True)
