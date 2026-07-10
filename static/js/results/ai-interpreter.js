/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS AI INTERPRETER — Streaming Edition
 * SSE (Server-Sent Events) ile chunk chunk typewriter render
 * ═══════════════════════════════════════════════════════════════════════════
 */

// Global state
window.currentInterpretationText = "";

const interpretationTitles = {
  birth_chart:          "Doğum Haritası & Karakter",
  relationship:         "İlişki Analizi",
  psychological_karmic: "Psikolojik & Karmik",
  daily:                "Günlük Enerji",
  transits:             "Aktif Gezegenler",
  short_term:           "Kısa Vadeli (1-3 Ay)",
  long_term:            "Uzun Vadeli (Yıllık)",
  career:               "Kariyer & Meslek",
  finance:              "Finansal",
  health:               "Sağlık",
  spiritual:            "Ruhsal Gelişim",
  summary:              "Kozmik Özet",
  vedic:                "Vedik Astroloji",
  eclipses:             "Tutulma Etkileri",
  harmonic:             "Harmonik Rezonans",
  esoteric:             "Ezoterik Etkiler",
  timing:               "Zamanlama Teknikleri",
  health_energy:        "Sağlık & Enerji",
};

// ─── Frontend DATA_FILTER — backend ai_service.py ile senkron ───────────────
const DATA_FILTER = {
  birth_chart: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "natal_dignity_scores","natal_declinations",
    "natal_midpoint_analysis","navamsa_chart",
    "vimshottari_dasa","firdaria_periods",
    "eclipses_nearby_birth","natal_lunation_cycle","natal_fixed_stars",
  ],
  relationship: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "natal_antiscia","natal_dignity_scores",
    "natal_arabic_parts","natal_declinations",
    "natal_midpoint_analysis","navamsa_chart",
    "natal_lunation_cycle","natal_fixed_stars","natal_part_of_fortune",
  ],
  psychological_karmic: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "natal_dignity_scores","natal_declinations",
    "natal_midpoint_analysis","deep_harmonic_analysis",
    "natal_lunation_cycle","natal_fixed_stars",
    "vimshottari_dasa","firdaria_periods",
    "eclipses_nearby_birth","natal_antiscia",
  ],
  // daily: solar_return ve lunar_return YOK (sadece bugünkü transitler)
  daily: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "transit_positions","transit_to_natal_aspects",
    "natal_aspects","natal_additional_points",
    "natal_lunation_cycle","eclipses_nearby_current",
  ],
  transits: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "transit_positions","transit_to_natal_aspects",
    "solar_return_chart","lunar_return_chart",
    "natal_aspects","natal_declinations",
    "eclipses_nearby_current","natal_lunation_cycle",
    "firdaria_periods","natal_fixed_stars",
  ],
  short_term: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "transit_positions","transit_to_natal_aspects",
    "solar_return_chart","lunar_return_chart",
    "natal_aspects","natal_additional_points",
    "eclipses_nearby_current","natal_lunation_cycle","firdaria_periods",
  ],
  long_term: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "transit_positions","transit_to_natal_aspects",
    "vimshottari_dasa","firdaria_periods",
    "solar_return_chart","deep_harmonic_analysis",
    "eclipses_nearby_current","natal_lunation_cycle","natal_aspects",
  ],
  career: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_dignity_scores",
    "natal_midpoint_analysis","natal_fixed_stars",
    "solar_return_chart","firdaria_periods",
    "transit_positions","transit_to_natal_aspects","natal_arabic_parts",
  ],
  health: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "natal_fixed_stars","natal_declinations",
    "solar_return_chart","transit_positions",
    "transit_to_natal_aspects","natal_lunation_cycle",
  ],
  finance: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_arabic_parts",
    "natal_part_of_fortune","natal_dignity_scores",
    "solar_return_chart","transit_positions","transit_to_natal_aspects",
  ],
  spiritual: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","deep_harmonic_analysis",
    "navamsa_chart","vimshottari_dasa",
    "natal_lunation_cycle","natal_fixed_stars",
    "natal_antiscia","natal_declinations","natal_midpoint_analysis",
  ],
  summary: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_summary_interpretation","transit_positions","transit_to_natal_aspects",
  ],
  vedic: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "vimshottari_dasa","firdaria_periods",
    "navamsa_chart","deep_harmonic_analysis",
    "natal_dignity_scores","natal_lunation_cycle","natal_fixed_stars",
  ],
  eclipses: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "eclipses_nearby_birth","eclipses_nearby_current",
    "transit_positions","transit_to_natal_aspects","natal_lunation_cycle",
  ],
  harmonic: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","deep_harmonic_analysis",
    "navamsa_chart","natal_midpoint_analysis",
    "natal_antiscia","natal_declinations","natal_dignity_scores",
  ],
  esoteric: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "natal_antiscia","natal_arabic_parts",
    "natal_declinations","natal_part_of_fortune",
    "natal_midpoint_analysis","natal_fixed_stars",
    "deep_harmonic_analysis","natal_lunation_cycle",
  ],
  timing: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","vimshottari_dasa","firdaria_periods",
    "solar_return_chart","lunar_return_chart",
    "transit_positions","transit_to_natal_aspects",
    "eclipses_nearby_current","eclipses_nearby_birth","natal_lunation_cycle",
  ],
  health_energy: [
    "natal_planet_positions","natal_houses","natal_ascendant",
    "natal_aspects","natal_additional_points",
    "natal_fixed_stars","natal_declinations",
    "natal_dignity_scores","natal_lunation_cycle",
    "solar_return_chart","transit_positions",
    "transit_to_natal_aspects","natal_midpoint_analysis",
  ],
};

