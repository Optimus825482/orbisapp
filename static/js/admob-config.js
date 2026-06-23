/**
 * ORBIS AdMob Config — tek kaynak.
 * Hem mobile (mobile/www/js/admob.js) hem web (static/js/mobile-bridge.js) import eder.
 *
 * Üretim birim ID'leri AdMob panelinden gelir. rewardedInterstitial ve rewardedAnalysis
 * ayrı birim olmalı (raporlama için); biri boşsa diğeri fallback kullanır.
 *
 * Test ID'leri Google official: ca-app-pub-3940256099942544/...
 */
(function () {
  "use strict";

  const IS_TEST = false; // production: false

  const AD_UNITS = {
    appId: {
      prod: "ca-app-pub-2444093901783574~9279937953",
      test: "ca-app-pub-3940256099942544~3347511713",
    },
    banner: {
      prod: "ca-app-pub-2444093901783574/1791137239",
      test: "ca-app-pub-3940256099942544/6300978111",
    },
    interstitial: {
      prod: "ca-app-pub-2444093901783574/8681172156",
      test: "ca-app-pub-3940256099942544/1033173712",
    },
    rewardedInterstitial: {
      // Genel ödüllü geçiş — mobile-bridge CONFIG.REWARDED
      prod: "ca-app-pub-2444093901783574/9994253824",
      test: "ca-app-pub-3940256099942544/5224354917",
    },
    rewardedAnalysis: {
      // Analiz için ödüllü — AdMob panelinde AYRI birim AÇILDI
      // (önceden 9994253824 shared). Boşsa rewardedInterstitial'a fallback.
      prod: "ca-app-pub-2444093901783574/3701964485",
      test: "ca-app-pub-3940256099942544/5224354917",
    },
  };

  function unit(key) {
    const u = AD_UNITS[key];
    if (!u) return null;
    return u[IS_TEST ? "test" : "prod"];
  }

  function rewardedAnalysisId() {
    // Analiz için ayrı birim; boşsa rewardedInterstitial fallback.
    const id = unit("rewardedAnalysis");
    return id || unit("rewardedInterstitial");
  }

  window.ADMOB_CONFIG = {
    IS_TEST: IS_TEST,
    AD_UNITS: AD_UNITS,
    appId: unit("appId"),
    bannerId: unit("banner"),
    interstitialId: unit("interstitial"),
    rewardedInterstitialId: unit("rewardedInterstitial"),
    rewardedAnalysisId: rewardedAnalysisId(),
    unit: unit,
    rewardedAnalysisUnit: rewardedAnalysisId,
  };
})();