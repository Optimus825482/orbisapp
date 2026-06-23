/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS RESULTS TABS
 * Tab switching functionality for results page
 * ═══════════════════════════════════════════════════════════════════════════
 */

function switchResultTab(tabId) {
  $(".tab-content").removeClass("active");
  $("#tab-" + tabId).addClass("active");

  $(".result-tab-btn")
    .removeClass("active bg-primary text-white shadow-lg shadow-primary/20")
    .addClass("text-slate-400");
  $("#tab-" + tabId + "-btn")
    .addClass("active bg-primary text-white shadow-lg shadow-primary/20")
    .removeClass("text-slate-400");

  window.scrollTo({ top: 0, behavior: "smooth" });

  // Harita sekmesi açıldığında çizimi tetikle
  if (tabId === "chart" && typeof renderAstroChart === "function") {
    setTimeout(renderAstroChart, 200);
  }
}

function shareResults() {
  if (navigator.share) {
    navigator
      .share({
        title: "ORBIS Kozmik Raporum",
        text: "Kaderin Geometrisi raporumu Keşfedin!",
        url: window.location.href,
      })
      .catch(console.error);
  } else {
    navigator.clipboard.writeText(window.location.href).then(() => {
      alert("Link kopyalandı!");
    });
  }
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { switchResultTab, shareResults };
}