// ─── Yardımcı: astroData'yı türe göre filtrele ──────────────────────────────
function filterAstroData(type) {
  const astroData = window.astroData || {};
  const allowedKeys = DATA_FILTER[type];
  if (!allowedKeys) return astroData;
  const filtered = {};
  for (const key of allowedKeys) {
    if (astroData[key] !== undefined) filtered[key] = astroData[key];
  }
  console.log(`[AI] ${type}: ${Object.keys(filtered).length}/${Object.keys(astroData).length} key gönderildi`);
  return filtered;
}

// ─── Markdown → HTML (hafif, kütüphane bağımlılığı yok) ─────────────────────
function renderMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/^#### (.+)$/gm, '<h4 class="text-base font-bold text-white mt-5 mb-2">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-bold text-white mt-6 mb-3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold text-primary mt-7 mb-4">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mt-8 mb-4">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em class="text-slate-300 italic">$1</em>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 mb-1.5 flex items-start gap-2"><span class="text-primary mt-0.5 shrink-0">•</span><span>$1</span></li>')
    .replace(/\n\n/g, '</p><p class="mb-3 text-slate-300 leading-relaxed text-sm">')
    .replace(/\n/g, '<br>');
}

// ─── Loading UI ──────────────────────────────────────────────────────────────
function showLoadingUI($body, type) {
  $body.html(`
    <div class="flex flex-col items-center justify-center py-10 gap-4">
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay:0ms"></div>
        <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay:150ms"></div>
        <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay:300ms"></div>
      </div>
      <p class="text-sm text-slate-400 text-center">Yorum hazırlanıyor...</p>
      <p class="text-[10px] text-slate-600 text-center max-w-[260px] mt-2">
        ⚠️ Bu yorumlar yapay zeka tarafından matematiksel astroloji hesaplamalarına dayanarak oluşturulmuştur. Eğlence amaçlıdır.
      </p>
    </div>
  `);
}

// ─── Streaming container hazırla ────────────────────────────────────────────
function prepareStreamingContainer($body) {
  $body.html(`
    <div id="ai-stream-content" class="text-sm text-slate-300 leading-relaxed ai-interpretation px-1"></div>
    <div id="ai-stream-cursor" class="inline-block w-0.5 h-4 bg-primary animate-pulse ml-0.5 align-middle"></div>
  `);
}

