"""
Abonelik Servisi
- Firestore'dan fiyatları okur (config/pricing)
- Admin panel Firestore'a yazar
- Fallback: varsayılan fiyatlar
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SubscriptionService:
    """Abonelik yönetimi - fiyatlar Firestore'dan gelir"""

    # Varsayılan fiyatlar (Firestore bağlantısı yoksa kullanılır)
    DEFAULT_PRICES = {
        "daily": 30,
        "monthly": 300,
        "yearly": 3000,
    }

    PLANS = {
        "free": {
            "name": "Ücretsiz",
            "price": 0,
            "daily_interpretations": 0,
            "requires_ad": True,
            "features": ["Reklam izleyerek analiz", "Reklam izleyerek AI yorum"]
        },
        "premium_daily": {
            "name": "Premium Günlük",
            "google_product_id": "astro_premium_daily",
            "daily_interpretations": -1,
            "requires_ad": False,
            "features": [
                "Sınırsız analiz",
                "Sınırsız AI yorumu",
                "Reklamsız deneyim",
                "24 saat geçerli"
            ]
        },
        "premium_monthly": {
            "name": "Premium Aylık",
            "google_product_id": "astro_premium_monthly",
            "daily_interpretations": -1,
            "features": [
                "Sınırsız AI yorumu",
                "Detaylı natal analiz",
                "Transit yorumları",
                "Uyumluluk analizi",
                "Reklamsız deneyim"
            ]
        },
        "premium_yearly": {
            "name": "Premium Yıllık",
            "google_product_id": "astro_premium_yearly",
            "daily_interpretations": -1,
            "features": [
                "Tüm premium özellikler",
                "2 ay hediye",
                "Öncelikli destek"
            ]
        }
    }

    # Fiyatları cache'le (bir kere yükle)
    _prices_loaded = False

    def _load_prices(self):
        """Firestore'dan fiyatları yükle"""
        if self._prices_loaded:
            return

        try:
            from services.firebase_service import firebase_service
            db = firebase_service.db

            if db:
                doc = db.collection("config").document("pricing").get()
                if doc.exists:
                    data = doc.to_dict()
                    daily = data.get("daily", self.DEFAULT_PRICES["daily"])
                    monthly = data.get("monthly", self.DEFAULT_PRICES["monthly"])
                    yearly = data.get("yearly", self.DEFAULT_PRICES["yearly"])

                    self.PLANS["premium_daily"]["price"] = float(daily)
                    self.PLANS["premium_monthly"]["price"] = float(monthly)
                    self.PLANS["premium_yearly"]["price"] = float(yearly)

                    logger.info(f"[Subscription] Fiyatlar Firestore'dan yüklendi: d={daily}, m={monthly}, y={yearly}")
                else:
                    self._use_defaults()
            else:
                self._use_defaults()
        except Exception as e:
            logger.error(f"[Subscription] Fiyat yükleme hatası: {e}")
            self._use_defaults()

        self._prices_loaded = True

    def _use_defaults(self):
        """Varsayılan fiyatları kullan"""
        self.PLANS["premium_daily"]["price"] = float(self.DEFAULT_PRICES["daily"])
        self.PLANS["premium_monthly"]["price"] = float(self.DEFAULT_PRICES["monthly"])
        self.PLANS["premium_yearly"]["price"] = float(self.DEFAULT_PRICES["yearly"])

    def get_plans(self):
        """Tüm planları getir (fiyatları Firestore'dan yükle)"""
        self._load_prices()
        return self.PLANS

    def get_plan(self, plan_id: str):
        """Belirli planı getir"""
        self._load_prices()
        return self.PLANS.get(plan_id)
