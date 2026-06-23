/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS COSMIC MODAL LOADER
 * Sayfanın ortasında modal dialog tarzında loading experience
 * Progress bar ve scrolling messages ile
 * ═══════════════════════════════════════════════════════════════════════════
 */

const CosmicLoader = {
  overlay: null,
  progressFill: null,
  progressPercent: null,
  currentProgress: 0,
  targetProgress: 0,
  animationFrame: null,
  isComplete: false,

  init() {
    this.overlay = document.getElementById("cosmic-loader-overlay");
    this.progressFill = document.getElementById("cosmic-progress-fill");
    this.progressPercent = document.getElementById("cosmic-progress-percent");

    if (this.overlay) {
      // Progress animasyonunu başlat
      this.animateProgress();
    }
  },

  // Progress bar'ı belirli bir yüzdeye ayarla
  setProgress(percent) {
    this.targetProgress = Math.min(100, Math.max(0, percent));
  },

  // Smooth progress animasyonu
  animateProgress() {
    const animate = () => {
      if (this.currentProgress < this.targetProgress) {
        // Yavaşça hedefe yaklaş
        const diff = this.targetProgress - this.currentProgress;
        const increment = Math.max(0.5, diff * 0.1);
        this.currentProgress = Math.min(
          this.targetProgress,
          this.currentProgress + increment
        );

        // DOM güncelle
        if (this.progressFill) {
          this.progressFill.style.width = `${this.currentProgress}%`;
        }
        if (this.progressPercent) {
          this.progressPercent.textContent = `${Math.round(
            this.currentProgress
          )}%`;
        }
      }

      if (!this.isComplete) {
        this.animationFrame = requestAnimationFrame(animate);
      }
    };

    animate();
  },

  // Adım tamamlandığında çağrılır (1-5 arası)
  completeStep(stepNumber) {
    // Her adım %20 progress
    const newProgress = stepNumber * 20;
    this.setProgress(newProgress);

    // Tüm adımlar tamamlandıysa loader'ı kapat
    if (stepNumber >= 5) {
      this.setProgress(100);
      setTimeout(() => this.hideLoader(), 600);
    }
  },

  // Loader'ı gizle
  hideLoader() {
    if (this.overlay && !this.isComplete) {
      this.isComplete = true;

      // Animasyonu durdur
      if (this.animationFrame) {
        cancelAnimationFrame(this.animationFrame);
      }

      // Fade out
      this.overlay.classList.add("hidden");
    }
  },

  // Zorla kapat (hata durumunda)
  forceHide() {
    if (this.overlay) {
      this.isComplete = true;
      if (this.animationFrame) {
        cancelAnimationFrame(this.animationFrame);
      }
      this.overlay.classList.add("hidden");
    }
  },

  // Loader'ı tekrar göster (refresh için)
  show() {
    if (this.overlay) {
      this.isComplete = false;
      this.currentProgress = 0;
      this.targetProgress = 0;

      if (this.progressFill) {
        this.progressFill.style.width = "0%";
      }
      if (this.progressPercent) {
        this.progressPercent.textContent = "0%";
      }

      this.overlay.classList.remove("hidden");
      this.animateProgress();
    }
  },
};

// Simüle edilmiş adım tamamlama (görsel efekt için)
function simulateLoaderSteps() {
  // Adım 1: Kozmik Özet (API'den gelecek, burada simüle etmiyoruz)
  // Adım 2-5: Diğer analizler (simüle)
  setTimeout(() => CosmicLoader.completeStep(2), 1500);
  setTimeout(() => CosmicLoader.completeStep(3), 2500);
  setTimeout(() => CosmicLoader.completeStep(4), 3500);
  setTimeout(() => CosmicLoader.completeStep(5), 4500);
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { CosmicLoader, simulateLoaderSteps };
}
