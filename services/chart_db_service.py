"""
ORBIS Chart Database Service
Firestore ile astrolojik hesaplama sonuçlarını kalıcı olarak saklama.

Strateji:
- KALICI (doğum bazlı): Sabit veri → BİR DEFA hesapla, SONSUZA KADAR sakla
  (natal houses, planets, aspects, fixed stars, antiscia, dignity, harmonics,
   dasa, firdaria, arabic parts, midpoints, declinations...)
- GÜNLÜK (tarih bazlı): Dinamik veri → GÜNDE BİR hesapla, tarih değişene kadar sakla
  (transit positions/aspects, progressions, solar/lunar return, progressed moon...)

NOT: AI yorumları burada DEPOLANMAZ. Her AI yorum isteği canlı API'den gelir.
"""

import hashlib
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def _get_db():
    """Firestore client'ı lazy olarak al"""
    try:
        from services.firebase_service import firebase_service
        if firebase_service and firebase_service.db:
            return firebase_service.db
    except Exception as e:
        logger.warning(f"[ChartDB] Firestore bağlantısı kurulamadı: {e}")
    return None


def _make_natal_key(birth_date: str, birth_time: str, lat: float, lon: float) -> str:
    """
    Doğum bilgilerinden benzersiz hash oluştur.
    Aynı kişi = aynı hash → aynı natal chart → tek hesaplama.
    """
    raw = f"{birth_date}|{birth_time}|{round(float(lat), 4)}|{round(float(lon), 4)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _make_transit_key(transit_date: str, lat: float, lon: float) -> str:
    """
    Transit bilgilerinden günlük hash oluştur.
    Aynı gün + aynı konum = aynı transit → günde bir hesaplama yeter.
    """
    raw = f"{transit_date}|{round(float(lat), 2)}|{round(float(lon), 2)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════
# HESAPLAMA SONUÇLARI KATEGORİLERİ
# Her key, calculate_astro_data() fonksiyonunun döndürdüğü dict key'lerine karşılık gelir.
# ═══════════════════════════════════════════════════════════════

# ━━━ KALICI (STATIC) ━━━
# Doğum bilgilerine dayalı, ASLA değişmez.
# Bir kere hesaplandıktan sonra sonsuza kadar Firestore'da saklanır.
NATAL_KEYS = [
    "birth_info",
    "natal_houses",
    "natal_ascendant",
    "natal_planet_positions",
    "natal_additional_points",
    "natal_aspects",
    "natal_azimuth_altitude",
    "natal_fixed_stars",
    "natal_antiscia",
    "natal_dignity_scores",
    "natal_part_of_fortune",
    "natal_arabic_parts",
    "natal_lunation_cycle",
    "natal_declinations",
    "natal_midpoint_analysis",
    "deep_harmonic_analysis",
    "navamsa_chart",
    "vimshottari_dasa",
    "firdaria_periods",
    "natal_summary_interpretation",
    "eclipses_nearby_birth",
]

# ━━━ GÜNLÜK DEĞİŞEN: TRANSİT ━━━
# Gezegen transit pozisyonları, günlük açılar, transit-natal açılar.
# Her gün değişir → günlük yenilenir.
TRANSIT_KEYS = [
    "transit_info",
    "transit_positions",
    "transit_houses",
    "transit_aspects",
    "transit_azimuth_altitude",
    "transit_to_natal_aspects",
    "eclipses_nearby_current",
]

# ━━━ GÜNLÜK DEĞİŞEN: PROGRESYON + RETURN ━━━
# Progresyonlar yavaş değişir (~1°/ay), return'lar periyodik değişir.
# Basitlik için hepsi günlük yenilenir (transit ile birlikte).
DYNAMIC_KEYS = [
    "secondary_progressions",
    "progressed_houses",
    "progressed_aspects",
    "progressed_moon_phase",
    "solar_arc_progressions",
    "solar_return_chart",
    "lunar_return_chart",
]


def _sanitize_for_firestore(data: Any) -> Any:
    """
    Firestore'a yazılmadan önce veriyi temizle.
    - datetime/date/time → string
    - bytes → string  
    - NaN/Inf → None
    - Büyük nested dict'ler JSON string olarak sakla
    """
    if data is None:
        return None
    
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    
    if isinstance(data, time):
        return data.strftime("%H:%M:%S")
    
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    
    if isinstance(data, float):
        import math
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    
    if isinstance(data, dict):
        return {str(k): _sanitize_for_firestore(v) for k, v in data.items()}
    
    if isinstance(data, (list, tuple)):
        return [_sanitize_for_firestore(item) for item in data]
    
    return data


def _split_large_data(data: dict, prefix: str = "") -> Dict[str, str]:
    """
    Firestore document boyut limiti 1MB.
    Büyük natal data'yı parçalara ayır ve JSON string olarak sakla.
    """
    result = {}
    for key, value in data.items():
        json_str = json.dumps(value, ensure_ascii=False, default=str)
        result[key] = json_str
    return result


