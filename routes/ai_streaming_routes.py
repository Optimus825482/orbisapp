# -*- coding: utf-8 -*-
"""
AI Streaming Routes - Server-Sent Events (SSE) ile gerçek zamanlı AI yanıtları
- Sadece ilgili hesaplama sonuçlarını LLM'e filtreler (gereksiz/eksik veri yok)
- Sıfır astrolojik terim, tamamen hesaplama verilerine dayalı derin uzman yorumu
- 16384 token ve 120sn timeout ile yarım kalmayan tam yanıt garantisi
- Aktif -> Yedek fallback zinciri ve anlık Queue tabanlı SSE aktarımı
"""
import asyncio
import json
import logging
import queue
import threading
import aiohttp
from flask import Blueprint, request, Response, stream_with_context

from services.ai_service import ai_service
from services.ai_service_streaming import AIServiceStreaming

logger = logging.getLogger(__name__)

ai_streaming_bp = Blueprint('ai_streaming', __name__, url_prefix='/api/ai')


@ai_streaming_bp.route('/interpret-stream', methods=['POST'])
def interpret_stream():
    """
    Streaming ile AI yorumu - Server-Sent Events (SSE)

    Request body:
    {
        "natal_data": {...},         # veya astro_data
        "interpretation_type": "...", # harmonic, birth_chart, relationship, career...
        "user_name": "...",
        "device_id": "...",
        "email": "..."
    }

    Response: SSE stream
    data: {"type": "chunk", "content": "..."}
    data: {"type": "done", "chunks": 12, "total_chars": 2340}
    data: {"type": "error", "message": "..."}
    """
    try:
        data = request.get_json() or {}
        astro_data = data.get('natal_data') or data.get('astro_data') or {}
        raw_type = data.get('interpretation_type', 'birth_chart')
        interpretation_type = ai_service.normalize_type(raw_type)
        user_name = data.get('user_name', 'Danışan')
        device_id = data.get('device_id')
        email = data.get('email')

        if not astro_data:
            return Response(
                f'data: {json.dumps({"type": "error", "message": "Hesaplama sonuçları (astro_data) bulunamadı"})}\n\n',
                mimetype='text/event-stream'
            )

        # 1. Yalnızca ilgili harita analizine ait hesaplama sonuçlarını filtrele
        filtered_data = ai_service._filter_astro_data(astro_data, interpretation_type)
        filtered_data = ai_service._deep_trim(filtered_data)
        data_json = json.dumps(filtered_data, default=str, ensure_ascii=False)
        data_size = len(data_json)
        logger.info(f"[AI Stream] '{interpretation_type}' için filtrelenmiş hesaplama boyutu: {data_size:,} bytes")

        # 2. Analiz türüne özel spesifik prompt ve kesin kuralları birleştir
        type_prompt = ai_service.TYPE_PROMPTS.get(interpretation_type)
        if type_prompt:
            prompt = f"User: {user_name}\n{type_prompt}\nData: {data_json}\n{ai_service.BASE_RULES}"
        else:
            prompt = f"User: {user_name}\nType: {interpretation_type}\nData: {data_json}\n{ai_service.BASE_RULES}"

        # 3. Provider fallback zincirini al (Aktif -> Yedek 1 -> Yedek 2 -> Yedek 3)
        fallback_chain = ai_service._get_fallback_chain()
        if not fallback_chain:
            return Response(
                f'data: {json.dumps({"type": "error", "message": "Hiçbir AI sağlayıcısı yapılandırılmamış"})}\n\n',
                mimetype='text/event-stream'
            )

        # PWA / Native kontrolü
        user_agent = request.headers.get('User-Agent', '')
        client_platform = request.headers.get('X-Client-Platform', '').lower()
        is_pwa = (
            'capacitor' not in user_agent.lower() and
            client_platform != 'capacitor' and
            client_platform != 'native' and
            client_platform != 'android'
        )

        # 4. Gerçek zamanlı Queue tabanlı SSE akışı (hafızada bekletmeden anında yield)
        def generate():
            q = queue.Queue()
            SENTINEL = object()

            def run_async_stream():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async def _stream():
                        async with aiohttp.ClientSession() as session:
                            for i, provider in enumerate(fallback_chain):
                                provider_name = provider.get('name', f'Provider-{i}')
                                try:
                                    logger.info(f"[AI Stream] Deneniyor: {provider_name} ({interpretation_type})")
                                    chunk_count = 0
                                    total_chars = 0

                                    async for chunk in AIServiceStreaming.call_provider_streaming(
                                        session=session,
                                        provider=provider,
                                        prompt=prompt,
                                        max_tokens=16384,
                                        timeout=120,
                                        interpretation_type=interpretation_type,
                                    ):
                                        chunk_count += 1
                                        total_chars += len(chunk)
                                        yield f'data: {json.dumps({"type": "chunk", "content": chunk})}\n\n'

                                    if chunk_count > 0:
                                        logger.info(f"[AI Stream] ✅ {provider_name} başarıyla tamamlandı ({chunk_count} chunk, {total_chars} karakter)")
                                        # Kullanım ve istatistik kaydı
                                        if device_id and not is_pwa:
                                            try:
                                                from monetization.usage_tracker import UsageTracker
                                                UsageTracker().record_usage(device_id, "ai_interpretation", email)
                                            except Exception as ut_err:
                                                logger.warning(f"[AI Stream] UsageTracker hatası: {ut_err}")

                                        try:
                                            from services.stats_counter import stats_counter
                                            stats_counter.on_analysis_completed()
                                        except Exception:
                                            pass

                                        yield f'data: {json.dumps({"type": "done", "chunks": chunk_count, "total_chars": total_chars})}\n\n'
                                        return

                                except Exception as prov_err:
                                    logger.warning(f"[AI Stream] Provider '{provider_name}' hatası: {prov_err}")
                                    if i == len(fallback_chain) - 1:
                                        # Son provider da başarısız olduysa hata mesajı fırlat
                                        yield f'data: {json.dumps({"type": "error", "message": f"AI yanıtı üretilemedi: {str(prov_err)[:200]}"})}\n\n'

                    async def _runner():
                        async for sse_item in _stream():
                            q.put(sse_item)
                        q.put(SENTINEL)

                    loop.run_until_complete(_runner())
                except Exception as exc:
                    logger.error(f"[AI Stream] Thread kritik hata: {exc}")
                    q.put(f'data: {json.dumps({"type": "error", "message": str(exc)[:200]})}\n\n')
                    q.put(SENTINEL)
                finally:
                    loop.close()

            # Background worker thread başlat
            worker_thread = threading.Thread(target=run_async_stream, daemon=True)
            worker_thread.start()

            while True:
                item = q.get()
                if item is SENTINEL:
                    break
                yield item

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Nginx/reverse proxy buffering'ini kapat
                'Connection': 'keep-alive',
            }
        )

    except Exception as e:
        logger.error(f"Endpoint hatası: {str(e)}")
        return Response(
            f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n',
            mimetype='text/event-stream'
        )