// ─── ANA FONKSİYON — streaming ile yorum al ─────────────────────────────────
async function interpretTab(type) {
  openAIModal();
  const $body = $("#ai-modal-body");
  const $title = $("#ai-modal-title");

  $title.text(interpretationTitles[type] || "AI Analizi");
  showLoadingUI($body, type);

  const astroData = window.astroData || {};
  const sendData  = filterAstroData(type);
  const userName  = astroData.user_name || astroData.birth_info?.user_name || "Kullanıcı";

  const startTime = Date.now();
  let   fullText  = "";
  let   started   = false;

  try {
    const response = await fetch("/api/get_ai_interpretation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interpretation_type: type,
        astro_data:          sendData,
        user_name:           userName,
        stream:              true,
      }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const reader      = response.body.getReader();
    const decoder     = new TextDecoder("utf-8");
    let   sseBuffer   = "";

    // ── SSE okuma döngüsü ────────────────────────────────────────
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      sseBuffer += decoder.decode(value, { stream: true });
      const lines = sseBuffer.split("\n");
      sseBuffer = lines.pop(); // Tamamlanmamış satırı buffer'da tut

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        let msg;
        try { msg = JSON.parse(raw); } catch { continue; }

        if (msg.type === "chunk" && msg.content) {
          // İlk chunk geldiğinde loading UI → streaming container
          if (!started) {
            started = true;
            prepareStreamingContainer($body);
          }
          fullText += msg.content;

          // Render: ham metni markdown'a çevir, canlı güncelle
          const html = renderMarkdown(fullText);
          const el = document.getElementById("ai-stream-content");
          if (el) el.innerHTML = `<p class="mb-3 text-slate-300 leading-relaxed text-sm">${html}</p>`;

          // Modal'ı otomatik scroll ettir
          const modalBody = document.getElementById("ai-modal-body");
          if (modalBody) modalBody.scrollTop = modalBody.scrollHeight;
        }

        if (msg.type === "done") {
          // Cursor'ı kaldır, süre bilgisini göster
          const cursor = document.getElementById("ai-stream-cursor");
          if (cursor) cursor.remove();

          const elapsed = Math.round((Date.now() - startTime) / 1000);
          const infoEl  = document.createElement("div");
          infoEl.className = "text-[10px] text-slate-600 mt-4 pt-3 border-t border-white/5";
          infoEl.textContent = `✨ ${elapsed} saniyede tamamlandı`;
          document.getElementById("ai-stream-content")?.appendChild(infoEl);

          window.currentInterpretationText = fullText;
          // TTS butonu aktif et
          if (typeof updateTTSButton === "function") updateTTSButton(true);
          break;
        }

        if (msg.type === "error") {
          throw new Error(msg.message || "Bilinmeyen hata");
        }
      }
    }

    // Eğer hiç chunk gelmediyse (boş yanıt)
    if (!started) throw new Error("Yanıt alınamadı");

  } catch (error) {
    console.error("[AI] Streaming hatası:", error);
    $body.html(`
      <div class="flex flex-col items-center gap-3 py-8 text-center">
        <span class="material-icons-round text-4xl text-red-400">error_outline</span>
        <p class="text-red-400 text-sm">${error.message || "Bağlantı hatası"}</p>
        <button onclick="interpretTab('${type}')"
          class="mt-2 px-4 py-2 bg-primary/20 border border-primary/30 rounded-xl text-xs text-primary">
          Tekrar Dene
        </button>
      </div>
    `);
  }
}

// ─── Modal aç/kapat ─────────────────────────────────────────────────────────
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
  if (typeof TTS !== "undefined" && TTS.status !== "idle") TTS.stop();
}

// ─── Export (test ortamları için) ────────────────────────────────────────────
if (typeof module !== "undefined" && module.exports) {
  module.exports = { interpretTab, openAIModal, closeAIModal, filterAstroData, renderMarkdown };
}
