"""
Flask App - Factory Pattern

Ana uygulama modülü. create_app() fonksiyonu tüm Flask uygulamasını oluşturur.
Bu dosyadan import yaparak veya doğrudan `python app.py` ile çalıştırılabilir.
"""
from __init__ import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5006)
