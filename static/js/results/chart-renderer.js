/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS CHART RENDERER
 * Handles astrological chart rendering using AstroChart library
 * ═══════════════════════════════════════════════════════════════════════════
 */

let chartType = "natal";

function mapPlanetData(positions) {
  if (!positions) return [];
  const points = [];
  const mapping = {
    Sun: "Sun",
    Moon: "Moon",
    Mercury: "Mercury",
    Venus: "Venus",
    Mars: "Mars",
    Jupiter: "Jupiter",
    Saturn: "Saturn",
    Uranus: "Uranus",
    Neptune: "Neptune",
    Pluto: "Pluto",
    Chiron: "Chiron",
    Lilith: "Lilith",
    True_Node: "NNode",
    Mean_Node: "NNode",
    Ascendant: "Asc",
    MC: "Mc",
  };

  for (let key in positions) {
    const targetKey = mapping[key];
    if (targetKey && positions[key] && positions[key].degree !== undefined) {
      points.push({
        name: targetKey,
        angle: parseFloat(positions[key].degree),
        isRetrograde: positions[key].retrograde || false,
      });
    }
  }
  return points;
}

function renderAstroChart() {
  if (!window.astroData || !window.astrology) {
    console.warn(
      "[AstroChart] astroData veya astrology kütüphanesi bulunamadı"
    );
    return;
  }

  const containerId = "chart-paper";
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";

  const width = container.offsetWidth || 500;
  const settings = {
    CHART_PADDING: 20,
    CHART_VIEWBOX_WIDTH: width,
    CHART_VIEWBOX_HEIGHT: width,
    CHART_STROKE: 1,
    CHART_STROKE_ONLY: false,
    CHART_FONT_FAMILY: "system-ui, -apple-system, sans-serif",
    CHART_MAIN_STROKE: "#ffffff20",
    CHART_MAIN_FILL: "transparent",
    CHART_BG_COLOR: "transparent",
    ASPECTS_FONT_SIZE: 10,
    ASPECTS_LINE_WIDTH: 0.5,
    POINT_COLLISION_RADIUS: 12,
    POINT_PROPERTIES_SHOW: true,
    POINT_PROPERTIES_FONT_SIZE: 8,
    CUSPS_FONT_SIZE: 10,
    CUSPS_STROKE: 0.5,
    CUSPS_FONT_COLOR: "#94a3b8",
    SIGNS_STROKE: 0.5,
    SIGNS_FONT_SIZE: 14,
    SIGNS_COLOR: "#5b2bee",
    SYMBOL_SCALE: 0.8,
    SYMBOL_AXIS_FONT_SCALE: 0.8,
    SYMBOL_CUSP_FONT_SCALE: 0.7,
    SYMBOL_POINT_FONT_SCALE: 0.9,
    ANIMATION_DURATION: 500,
    ANIMATION_EASING: "easeOutQuad",
  };

  const aspectSettings = {
    conjunction: { degree: 0, orbit: 8, color: "#5b2bee" },
    opposition: { degree: 180, orbit: 8, color: "#f59e0b" },
    trine: { degree: 120, orbit: 8, color: "#38bdf8" },
    square: { degree: 90, orbit: 7, color: "#ef4444" },
    sextile: { degree: 60, orbit: 6, color: "#10b981" },
  };

  // Cusps hazırla
  const cusps = [];
  if (window.astroData.natal_houses?.house_cusps) {
    for (let i = 1; i <= 12; i++) {
      cusps.push({
        angle: parseFloat(window.astroData.natal_houses.house_cusps[i]),
      });
    }
  } else {
    for (let i = 0; i < 12; i++) {
      cusps.push({ angle: i * 30 });
    }
  }

  // Points hazırla
  let points;
  if (chartType === "natal") {
    points = mapPlanetData(window.astroData.natal_planet_positions);
  } else if (chartType === "transit" && window.astroData.transit_positions) {
    points = mapPlanetData(window.astroData.transit_positions);
  } else if (chartType === "solar" && window.astroData.solar_return_chart) {
    points = mapPlanetData(
      window.astroData.solar_return_chart.planet_positions
    );
  } else if (chartType === "navamsa" && window.astroData.navamsa_chart) {
    points = mapPlanetData(window.astroData.navamsa_chart);
  } else {
    points = mapPlanetData(window.astroData.natal_planet_positions);
  }

  const chartData = { points: points, cusps: cusps };

  try {
    // astrochart2 API: Universe -> radix() -> setData()
    const universe = new astrology.Universe(containerId, settings);
    const radix = universe.radix();
    radix.setData(chartData);
    radix.aspects(aspectSettings);
  } catch (e) {
    console.error("Chart render error:", e);
    container.innerHTML =
      '<p class="text-center text-slate-500 py-8">Harita yüklenemedi</p>';
  }
}

function setChartType(type) {
  chartType = type;
  document
    .querySelectorAll(".chart-selector-pill")
    .forEach((p) => p.classList.remove("active"));
  const pill = document.getElementById("pill-" + type);
  if (pill) pill.classList.add("active");
  renderAstroChart();
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { renderAstroChart, setChartType, mapPlanetData };
}
