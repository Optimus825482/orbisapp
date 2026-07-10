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
## KESİN KURALLAR
### 1. YASAK TERİMLER (ASLA KULLANMA)
- Gezegen isimleri: Mars, Venüs, Satürn, Jüpiter, Merkür, Ay, Güneş, Uranüs, Neptün, Plüton
- Burç isimleri: Koç, Boğa, İkizler, Yengeç, Aslan, Başak, Terazi, Akrep, Yay, Oğlak, Kova, Balık
- Ev numaraları: 1. ev, 7. ev, 10. ev vb.
- Açı isimleri: kavuşum, karşıt, üçgen, kare, altmışlık, kuintil
- Teknik terimler: transit, progresyon, natal, ascendant, midheaven, düğüm, retrograd
### 2. DİL VE ÜSLUP
- Sade, anlaşılır Türkçe
- Doğrudan ve net ifadeler
- Mistik/ezoterik dil KULLANMA
- Kişiye adıyla hitap et, samimi ama profesyonel
### 3. UZUNLUK (ÖNEMLİ)
- Yanitin 500-800 kelime arasi olsun; daha uzun yazma, daha kisa da yazma.
- Tum onemli basliklari isle ama her birini 1-2 paragrafta ozetle.
- Gereksiz detay ve tekrardan kacin, yorum odakli ol.
### 4. TAVSİYE YASAĞI (KESİN KURAL — İSTİSNASIZ)
- TAVSİYE VERME. Asla "yapmalısın", "kaçınmalısın", "dene", "önerim şu", "dikkat et" gibi yönlendirici ifadeler kullanma.
- Yorumun görevi sadece astrolojik tabloyu ve olası enerjiyi TANIMLAMAK, AÇIKLAMAK ve YORUMLAMAKTIR.
- Kullanıcıya ne yapacağını söyleme. Ne olduğunu veya ne olabileceğini söyle.
- Doğru format: "Bu dönemde iş alanında yoğun bir enerji aktif." (tasvir)
- Yanlış format: "Bu dönemde iş konularına odaklanmalısın." (tavsiye — YASAK)
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
            "solar_return_chart", "lunar_return_chart",
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

    # Her analiz türü için özel prompt (kapsamlı ama sadece ilgili veriyle)
    TYPE_PROMPTS = {
        "birth_chart": """
## DOĞUM HARİTASI VE KARAKTER ANALİZİ
Yukarıdaki verileri kullanarak kapsamlı bir doğum haritası analizi yap.
Şu başlıkları detaylıca işle:
1. Yükselen burcun kişiliğe etkisi — dış dünyaya yansıyan karakter
2. Ay burcunun duygusal yapıya etkisi — iç dünya ve ihtiyaçlar
3. Güneş burcunun temel karaktere etkisi — ego ve yaşam amacı
4. Gezegenlerin ev yerleşimleri — hayatın hangi alanında hangi enerji
5. Önemli açılar ve kişilik dinamikleri (büyük üçgen, T-kare, grand cross varsa)
6. Vimshottari Dasha dönemi ve Firdaria periyotlarına göre yaşam döngüleri
7. Vedic Navamsa haritasından evlilik/partnerlik potansiyeli
8. Doğum tutulmalarının yaşam temasına etkisi
""",
        "relationship": """
## İLİŞKİ ANALİZİ
Yukarıdaki verileri kullanarak ilişki potansiyelini ve dinamiklerini analiz et:
1. Venüs ve Mars yerleşimleri — aşk ve arzu dili
2. 5. ev (romantizm) ve 7. ev (partnerlik) vurguları
3. Lilith'in konumu — bastırılan arzular ve gölge yönler
4. Ay düğümleri (Kuzey/Güney) — ilişkilerdeki kadersel yolculuk
5. Arap noktalarından evlilik ve ilişki göstergeleri
6. Navamsa haritasından partner profili
7. Deklinasyon paralelleri — manyetik çekim dinamikleri
8. Sabit yıldızların romantik etkileri
""",
        "psychological_karmic": """
## PSİKOLOJİK VE KARMİK ANALİZ
Yukarıdaki verileri kullanarak derinlemesine psikolojik ve karmik analiz yap:
1. Satürn yerleşimi — karmik dersler, korkular, sınırlanma alanları
2. Plüton ve 8. ev — dönüşüm, güç dinamikleri, travma noktaları
3. Chiron — şifa alanı, en derin yara ve iyileşme potansiyeli
4. 12. ev gezegenleri — bilinçaltı, bastırılanlar, geçmiş yaşam izleri
5. Sert açılar (kare, karşıt) — iç çatışma ve büyüme alanları
6. Vimshottari Dasha — karmik zamanlama ve dönem dersleri
7. Deep harmonic (H7, H9) — ilişkisel ve spiritüel titreşimler
8. Doğum tutulmaları — ruhsal sözleşme ve misyon
""",
        "daily": """
## GÜNLÜK YORUM — BUGÜN HANGİ ENERJİ AKTİF?
Yukarıdaki transit ve natal verileri kullanarak BUGÜN hangi astrolojik enerjilerin aktif olduğunu yorumla.
Odak: O GÜN aktif olan enerji tablosu ve bunun hangi yaşam alanlarında hissedileceği.

1. BUGÜNÜN ANA ENERJİSİ
   - Günün dominant transit etkisi ve kişiyle olan ilişkisi
   - Ay'ın konumu — bugünkü duygusal ton ve iç dünya

2. GÜNLÜK ENERJİ TABLOLARI (alan bazlı tespit)
   - İş/kariyer alanında bugün hangi enerji aktif
   - İletişim ve sosyal alanda öne çıkan tema
   - Maddi/finansal konularda bugünkü enerji
   - İlişki alanında bugün hangi dinamik ön planda

3. EN YOĞUN VE EN GERGİN ZAMAN DİLİMLERİ
   - Enerjinin en güçlü hissedildiği saatler
   - Gerilim veya yavaşlama hissinin öne çıktığı saatler

4. TUTULMA VEYA ÖZEL KONJONKTÜR ETKİSİ
   - Yakın dönem tutulma aktifse bugünkü yansıması

UYARI: Genel yorumlardan kaçın. "Bu dönemde" değil, "BUGÜN" hangi enerjinin aktif olduğunu tespit et.
Çıktı 400-600 kelime olsun.
""",
        "transits": """
## TRANSİT ANALİZİ
Yukarıdaki verileri kullanarak transit etkilerini detaylı analiz et:
1. Büyük gezegen transitleri (Jüpiter, Satürn, Uranüs, Neptün, Plüton) — uzun vadeli etkiler
2. Transit-natal açıları ve ev etkileşimleri
3. Solar Return yıllık teması
4. Lunar Return aylık teması
5. Yakın dönem tutulmalarının etkisi
6. Firdaria periyotlarına göre yaşam döngüleri
7. Transit sabit yıldız etkileri
""",
        "short_term": """
## KISA VADELİ ÖNGÖRÜ (1-3 AY)
Yukarıdaki verileri kullanarak önümüzdeki 1-3 aylık dönemin enerji tablosunu yorumla:
1. Hızlı gezegen transitleri — hangi yaşam alanlarında ne tür bir enerji aktif olacak
2. Ay düğümleri ve yakın tutulmalar — kadersel dönemeç ve kırılma noktaları
3. Solar/Lunar Return dönemsel mesajları — bu ay/yılın ana teması
4. Firdaria periyodu — şu an hangi enerji döneminde olduğu ve bu dönemin genel tonu
5. Enerji pencereleri: hangi zaman aralıklarında hangi alan yoğun aktif
6. Kariyer, ilişki, sağlık ve finans alanlarında 1-3 aylık enerji tablosu
""",
        "long_term": """
## UZUN VADELİ ÖNGÖRÜ (1-5 YIL)
Yukarıdaki verileri kullanarak önümüzdeki 1-5 yıllık dönemi analiz et:
1. Vimshottari Dasha ana dönemi — yaşamın büyük döngüsü
2. Firdaria kronokrator değişimleri — yıllık yönetici etkileri
3. Büyük gezegen transitleri (Jüpiter döngüsü, Satürn döngüsü)
4. Solar Return yıllık haritalarının kümülatif etkisi
5. Deep harmonic uzun dalga analizi
6. Kariyer, ilişki, sağlık, finans ve spiritüel gelişim başlıklarında uzun vadeli yol haritası
""",
        "career": """
## KARİYER ANALİZİ
Yukarıdaki verileri kullanarak kariyer ve mesleki potansiyeli analiz et:
1. MC (Tepe Noktası) ve 10. ev yerleşimleri — kariyer yönü
2. Satürn ve Jüpiter konumları — profesyonel disiplin ve şans
3. 6. ev (günlük çalışma) ve 2. ev (gelir) vurguları
4. Sabit yıldızların kariyer etkileri (Spica, Regulus, Sirius vb.)
5. Solar Return kariyer ev vurguları
6. Firdaria profesyonel dönem döngüleri
7. Arap noktalarından meslek ve başarı göstergeleri
8. Transit etkilerle kariyer fırsat pencereleri
""",
        "health": """
## SAĞLIK ANALİZİ
Yukarıdaki verileri kullanarak sağlık ve bedensel potansiyeli analiz et:
1. 6. ev (sağlık) ve 1. ev (beden) yerleşimleri — doğuştan gelen beden yapısı
2. Chiron konumu — en derin fiziksel/psikolojik yara ve iyileşme kapısı
3. Mars enerjisi ve fiziksel dayanıklılık — enerji yönetimi
4. Satürn kronik eğilimleri ve dikkat edilmesi gereken zayıf bölgeler
5. Sabit yıldızların sağlık etkileri (Algol, Caput Algol vb.)
6. Deklinasyon paralellerinde sağlık göstergeleri
7. Solar Return sağlık ev vurguları — bu yıl öne çıkan sağlık temaları
8. Transit etkilerle sağlık uyarıları ve yenileme dönemleri
9. Ay fazı — beden döngüsü ve enerji ritmi
""",
        "finance": """
## FİNANSAL ANALİZ
Yukarıdaki verileri kullanarak finansal potansiyeli ve para yönetimini analiz et:
1. 2. ev (gelir) ve 8. ev (ortak kaynaklar) yerleşimleri
2. Jüpiter ve Venüs'ün finansal etkileri — bolluk ve kaynak akışı
3. Part of Fortune (Şans Noktası) ve Arap finans noktaları
4. Gezegen dignity skorlarına göre kaynak yönetimi gücü
5. Solar Return finansal ev vurguları
6. Transit Jüpiter ve Satürn'ün 2. ve 8. evden geçişleri
7. Finansal fırsat pencereleri ve riskli dönemler
""",
        "spiritual": """
## RUHSAL GELİŞİM ANALİZİ
Yukarıdaki verileri kullanarak spiritüel potansiyeli ve ruhsal yolculuğu analiz et:
1. 9. ev (yüksek bilinç), 12. ev (spiritüel derinlik), Neptün yerleşimi
2. Deep harmonic (H5, H7, H9, H12) — spiritüel titreşim katmanları
3. Vimshottari Dasha spiritüel dönemi — içsel yolculuk zamanlaması
4. Navamsa (H9) haritasından ruhsal eğilimler
5. Ay düğümleri — kadersel ruhsal misyon
6. Ay fazı (lunation cycle) — spiritüel ritim
7. Sabit yıldızların spiritüel etkileri (Fomalhaut, Aldebaran vb.)
8. Antiscia noktaları — gölge ve denge dinamikleri
""",
        "summary": """
## KOZMİK ÖZET (KISA)
Yukarıdaki verileri kullanarak 300-500 kelimelik kısa ve öz bir kozmik özet hazırla:
1. En güçlü 3 gezegen ve hayata somut etkisi
2. Yaşam amacı ve kullanılmayan en büyük potansiyel
3. Şu anki transit dönemin ana mesajı — aktif transit açıları ne söylüyor
4. Önümüzdeki dönem için en önemli tek somut tavsiye
KISA olsun, uzun yazma. Her başlık 2-3 cümle yeterli.
""",
        # ── YENİ TÜRLER ──────────────────────────────────────────────
        "vedic": """
## VEDİK ASTROLOJİ ANALİZİ (Dasha & Nakshatra)
Yukarıdaki verileri kullanarak Vedik astroloji perspektifinden derinlemesine analiz yap:
1. Vimshottari Dasha — şu anki Ana Dönem (Mahadasha) ve Alt Dönem (Antardasha): hangi gezegenin enerjisi hâkim, ne anlama geliyor
2. Dasha döneminin pratik yansımaları — bu dönemde hangi yaşam alanları öne çıkıyor
3. Nakshatra analizi — Ay'ın Nakshatra'sı ve kişilik, kader üzerindeki etkisi
4. Navamsa (D9) haritası — ruhsal amaç, partnerlik ve derinlik katmanı
5. Firdaria periyodu ile Vedik dönem karşılaştırması — çakışan temalar
6. Gezegen dignity skorları (Vedik perspektif) — hangi gezegenler güçlü veya zayıf
7. Önümüzdeki Dasha değişimi — ne zaman olacak ve yaşamda nasıl bir kırılma getirecek
8. Vedik harmonik (H9 Navamsa) üzerinden ruhsal misyon özeti
""",
        "eclipses": """
## TUTULMA ETKİLERİ ANALİZİ
Yukarıdaki verileri kullanarak tutulmaların yaşam üzerindeki etkilerini analiz et:
1. Doğum tutulmaları — doğuma yakın güneş/ay tutulmaları ve yaşam temasına kalıcı etkisi
2. Kadersel aktivasyon noktaları — natal haritadaki hangi noktalar tutulma ekseninde
3. Şu anki/yakın dönem tutulmaları — aktif tutulma hangi natal noktayı tetikliyor
4. Tutulma ekseninin yaşam alanlarına etkisi — hangi ev ve konu bu aktivasyondan etkileniyor
5. Tutulma sonrası 6 aylık açılım penceresi — bu dönemde hangi yaşam alanı yoğun aktif
6. Ay düğümleri (Kuzey/Güney) — karmik yön ve tutulma ekseninin mesajı
7. Bu tutulma döneminin genel enerjisi ve yaşam üzerindeki olası temaları
""",
        "harmonic": """
## HARMONİK REZONANS ANALİZİ
Yukarıdaki derin harmonik verileri kullanarak gizli potansiyelleri ve örüntüleri analiz et:
1. H5 (5. Harmonik) — yaratıcı ifade, sanat ve ilham kapasitesi
2. H7 (7. Harmonik) — manevi yetenek, ilham ve spiritüel bağlantı
3. H9 Navamsa — ruhsal amaç ve evlilik/partnerlik derinliği
4. H12 (12. Harmonik) — bilinçaltı örüntüler ve gizli güçler
5. Midpoint analizi — gezegen orta noktalarındaki gizli yapılandırıcı güçler
6. Antiscia noktaları — gölge yansımalar ve dengelenmesi gereken enerjiler
7. Deklinasyon paralelleri — gizli konjonksiyonlar ve fark edilmemiş bağlantılar
8. Bu harmonik haritanın yaşama pratik yansıması — ne tür alanlarda güçlü rezonans var
""",
        "esoteric": """
## EZOTERİK ETKİLER ANALİZİ
Yukarıdaki verileri kullanarak gizli, ezoterik ve kadim astroloji tekniklerini analiz et:
1. Arap noktaları — Şans Noktası, Ruh Noktası, Aşk Noktası ve diğer kritik Arap noktaları
2. Part of Fortune — maddi şans ve bereket akışının haritadaki yeri
3. Antiscia ve Contra-antiscia — gölge eksen ve bastırılmış enerji odakları
4. Sabit yıldızlar — natalde güçlü sabit yıldızların ezoterik mesajı (Spica, Algol, Regulus vb.)
5. Deklinasyon paralelleri — görünmez konjonksiyonlar ve gizli müttefikler
6. Midpoint yapıları — karmaşık gezegen birleşimlerindeki saklı mesajlar
7. Ay fazı (lunation cycle) — doğumdaki Ay fazının yaşam ritmi ve spiritüel misyona etkisi
8. Bu ezoterik haritanın bütünsel yorumu — tüm gizli göstergeler ne söylüyor
""",
        "timing": """
## ZAMANLAMA TEKNİKLERİ — DÖNEM ANALİZİ
Yukarıdaki verileri kullanarak birden fazla zamanlama tekniğini sentezleyerek dönem analizi yap:
1. Firdaria Kronokrator — şu anki dönemin yöneticisi ve alt dönem: bu kombinasyonun tonu ve odağı
2. Vimshottari Dasha ana + alt dönem — Vedik zamanlama katmanı
3. Solar Return — bu yılın başlangıcı ve yıl boyunca aktif olacak ana tema
4. Lunar Return — bu aydaki odak ve duygusal iklim
5. Tutulmalar — yakın dönem tutulmalarının zamanlama üzerindeki aktivasyon etkisi
6. Transit tetikleyiciler — büyük gezegenlerin natal noktalara kritik geçiş tarihleri
7. Tüm tekniklerin sentezi — hangi dönemler birden fazla teknik tarafından öne çıkarılıyor
8. Önümüzdeki 3-6 ay için en kritik tarih aralıkları ve o dönemlerde aktif enerji temaları
""",
        "health_energy": """
## SAĞLIK & ENERJİ — VİTALİTE PROFİLİ
Yukarıdaki verileri kullanarak sağlık ve enerji potansiyelini çok katmanlı yorumla:
1. Beden vitalitenin temel haritası — Yükselen ve 1. ev beden yapısını nasıl şekillendiriyor
2. Chiron — ruhsal yara ve bedensel zayıflık noktası; haritada nerede konumlanıyor ve ne anlam taşıyor
3. Mars enerjisi — fiziksel güç kaynağı, enerji boşalma biçimi, yorgunluk kalıpları
4. Satürn — kronik zayıflıklar ve hangi beden alanlarında dikkat gerektiren yapısal eğilimler
5. Sabit yıldızların sağlık bağlantıları — kritik yıldız bağlantıları varsa yorumla
6. Deklinasyon paralelleri — gizli sağlık bağlantıları ve enerji ittifakları
7. Gezegen dignity skorları — zayıf gezegenlerin ilişkili olduğu organ/sistem eğilimleri
8. Solar Return sağlık ev vurguları — bu yıl öne çıkan sağlık temaları
9. Transit tetikleyiciler — yakın dönemde aktif olan sağlık enerji penceresi
10. Ay fazı ve beden ritmi — enerji dalgalanmalarının döngüsel yapısı
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
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Sen dünyanın en iyi astroloğusun."},
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
