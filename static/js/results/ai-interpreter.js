/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS AI INTERPRETER
 * Handles AI interpretation requests and modal display
 * ═══════════════════════════════════════════════════════════════════════════
 */

// Global state
window.currentInterpretationText = "";

const interpretationTitles = {
  birth_chart: "Doğum Haritası Analizi",
  relationship: "İlişki Analizi",
  psychological_karmic: "Psikolojik & Karmik Analiz",
  daily: "Günlük Yorum",
  transits: "Transit Analizi",
  short_term: "Kısa Vadeli Öngörü",
  long_term: "Uzun Vadeli Öngörü",
  career: "Kariyer Analizi",
  health: "Sağlık Analizi",
  finance: "Finansal Analiz",
  spiritual: "Ruhsal Gelişim",
  summary: "Kozmik Özet",
};

async function interpretTab(type) {
  openAIModal();
  const $body = $("#ai-modal-body");
  const $title = $("#ai-modal-title");

  $title.text(interpretationTitles[type] || "AI Analizi");

  // Dinamik geri sayım sayacı
  const startTime = Date.now();
  $body.html(`
        <div class="flex flex-col items-center justify-center py-12 gap-5">
            <div class="relative w-20 h-20">
                <svg class="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                    <circle class="text-slate-700/40" stroke="currentColor" stroke-width="4" fill="none" cx="40" cy="40" r="34"/>
                    <circle id="ai-progress-ring" class="text-primary" stroke="currentColor" stroke-width="4" fill="none" cx="40" cy="40" r="34"
                        stroke-dasharray="213.6" stroke-dashoffset="0" stroke-linecap="round"/>
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                    <span id="ai-elapsed" class="text-lg font-bold text-slate-300">0sn</span>
                </div>
            </div>
            <p id="ai-status-text" class="text-sm text-slate-400">Kozmik veriler analiz ediliyor...</p>
        </div>
    `);

  // Gerçek zamanlı sayaç
  const elapsedEl = document.getElementById("ai-elapsed");
  const statusEl = document.getElementById("ai-status-text");
  const ringEl = document.getElementById("ai-progress-ring");
  const tick = setInterval(() => {
    const sec = Math.round((Date.now() - startTime) / 1000);
    if (elapsedEl) elapsedEl.textContent = sec + "sn";
    if (ringEl) {
      const offset = Math.max(0, 213.6 - (sec / 45) * 213.6);
      ringEl.style.strokeDashoffset = offset;
    }
    if (statusEl) {
      if (sec < 10) statusEl.textContent = "Kozmik veriler analiz ediliyor...";
      else if (sec < 25) statusEl.textContent = "Gezegen pozisyonları değerlendiriliyor...";
      else if (sec < 45) statusEl.textContent = "Açılar ve ev etkileşimleri yorumlanıyor...";
      else if (sec < 65) statusEl.textContent = "Tüm veriler sentezleniyor...";
      else statusEl.textContent = "Neredeyse tamam, son rötuşlar...";
    }
  }, 1000);

  try {
    const astroData = window.astroData || {};
    const response = await fetch("/api/get_ai_interpretation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interpretation_type: type,
        astro_data: astroData,
        user_name: astroData.user_name || astroData.birth_info?.user_name || "Kullanıcı",
      }),
    });

    clearInterval(tick);
    const elapsed = Math.round((Date.now() - startTime) / 1000);
    const result = await response.json();

    if (result.success) {
      window.currentInterpretationText = result.interpretation;
      $body.html(`
                <div class="text-[10px] text-slate-500 mb-2">✨ ${elapsed} saniyede hazırlandı</div>
                ${marked.parse(result.interpretation)}
            `);
    } else {
      $body.html(`
                <div class="text-center py-8">
                    <span class="material-icons-round text-4xl text-red-400 mb-4">error_outline</span>
                    <p class="text-red-400">${result.error || "Bir hata oluştu"}</p>
                    <p class="text-xs text-slate-500 mt-2">${elapsed} saniye sonra başarısız</p>
                </div>
            `);
    }
  } catch (error) {
    clearInterval(tick);
    console.error("Interpretation error:", error);
    $body.html(`
            <div class="text-center py-8">
                <span class="material-icons-round text-4xl text-red-400 mb-4">wifi_off</span>
                <p class="text-red-400">Bağlantı hatası. Lütfen tekrar deneyin.</p>
            </div>
        `);
  }
}

function openAIModal() {
  const modal = document.getElementById("ai-modal");
  if (modal) {
    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }
}

function closeAIModal() {
  const modal = document.getElementById("ai-modal");
  if (modal) {
    modal.classList.add("hidden");
    document.body.style.overflow = "";
  }
  // TTS'i durdur
  if (typeof TTS !== "undefined" && TTS.status !== "idle") {
    TTS.stop();
  }
}

function formatInterpretation(text) {
  if (!text) return "";
  let formatted = text
    .replace(
      /\*\*(.*?)\*\*/g,
      '<strong class="text-white font-semibold">$1</strong>'
    )
    .replace(/\n\n/g, '</p><p class="mb-4">')
    .replace(
      /### (.*)/g,
      '<h3 class="text-lg font-bold text-white mt-6 mb-3">$1</h3>'
    )
    .replace(
      /## (.*)/g,
      '<h2 class="text-xl font-bold text-white mt-8 mb-4">$1</h2>'
    )
    .replace(
      /- (.*)/g,
      '<li class="ml-4 mb-2 flex items-start gap-2"><span class="text-primary mt-1">•</span> $1</li>'
    );
  return `<p class="mb-4">${formatted}</p>`;
}

// Export
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    interpretTab,
    openAIModal,
    closeAIModal,
    formatInterpretation,
  };
}
