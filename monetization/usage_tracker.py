"""
Kullanım Takip Sistemi - REKLAM ZORUNLU STRATEJİ
- Tüm kullanıcılar ücretsiz
- Her analiz için rewarded ad izleme ZORUNLU
- Admin/Preminum yok
"""
from datetime import datetime, date
from flask import current_app
import json
import os
import logging

logger = logging.getLogger(__name__)


class UsageTracker:
    """Kullanıcı kullanım takibi - Her işlem için reklam zorunlu"""

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

    def get_user_usage(self, device_id: str, email: str = None) -> dict:
        """Kullanıcının bugünkü kullanımını getir"""
        today = date.today().isoformat()

        # Firestore'dan oku
        if self.use_supabase:
            try:
                doc = self.db.collection('usage_tracking').document(device_id).get()
                if doc.exists:
                    user_data = doc.to_dict()
                else:
                    # Yeni kullanıcı oluştur
                    user_data = {
                        "device_id": device_id,
                        "email": email,
                        "usage": {},
                        "created_at": datetime.now().isoformat()
                    }
                    self.db.collection('usage_tracking').document(device_id).set(user_data)
            except Exception as e:
                logger.debug(f"[UsageTracker] Firestore error: {e}")
                user_data = self._memory_storage.get(device_id, {"usage": {}})
        else:
            data = self._load_data()
            if device_id not in data:
                data[device_id] = {"usage": {}}
                self._save_data(data)
            user_data = data[device_id]

        today_usage = user_data.get("usage", {}).get(today, 0)

        result = {
            "device_id": device_id,
            "today_usage": today_usage,
            "daily_limit": 0,
            "remaining": "requires_ad",
            "is_premium": False,
            "show_ads": True,
            "requires_ad": True,
            "last_ad_watch": user_data.get("last_ad_watch")
        }

        return result

    def can_use_feature(self, device_id: str, feature: str = "ad_watch", email: str = None) -> dict:
        """
        Kullanıcı özelliği kullanabilir mi?
        Tüm kullanıcılar için her işlem reklam ZORUNLU.
        """
        return {
            "allowed": True,
            "reason": "requires_ad",
            "remaining": "requires_ad",
            "show_ads": True,
            "requires_ad": True,
            "message": "Devam etmek için reklam izlemeniz gerekiyor."
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
                    self._memory_storage[device_id] = {"usage": {}}
                if today not in self._memory_storage[device_id].get("usage", {}):
                    self._memory_storage[device_id]["usage"][today] = 0
                self._memory_storage[device_id]["usage"][today] += 1
                self._memory_storage[device_id]["last_ad_watch"] = now.isoformat()
        else:
            data = self._load_data()

            if device_id not in data:
                data[device_id] = {"usage": {}}

            if "usage" not in data[device_id]:
                data[device_id]["usage"] = {}

            if today not in data[device_id]["usage"]:
                data[device_id]["usage"][today] = 0

            data[device_id]["usage"][today] += 1
            data[device_id]["last_ad_watch"] = now.isoformat()

            self._save_data(data)

        result = self.get_user_usage(device_id, email)
        return result