def _reassemble_data(stored: dict, keys: list) -> dict:
    """
    Firestore'dan okunan JSON string'leri geri dict'e çevir.
    """
    result = {}
    for key in keys:
        if key in stored:
            try:
                if isinstance(stored[key], str):
                    result[key] = json.loads(stored[key])
                else:
                    result[key] = stored[key]
            except (json.JSONDecodeError, TypeError):
                result[key] = stored[key]
    return result


# ═══════════════════════════════════════════════════════════════
# ANA FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════

def get_natal_chart(birth_date: str, birth_time: str, lat: float, lon: float) -> Optional[dict]:
    """
    Firestore'dan saklı natal chart verisini getir.
    
    Returns:
        dict veya None (bulunamazsa)
    """
    db = _get_db()
    if not db:
        logger.debug("[ChartDB] Firestore bağlantısı yok, natal cache atlanıyor")
        return None
    
    natal_key = _make_natal_key(birth_date, birth_time, lat, lon)
    
    try:
        doc = db.collection("natal_charts").document(natal_key).get()
        if doc.exists:
            stored = doc.to_dict() or {}
            natal_data = _reassemble_data(stored, NATAL_KEYS)
            logger.info(f"[ChartDB] ✅ Natal chart CACHE HIT: {natal_key}")
            return natal_data
        else:
            logger.debug(f"[ChartDB] Natal chart bulunamadı: {natal_key}")
            return None
    except Exception as e:
        logger.error(f"[ChartDB] Natal chart okuma hatası: {e}")
        return None


def save_natal_chart(birth_date: str, birth_time: str, lat: float, lon: float, 
                     astro_data: dict) -> bool:
    """
    Natal chart verisini Firestore'a kaydet (SONSUZA KADAR).
    Sadece NATAL_KEYS'deki verileri saklar.
    """
    db = _get_db()
    if not db:
        logger.debug("[ChartDB] Firestore bağlantısı yok, natal kayıt atlanıyor")
        return False
    
    natal_key = _make_natal_key(birth_date, birth_time, lat, lon)
    
    try:
        # Sadece natal key'leri al
        natal_data = {}
        for key in NATAL_KEYS:
            if key in astro_data:
                natal_data[key] = astro_data[key]
        
        if not natal_data:
            logger.warning("[ChartDB] Kaydedilecek natal veri yok!")
            return False
        
        # Firestore'a uyumlu hale getir
        sanitized = _sanitize_for_firestore(natal_data)
        
        # JSON string olarak sakla (boyut optimizasyonu)
        doc_data = _split_large_data(sanitized)
        doc_data["_created_at"] = datetime.utcnow().isoformat()
        doc_data["_birth_date"] = str(birth_date)
        doc_data["_birth_time"] = str(birth_time)
        doc_data["_lat"] = str(float(lat))
        doc_data["_lon"] = str(float(lon))
        
        db.collection("natal_charts").document(natal_key).set(doc_data)
        logger.info(f"[ChartDB] ✅ Natal chart KAYDEDILDI: {natal_key} ({len(natal_data)} key)")
        return True
        
    except Exception as e:
        logger.error(f"[ChartDB] Natal chart kayıt hatası: {e}", exc_info=True)
        return False


def get_daily_transit(transit_date: str, lat: float, lon: float,
                      birth_date: str, birth_time: str) -> Optional[dict]:
    """
    Günlük transit verisini Firestore'dan getir.
    Transit + Progresyon + Return verilerini içerir.
    
    Key, natal bilgiyi de içerir çünkü transit_to_natal_aspects natal'e bağlıdır.
    """
    db = _get_db()
    if not db:
        return None
    
    natal_key = _make_natal_key(birth_date, birth_time, lat, lon)
    transit_key = f"{natal_key}_{transit_date}"
    
    try:
        doc = db.collection("daily_transits").document(transit_key).get()
        if doc.exists:
            stored = doc.to_dict() or {}
            
            # Tarih kontrolü - bugünün verisi mi?
            stored_date = stored.get("_transit_date", "")
            if stored_date != transit_date:
                logger.debug(f"[ChartDB] Transit verisi eski: {stored_date} != {transit_date}")
                return None
            
            all_dynamic_keys = TRANSIT_KEYS + DYNAMIC_KEYS
            transit_data = _reassemble_data(stored, all_dynamic_keys)
            logger.info(f"[ChartDB] ✅ Transit CACHE HIT: {transit_key}")
            return transit_data
        else:
            logger.debug(f"[ChartDB] Transit bulunamadı: {transit_key}")
            return None
    except Exception as e:
        logger.error(f"[ChartDB] Transit okuma hatası: {e}")
        return None


