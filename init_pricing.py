"""
ORBIS - Firestore Fiyat Yapılandırması Başlatma Script'i

Firebase Admin SDK ile Firestore'a config/pricing dokümanını oluşturur.
Fiyatlar daha sonra Admin Panel üzerinden yönetilebilir.

Kullanım:
    cd D:\astro-ai-predictor\backend\flask_app
    pip install firebase-admin
    python scripts\init_pricing.py
"""

import json
import os
import sys
from datetime import datetime

# Flask proje kök dizini
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

def main():
    print("=" * 60)
    print("ORBIS - Firestore Fiyat Yapılandırması")
    print("=" * 60)

    # 1. Firebase Admin SDK'yı başlat
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print("\n❌ firebase-admin paketi yüklü değil!")
        print("   Yüklemek için: pip install firebase-admin")
        sys.exit(1)

    # Credential dosyasının yolunu bul
    cred_path = os.path.join(PROJECT_ROOT, "orbis-ffa9e-firebase-adminsdk-fbsvc-b4ac1afabf.json")
    
    if not os.path.exists(cred_path):
        print(f"\n❌ Credential dosyası bulunamadı: {cred_path}")
        # Alternatif yolları dene
        for alt in [
            "firebase-credentials.json",
            "serviceAccountKey.json",
            os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
        ]:
            if alt and os.path.exists(alt):
                cred_path = alt
                break
        else:
            print("   Lütfen FIREBASE_CREDENTIALS_PATH ortam değişkenini ayarlayın.")
            sys.exit(1)

    print(f"\n📁 Credential dosyası: {cred_path}")

    try:
        with open(cred_path) as f:
            cred_data = json.load(f)
        print(f"📋 Proje: {cred_data.get('project_id', '?')}")
        print(f"📧 Client Email: {cred_data.get('client_email', '?')}")
    except Exception as e:
        print(f"❌ Credential dosyası okunamadı: {e}")
        sys.exit(1)

    # Firebase Admin SDK'yı başlat
    try:
        cred = credentials.Certificate(cred_path)
        try:
            app = firebase_admin.get_app()
            print("ℹ️  Firebase Admin SDK zaten başlatılmış.")
        except ValueError:
            app = firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK başlatıldı.")
        
        db = firestore.client()
        print("✅ Firestore client hazır.")
    except Exception as e:
        print(f"❌ Firebase başlatma hatası: {e}")
        sys.exit(1)

    # 2. Varsayılan fiyatları tanımla
    pricing_data = {
        "daily": 30,
        "monthly": 300,
        "yearly": 3000,
        "currency": "TRY",
        "updated_at": firestore.SERVER_TIMESTAMP,
        "updated_by": "system_init",
        "note": "Varsayılan fiyatlar. Admin panel üzerinden değiştirilebilir."
    }

    print("\n" + "=" * 60)
    print("Kaydedilecek Fiyatlar:")
    print("=" * 60)
    print(f"  Günlük Premium:    ₺{pricing_data['daily']}")
    print(f"  Aylık Premium:     ₺{pricing_data['monthly']}  (~~₺{pricing_data['daily'] * 30}~~ -> %{100 - round(pricing_data['monthly']/(pricing_data['daily']*30)*100)} indirim)")
    print(f"  Yıllık Premium:    ₺{pricing_data['yearly']}  (ayda ₺{round(pricing_data['yearly']/12)})")
    print(f"  Para Birimi:       {pricing_data['currency']}")
    
    print("\n" + "=" * 60)

    # 3. Firestore'a yaz
    doc_ref = db.collection("config").document("pricing")
    
    try:
        # Önce mevcut dokümanı kontrol et
        existing = doc_ref.get()
        
        if existing.exists:
            existing_data = existing.to_dict()
            print(f"\n⚠️  config/pricing dokümanı ZATEN VAR!")
            print(f"   Mevcut fiyatlar:")
            print(f"     Günlük: ₺{existing_data.get('daily', '?')}")
            print(f"     Aylık:  ₺{existing_data.get('monthly', '?')}")
            print(f"     Yıllık: ₺{existing_data.get('yearly', '?')}")
            print(f"     Son güncelleme: {existing_data.get('updated_by', '?')}")
            
            # Kullanıcıya sor
            answer = input("\nÜzerine yazılsın mı? (e/H): ").strip().lower()
            if answer != "e":
                print("\n❌ İşlem iptal edildi. Doküman değiştirilmedi.")
                sys.exit(0)
        
        # Dokümanı yaz
        doc_ref.set(pricing_data)
        
        print(f"\n✅ config/pricing dokümanı başarıyla oluşturuldu/güncellendi!")
        print(f"   Firestore path: config/pricing")
        
        # 4. Doğrulama
        print("\n📝 Doğrulama: Veriyi geri okuyorum...")
        verify = doc_ref.get()
        if verify.exists:
            vdata = verify.to_dict()
            print(f"   ✅ Okuma başarılı!")
            print(f"   📊 Günlük: ₺{vdata.get('daily')}")
            print(f"   📊 Aylık:  ₺{vdata.get('monthly')}")
            print(f"   📊 Yıllık: ₺{vdata.get('yearly')}")
            
            # SERVER_TIMESTAMP'ı göstermek için
            ts = vdata.get('updated_at')
            if hasattr(ts, 'seconds'):
                dt = datetime.fromtimestamp(ts.seconds)
                print(f"   🕐 Güncelleme: {dt.strftime('%d.%m.%Y %H:%M:%S')}")
            
        print("\n" + "=" * 60)
        print("✅ TAMAM! Artık admin panelden fiyatları yönetebilirsiniz.")
        print("   Adres: https://app.orbisastro.online/admin/pricing")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Firestore yazma hatası: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
