"""
ORBIS Stats Counter Service
- Firestore stats/dashboard dokumanini yonetir
- Her kullanici isleminde counter'lari gunceller
- Admin dashboard sayfalama icin optimize edilmistir
- PREMIUM YOK: Uygulama tamamen ucretsiz, sadece reklam destekli
"""
import logging
import time
from datetime import datetime
from typing import Optional
from functools import wraps

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

# Field yollari (premium kaldirildi)
FIELD_TOTAL_USERS = "total_users"
FIELD_TOTAL_ANALYSES = "total_analyses"
FIELD_ACTIVE_TODAY = "active_today"
FIELD_TOTAL_ADS_WATCHED = "total_ads_watched"
FIELD_TOTAL_REWARDED_ADS = "total_rewarded_ads"

# Heartbeat throttling: aynı kullanıcı için 30 saniyede 1 yazma
HEARTBEAT_THROTTLE_SECONDS = 30
_last_heartbeat_times = {}


def retry_on_deadline(max_retries=3, timeout_seconds=5):
    """Firestore 504 Deadline Exceeded hatalarını retry eden decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e)
                    if "504" in error_msg or "Deadline Exceeded" in error_msg or "DEADLINE_EXCEEDED" in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                            logger.warning(f"[Stats] Deadline exceeded, retry {attempt + 1}/{max_retries} after {wait_time}s")
                            time.sleep(wait_time)
                            continue
                    # Başka hata veya max retry aşıldı
                    raise
            return None
        return wrapper
    return decorator


class StatsCounter:
    """Firestore counter yonetimi - her islemde sadece ilgili field'i gunceller"""

    def __init__(self):
        self.db = None
        self._init_db()

    def _init_db(self):
        try:
            from services.firebase_service import firebase_service
            self.db = firebase_service.db
        except Exception as e:
            logger.error(f"[Stats] DB init error: {e}")

    @property
    def _doc(self):
        """stats/dashboard dokuman referansi"""
        if not self.db:
            return None
        return self.db.collection("stats").document("dashboard")

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def _increment(self, field: str, amount: int = 1):
        """Bir counter field'ini Increment ile guncelle"""
        if not self.db:
            return
        try:
            from firebase_admin import firestore
            self._doc.update({field: firestore.Increment(amount)})
        except Exception as e:
            logger.error(f"[Stats] Increment error ({field}): {e}")

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def _set_active_today(self, count: int):
        """active_today degerini dogrudan set et (gu sonu sifirlanir)"""
        if not self.db:
            return
        try:
            self._doc.update({FIELD_ACTIVE_TODAY: count})
        except Exception as e:
            logger.error(f"[Stats] set_active_today error: {e}")

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def _increment_today_counter(self, field: str):
        """Bugünlük counter: gün değiştiyse sıfırla, sonra Increment.

        Her çağrıda doc'tan _today_date kontrol edilir, farklıysa 0'a set edilir.
        Aynı gün içinde Increment yapılır.
        """
        if not self.db:
            return
        try:
            from datetime import datetime
            from firebase_admin import firestore
            today = datetime.now().strftime("%Y-%m-%d")
            doc = self._doc.get()
            data = doc.to_dict() or {}
            cur_date = data.get(f'{field}_date')
            doc_ref = self._doc
            if cur_date != today:
                # Gün değişti — sıfırla ve yeni tarihi yaz
                doc_ref.update({field: 0, f'{field}_date': today, field: firestore.Increment(1)})
            else:
                doc_ref.update({field: firestore.Increment(1)})
        except Exception as e:
            logger.error(f"[Stats] today counter error ({field}): {e}")

    # ═══════════════════════════════════════════════════════════════
    # PUBLIC API - Kullanici islemleri (Premium'suz)
    # ═══════════════════════════════════════════════════════════════

    def on_user_created(self, is_premium: bool = False):
        """Yeni kullanici olustu (premium arg ignored, geriye uyumluluk)"""
        # is_premium arg no-op: artik herkes ucretsiz kullanici
        self._increment(FIELD_TOTAL_USERS, 1)

    def on_user_deleted(self, was_premium: bool = False, credits: int = 0, analyses: int = 0):
        """Kullanici silindi (premium arg ignored)"""
        self._increment(FIELD_TOTAL_USERS, -1)
        if analyses:
            self._increment(FIELD_TOTAL_ANALYSES, -analyses)

    def on_premium_changed(self, became_premium: bool):
        """DEPRECATED: Premium kaldirildi, no-op"""
        # Geriye uyumluluk icin bos metod
        logger.debug("[Stats] on_premium_changed called but premium is removed (no-op)")

    def on_credits_changed(self, delta: int):
        """DEPRECATED: Krediler kaldirildi, no-op"""
        logger.debug("[Stats] on_credits_changed called but credits are removed (no-op)")

    def on_analysis_completed(self):
        """Analiz yapildi"""
        self._increment(FIELD_TOTAL_ANALYSES, 1)
        self._increment_today_counter('analyses_today')

    def on_ad_watched(self, rewarded: bool = False):
        """Reklam izlendi (banner/interstitial/rewarded)"""
        self._increment(FIELD_TOTAL_ADS_WATCHED, 1)
        if rewarded:
            self._increment(FIELD_TOTAL_REWARDED_ADS, 1)
            self._increment_today_counter('rewarded_ads_today')

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def on_daily_activity(self, today: str):
        """Gunluk aktif kullanici sayisini guncelle"""
        if not self.db:
            return
        try:
            # Bugunku aktif kullanicilari say (select projection ile)
            result = self.db.collection("users").where(
                filter=FieldFilter("dailyUsage.date", "==", today)
            ).count().get()
            count = result[0][0].value
            self._set_active_today(count)
        except Exception:
            # Detaylı stack: hangi sorgu patladığını günlüğe yaz
            import traceback
            logger.error("[Stats] daily_activity failed: %s", traceback.format_exc())

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def on_user_login(self, email: str, display_name: str):
        """Kullanici giris yapti - son login kaydi"""
        if not self.db:
            return
        try:
            now = datetime.now()
            self._doc.update({
                "last_login_email": email,
                "last_login_name": display_name or email,
                "last_login_time": now.isoformat(),
            })
        except Exception as e:
            logger.error(f"[Stats] login tracking error: {e}")

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def on_heartbeat(self, email: str, display_name: str):
        """Aktif kullanici kalp atisi - heartbeat dokumanina yaz

        Throttling: Aynı kullanıcı için 30 saniyede 1 yazma yapılır.
        """
        if not self.db:
            return

        # Throttling kontrolü
        now = time.time()
        last_time = _last_heartbeat_times.get(email, 0)
        if now - last_time < HEARTBEAT_THROTTLE_SECONDS:
            # Son heartbeat'ten beri 30 saniye geçmemiş, skip et
            return

        try:
            from firebase_admin import firestore
            from datetime import datetime, timezone
            # ⚠️ SERVER_TIMESTAMP kullanma - filtrelemede sorun cikarir
            # Gercek timestamp ile yaz, boylece sorgu calisir
            timestamp = datetime.now(timezone.utc).isoformat()
            key = email.replace("@", "_at_").replace(".", "_dot_")
            self.db.collection("stats_heartbeats").document(key).set({
                "email": email,
                "display_name": display_name or email,
                "last_seen": timestamp,
            })
            # Başarılı yazma sonrası throttle cache'ini güncelle
            _last_heartbeat_times[email] = now
        except Exception as e:
            logger.error(f"[Stats] heartbeat error: {e}")

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def get_online_users(self, within_minutes: int = 5) -> list:
        """Son N dakikada heartbeat atan kullanicilar"""
        if not self.db:
            return []
        try:
            from datetime import datetime, timedelta, timezone
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=within_minutes)).isoformat()
            docs = list(self.db.collection("stats_heartbeats")
                        .where(filter=FieldFilter("last_seen", ">=", cutoff))
                        .stream())
            users = []
            for d in docs:
                data = d.to_dict()
                users.append({
                    "email": data.get("email"),
                    "display_name": data.get("display_name"),
                    "last_seen": data.get("last_seen", ""),
                })
            return users
        except Exception as e:
            logger.error(f"[Stats] online error: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════
    # ADMIN DASHBOARD - Hizli okuma (tek dokuman, 1 read)
    # ═══════════════════════════════════════════════════════════════

    @retry_on_deadline(max_retries=3, timeout_seconds=5)
    def get_overview(self) -> Optional[dict]:
        """Dashboard icin tum istatistikleri tek dokumandan oku (SADECE 1 READ)"""
        if not self.db:
            return None

        # ONCE counter dokumanindan oku
        try:
            doc = self._doc.get()
            if doc.exists:
                data = doc.to_dict()
                # Gunluk aktif sayisini guncelle (arka planda)
                self.on_daily_activity(datetime.now().strftime("%Y-%m-%d"))
                return data
        except Exception as e:
            logger.error(f"[Stats] Overview read error: {e}")

        # COUNTER YOKSA fallback: `select()` projection ile sadece gerekli field'lar
        try:
            logger.info("[Stats] Counter dokumani bulunamadi, fallback select() ile okunuyor...")
            docs = list(self.db.collection("users").select([
                "totalAnalyses", "adsWatched", "rewardedAdsWatched", "dailyUsage.date"
            ]).stream())

            total = len(docs)
            analyses = 0
            ads = 0
            rewarded_ads = 0
            today = datetime.now().strftime("%Y-%m-%d")
            active = 0

            for d in docs:
                data = d.to_dict()
                analyses += data.get("totalAnalyses", 0) or 0
                ads += data.get("adsWatched", 0) or 0
                rewarded_ads += data.get("rewardedAdsWatched", 0) or 0
                if data.get("dailyUsage", {}).get("date") == today:
                    active += 1

            return {
                "total_users": total,
                "total_analyses": analyses,
                "total_ads_watched": ads,
                "total_rewarded_ads": rewarded_ads,
                "active_today": active,
            }
        except Exception as e:
            logger.error(f"[Stats] Fallback read error: {e}")
            return None


stats_counter = StatsCounter()
