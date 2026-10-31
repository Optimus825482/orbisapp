"""
Kullanım Takip Sistemi - REKLAM ZORUNLU STRATEJİ
- Tüm kullanıcılar ücretsiz
- Her analiz için rewarded ad izleme ZORUNLU
- Admin/Preminum yok
"""
from datetime import datetime, date, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)


class UsageTracker:
    """Kullanıcı kullanım takibi - Kozmik Kredi & 24h Reklamsız Pass Destekli"""

    # In-memory storage (fallback)
    _memory_storage = {}

    def __init__(self, storage_path=None, use_supabase=True):
        self.storage_path = storage_path or "instance/usage_data.json"
        self.use_supabase = use_supabase and self._init_supabase()
        self.use_memory = not self.use_supabase

        # Local development için file storage dene
        if not self.use_supabase:
            try:
                self._ensure_storage()
            except:
                self.use_memory = True

    def _init_supabase(self) -> bool:
        """Firestore bağlantısını başlat"""
        try:
            from services.firebase_service import firebase_service
            if firebase_service and firebase_service.db:
                self.db = firebase_service.db
                return True
        except Exception as e:
            logger.error(f"[UsageTracker] Firestore init hatası: {e}")
        return False

    def _ensure_storage(self):
        """Storage dosyasını oluştur (sadece local)"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            if not os.path.exists(self.storage_path):
                with open(self.storage_path, 'w') as f:
                    json.dump({}, f)
        except:
            self.use_memory = True

    def _load_data(self):
        """Veriyi yükle (Firestore, memory veya file)"""
        if self.use_supabase:
            return {}
        if self.use_memory:
            return self._memory_storage
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_data(self, data):
        """Veriyi kaydet (Firestore, memory veya file)"""
        if self.use_supabase:
            return
        if self.use_memory:
            self._memory_storage = data
        else:
            try:
                with open(self.storage_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except:
                self._memory_storage = data

    def _parse_ad_free_status(self, user_data: dict) -> tuple[bool, int]:
        """Kullanıcının 24 saatlik reklamsız pass'i aktif mi ve kaç saniyesi kaldı hesaplar."""
        ad_free_until_str = user_data.get("ad_free_until")
        if not ad_free_until_str:
            return False, 0
        try:
            until_dt = datetime.fromisoformat(ad_free_until_str)
            now = datetime.now()
            diff = (until_dt - now).total_seconds()
            if diff > 0:
                return True, int(diff)
        except Exception as e:
            logger.debug(f"[UsageTracker] ad_free_until parse error: {e}")
        return False, 0

    def get_user_usage(self, device_id: str, email: str = None) -> dict:
        """Kullanıcının bugünkü kullanımını, kredisini ve reklamsız mod durumunu getir"""
        today = date.today().isoformat()
        now = datetime.now()

        # Firestore'dan oku
        if self.use_supabase:
            try:
                doc_ref = self.db.collection('usage_tracking').document(device_id)
                doc = doc_ref.get()
                if doc.exists:
                    user_data = doc.to_dict()
                else:
                    # Yeni kullanıcı oluştur - 2 hoş geldin kredisi tanımla
                    user_data = {
                        "device_id": device_id,
                        "email": email,
                        "usage": {},
                        "cosmic_credits": 2,
                        "ad_free_until": None,
                        "created_at": now.isoformat()
                    }
                    doc_ref.set(user_data)
            except Exception as e:
                logger.debug(f"[UsageTracker] Firestore error: {e}")
                user_data = self._memory_storage.get(device_id, {
                    "usage": {},
                    "cosmic_credits": 2,
                    "ad_free_until": None
                })
        else:
            data = self._load_data()
            if device_id not in data:
                data[device_id] = {
                    "usage": {},
                    "cosmic_credits": 2,
                    "ad_free_until": None,
                    "created_at": now.isoformat()
                }
                self._save_data(data)
            user_data = data[device_id]

        today_usage = user_data.get("usage", {}).get(today, 0)
        credits = user_data.get("cosmic_credits")
        if credits is None:
            credits = 2  # Geriye uyumluluk: eski kayıtlara 2 kredi tanımla

        is_ad_free, ad_free_seconds = self._parse_ad_free_status(user_data)

        # Eğer reklamsız pass aktifse reklam gösterme zorunluluğu yok
        requires_ad = not is_ad_free and (credits <= 0)

        result = {
            "device_id": device_id,
            "today_usage": today_usage,
            "cosmic_credits": int(credits),
            "is_ad_free": is_ad_free,
            "ad_free_until": user_data.get("ad_free_until"),
            "ad_free_seconds": ad_free_seconds,
            "daily_limit": 0,
            "remaining": "unlimited" if is_ad_free else credits,
            "is_premium": is_ad_free,
            "show_ads": not is_ad_free,
            "requires_ad": requires_ad,
            "last_ad_watch": user_data.get("last_ad_watch")
        }

        return result

    def can_use_feature(self, device_id: str, feature: str = "ad_watch", email: str = None) -> dict:
        """
        Kullanıcı özelliği kullanabilir mi?
        - 24 saatlik Reklamsız Mod aktifse: Doğrudan izin verilir.
        - Kozmik Kredisi varsa (> 0): Kredi harcayarak doğrudan başlanabilir.
        - Hiçbiri yoksa: 1 video izleyerek veya kredi kazanarak devam edebilir.
        """
        usage = self.get_user_usage(device_id, email)
        is_ad_free = usage.get("is_ad_free", False)
        credits = usage.get("cosmic_credits", 0)

        if is_ad_free:
            return {
                "allowed": True,
                "requires_ad": False,
                "is_ad_free": True,
                "ad_free_seconds": usage.get("ad_free_seconds", 0),
                "cosmic_credits": credits,
                "message": "Reklamsız mod aktif"
            }

        if credits > 0:
            return {
                "allowed": True,
                "requires_ad": False,
                "can_spend_credit": True,
                "cosmic_credits": credits,
                "is_ad_free": False,
                "message": f"{credits} Kozmik Krediniz var. Kredi harcanarak açılabilir."
            }

        return {
            "allowed": True,
            "requires_ad": True,
            "can_spend_credit": False,
            "cosmic_credits": 0,
            "is_ad_free": False,
            "message": "Devam etmek için reklam izleyebilir veya kredi kazanabilirsiniz."
        }

    def claim_reward(self, device_id: str, reward_type: str = "credits", email: str = None) -> dict:
        """
        Ödül tanımla (kullanıcı reklam izledi):
        - reward_type == 'credits': +2 Kozmik Kredi ekler.
        - reward_type == 'ad_free_24h': 24 saat reklamsız pass verir/uzatır.
        """
        now = datetime.now()
        user_usage = self.get_user_usage(device_id, email)
        cur_credits = user_usage.get("cosmic_credits", 2)
        cur_until_str = user_usage.get("ad_free_until")

        new_credits = cur_credits
        new_until = None
        message = ""

        if reward_type == "ad_free_24h":
            base_time = now
            if cur_until_str:
                try:
                    cur_until_dt = datetime.fromisoformat(cur_until_str)
                    if cur_until_dt > now:
                        base_time = cur_until_dt
                except Exception:
                    pass
            new_until_dt = base_time + timedelta(hours=24)
            new_until = new_until_dt.isoformat()
            message = "24 Saat Reklamsız Mod başarıyla aktifleştirildi! 🛡️"
        else:
            reward_type = "credits"
            new_credits = cur_credits + 2
            message = "+2 Kozmik Kredi hesabınıza eklendi! ⭐"

        # Kaydet
        if self.use_supabase:
            try:
                doc_ref = self.db.collection('usage_tracking').document(device_id)
                update_fields = {
                    "last_ad_watch": now.isoformat(),
                    "updated_at": now.isoformat()
                }
                if reward_type == "credits":
                    update_fields["cosmic_credits"] = new_credits
                elif reward_type == "ad_free_24h":
                    update_fields["ad_free_until"] = new_until
                doc_ref.set(update_fields, merge=True)
            except Exception as e:
                logger.error(f"[UsageTracker] claim_reward Firestore error: {e}")
        else:
            data = self._load_data()
            if device_id not in data:
                data[device_id] = {}
            data[device_id]["last_ad_watch"] = now.isoformat()
            if reward_type == "credits":
                data[device_id]["cosmic_credits"] = new_credits
            elif reward_type == "ad_free_24h":
                data[device_id]["ad_free_until"] = new_until
            self._save_data(data)

        updated_usage = self.get_user_usage(device_id, email)
        return {
            "success": True,
            "reward_type": reward_type,
            "message": message,
            "cosmic_credits": updated_usage.get("cosmic_credits", 0),
            "is_ad_free": updated_usage.get("is_ad_free", False),
            "ad_free_seconds": updated_usage.get("ad_free_seconds", 0),
            "ad_free_until": updated_usage.get("ad_free_until")
        }

    def spend_credit(self, device_id: str, amount: int = 1, feature: str = "analysis", email: str = None) -> dict:
        """
        Kozmik Kredi harca (analiz veya özellik kilidi açmak için).
        - Reklamsız pass aktifse kredi düşmeden izin verilir.
        - Yeterli kredi varsa 1 düşülür.
        - Kredi yoksa hata döner.
        """
        now = datetime.now()
        user_usage = self.get_user_usage(device_id, email)
        is_ad_free = user_usage.get("is_ad_free", False)
        cur_credits = user_usage.get("cosmic_credits", 0)

        # Reklamsız moddaysa kredi düşmeye gerek yok
        if is_ad_free:
            return {
                "success": True,
                "spent": 0,
                "is_ad_free": True,
                "cosmic_credits": cur_credits,
                "message": "Reklamsız mod aktif, kredi harcanmadı."
            }

        if cur_credits < amount:
            return {
                "success": False,
                "error": "INSUFFICIENT_CREDITS",
                "cosmic_credits": cur_credits,
                "message": "Yetersiz Kozmik Kredi. Video izleyerek hemen kredi kazanabilirsiniz."
            }

        new_credits = max(0, cur_credits - amount)

        # Kaydet
        if self.use_supabase:
            try:
                doc_ref = self.db.collection('usage_tracking').document(device_id)
                doc_ref.set({
                    "cosmic_credits": new_credits,
                    "updated_at": now.isoformat()
                }, merge=True)
            except Exception as e:
                logger.error(f"[UsageTracker] spend_credit Firestore error: {e}")
        else:
            data = self._load_data()
            if device_id in data:
                data[device_id]["cosmic_credits"] = new_credits
                self._save_data(data)

        return {
            "success": True,
            "spent": amount,
            "is_ad_free": False,
            "cosmic_credits": new_credits,
            "message": f"{amount} Kozmik Kredi harcandı."
        }

    def record_usage(self, device_id: str, feature: str = "ad_watch", email: str = None) -> dict:
        """
        Kullanımı kaydet (reklam izleme)
        """
        today = date.today().isoformat()
        now = datetime.now()

        if self.use_supabase:
            try:
                doc_ref = self.db.collection('usage_tracking').document(device_id)
                doc = doc_ref.get()

                if doc.exists:
                    user_data = doc.to_dict()
                else:
                    user_data = {
                        "device_id": device_id,
                        "email": email,
                        "usage": {},
                        "cosmic_credits": 2,
                        "ad_free_until": None,
                        "created_at": now.isoformat()
                    }

                if "usage" not in user_data:
                    user_data["usage"] = {}
                old_usage = user_data["usage"].get(today, 0)
                user_data["usage"][today] = old_usage + 1
                user_data["last_ad_watch"] = now.isoformat()
                user_data["updated_at"] = now.isoformat()

                doc_ref.set(user_data)

            except Exception as e:
                logger.debug(f"[UsageTracker] Firestore error: {e}")
                if device_id not in self._memory_storage:
                    self._memory_storage[device_id] = {"usage": {}, "cosmic_credits": 2, "ad_free_until": None}
                if today not in self._memory_storage[device_id].get("usage", {}):
                    self._memory_storage[device_id]["usage"][today] = 0
                self._memory_storage[device_id]["usage"][today] += 1
                self._memory_storage[device_id]["last_ad_watch"] = now.isoformat()
        else:
            data = self._load_data()

            if device_id not in data:
                data[device_id] = {"usage": {}, "cosmic_credits": 2, "ad_free_until": None}

            if "usage" not in data[device_id]:
                data[device_id]["usage"] = {}

            if today not in data[device_id]["usage"]:
                data[device_id]["usage"][today] = 0

            data[device_id]["usage"][today] += 1
            data[device_id]["last_ad_watch"] = now.isoformat()

            self._save_data(data)

        result = self.get_user_usage(device_id, email)
        return result
