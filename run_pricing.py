"""Run this: cd D:\astro-ai-predictor\backend\flask_app && python scripts\run_pricing.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("firebase-admin not installed. Run: pip install firebase-admin")
    sys.exit(1)

cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                         "orbis-ffa9e-firebase-adminsdk-fbsvc-b4ac1afabf.json")
print(f"Credential: {cred_path}")
print(f"Exists: {os.path.exists(cred_path)}")

cred = credentials.Certificate(cred_path)
try:
    app = firebase_admin.get_app()
except ValueError:
    app = firebase_admin.initialize_app(cred)
    
db = firestore.client()
print("Firestore client ready ✓")

pricing_data = {
    "daily": 30,
    "monthly": 300,
    "yearly": 3000,
    "currency": "TRY",
    "updated_at": firestore.SERVER_TIMESTAMP,
    "updated_by": "system_init",
}

doc_ref = db.collection("config").document("pricing")
doc_ref.set(pricing_data)
print("✅ config/pricing Firestore'a yazıldı!")

verify = doc_ref.get()
if verify.exists:
    v = verify.to_dict()
    print(f"   Günlük: ₺{v.get('daily')}")
    print(f"   Aylık:  ₺{v.get('monthly')}")
    print(f"   Yıllık: ₺{v.get('yearly')}")
    print(f"   Kaydeden: {v.get('updated_by')}")
    print("✅ TAMAM!")
