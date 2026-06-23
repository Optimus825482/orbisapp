"""Firestore'a varsayilan AI provider ayarlarini kaydeder"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore

cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "orbis-ffa9e-firebase-adminsdk-fbsvc-b4ac1afabf.json")
cred = credentials.Certificate(cred_path)
try:
    app = firebase_admin.get_app()
except ValueError:
    app = firebase_admin.initialize_app(cred)
db = firestore.client()

ai_settings = {
    "providers": [
        {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "model": "deepseek-chat",
        },
        {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
            "model": "openrouter/auto",
        },
    ],
    "active_provider": "DeepSeek",
    "backup_1": "OpenRouter",
    "backup_2": "",
    "backup_3": "",
    "updated_at": firestore.SERVER_TIMESTAMP,
    "updated_by": "system_init",
}

db.collection("config").document("ai_settings").set(ai_settings)
print("config/ai_settings Firestore'a yazildi!")

verify = db.collection("config").document("ai_settings").get()
if verify.exists:
    v = verify.to_dict()
    print("Provider sayisi:", len(v.get("providers", [])))
    print("Aktif:", v.get("active_provider"))
    print("Yedek-1:", v.get("backup_1"))
