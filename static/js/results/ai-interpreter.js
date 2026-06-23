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
  $body.html(`
        <div class="flex flex-col items-center justify-center py-16 gap-4">
            <div class="w-12 h-12 rounded-full border-2 border-primary/30 border-t-primary animate-spin"></div>
            <p class="text-sm text-slate-400">Kozmik veriler analiz ediliyor...</p>
        </div>
    `);

  try {
    const response = await fetch("/api/get_ai_interpretation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interpretation_type: type,
        astro_data: window.astroData,
        user_name: window.astroData?.user_name || "Kullanıcı",
      }),
    });

    const result = await response.json();

    if (result.success) {
      window.currentInterpretationText = result.interpretation;
      $body.html(marked.parse(result.interpretation));
    } else {
      $body.html(`
                <div class="text-center py-8">
                    <span class="material-icons-round text-4xl text-red-400 mb-4">error_outline</span>
                    <p class="text-red-400">${
                      result.error || "Bir hata oluştu"
                    }</p>
                </div>
            `);
    }
  } catch (error) {
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
