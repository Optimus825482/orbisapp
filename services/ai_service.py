"""
ORBIS AI Service
- Firestore'dan provider ayarlarını okur (config/ai_settings)
- Sıralı yedekleme: Aktif -> Y-1 -> Y-2 -> Y-3
- Async HTTP çağrıları
"""
import os
import json
import logging
import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

import aiohttp
from openai import OpenAI

from extensions import cache
from utils import Constants

logger = logging.getLogger(__name__)


class AIService:
    BASE_RULES = """
## KESİN KURALLAR — TÜM YORUMLAR İÇİN BAĞLAYICI

### 1. YASAK TERİMLER (ASLA KULLANMA — TEKNİK TERIM SIFIR TOLERANS)
Aşağıdaki terimler çıktıda HİÇBİR KOŞULDA geçmeyecek:
- Gezegen adları: Mars, Venüs, Satürn, Jüpiter, Merkür, Uranüs, Neptün, Plüton
  (Ay ve Güneş de dahil — bunlar yerine "duygusal enerji", "yaşam enerjisi" gibi ifadeler kullan)
- Burç adları: Koç, Boğa, İkizler, Yengeç, Aslan, Başak, Terazi, Akrep, Yay, Oğlak, Kova, Balık
- Ev numaraları: "1. ev", "7. ev", "10. ev" vb.
- Açı adları: kavuşum, karşıt, üçgen, kare, altmışlık, sextile, trine, opposition, conjunction
- Teknik terimler: transit, natal, ascendant, midheaven, Chiron, Lilith, Dasha, Antardasha,
  Mahadasha, Nakshatra, Navamsa, Firdaria, Kronokrator, antiscia, midpoint, dignity,
  declination, progresyon, düğüm, retrograd, harmonic, orb, cusp, yükselen, alçalan

### 2. ÇEVRESEL DÖNÜŞÜM KURALI
Yukarıdaki terimleri DOĞRUDAN kullanma; bunun yerine etkiyi ve enerjiyi ANLAT:
- "Satürn" → "yapısal baskı", "sorumluluk enerjisi", "olgunlaştırıcı güç"
- "Venüs transiti" → "ilişki alanındaki aktif enerji"
- "kare açısı" → "gerilim ve zorlayıcı dinamik"
- "12. ev" → "bilinçaltı alanı", "içe dönük enerji bölgesi"
- "Dasha dönemi" → "aktif dönem enerjisi", "yaşam döngüsünün şu anki tonu"

### 3. DİL VE ÜSLUP
- Sade, anlaşılır Türkçe — teknik bilgisi olmayan biri okuyup anlayabilmeli
- Doğrudan ve somut ifadeler — soyut ezoterik dil YASAK
- Kişiye adıyla hitap et, samimi ama profesyonel

### 4. UZUNLUK
- 500-800 kelime arası; ne daha uzun ne daha kısa
- Her başlık 1-2 paragraf — tekrar ve dolgu yok

### 5. TAVSİYE YASAĞI (İSTİSNASIZ)
- "yapmalısın", "kaçınmalısın", "odaklanmalısın", "dikkat et", "önerim şu" YASAK
- Görev: tabloyu TANIMLA ve YORUMLA, yönlendirme YAPMA
- Doğru → "Bu alanda yoğun ve zorlayıcı bir enerji aktif."
- Yanlış → "Bu alanda dikkatli olmalısın." (TAVSİYE — YASAK)
"""

    # ════════════════════════════════════════════════════════════════════
    # VERİ FİLTRELEME — hesaplamalar → 18 analiz türü
    # Her hesaplama en az 1 analiz türünde kullanılır, hiçbiri boşa gitmez.
    # ════════════════════════════════════════════════════════════════════
    DATA_FILTER = {
        "birth_chart": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "natal_dignity_scores", "natal_declinations",
            "natal_midpoint_analysis", "navamsa_chart",
            "vimshottari_dasa", "firdaria_periods",
            "eclipses_nearby_birth", "natal_lunation_cycle",
            "natal_fixed_stars",
        ],
        "relationship": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "natal_antiscia", "natal_dignity_scores",
            "natal_arabic_parts", "natal_declinations",
            "natal_midpoint_analysis", "navamsa_chart",
            "natal_lunation_cycle", "natal_fixed_stars",
            "natal_part_of_fortune",
        ],
        "psychological_karmic": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "natal_dignity_scores", "natal_declinations",
            "natal_midpoint_analysis", "deep_harmonic_analysis",
            "natal_lunation_cycle", "natal_fixed_stars",
            "vimshottari_dasa", "firdaria_periods",
            "eclipses_nearby_birth", "natal_antiscia",
        ],
        "daily": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "transit_positions", "transit_to_natal_aspects",
            "natal_aspects", "natal_additional_points",
            "natal_lunation_cycle", "eclipses_nearby_current",
        ],
        "transits": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "transit_positions", "transit_to_natal_aspects",
            "solar_return_chart", "lunar_return_chart",
            "natal_aspects", "natal_declinations",
            "eclipses_nearby_current", "natal_lunation_cycle",
            "firdaria_periods", "natal_fixed_stars",
        ],
        "short_term": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "transit_positions", "transit_to_natal_aspects",
            "solar_return_chart", "lunar_return_chart",
            "natal_aspects", "natal_additional_points",
            "eclipses_nearby_current", "natal_lunation_cycle",
            "firdaria_periods",
        ],
        "long_term": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "transit_positions", "transit_to_natal_aspects",
            "vimshottari_dasa", "firdaria_periods",
            "solar_return_chart", "deep_harmonic_analysis",
            "eclipses_nearby_current", "natal_lunation_cycle",
            "natal_aspects",
        ],
        "career": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_dignity_scores",
            "natal_midpoint_analysis", "natal_fixed_stars",
            "solar_return_chart", "firdaria_periods",
            "transit_positions", "transit_to_natal_aspects",
            "natal_arabic_parts",
        ],
        "health": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "natal_fixed_stars", "natal_declinations",
            "solar_return_chart", "transit_positions",
            "transit_to_natal_aspects", "natal_lunation_cycle",
        ],
        "finance": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_arabic_parts",
            "natal_part_of_fortune", "natal_dignity_scores",
            "solar_return_chart", "transit_positions",
            "transit_to_natal_aspects",
        ],
        "spiritual": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "deep_harmonic_analysis",
            "navamsa_chart", "vimshottari_dasa",
            "natal_lunation_cycle", "natal_fixed_stars",
            "natal_antiscia", "natal_declinations",
            "natal_midpoint_analysis",
        ],
        "summary": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_summary_interpretation", "transit_positions",
            "transit_to_natal_aspects",
        ],
        # ── YENİ TÜRLER ──────────────────────────────────────────────
        "vedic": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "vimshottari_dasa", "firdaria_periods",
            "navamsa_chart", "deep_harmonic_analysis",
            "natal_dignity_scores", "natal_lunation_cycle",
            "natal_fixed_stars",
        ],
        "eclipses": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "eclipses_nearby_birth", "eclipses_nearby_current",
            "transit_positions", "transit_to_natal_aspects",
            "natal_lunation_cycle",
        ],
        "harmonic": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "deep_harmonic_analysis",
            "navamsa_chart", "natal_midpoint_analysis",
            "natal_antiscia", "natal_declinations",
            "natal_dignity_scores",
        ],
        "esoteric": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "natal_antiscia", "natal_arabic_parts",
            "natal_declinations", "natal_part_of_fortune",
            "natal_midpoint_analysis", "natal_fixed_stars",
            "deep_harmonic_analysis", "natal_lunation_cycle",
        ],
        "timing": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "vimshottari_dasa", "firdaria_periods",
            "solar_return_chart", "lunar_return_chart",
            "transit_positions", "transit_to_natal_aspects",
            "eclipses_nearby_current", "eclipses_nearby_birth",
            "natal_lunation_cycle",
        ],
        "health_energy": [
            "natal_planet_positions", "natal_houses", "natal_ascendant",
            "natal_aspects", "natal_additional_points",
            "natal_fixed_stars", "natal_declinations",
            "natal_dignity_scores", "natal_lunation_cycle",
            "solar_return_chart", "transit_positions",
            "transit_to_natal_aspects", "natal_midpoint_analysis",
        ],
    }

    # Her analiz türü için özel prompt — teknik terim içermeyen, saf enerji dili
    TYPE_PROMPTS = {
        "birth_chart": """
## DOĞUM HARİTASI VE KİŞİLİK ANALİZİ
Verilen hesaplama sonuçlarını kullanarak kişinin temel yapısını yorumla.
Teknik terim kullanma — sadece enerjiyi ve etkiyi anlat:

1. DIŞ DÜNYAYA YANSIMA — Kişinin çevresine nasıl göründüğü, ilk izlenim, genel duruş
2. İÇ DÜNYA VE DUYGULAR — Duygusal yapı, ihtiyaçlar, güvenlik hissi, içsel ritim
3. TEMEL KİŞİLİK VE YAŞAM AMACI — Ego, güç alanı, hayatı sürdüren temel enerji
4. YAŞAM ALANLARI ENERJİSİ — Hangi hayat alanında hangi enerji baskın (iş, ilişki, yaratıcılık vb.)
5. İÇ GERİLİM VE BÜYÜME — Kişilikteki çatışmalar, zorlayıcı dinamikler ve büyümeye dönüşme biçimi
6. AKTİF DÖNGÜSEL YAPI — Şu an hangi büyük yaşam döngüsünde olunduğu ve bu dönemin tonu
7. ORTAKLIK VE DERİNLİK — Ruhsal amaç açısından ilişki ve partnerlik boyutu
8. KADERSEL TEMA — Doğum döneminin yaşam temasına bıraktığı kalıcı iz
""",
        "relationship": """
## İLİŞKİ POTANSİYELİ ANALİZİ
Verilen hesaplama sonuçlarını kullanarak ilişki dinamiklerini yorumla.
Teknik terim kullanma:

1. AŞK VE ARZU DİLİ — Romantik çekim biçimi, ilişkide ne aranır, nasıl bağlanılır
2. ROMANTİZM VE ORTAKLIK — Kısa vadeli ilgi ile uzun vadeli bağlılık arasındaki fark
3. GİZLİ ARZULAR VE GÖLGE — Bastırılmış ya da farkında olunmayan çekim örüntüleri
4. KADERSEL İLİŞKİ YÖNELİMİ — İlişkilerde tekrar eden kadersel tema
5. BAĞLILIK GÖSTERGELERİ — Uzun süreli ortaklık potansiyelinin genel tablosu
6. RUHSAL PARTNER PROFİLİ — Ruhsal uyum açısından hangi tip ortaklığın rezonans yarattığı
7. ÇEKİM DİNAMİKLERİ — Manyetik çekim, uyum ve gerilim alanları
8. DUYGUSAL DERİNLİK — İlişkide duygusal açılma kapasitesi ve sınırları
""",
        "psychological_karmic": """
## PSİKOLOJİK VE DERİN ANALİZ
Verilen hesaplama sonuçlarını kullanarak kişinin psikolojik yapısını yorumla.
Teknik terim kullanma:

1. SORUMLULUK VE SINIR ENERJİSİ — Hayatta yapısal baskı ve kısıtlama hissedilen alanlar
2. DÖNÜŞÜM VE GÜÇ — Güç dinamikleri, köklü değişim kapısı, bastırılmış enerjinin açığa çıkışı
3. EN DERİN YARA — Taşınan temel yara noktası ve dönüşüm potansiyeli
4. BİLİNÇALTI ALANI — Görünmez örüntüler, baskılanmış içerikler, geçmişten gelen izler
5. İÇ ÇATIŞMA VE BÜYÜME — Kişilik içindeki gerilimler ve büyüme enerjisine dönüşümü
6. AKTİF DÖNEM ENERJİSİ — Şu anki büyük yaşam döngüsünün tonu ve dersi
7. DERİN REZONANS — Bilinçdışı titreşim katmanları ve spiritüel bağlantı kapasitesi
8. KADERSEL MİSYON — Doğum döneminin ruhsal sözleşme ve yaşam misyonuna etkisi
""",
        "daily": """
## GÜNLÜK ENERJİ — SADECE BUGÜN

KESİN KISITLAMA: YALNIZCA bugünkü gezegen pozisyonları ile doğum haritası arasındaki aktif etkileşimler yorumlanır. Dönem analizi, karakter yorumu, uzun vade YASAK. "Bu dönemde", "bu yıl", "doğum haritanızda" ifadeleri YASAK.

**BUGÜNÜN GENEL TONU**
Bugün aktif olan enerji etkileşimlerinin birleşik atmosferi nasıl? (2-3 cümle, sade dil)

**DUYGUSAL RENK**
Bugün iç dünya ve duygusal iklim nasıl bir tona bürünüyor?

**ALAN BAZLI ENERJİ** (sadece bugün aktif etkileşimlerden türet, yoksa o başlığı atla)
- İş ve üretkenlik alanında bugün hangi enerji aktif?
- İletişim ve sosyal alanda bugün ne öne çıkıyor?
- İlişkiler alanında bugün hangi dinamik var?
- Fiziksel enerji ve beden alanında bugün tablo nasıl?

**GÜNÜN RİTMİ**
Sabah / öğle / akşam enerji dağılımında belirgin bir fark var mı?

Çıktı 350-500 kelime. Karakter analizi, dönem yorumu, uzun vade YASAK.
""",
        "transits": """
## AKTİF DÖNEM ENERJİLERİ
Verilen verileri kullanarak aktif dönemin enerji tablosunu yorumla.
Teknik terim kullanma:

1. BÜYÜK DÖNEM ETKİLERİ — Uzun süre aktif kalan yavaş hareket eden gezegen enerjilerinin genel tonu
2. AKTİF ETKİLEŞİMLER — Şu an doğum haritasıyla oluşan önemli enerji bağlantıları ve hayata yansımaları
3. YILLIK TEMA — Bu yılın ana enerji teması
4. AYLIK ODAK — Bu ay öne çıkan duygusal ve pratik alan
5. YAKIN DÖNEM KIRIŞ NOKTALARI — Kozmik enerji değişimlerine yol açan olayların etkisi
6. DÖNGÜ TONU — Şu an hangi büyük yaşam döngüsünde olunduğu
7. YILDIZ ENERJİLERİ — Varsa güçlü yıldız bağlantılarının tonu
""",
        "short_term": """
## KISA VADELİ ENERJİ TABLOSU (1-3 AY)
Verilen verileri kullanarak önümüzdeki 1-3 aylık dönemin enerji tablosunu yorumla.
Teknik terim kullanma:

1. HIZLI DÖNEM ETKİLERİ — Kısa sürede geçen gezegen enerjilerinin tetikleyeceği genel ton
2. KADERSEL DÖNEMEÇLER — Yakın dönemde öne çıkan kozmik kırılma noktaları
3. AYLIK VE YILLIK TEMA — Bu ay ile bu yılın birleşen mesajı
4. AKTİF DÖNEM TONU — Şu anki büyük döngünün bu 1-3 ay boyunca nasıl hissettireceği
5. ENERJİ PENCERELERİ — Hangi zaman dilimlerinde hangi yaşam alanında yoğunluk var
6. ALAN BAZLI TABLO — Kariyer, ilişki, sağlık ve maddi alan için 1-3 aylık enerji özeti
""",
        "long_term": """
## UZUN VADELİ ENERJİ TABLOSU (1-5 YIL)
Verilen verileri kullanarak önümüzdeki 1-5 yıllık dönemin enerjisini yorumla.
Teknik terim kullanma:

1. BÜYÜK YAŞAM DÖNGÜSÜ — Şu an hangi büyük döngüde olunduğu ve genel mesajı
2. DÖNEM DEĞİŞİMLERİ — Yıllık enerji yöneticilerinin sıralanması ve tonu
3. YAVAŞ ETKİLER — Yıllarca aktif olan büyük enerji dönüşümleri
4. YILLIK BİRİKİMLİ TABLO — Yıl yıl enerji tablosu
5. DERİN DÖNÜŞÜM — Uzun vadeli psikolojik ve spiritüel dönüşüm süreci
6. ALAN BAZLI UZUN VADE — Kariyer, ilişki, sağlık, maddi alan ve spiritüel gelişim yol haritası
""",
        "career": """
## KARİYER VE MESLEK ANALİZİ
Verilen verileri kullanarak kariyer potansiyelini yorumla.
Teknik terim kullanma:

1. DOĞAL KARİYER ALANI — Kişinin doğasına uygun meslek ve çalışma biçimi
2. DİSİPLİN VE ŞANS ENERJİSİ — Profesyonel hayatta yapısal zorluk ve büyüme potansiyeli
3. ÇALIŞMA VE GELİR İLİŞKİSİ — Günlük iş ritmi ile maddi kazanç arasındaki enerji dengesi
4. YILDIZ ENERJİLERİ — Güçlü kariyer bağlantısı olan yıldız etkilerinin tonu
5. YILLIK KARİYER ODAĞI — Bu yılın kariyer alanındaki ana teması
6. AKTİF DÖNEM MESLEKİ TONU — Şu anki yaşam döngüsünün kariyer üzerindeki etkisi
7. BEREKET GÖSTERGELERİ — Maddi başarı ve meslek alanındaki güç noktaları
8. FIRSATLAR VE ZOR DÖNEMLER — Kariyer alanındaki yoğun ve durağan enerji pencereleri
""",
        "health": """
## SAĞLIK ANALİZİ
Verilen verileri kullanarak sağlık ve beden enerjisini yorumla.
Teknik terim kullanma:

1. BEDEN YAPISI VE VİTALİTE — Doğuştan gelen fiziksel enerji tonu ve dayanıklılık kapasitesi
2. DERİN YARA VE İYİLEŞME — Taşınan en derin fiziksel veya duygusal yara ve iyileşme potansiyeli
3. FİZİKSEL GÜÇ ENERJİSİ — Hareket, atılganlık ve enerji boşalma biçimi; yorgunluk kalıpları
4. YAPISAL ZAYIFLIKLAR — Kronik yüklenme eğilimi gösteren beden alanları
5. YILDIZ SAĞLIK BAĞLANTILARI — Varsa güçlü yıldız etkilerinin sağlık boyutu
6. DERİN ENERJİ BAĞLANTILARI — Görünmez enerji ittifakları ve dengesizlik odakları
7. AY RİTMİ VE BEDEN DÖNGÜSÜ — Enerji dalgalanmalarının aylık yapısı
8. YILLIK SAĞLIK ODAĞI — Bu yıl öne çıkan sağlık enerjisi
9. AKTİF DÖNEM ETKİSİ — Yakın dönemde sağlık alanında aktif enerji penceresi
""",
        "finance": """
## FİNANSAL ENERJİ ANALİZİ
Verilen verileri kullanarak finansal potansiyeli yorumla.
Teknik terim kullanma:

1. GELİR VE KAYNAK ENERJİSİ — Kişisel kazanç enerjisi ve para ile ilişki biçimi
2. ORTAK KAYNAKLAR — Ortak sermaye, miras, yatırım alanlarıyla ilişki enerjisi
3. BEREKET AKIŞI — Şans ve bolluk noktası; maddi akışın doğal kanalları
4. KAYNAK YÖNETİMİ GÜCÜ — Sahip olunan kaynakları kullanma kapasitesi
5. YILLIK MADDİ ODAK — Bu yılın finansal alandaki ana teması
6. BÜYÜK GEÇİŞ ENERJİLERİ — Gelir ve kaynak alanındaki uzun vadeli dönüşümler
7. FIRSAT VE ZOR DÖNEMLER — Maddi alanda yoğun ve durağan enerji pencereleri
""",
        "spiritual": """
## RUHSAL GELİŞİM ANALİZİ
Verilen verileri kullanarak spiritüel potansiyeli yorumla.
Teknik terim kullanma:

1. YÜKSEK BİLİNÇ VE DERİNLİK — Ruhsal anlayış kapasitesi ve içe dönüşe eğilim
2. SPİRİTÜEL TİTREŞİM KATMANLARI — Farklı düzeylerdeki ruhsal potansiyel ve içsel bağlantı
3. İÇSEL YOLCULUK DÖNGÜSÜ — Şu anki büyük döngünün spiritüel gelişime açtığı pencere
4. RUHSAL ORTAKLIK — Spiritüel uyum açısından ilişki boyutunun derinliği
5. KADERSEL MİSYON — Yaşam misyonunun ruhsal yönü ve yönelim
6. SPİRİTÜEL RİTİM — Ruhsal enerji akışının döngüsel yapısı
7. YILDIZ BAĞLANTILARI — Varsa spiritüel güç katan yıldız enerjilerinin tonu
8. GÖLGE VE DENGE — Entegre edilmesi gereken gizli enerjiler
""",
        "summary": """
## KOZMİK ÖZET
Verilen verileri kullanarak 300-500 kelimelik kısa ve öz bir özet hazırla.
Teknik terim kullanma:

1. EN GÜÇLÜ 3 ENERJİ — Haritadaki en baskın 3 enerji odağı ve hayata somut yansıması
2. YAŞAM AMACI — En büyük kullanılmamış potansiyel ve hayatı yönlendiren temel enerji
3. ŞU ANKİ DÖNEM MESAJI — Aktif dönemin tek net mesajı
4. EN KRİTİK TEMA — Önümüzdeki dönemde en belirgin şekilde hissedilecek enerji alanı
Her başlık 2-3 cümle — kısa, öz, net.
""",
        # ── YENİ TÜRLER ──────────────────────────────────────────────
        "vedic": """
## DÖNEMSELLİK ANALİZİ (Vedik Sistem)
Verilen Vedik hesaplama verilerini kullanarak dönemsel enerji tablosunu yorumla.
Teknik terim kullanma:

1. ANA DÖNEM ENERJİSİ — Şu an aktif olan büyük dönemin yönetici enerjisi ve genel tonu
2. ALT DÖNEM ETKİSİ — Ana dönemin içindeki aktif alt dönemin etkisi ve bu kombinasyonun hayata yansıması
3. DOĞUMSAL YILDIZ ENERJİSİ — Doğumdaki duygusal enerji noktasının kişilik ve kader üzerindeki etkisi
4. RUHSAL AMAÇ BOYUTU — Ruhsal gelişim haritasından partnerlik ve derin anlam katmanı
5. DÖNEM KARŞILAŞTIRMASI — Farklı dönem sistemlerinin birbiriyle uyumu veya çelişkisi
6. GÜÇLÜ VE ZAYIF ENERJİ NOKTALARI — Hangi enerjilerin güçlü, hangilerinin zayıf konumda olduğu
7. YAKLAŞAN DÖNEM DEĞİŞİMİ — Bir sonraki büyük dönem geçişinin zamanı ve genel tonu
8. RUHSAL MİSYON ÖZETI — Dönemsel enerji tablosundan çıkan genel yönelim
""",
        "eclipses": """
## TUTULMA ETKİLERİ ANALİZİ
Verilen tutulma verilerini kullanarak tutulmaların yaşam üzerindeki etkilerini yorumla.
Teknik terim kullanma:

1. DOĞUMSAL TUTULMA İZİ — Doğum dönemindeki kozmik kırılma noktalarının yaşam temasına kalıcı etkisi
2. AKTİVASYON NOKTALARI — Doğum haritasındaki hangi enerji alanlarının tutulma ekseniyle kesiştiği
3. AKTİF TUTULMA ETKİSİ — Şu an veya yakın dönemde aktif tutulmanın hangi enerji alanını tetiklediği
4. ETKİLENEN YAŞAM ALANLARI — Tutulma ekseninin hangi hayat alanını öne çıkardığı
5. AÇILIM PENCERESİ — Tutulma sonrası 6 aylık dönemde hangi yaşam alanının yoğun aktif olacağı
6. KADERSEL YÖNELİM — Tutulma ekseninin kadersel mesajı
7. DÖNEM ENERJİSİ — Bu tutulma döneminin genel tonu ve yaşam üzerindeki temaları
""",
        "harmonic": """
## DERİN ENERJİ VE REZONANS ANALİZİ
Verilen derin harmonik verileri kullanarak gizli potansiyelleri yorumla.
Teknik terim kullanma:

1. YARATICI İFADE ALANI — Sanat, yaratıcılık ve kendini ifade etme kapasitesinin enerji yapısı
2. MANEVİ BAĞLANTI — Spiritüel yetenek, ilham kapasitesi ve yüksek frekans bağlantısı
3. RUHSAL ORTAKLIK DERİNLİĞİ — Ruhsal amaç ve derin ilişki bağının rezonansı
4. GİZLİ BİLİNÇALTI ÖRÜNTÜLER — Bilinçdışı enerji kalıpları ve gizli güçler
5. GİZLİ YAPISAL GÖSTERGELER — Gezegen orta noktalarındaki derin enerji yapılandırıcıları
6. GÖLGE VE DENGE ENERJİLERİ — Yansıma enerjileri ve dengelenmesi gereken alanlar
7. GİZLİ BAĞLANTILAR — Görünmez enerji köprüleri ve fark edilmemiş örüntüler
8. PRATİK YANSIMA — Bu derin haritanın günlük yaşama ve ilişkilere somut yansıması
""",
        "esoteric": """
## EZOTERİK ENERJİ ANALİZİ
Verilen ezoterik hesaplama verilerini kullanarak gizli enerji haritasını yorumla.
Teknik terim kullanma:

1. ŞANS VE BEREKET NOKTASI — Maddi şans ve bolluk akışının doğal kanalı
2. RUH NOKTASI VE AŞK ENERJİSİ — Ruhsal merkez ve aşk alanındaki enerji odağı
3. GÖLGE EKSENİ — Bastırılmış veya farkında olunmayan enerji odakları
4. YILDIZ ENERJİ BAĞLANTILARI — Güçlü yıldız enerjilerinin ezoterik mesajı
5. GİZLİ ENERJİ KÖPRÜLERİ — Görünmez enerji bağlantıları ve gizli müttefikler
6. GİZLİ YAPISAL MESAJLAR — Enerji orta noktalarındaki saklı anlam katmanları
7. AY DÖNGÜSÜ VE YAŞAM RİTMİ — Doğumsal ay enerjisinin yaşam ritmi ve ruhsal misyona etkisi
8. BÜTÜNSEL EZOTERİK TABLO — Tüm gizli göstergelerin birleşik mesajı
""",
        "timing": """
## ZAMANLAMA ANALİZİ — DÖNEM SENTEZİ
Verilen zamanlama verilerini kullanarak birden fazla sistem üzerinden dönem sentezi yap.
Teknik terim kullanma:

1. DÖNEM YÖNETİCİSİ — Şu anki dönemin yönetici enerjisi ve alt dönem kombinasyonunun genel tonu
2. VEDİK ZAMAN KATMANI — Vedik sistemden dönem enerjisi
3. YILLIK AÇILIŞ — Bu yılın kozmik başlangıç enerjisi ve yıl boyunca taşıyacağı tema
4. AYLIK ODAK — Bu aydaki duygusal iklim ve pratik yönelim
5. KOZMİK KIRIŞ NOKTALARI — Yakın dönem büyük kozmik olayların zamanlama üzerindeki etkisi
6. BÜYÜK GEÇİŞ DÖNEMLERİ — Önemli enerji değişimlerinin kritik geçiş dönemleri
7. SİSTEMLERİN SENTEZİ — Birden fazla sistemin aynı anda öne çıkardığı dönem ve tonu
8. ÖNÜMÜZDEKİ 3-6 AY — En kritik enerji aralıkları ve baskın temaları
""",
        "health_energy": """
## SAĞLIK VE VİTALİTE PROFİLİ
Verilen verileri kullanarak sağlık, enerji ve beden potansiyelini çok katmanlı yorumla.
Teknik terim kullanma:

1. TEMEL VİTALİTE YAPISI — Doğuştan gelen fiziksel enerji tonu ve dayanıklılık kapasitesi
2. DERİN YARA VE İYİLEŞME NOKTASI — En derin fiziksel veya duygusal yara alanı ve dönüşüm kapasitesi
3. FİZİKSEL GÜÇ VE ENERJİ — Hareket enerjisi, atılganlık ve enerji boşalma kalıpları
4. YAPISAL ZAYIFLIK EĞİLİMLERİ — Kronik yüklenme ve dikkat gerektiren beden alanları
5. YILDIZ SAĞLIK REZONANSSI — Varsa güçlü yıldız bağlantılarının sağlık üzerindeki etkisi
6. GİZLİ ENERJİ BAĞLANTILARI — Görünmez sağlık örüntüleri ve enerji dengesizlik odakları
7. ENERJİ TONU VE BEDEN SİSTEMLERİ — Zayıf enerji alanlarının ilişkili olduğu beden sistemleri
8. YILLIK SAĞLIK ODAĞI — Bu yıl öne çıkan sağlık enerji teması
9. AKTİF DÖNEM SAĞLIK PENCERESİ — Yakın dönemde aktif olan sağlık enerjisi
10. AY DÖNGÜSÜ VE BEDEN RİTMİ — Enerji dalgalanmalarının döngüsel yapısı
""",
    }

    # Provider ayarlarını cache'le
    _providers_cache = None
    _fallback_order = []
    _last_fetch = 0
    CACHE_TTL = 60  # saniye

    def __init__(self):
        self.sync_client = None
        # Fallback: env'den oku (Firestore yoksa)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            self.sync_client = OpenAI(
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1"
            )

    def _get_providers_from_firestore(self) -> dict:
        """Firestore'dan AI ayarlarını getir (cache'li)"""
        now = datetime.now().timestamp()
        if self._providers_cache and (now - self._last_fetch) < self.CACHE_TTL:
            return self._providers_cache

        try:
            from services.firebase_service import firebase_service
            db = firebase_service.db
            if db:
                doc = db.collection('config').document('ai_settings').get()
                if doc.exists:
                    data = doc.to_dict()
                    self._providers_cache = data
                    self._last_fetch = now
                    logger.info(f"[AI] Ayarlar Firestore'dan yüklendi. Provider: {len(data.get('providers', []))} adet")
                    return data
        except Exception as e:
            logger.error(f"[AI] Firestore okuma hatası (önemsiz, env fallback): {e}")

        return {}

    def _get_provider_by_name(self, name: str, providers: list) -> Optional[dict]:
        """Provider adına göre provider bilgisini bul"""
        if not name or not providers:
            return None
        for p in providers:
            if p.get('name') == name:
                return p
        return None

    def _get_fallback_chain(self) -> List[dict]:
        """Aktif + yedek sırasına göre provider listesi döndür"""
        settings = self._get_providers_from_firestore()
        providers = settings.get('providers', [])

        if not providers:
            # Firestore'da provider yoksa env'den dene
            return self._get_env_fallback_chain()

        chain = []
        order_keys = ['active_provider', 'backup_1', 'backup_2', 'backup_3']

        for key in order_keys:
            name = settings.get(key, '')
            provider = self._get_provider_by_name(name, providers)
            if provider:
                chain.append(provider)

        # Eğer hiç provider yoksa env'den dene
        if not chain:
            return self._get_env_fallback_chain()

        logger.info(f"[AI] Fallback zinciri: {' -> '.join(p['name'] for p in chain)}")
        return chain

    def _get_env_fallback_chain(self) -> List[dict]:
        """Ortam değişkenlerinden provider bilgilerini oku (eski sistem)"""
        chain = []
        if os.getenv("DEEPSEEK_API_KEY"):
            chain.append({
                "name": "DeepSeek (env)",
                "base_url": "https://api.deepseek.com",
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "model": "deepseek-chat",
            })
        if os.getenv("ZAI_API_KEY"):
            chain.append({
                "name": "ZAI (env)",
                "base_url": "https://api.zai-api.com/v1",
                "api_key": os.getenv("ZAI_API_KEY"),
                "model": "zai-chat",
            })
        if os.getenv("OPENROUTER_API_KEY"):
            chain.append({
                "name": "OpenRouter (env)",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": "openrouter/auto",
            })
        return chain

    @staticmethod
    def remove_emojis(text: str) -> str:
        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f700-\U0001f77f"
            "\U0001f780-\U0001f7ff\U0001f800-\U0001f8ff\U0001f900-\U0001f9ff\U0001fa00-\U0001fa6f"
            "\U0001fa70-\U0001faff\U00002702-\U000027b0\U000024c2-\U0001f251\U0001f1e0-\U0001f1ff"
            "\U00002600-\U000026ff\U00002700-\U000027bf\U0000fe00-\U0000fe0f\U0001f000-\U0001f02f"
            "\U0001f0a0-\U0001f0ff]+",
            flags=re.UNICODE,
        )
        cleaned = emoji_pattern.sub("", text)
        cleaned = re.sub(r" +", " ", cleaned)
        return "\n".join(line.strip() for line in cleaned.split("\n")).strip()

    async def call_provider(self, session: aiohttp.ClientSession, provider: dict, prompt: str, interpretation_type: str = "") -> dict:
        """Tek bir provider'a API çağrısı yap"""
        base_url = provider['base_url'].rstrip('/')
        api_key = provider['api_key']
        model = provider.get('model', 'deepseek-chat')
        name = provider.get('name', 'Bilinmeyen')

        # OpenAI uyumlu API endpoint
        url = f"{base_url}/chat/completions" if not base_url.endswith('/chat/completions') else base_url

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Yorum türüne göre system prompt belirle
        if interpretation_type == "daily":
            system_content = (
                "Sen bir astroloji yorumlama motorusun. "
                "Görevin SADECE bugünkü transit pozisyonlarını ve transit-natal açılarını yorumlamaktır. "
                "Dasha, Firdaria, Solar Return, karakter analizi veya uzun vadeli dönemlerden KESİNLİKLE bahsetme. "
                "Tavsiye vermezsin. Sadece bugünkü aktif transit enerjisini ve bunun yaşam alanlarına yansımasını betimlersin."
            )
        else:
            system_content = (
                "Sen bir astroloji yorumlama motorusun. "
                "Görevin yalnızca sana verilen hesaplama verisini yorumlamaktır. "
                "Tavsiye vermezsin. Yönlendirmezsin. Sadece astrolojik tabloyu ve enerjiyi tanımlarsın."
            )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        try:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    # Token limitinden dolayi kesilme kontrolu
                    finish_reason = data["choices"][0].get("finish_reason", "stop")
                    if finish_reason == "length":
                        logger.warning(f"[AI] ⚠️ {name} max_tokens'e ulasti, yanit kesilmis olabilir")
                    # content None olabilir (API hatasi veya bos yanit)
                    content_len = len(content) if content else 0
                    if not content:
                        logger.warning(f"[AI] ❌ {name} boş yanit döndü (finish_reason={finish_reason})")
                        return {"success": False, "error": f"{name}: boş yanit", "provider": name}
                    logger.info(f"[AI] ✅ {name} başarılı (finish_reason={finish_reason}, len={content_len})")
                    return {"success": True, "interpretation": self.remove_emojis(content), "provider": name}
                else:
                    error_text = await resp.text()
                    logger.warning(f"[AI] ❌ {name} hata {resp.status}: {error_text[:200]}")
                    return {"success": False, "error": f"{name}: HTTP {resp.status}", "provider": name}
        except asyncio.TimeoutError:
            logger.warning(f"[AI] ⏰ {name} timeout (90sn)")
            return {"success": False, "error": f"{name}: timeout", "provider": name}
        except Exception as e:
            logger.warning(f"[AI] ❌ {name} exception: {str(e)[:100]}")
            return {"success": False, "error": f"{name}: {str(e)[:100]}", "provider": name}

    def _filter_astro_data(self, astro_data: dict, analysis_type: str) -> dict:
        """Her analiz türü için sadece gerekli hesaplama sonuçlarını filtrele.
        Eşleşme yoksa tüm veriyi döndür (geriye dönük uyumlu)."""
        if not astro_data or not isinstance(astro_data, dict):
            logger.warning(f"[AI] astro_data None veya geçersiz, boş dict dönülüyor.")
            return {}
        allowed_keys = self.DATA_FILTER.get(analysis_type)
        if not allowed_keys:
            logger.warning(f"[AI] {analysis_type} için filtre tanımı yok, tüm veri gönderiliyor.")
            return astro_data
        filtered = {}
        skipped_count = 0
        for key in allowed_keys:
            if key in astro_data:
                filtered[key] = astro_data[key]
        # Hangi hesaplamalar atlandı logla
        skipped = [k for k in astro_data if k not in allowed_keys]
        if skipped:
            logger.info(f"[AI] Filtre '{analysis_type}': {len(filtered)}/{len(astro_data)} key gönderildi, {len(skipped)} atlandı: {skipped}")
        else:
            logger.info(f"[AI] Filtre '{analysis_type}': Tüm {len(filtered)} key gönderildi.")
        return filtered

    # Sadece major açılar: Conjunction, Opposition, Square, Trine, Sextile
    MAJOR_ASPECTS = {"Conjunction", "Opposition", "Square", "Trine", "Sextile"}
    # Sadece ana gezegenler + önemli noktalar arası açılar (asteroid ve uranyenler yok)
    IMPORTANT_BODIES = {
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        "Ascendant", "MC", "Armc", "True_Node",
    }

    @staticmethod
    def _is_important_aspect(item: dict) -> bool:
        """Sadece ana gezegenler/noktalar arası major açılar, orb < 8"""
        p1 = item.get("planet1", "")
        p2 = item.get("planet2", "")
        aspect = item.get("aspect_type", "")
        orb = abs(float(item.get("orb", 99)))
        # Major aspect kontrol
        if aspect not in AIService.MAJOR_ASPECTS:
            return False
        # İki taraf da önemli cisimlerden olmalı
        if p1 not in AIService.IMPORTANT_BODIES or p2 not in AIService.IMPORTANT_BODIES:
            return False
        # Orb sınırı (Conjunction/Opposition: 8, Square/Trine: 7, Sextile: 5)
        if aspect == "Sextile" and orb > 5:
            return False
        if orb > 8:
            return False
        return True

    @staticmethod
    def _deep_trim(data: dict, max_items: int = 30) -> dict:
        """Büyük dizileri derinlemesine kırp: sadece önemli major açılar, en dar orb'lular."""
        trimmed = {}
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 10:
                # Açı listeleri: sadece önemli major açılar → orb sıralı
                if all(isinstance(item, dict) and "aspect_type" in item for item in value[:3]):
                    filtered = [item for item in value if AIService._is_important_aspect(item)]
                    filtered.sort(key=lambda x: abs(float(x.get("orb", 99))))
                    trimmed[key] = filtered[:max_items]
                    logger.info(f"[AI] Deep trim '{key}': {len(value)} → {len(filtered[:max_items])} (önemli major açılar)")

                # Sabit yıldızlar: top 10
                elif all(isinstance(item, dict) and ("star" in str(item).lower() or "name" in item) for item in value[:3]):
                    trimmed[key] = value[:10]
                    logger.info(f"[AI] Deep trim '{key}': {len(value)} → {len(value[:10])} (top 10)")

                # Midpoint / genel dizi: top 10
                elif all(isinstance(item, dict) for item in value[:3]):
                    trimmed[key] = value[:10]
                    logger.info(f"[AI] Deep trim '{key}': {len(value)} → {len(value[:10])} (top 10)")

                else:
                    trimmed[key] = value
            elif isinstance(value, dict):
                trimmed[key] = AIService._deep_trim(value, max_items)
            else:
                trimmed[key] = value
        return trimmed

    async def get_ai_interpretation_async(self, astro_data: dict, interpretation_type: str, user_name: str, **kwargs) -> dict:
        """Sıralı yedekleme ile AI yorumu al — analiz türüne özel veri + prompt"""
        # Veriyi filtrele
        filtered_data = self._filter_astro_data(astro_data, interpretation_type)
        # Derinlemesine kırp: major açılar, top N
        filtered_data = self._deep_trim(filtered_data)
        data_json = json.dumps(filtered_data, default=str)
        data_size = len(data_json)
        logger.info(f"[AI] Prompt data boyutu: {data_size:,} bytes (~{data_size//4:,} token)")

        # Analiz türüne özel prompt veya genel prompt
        type_prompt = self.TYPE_PROMPTS.get(interpretation_type)
        if type_prompt:
            prompt = f"User: {user_name}\n{type_prompt}\nData: {data_json}\n{self.BASE_RULES}"
        else:
            prompt = f"User: {user_name}\nType: {interpretation_type}\nData: {data_json}\n{self.BASE_RULES}"

        extra = {k: v for k, v in kwargs.items() if v}
        if extra:
            prompt += f"\nExtra: {json.dumps(extra, default=str)}"

        fallback_chain = self._get_fallback_chain()

        if not fallback_chain:
            return {"success": False, "error": "Hiçbir AI provider yapılandırılmamış"}

        errors = []
        async with aiohttp.ClientSession() as session:
            for i, provider in enumerate(fallback_chain):
                tag = "AKTİF" if i == 0 else f"YEDEK-{i}"
                logger.info(f"[AI] Deneniyor: {tag} -> {provider['name']}")
                result = await self.call_provider(session, provider, prompt, interpretation_type)
                if result["success"]:
                    return result
                errors.append(result.get("error", "Bilinmeyen hata"))

        logger.error(f"[AI] Tüm provider'lar başarısız: {' | '.join(errors)}")
        return {"success": False, "error": f"Tüm AI sağlayıcıları başarısız: {'; '.join(errors)}"}

    def get_ai_interpretation(self, astro_data: dict, interpretation_type: str, user_name: str, **kwargs) -> dict:
        """Senkron wrapper"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.get_ai_interpretation_async(astro_data, interpretation_type, user_name, **kwargs)
        )


ai_service = AIService()


def get_ai_interpretation_engine(astro_data, interpretation_type, user_name, **kwargs):
    return ai_service.get_ai_interpretation(astro_data, interpretation_type, user_name, **kwargs)
