/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS COSMIC MODAL LOADER - Dinamik Geri Sayım
 * SVG ring + saniye sayacı + gizemli dönen mesajlar
 * ═══════════════════════════════════════════════════════════════════════════
 */

const CosmicLoader = {
  overlay: null,
  ringEl: null,
  elapsedEl: null,
  statusEl: null,
  disclaimerEl: null,
  greetingEl: null,
  tickInterval: null,
  startTime: 0,
  isComplete: false,

  // Gizemli dönen mesajlar
  statusMessages: [
    "Doğum haritanız hazırlanıyor...",
    "Gezegenlerin konumları Swiss Ephemeris ile hesaplandı...",
    "139 gezegen açısından en önemlileri seçiliyor...",
    "Ev yerleşimleri ve yükselen burcunuz analiz ediliyor...",
    "Vedik astroloji hesaplamaları (Navamsa) yapılıyor...",
    "Sabit yıldızların etkileri değerlendiriliyor...",
    "İleri seviye yapay zeka modelleri verileri yorumluyor...",
    "AI astrolojik pattern'leri tanımlıyor...",
    "Gezegen yerleşimleri yaşam alanlarına göre sınıflandırılıyor...",
    "Transit etkileri natal haritanızla karşılaştırılıyor...",
    "Kişisel yaşam temalarınız belirleniyor...",
    "Tüm astrolojik göstergeler birleştiriliyor...",
    "Kapsamlı yorum metni oluşturuluyor...",
    "Kariyer, ilişki, sağlık ve finans başlıkları hazırlanıyor...",
    "Spiritüel ve karmik içgörüler ekleniyor...",
    "Size özel tavsiyeler formüle ediliyor...",
    "Son rötuşlar yapılıyor, az kaldı...",
    "Kozmik mesajınız neredeyse hazır...",
    "Astroloji bir rehberdir, nihai karar her zaman size aittir...",
    "Yıldızlar eğilimleri gösterir, kaderi değil...",
    "Bu yorumlar eğlence amaçlıdır, sezgilerinize güvenin...",
    "ORBIS'in uzman AI modelleri size özel yorumunuzu hazırlıyor...",
  ],

  init() {
    this.overlay = document.getElementById("cosmic-loader-overlay");
    this.ringEl = document.getElementById("cosmic-progress-ring");
    this.elapsedEl = document.getElementById("cosmic-elapsed-sec");
    this.statusEl = document.getElementById("cosmic-status-msg");
    this.disclaimerEl = document.getElementById("cosmic-disclaimer");
    this.greetingEl = document.getElementById("cosmic-greeting-text");

    if (!this.overlay) return;

    this.startTime = Date.now();
    let lastMsgIdx = -1;

    this.tickInterval = setInterval(() => {
      const sec = Math.round((Date.now() - this.startTime) / 1000);

      // Saniye sayacı
      if (this.elapsedEl) this.elapsedEl.textContent = sec + "sn";

      // SVG ring: 60sn'de tamamlanacak şekilde dolsun
      if (this.ringEl) {
        const progress = Math.min(sec / 55, 1);
        this.ringEl.style.strokeDashoffset = 213.6 * (1 - progress);
      }

      // Her ~2.5sn'de mesaj değiştir
      const msgIdx = Math.floor(sec / 2.5) % this.statusMessages.length;
      if (msgIdx !== lastMsgIdx && this.statusEl) {
        this.statusEl.textContent = this.statusMessages[msgIdx];
        lastMsgIdx = msgIdx;
      }

      // 12sn sonra disclaimer
      if (sec >= 12 && this.disclaimerEl && this.disclaimerEl.classList.contains("hidden")) {
        this.disclaimerEl.classList.remove("hidden");
      }

      // 15sn sonra greeting güncelle
      if (sec >= 15 && this.greetingEl && this.greetingEl.dataset.updated !== "1") {
        this.greetingEl.textContent = "Analizlerin neredeyse hazır, az kaldı...";
        this.greetingEl.dataset.updated = "1";
      }
    }, 1000);
  },

  // AI yorumu geldiğinde: ring full, loader'ı kapat
  completeStep(stepNumber) {
    // Bu fonksiyon artık sadece hideLoader'ı tetikler
    if (stepNumber >= 5) {
      this.hideLoader();
    }
  },

  // Loader'ı fade-out ile gizle
  hideLoader() {
    if (!this.overlay || this.isComplete) return;
    this.isComplete = true;

    if (this.tickInterval) {
      clearInterval(this.tickInterval);
      this.tickInterval = null;
    }

    // Ring'i full yap
    if (this.ringEl) {
      this.ringEl.style.strokeDashoffset = "0";
    }
    if (this.elapsedEl) {
      this.elapsedEl.textContent = "✓";
      this.elapsedEl.style.color = "#22c55e";
    }

    // 500ms sonra gizle
    setTimeout(() => {
      this.overlay.classList.add("hidden");
    }, 500);
  },

  // Hata durumunda hemen gizle
  forceHide() {
    if (!this.overlay) return;
    this.isComplete = true;

    if (this.tickInterval) {
      clearInterval(this.tickInterval);
      this.tickInterval = null;
    }

    this.overlay.classList.add("hidden");
  },

  // Manuel tekrar göster
  show() {
    if (!this.overlay) return;
    this.isComplete = false;
    this.startTime = Date.now();

    if (this.ringEl) this.ringEl.style.strokeDashoffset = "213.6";
    if (this.elapsedEl) { this.elapsedEl.textContent = "0sn"; this.elapsedEl.style.color = ""; }
    if (this.disclaimerEl) this.disclaimerEl.classList.add("hidden");
    if (this.greetingEl) { this.greetingEl.textContent = "Hesaplamaların tamamlandı, şimdi yapay zeka yorumlarını hazırlıyorum..."; this.greetingEl.dataset.updated = "0"; }

    this.overlay.classList.remove("hidden");
    this.init();
  },
};

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { CosmicLoader };
}
