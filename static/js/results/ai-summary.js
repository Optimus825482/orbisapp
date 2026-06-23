/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS AI SUMMARY MODULE
 * Handles AI-generated cosmic summary loading and display
 * ═══════════════════════════════════════════════════════════════════════════
 */

async function loadAISummary() {
  const $content = $("#ai-summary-content");
  const $btn = $("#refresh-summary-btn");

  // Loading state
  $content.html(`
        <div class="flex flex-col items-center gap-3 py-4 text-center">
            <div class="w-8 h-8 rounded-full border-2 border-accent/30 border-t-accent animate-spin"></div>
            <div>
                <p class="text-[11px] text-slate-400 font-medium">Lütfen bekleyin...</p>
                <p class="text-[10px] text-slate-500">Kozmik özet hazırlanıyor</p>
            </div>
        </div>
    `);
  $btn.prop("disabled", true).addClass("opacity-50");

  try {
    const response = await fetch("/api/get_ai_interpretation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interpretation_type: "summary",
        astro_data: window.astroData,
        user_name: window.astroData?.user_name || "Kullanıcı",
      }),
    });
    const result = await response.json();

    if (result.success) {
      $content.html(marked.parse(result.interpretation));
      if (typeof CosmicLoader !== "undefined") {
        CosmicLoader.completeStep(1);
      }
    } else {
      $content.html(
        `<p class="text-red-400 text-[11px]">Özet yüklenemedi: ${result.error}</p>`
      );
      if (typeof CosmicLoader !== "undefined") {
        CosmicLoader.forceHide();
      }
    }
  } catch (error) {
    $content.html(
      `<p class="text-red-400 text-[11px]">Bağlantı hatası. Lütfen tekrar deneyin.</p>`
    );
    if (typeof CosmicLoader !== "undefined") {
      CosmicLoader.forceHide();
    }
  } finally {
    $btn.prop("disabled", false).removeClass("opacity-50");
  }
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { loadAISummary };
}