def save_daily_transit(transit_date: str, lat: float, lon: float,
                       birth_date: str, birth_time: str, 
                       astro_data: dict) -> bool:
    """
    Günlük transit verisini Firestore'a kaydet.
    Transit + Progresyon + Return + transit_to_natal_aspects saklar.
    """
    db = _get_db()
    if not db:
        return False
    
    natal_key = _make_natal_key(birth_date, birth_time, lat, lon)
    transit_key = f"{natal_key}_{transit_date}"
    
    try:
        all_dynamic_keys = TRANSIT_KEYS + DYNAMIC_KEYS
        transit_data = {}
        for key in all_dynamic_keys:
            if key in astro_data:
                transit_data[key] = astro_data[key]
        
        if not transit_data:
            return False
        
        sanitized = _sanitize_for_firestore(transit_data)
        doc_data = _split_large_data(sanitized)
        doc_data["_transit_date"] = transit_date
        doc_data["_created_at"] = datetime.utcnow().isoformat()
        doc_data["_natal_key"] = natal_key
        
        db.collection("daily_transits").document(transit_key).set(doc_data)
        logger.info(f"[ChartDB] ✅ Daily transit KAYDEDILDI: {transit_key}")
        return True
        
    except Exception as e:
        logger.error(f"[ChartDB] Transit kayıt hatası: {e}", exc_info=True)
        return False


# ═══════════════════════════════════════════════════════════════
# ANA ORKESTRATÖR: Akıllı Hesaplama
# ═══════════════════════════════════════════════════════════════

def smart_calculate(birth_date, birth_time, latitude, longitude, 
                    transit_info=None, house_system=b"P", elevation_m=0) -> dict:
    """
    Akıllı hesaplama orkestratörü.
    
    1. Natal veri Firestore'da var mı? → Varsa kullan, yoksa hesapla + kaydet
    2. Bugünün transit verisi var mı? → Varsa kullan, yoksa hesapla + kaydet
    3. İkisini birleştirip döndür
    
    Sonuç: İlk istek ~3-5s, sonraki istekler ~0.1-0.3s
    """
    from services.astro_service import calculate_astro_data
    
    # String'e normalize et
    birth_date_str = str(birth_date)
    birth_time_str = str(birth_time)
    lat = float(latitude)
    lon = float(longitude)
    
    # Transit tarihini belirle
    if transit_info and transit_info.get("date"):
        transit_date_str = transit_info["date"]
    else:
        transit_date_str = datetime.now().strftime("%Y-%m-%d")
    
    natal_key = _make_natal_key(birth_date_str, birth_time_str, lat, lon)
    
    # ═══ ADIM 1: KALICI + GÜNLÜK VERİYİ KONTROL ET ═══
    cached_natal = get_natal_chart(birth_date_str, birth_time_str, lat, lon)
    cached_transit = get_daily_transit(
        transit_date_str, lat, lon, birth_date_str, birth_time_str
    )
    
    # Her ikisi de varsa → cache'den döndür (EN HIZLI YOL)
    if cached_natal and cached_transit:
        logger.info(f"[ChartDB] ⚡ FULL CACHE HIT - Hesaplama atlanıyor!")
        result = {}
        result.update(cached_natal)
        result.update(cached_transit)
        result["_cache_status"] = "full_hit"
        result["_natal_key"] = natal_key
        return result
    
    # ═══ ADIM 2: EN AZ BİR VERİ EKSİK → HESAPLA ═══
    logger.info(f"[ChartDB] 🔄 Hesaplama gerekli - Kalıcı: {'HIT' if cached_natal else 'MISS'}, Günlük: {'HIT' if cached_transit else 'MISS'}")
    
    # Tam hesaplama yap
    astro_data = calculate_astro_data(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation_m,
        house_system=house_system,
        transit_info=transit_info,
    )
    
    if not astro_data or "error" in astro_data:
        return astro_data
    
    # ═══ ADIM 3: SONUÇLARI DEPOLA ═══
    # Kalıcı (natal) verisini kaydet (yoksa)
    if not cached_natal:
        save_natal_chart(birth_date_str, birth_time_str, lat, lon, astro_data)
    
    # Günlük (transit+progresyon+return) verisini kaydet (yoksa veya eski ise)
    if not cached_transit:
        save_daily_transit(
            transit_date_str, lat, lon, 
            birth_date_str, birth_time_str, astro_data
        )
    
    astro_data["_cache_status"] = "calculated_and_saved"
    astro_data["_natal_key"] = natal_key
    
    return astro_data


def cleanup_old_transits(days_old: int = 7) -> int:
    """
    Eski transit verilerini temizle (opsiyonel bakım fonksiyonu).
    days_old gün öncesinden eski transit'ler silinir.
    """
    db = _get_db()
    if not db:
        return 0
    
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        
        old_docs = (
            db.collection("daily_transits")
            .where("_created_at", "<", cutoff)
            .limit(100)
            .stream()
        )
        
        deleted = 0
        for doc in old_docs:
            doc.reference.delete()
            deleted += 1
        
        if deleted > 0:
            logger.info(f"[ChartDB] 🧹 {deleted} eski transit verisi temizlendi")
        return deleted
        
    except Exception as e:
        logger.error(f"[ChartDB] Transit temizleme hatası: {e}")
        return 0
