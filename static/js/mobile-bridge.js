/**
 * ORBIS Monetizasyon & Capacitor Bridge
 * - Sadece reklam destekli uygulama
 * - PREMIUM KALDIRILDI: Uygulama tamamen ucretsiz.
 *   Geriye uyumluluk icin state.isPremium her zaman false dondurulur,
 *   premium satin alma/paket gosterim fonksiyonlari no-op.
 *
 * KURALLAR:
 * - Her analiz icin Rewarded reklam ZORUNLU
 * - Banner + interstitial ek gelir
 * - Premium satin alma KAPALI
 */

const OrbisBridge = {
  // ═══════════════════════════════════════════════════════════════
  // YAPILANDIRMA
  // ═══════════════════════════════════════════════════════════════

  CONFIG: {
    // Ücretsiz kullanıcı limitleri
    // ARTIK HER ANALİZ İÇİN REKLAM ZORUNLU (Premium hariç)
    FREE_FIRST_DAY_TOTAL: 999, // Sınırsız (reklam izleyerek)
    FREE_FIRST_DAY_NO_AD: 0, // Reklamsız hak YOK
    FREE_DAILY_LIMIT: 999, // Sınırsız (reklam izleyerek)

    // Premium paketleri
    PREMIUM_PACKAGES: [
      { id: "daily", name: "Günlük", price: 30, credits: 0, months: 0 },
      { id: "monthly", name: "Aylık", price: 300, credits: 0, months: 1 },
      { id: "yearly", name: "Yıllık", price: 3000, credits: 0, months: 12 },
    ],

    // AdMob ID'leri — tek kaynak window.ADMOB_CONFIG (static/js/admob-config.js).
    // IS_TEST flag tek yerde; test/prod blokları kaldırıldı.
    ADMOB_CONFIG_REF: true, // window.ADMOB_CONFIG'ten beslenir
    ADMOB_FALLBACK: {
      // window.ADMOB_CONFIG yüklenmezse (script tag eksikse) fallback
      APP_ID: "ca-app-pub-2444093901783574~9279937953",
      BANNER: "ca-app-pub-2444093901783574/1791137239",
      INTERSTITIAL: "ca-app-pub-2444093901783574/8681172156",
      REWARDED: "ca-app-pub-2444093901783574/9994253824",
      REWARDED_ANALIZ: "ca-app-pub-2444093901783574/3701964485",
    },

    // Interstitial gösterim aralığı (her X analizde bir)
    INTERSTITIAL_INTERVAL: 3,

    // Test modu - Production için false
    IS_TESTING: false,
  },

  // ═══════════════════════════════════════════════════════════════
  // ADMOB CEZA KORUMASI - Geliştirici & Yönetici Hesapları
  // ═══════════════════════════════════════════════════════════════
  EXEMPT_EMAILS: [
    'ikinciyenikitap54@gmail.com',
    'erkanerdem8254@gmail.com',
    'djerkan8254@gmail.com'
  ],

  /**
   * AdSense / AdMob geçersiz tıklama cezası koruması:
   * Geliştirici veya hesap sahibi oturum açmışsa ASLA reklam yükleme veya gösterme!
   */
  isExemptUser() {
    try {
      const stored = (localStorage.getItem('orbis_user_email') || '').trim().toLowerCase();
      if (stored && this.EXEMPT_EMAILS.includes(stored)) return true;
      if (window.firebaseAuth?.user?.email && this.EXEMPT_EMAILS.includes(window.firebaseAuth.user.email.toLowerCase().trim())) return true;
      if (window.OrbisFirebase?.getCurrentUser()?.email && this.EXEMPT_EMAILS.includes(window.OrbisFirebase.getCurrentUser().email.toLowerCase().trim())) return true;
      if (window.firebase?.auth && window.firebase.auth().currentUser?.email && this.EXEMPT_EMAILS.includes(window.firebase.auth().currentUser.email.toLowerCase().trim())) return true;
    } catch (e) {
      console.warn("[ORBIS] isExemptUser kontrol hatası:", e);
    }
    return false;
  },

  /** AdMob config döndür — tek kaynak window.ADMOB_CONFIG; fallback CONFIG.ADMOB_FALLBACK. */
  _getAdmob() {
    const cfg = window.ADMOB_CONFIG;
    if (cfg) {
      return {
        APP_ID: cfg.appId,
        BANNER: cfg.bannerId,
        INTERSTITIAL: cfg.interstitialId,
        REWARDED: cfg.rewardedInterstitialId,
        REWARDED_ANALIZ: cfg.rewardedAnalysisId,
      };
    }
    return this.CONFIG.ADMOB_FALLBACK;
  },

  // ═══════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════

  state: {
    isNative: false,
    // Premium kaldirildi: her zaman false. Eski localStorage verileri temizlenir.
    isPremium: false,
    credits: 0,
    premiumPackageId: null, // Hangi premium paketi aldı (artik kullanilmiyor)

    // Ücretsiz kullanıcı için
    installDate: null, // İlk kurulum tarihi
    todayUsage: 0, // Bugünkü kullanım
    todayAdsWatched: 0, // Bugün izlenen reklam
    lastUsageDate: null, // Son kullanım tarihi
    totalAnalyses: 0, // Toplam analiz (interstitial için)

    // Premium için (artik kullanilmiyor)
    premiumExpiry: null, // Premium bitiş tarihi
  },

  // ═══════════════════════════════════════════════════════════════
  // FIRESTORE'DAN FİYAT YÜKLEME
  // ═══════════════════════════════════════════════════════════════

  async loadPricingFromServer() {
    try {
      const res = await fetch("/api/config/pricing");
      const json = await res.json();

      if (json.success && json.data) {
        const p = json.data;
        console.log("[ORBIS] Fiyatlar Firestore'dan yüklendi:", p);

        // PREMIUM_PACKAGES fiyatlarını güncelle
        const dailyPkg = this.CONFIG.PREMIUM_PACKAGES.find(x => x.id === "daily");
        const monthlyPkg = this.CONFIG.PREMIUM_PACKAGES.find(x => x.id === "monthly");
        const yearlyPkg = this.CONFIG.PREMIUM_PACKAGES.find(x => x.id === "yearly");

        if (dailyPkg) dailyPkg.price = p.daily || dailyPkg.price;
        if (monthlyPkg) monthlyPkg.price = p.monthly || monthlyPkg.price;
        if (yearlyPkg) yearlyPkg.price = p.yearly || yearlyPkg.price;

        this.CONFIG.PRICING_SOURCE = "firestore";
      }
    } catch (e) {
      console.log("[ORBIS] Fiyatlar sunucudan yüklenemedi, varsayılanlar kullanılacak:", e.message);
      this.CONFIG.PRICING_SOURCE = "default";
    }

    // UI'ı güncelle (fiyatlar değişmiş olabilir)
    this.updateUI();
  },

  // ═══════════════════════════════════════════════════════════════
  // PREMIUM DOĞRULAMA - localStorage'daki premium'u backend'den kontrol et
  // ═══════════════════════════════════════════════════════════════

  async verifyPremiumWithBackend() {
    // DEPRECATED: Premium kaldirildi. Eski premium state'lerini temizle.
    if (this.state.isPremium || this.state.premiumPackageId || this.state.premiumExpiry || this.state.credits > 0) {
      console.info("[ORBIS] Eski premium/credit state temizleniyor (premium kaldirildi).");
      this.state.isPremium = false;
      this.state.premiumPackageId = null;
      this.state.premiumExpiry = null;
      this.state.credits = 0;
      this.saveState();
    }
  },

  getDeviceId() {
    let id = localStorage.getItem("orbis_device_id");
    if (!id) {
      id = "dev_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
      localStorage.setItem("orbis_device_id", id);
    }
    return id;
  },

  // ═══════════════════════════════════════════════════════════════
  // BAŞLATMA
  // ═══════════════════════════════════════════════════════════════

  async init() {
    console.log("[ORBIS] Monetizasyon sistemi başlatılıyor...");

    // State'i yükle
    this.loadState();

    // Günlük reset kontrolü
    this.checkDailyReset();

    // ═══════════════════════════════════════════════════════════════
    // FIRESTORE'DAN FİYATLARI ÇEK
    // ═══════════════════════════════════════════════════════════════
    this.loadPricingFromServer();

    // ⚠️ KRİTİK: Premium doğrulama - localStorage'da premium varsa
    // backend'den kontrol et ve state'i düzelt. Bekle ki analiz
    // başlamadan premium durumu netleşsin.
    await this.verifyPremiumWithBackend();

    // ═══════════════════════════════════════════════════════════════
    // PLATFORM TESPİTİ (iyileştirilmiş)
    // ═══════════════════════════════════════════════════════════════
    
    // 1. Capacitor Native API kontrolü
    if (typeof Capacitor !== "undefined" && Capacitor.isNativePlatform()) {
      this.state.isNative = true;
      console.log("[ORBIS] Native platform tespit edildi (Capacitor API)");
    }
    // 2. UA kontrolü - Android/iOS
    else if (/android|ipad|iphone|ipod/i.test(navigator.userAgent)) {
      this.state.isNative = true;
      console.log("[ORBIS] Native platform tespit edildi (User-Agent)");
    }
    // 3. Dosya protokolü kontrolü (Capacitor WebView file:// ile çalışır)
    else if (location.protocol === 'file:' || location.protocol === 'capacitor:') {
      this.state.isNative = true;
      console.log("[ORBIS] Native platform tespit edildi (protocol)");
    }
    // 4. Capacitor varlık kontrolü (window seviyesinde)
    else if (typeof window.Capacitor !== 'undefined') {
      this.state.isNative = true;
      console.log("[ORBIS] Native platform tespit edildi (window.Capacitor)");
    }
    // 5. WebView kontrolü - navigator.webdriver false ise WebView olabilir
    else if (navigator.webdriver === false && /mobile|webview/i.test(navigator.userAgent)) {
      this.state.isNative = true;
      console.log("[ORBIS] Native platform tespit edildi (WebView)");
    }
    else {
      console.log("[ORBIS] Web platform");
      this.state.isNative = false;
    }

    // Native ise AdMob'u başlat
    if (this.state.isNative) {
      this.initAdMob();
      // ═══════════════════════════════════════════════════════════════
      // CAPACITOR BROWSER OAUTH CALLBACK LISTENER
      // Native Google Sign-In başarısız olduğunda Browser OAuth flow
      // kullanılır. Browser plugin'den dönen callback'i handle et.
      // ═══════════════════════════════════════════════════════════════
      this.initBrowserOAuthCallback();
    } else {
      // Web'de de AdMob'u dene (bazı WebView'lar Capacitor olmadan da AdMob çalıştırabilir)
      try { this.initAdMob(); } catch(e) { /* sessiz */ }
    }

    // Bildirim izni kontrolü & prompt (Hem Web/PWA hem Native)
    this.checkAndPromptNotificationPermission();

    // UI güncelle
    this.updateUI();

    console.log("[ORBIS] Durum:", this.getStatusSummary());

    // User properties ayarla
    this.setUserProperties({
      user_type: this.state.isPremium ? "premium" : "free",
      credits_available: this.state.credits,
      platform: this.state.isNative ? "mobile" : "web",
      install_date: this.state.installDate || "unknown",
    });

    // GA: Uygulama başlatma event'i
    this.trackEvent("app_start", {
      platform: this.state.isNative ? "native" : "web",
      is_premium: this.state.isPremium,
      credits: this.state.credits,
      total_analyses: this.state.totalAnalyses || 0,
    });
  },

  // ═══════════════════════════════════════════════════════════════
  // GOOGLE ANALYTICS TRACKING
  // ═══════════════════════════════════════════════════════════════

  /**
   * Google Analytics Event Gönder
   * @param {string} eventName - Event adı
   * @param {object} params - Event parametreleri
   */
  trackEvent(eventName, params = {}) {
    try {
      const enrichedParams = {
        ...params,
        timestamp: new Date().toISOString(),
        user_type: this.state.isPremium ? "premium" : "free",
        platform: this.state.isNative ? "mobile" : "web",
        session_id: this.getSessionId(),
      };

      // Google Analytics
      if (typeof gtag === "function") {
        gtag("event", eventName, enrichedParams);
        console.log(`[GA4] Event: ${eventName}`, enrichedParams);
      }

      // Firebase Analytics (native only)
      if (this.state.isNative && typeof Capacitor !== "undefined") {
        try {
          const { FirebaseAnalytics } = Capacitor.Plugins;
          if (FirebaseAnalytics) {
            FirebaseAnalytics.logEvent({
              name: eventName,
              params: this.sanitizeFirebaseParams(enrichedParams),
            });
            console.log(`[Firebase] Event: ${eventName}`);
          }
        } catch (fbError) {
          console.log("[Firebase] Analytics not available:", fbError.message);
        }
      }
    } catch (error) {
      console.error("[GA] Event tracking error:", error);
    }
  },

  /**
   * Firebase için parametre temizleme (max 100 karakter)
   */
  sanitizeFirebaseParams(params) {
    const sanitized = {};
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === "string" && value.length > 100) {
        sanitized[key] = value.substring(0, 97) + "...";
      } else if (typeof value === "object") {
        sanitized[key] = JSON.stringify(value).substring(0, 100);
      } else {
        sanitized[key] = value;
      }
    }
    return sanitized;
  },

  /**
   * Session ID oluştur/al
   */
  getSessionId() {
    let sessionId = sessionStorage.getItem("orbis_session_id");
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem("orbis_session_id", sessionId);
    }
    return sessionId;
  },

  /**
   * User properties ayarla
   */
  setUserProperties(properties) {
    try {
      if (typeof gtag === "function") {
        gtag("set", "user_properties", properties);
        console.log("[GA4] User properties set:", properties);
      }

      if (this.state.isNative && typeof Capacitor !== "undefined") {
        try {
          const { FirebaseAnalytics } = Capacitor.Plugins;
          if (FirebaseAnalytics) {
            for (const [key, value] of Object.entries(properties)) {
              FirebaseAnalytics.setUserProperty({ name: key, value: String(value) });
            }
          }
        } catch (fbError) {
          console.log("[Firebase] setUserProperty failed:", fbError.message);
        }
      }
    } catch (error) {
      console.error("[GA] User properties error:", error);
    }
  },

  /**
   * Conversion tracking
   */
  trackConversion(conversionType, value = 0, currency = "TRY") {
    this.trackEvent("conversion", {
      conversion_type: conversionType,
      value: value,
      currency: currency,
    });

    // Enhanced ecommerce için
    if (typeof gtag === "function" && value > 0) {
      gtag("event", "purchase", {
        transaction_id: `txn_${Date.now()}`,
        value: value,
        currency: currency,
        items: [
          {
            item_id: conversionType,
            item_name: conversionType,
            price: value,
            quantity: 1,
          },
        ],
      });
    }
  },

  /**
   * Error tracking
   */
  trackError(error, context = {}) {
    const errorData = {
      error_message: error.message || String(error),
      error_stack: error.stack ? error.stack.substring(0, 500) : "N/A",
      error_context: JSON.stringify(context).substring(0, 200),
      page_url: window.location.href,
    };

    this.trackEvent("app_error", errorData);

    console.error("[ORBIS] Error tracked:", errorData);
  },

  /**
   * Funnel tracking
   */
  trackFunnelStep(funnelName, stepName, stepNumber) {
    this.trackEvent("funnel_step", {
      funnel_name: funnelName,
      step_name: stepName,
      step_number: stepNumber,
    });
  },

  /**
   * Sayfa görüntüleme (SPA için)
   * @param {string} pagePath - Sayfa yolu
   * @param {string} pageTitle - Sayfa başlığı
   */
  trackPageView(pagePath, pageTitle) {
    try {
      if (typeof gtag === "function") {
        gtag("event", "page_view", {
          page_path: pagePath,
          page_title: pageTitle,
        });
        console.log(`[GA] Page view: ${pagePath}`);
      }
    } catch (error) {
      console.error("[GA] Page view tracking error:", error);
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // STATE YÖNETİMİ
  // ═══════════════════════════════════════════════════════════════

  loadState() {
    try {
      const saved = localStorage.getItem("orbis_monetization");
      if (saved) {
        const data = JSON.parse(saved);
        this.state = { ...this.state, ...data };
      }

      // İlk kurulum tarihi yoksa kaydet
      if (!this.state.installDate) {
        this.state.installDate = new Date().toISOString().split("T")[0];
        this.saveState();
      }
    } catch (e) {
      console.error("[ORBIS] State yükleme hatası:", e);
    }
  },

  saveState() {
    try {
      localStorage.setItem("orbis_monetization", JSON.stringify(this.state));
    } catch (e) {
      console.error("[ORBIS] State kaydetme hatası:", e);
    }
  },

  checkDailyReset() {
    const today = new Date().toISOString().split("T")[0];

    if (this.state.lastUsageDate !== today) {
      // Yeni gün - sayaçları sıfırla
      this.state.todayUsage = 0;
      this.state.todayAdsWatched = 0;
      this.state.lastUsageDate = today;
      this.saveState();
      console.log("[ORBIS] Günlük sayaçlar sıfırlandı");
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // BİLDİRİM İZNİ (PWA & NATIVE)
  // ═══════════════════════════════════════════════════════════════

  async checkAndPromptNotificationPermission() {
    const isNative = typeof Capacitor !== "undefined" && typeof Capacitor.isNativePlatform === "function" && Capacitor.isNativePlatform();
    const hasWebNotification = ("Notification" in window);

    if (!isNative && !hasWebNotification) {
      console.log("[ORBIS] Bu tarayıcı veya ortamda bildirim desteği yok.");
      return;
    }

    // A) Native platform kontrolü
    if (isNative) {
      try {
        if (Capacitor.Plugins && Capacitor.Plugins.PushNotifications) {
          const perm = await Capacitor.Plugins.PushNotifications.checkPermissions();
          if (perm.receive === "granted") {
            console.log("[ORBIS] Native bildirim izni zaten verilmiş.");
            await this.registerNativePush();
            return;
          }
        }
      } catch (e) {
        console.warn("[ORBIS] Native perm check hatası:", e);
      }
    } else {
      // B) Web / PWA platform kontrolü
      if (Notification.permission === "granted") {
        console.log("[ORBIS] Web bildirim izni zaten verilmiş.");
        await this.initWebPush();
        return;
      }
      if (Notification.permission === "denied") {
        console.log("[ORBIS] Web bildirim izni tarayıcı ayarlarından engellenmiş.");
        return;
      }
    }

    // C) Henüz izin verilmemiş ('default' veya prompt durumu)
    // Eğer kullanıcı son 12 saat içinde "Şimdi Değil" demişse beklet
    const dismissedAt = localStorage.getItem("orbis_notif_dismissed_at");
    if (dismissedAt) {
      const hours = (Date.now() - parseInt(dismissedAt, 10)) / (1000 * 60 * 60);
      if (hours < 12) {
        console.log("[ORBIS] Bildirim izni beklemede (" + hours.toFixed(1) + " saat önce soruldu)");
        return;
      }
    }

    // Girişten 1.5 saniye sonra kullanıcıyı karşıla
    setTimeout(() => {
      this.showNotificationPermissionModal();
    }, 1500);
  },

  showNotificationPermissionModal() {
    if (document.getElementById("notification-permission-modal")) return;

    // Modal HTML oluştur (inline fallback + modern glassmorphism)
    const modalHTML = `
      <div id="notification-permission-modal" style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.78); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); z-index: 99999; display: flex; align-items: center; justify-content: center; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;">
        <div style="background: linear-gradient(145deg, #0f172a 0%, #1e293b 100%); border-radius: 24px; padding: 24px 20px; width: 100%; max-width: 360px; border: 1px solid rgba(255, 255, 255, 0.12); box-shadow: 0 25px 50px -12px rgba(124, 58, 237, 0.35); text-align: center; position: relative;">
          
          <div style="width: 60px; height: 60px; border-radius: 50%; background: rgba(124, 58, 237, 0.18); border: 1px solid rgba(124, 58, 237, 0.35); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; box-shadow: 0 8px 20px rgba(124, 58, 237, 0.25);">
            <span class="material-icons-round" style="font-size: 30px; color: #c084fc;">notifications_active</span>
          </div>

          <h3 style="font-size: 19px; font-weight: 700; color: #ffffff; margin: 0 0 6px 0; letter-spacing: -0.01em;">Bildirimleri Aç</h3>
          <p style="font-size: 13px; color: #94a3b8; line-height: 1.5; margin: 0 0 18px 0;">
            Önemli gökyüzü olaylarını, günlük burç ve kozmik enerjinizi anında takip edin.
          </p>
          
          <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; text-align: left;">
            <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 14px;">
              <span class="material-icons-round" style="font-size: 20px; color: #fbbf24;">wb_sunny</span>
              <span style="font-size: 12px; color: #e2e8f0; font-weight: 500;">Günlük Burç & Enerji Yorumları</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 14px;">
              <span class="material-icons-round" style="font-size: 20px; color: #c084fc;">auto_awesome</span>
              <span style="font-size: 12px; color: #e2e8f0; font-weight: 500;">Önemli Gezegen Transitleri & Retrolar</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 14px;">
              <span class="material-icons-round" style="font-size: 20px; color: #34d399;">notifications</span>
              <span style="font-size: 12px; color: #e2e8f0; font-weight: 500;">Kişisel Harita ve Zamanlama Uyarıları</span>
            </div>
          </div>
          
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <button id="accept-notif-btn" type="button" style="width: 100%; padding: 13px; background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%); color: #ffffff; font-weight: 600; font-size: 14px; border: none; border-radius: 14px; box-shadow: 0 8px 20px rgba(124, 58, 237, 0.35); cursor: pointer; transition: all 0.2s;">
              Bildirimleri Aç
            </button>
            <button id="decline-notif-btn" type="button" style="width: 100%; padding: 9px; background: transparent; color: #94a3b8; font-size: 12px; border: none; cursor: pointer; transition: color 0.2s;">
              Şimdi Değil
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHTML);

    document.getElementById("accept-notif-btn")?.addEventListener("click", () => this.acceptNotifications());
    document.getElementById("decline-notif-btn")?.addEventListener("click", () => this.declineNotifications());
  },

  declineNotifications() {
    document.getElementById("notification-permission-modal")?.remove();
    // Kullanıcı şimdi değil dedi; 12 saat sonra tekrar hatırlat
    localStorage.setItem("orbis_notif_dismissed_at", Date.now().toString());
    console.log("[ORBIS] Bildirim izni ertelendi.");
  },

  async acceptNotifications() {
    document.getElementById("notification-permission-modal")?.remove();
    localStorage.removeItem("orbis_notif_dismissed_at");

    const isNative = typeof Capacitor !== "undefined" && typeof Capacitor.isNativePlatform === "function" && Capacitor.isNativePlatform();

    try {
      if (isNative && Capacitor.Plugins && Capacitor.Plugins.PushNotifications) {
        const { PushNotifications } = Capacitor.Plugins;
        const result = await PushNotifications.requestPermissions();
        console.log("[ORBIS] Native push izin sonucu:", result);

        if (result.receive === "granted") {
          localStorage.setItem("orbis_push_granted", "true");
          await this.registerNativePush();
        } else {
          localStorage.setItem("orbis_notif_dismissed_at", Date.now().toString());
        }
      } else if ("Notification" in window) {
        const permission = await Notification.requestPermission();
        console.log("[ORBIS] Web notification izin sonucu:", permission);

        if (permission === "granted") {
          localStorage.setItem("orbis_push_granted", "true");
          await this.initWebPush();
        } else {
          localStorage.setItem("orbis_notif_dismissed_at", Date.now().toString());
        }
      }
    } catch (error) {
      console.error("[ORBIS] Bildirim izin hatası:", error);
    }
  },

  async registerNativePush() {
    try {
      if (typeof Capacitor === "undefined" || !Capacitor.Plugins || !Capacitor.Plugins.PushNotifications) return;
      const { PushNotifications } = Capacitor.Plugins;
      PushNotifications.removeAllListeners();
      PushNotifications.addListener("registration", async (token) => {
        console.log("[ORBIS] Native FCM Token:", token.value);
        await this.registerFCMToken(token.value, "android");
      });
      PushNotifications.addListener("registrationError", (error) => {
        console.error("[ORBIS] Native FCM Registration error:", error);
      });
      PushNotifications.addListener("pushNotificationReceived", (notification) => {
        console.log("[ORBIS] Native push received:", notification);
        this.showInAppNotification(notification.title, notification.body);
      });
      await PushNotifications.register();
      console.log("[ORBIS] Native PushNotifications registered.");
    } catch (err) {
      console.warn("[ORBIS] registerNativePush error:", err);
    }
  },

  async registerFCMToken(token, platform) {
    if (!token) return;
    try {
      const headers = { "Content-Type": "application/json" };
      let userId = null;
      if (window.OrbisFirebase && window.OrbisFirebase.auth && window.OrbisFirebase.auth.currentUser) {
        try {
          const user = window.OrbisFirebase.auth.currentUser;
          userId = user.uid;
          const idToken = await user.getIdToken();
          headers["Authorization"] = "Bearer " + idToken;
        } catch(e) {}
      }

      const response = await fetch("/api/fcm/register", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          token: token,
          platform: platform || (this.state.isNative ? "android" : "web"),
          userId: userId,
          device_id: this.getDeviceId(),
          topics: ["all_users", "daily_horoscope"],
        }),
      });

      const data = await response.json();
      console.log("[ORBIS] FCM token sunucuya kaydedildi:", data);
      localStorage.setItem("orbis_fcm_token", token);
      localStorage.setItem("orbis_push_granted", "true");
    } catch (error) {
      console.error("[ORBIS] FCM token registration error:", error);
    }
  },

  async initWebPush() {
    try {
      const VAPID_KEY = "BDG800ijmQ1av11kHWR-ZnW_gVUKUYjKMH7oYqKnF-BsSb2K4ECB9PL0cQzpP90jehx5zwnR7WH46kYdlq6kUbE";
      let token = null;

      // 1. OrbisFirebase üzerinden dene
      if (window.OrbisFirebase && typeof window.OrbisFirebase.getFCMToken === "function") {
        token = await window.OrbisFirebase.getFCMToken();
      }

      // 2. Fallback: firebase.messaging doğrudan
      if (!token && typeof firebase !== "undefined" && typeof firebase.messaging === "function") {
        let swReg = null;
        if ("serviceWorker" in navigator) {
          swReg = await navigator.serviceWorker.register("/firebase-messaging-sw.js", {
            scope: "/firebase-cloud-messaging-push-scope"
          });
          await navigator.serviceWorker.ready;
        }
        const messaging = firebase.messaging();
        token = await messaging.getToken({
          vapidKey: VAPID_KEY,
          serviceWorkerRegistration: swReg || undefined
        });
      }

      if (token) {
        await this.registerFCMToken(token, "web");
      }
    } catch (error) {
      console.error("[ORBIS] Web push init error:", error);
    }
  },

  showInAppNotification(title, body) {
    // Foreground'da güzel bir in-app notification göster
    const notifHTML = `
      <div id="in-app-notif" class="fixed top-4 left-4 right-4 z-[300] animate-slide-down">
        <div class="bg-slate-800/95 backdrop-blur-xl rounded-2xl p-4 border border-white/10 shadow-2xl flex items-start gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
            <span class="material-icons-round text-primary">notifications</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-bold text-sm text-white">${title || "ORBIS"}</div>
            <p class="text-xs text-slate-400 mt-1 line-clamp-2">${
              body || ""
            }</p>
          </div>
          <button id="notif-close-btn" class="text-slate-500 hover:text-white">
            <span class="material-icons-round text-lg">close</span>
          </button>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", notifHTML);

    // CSP-uyumlu: close button addEventListener
    document.getElementById("notif-close-btn")?.addEventListener("click", () => {
      document.getElementById("in-app-notif")?.remove();
    });

    // 5 saniye sonra otomatik kapat
    setTimeout(() => {
      document.getElementById("in-app-notif")?.remove();
    }, 5000);
  },

  declineNotifications() {
    // Modal'ı kapat
    document.getElementById("notification-permission-modal")?.remove();
    localStorage.setItem("orbis_notification_asked", "true");
    console.log("[ORBIS] Bildirimler reddedildi");
  },

  // ═══════════════════════════════════════════════════════════════
  // DURUM SORGULAMA
  // ═══════════════════════════════════════════════════════════════

  isFirstDay() {
    const today = new Date().toISOString().split("T")[0];
    return this.state.installDate === today;
  },

  getDailyLimit() {
    if (this.state.isPremium) {
      return Infinity; // Premium için limit yok (kredi varsa)
    }
    return this.isFirstDay()
      ? this.CONFIG.FREE_FIRST_DAY_TOTAL
      : this.CONFIG.FREE_DAILY_LIMIT;
  },

  getRemainingToday() {
    if (this.state.isPremium) {
      return "∞"; // Sınırsız
    }
    return "Reklam ile sınırsız"; // Reklam izleyerek sınırsız
  },

  needsAd() {
    if (this.state.isPremium) return false;
    // ÜCRETSİZ KULLANICI = HER ZAMAN REKLAM GEREKLİ
    return true;
  },

  canAnalyze() {
    // Premium: her zaman
    // Ücretsiz: her zaman (reklamla)
    return true;
  },

  getStatusSummary() {
    return {
      isPremium: this.state.isPremium,
      credits: this.state.credits,
      isFirstDay: this.isFirstDay(),
      todayUsage: this.state.todayUsage,
      remaining: this.getRemainingToday(),
      needsAd: this.needsAd(),
    };
  },

  // ═══════════════════════════════════════════════════════════════
  // ANALİZ İSTEĞİ
  // ═══════════════════════════════════════════════════════════════

  async requestAnalysis(onSuccess, onCancel) {
    console.log("[ORBIS] Analiz isteği başladı...");

    // ⚠️ KRİTİK: Premium kaldırıldı. Uygulama tamamen ücretsiz.
    // Bonus modal zaten new_result.html'de (Asıl Analiz sekmesi) — analiz
    // tıklamasında AdMob Rewarded Interstitial gösterilir.
    // Bu fonksiyon sadece doğrudan onSuccess çağırır; koşul/limit yok.

    // Sayaçları güncelle (analytics için)
    this.state.todayUsage = (this.state.todayUsage || 0) + 1;
    this.state.totalAnalyses = (this.state.totalAnalyses || 0) + 1;
    this.saveState();
    this.updateUI();

    // GA: analiz event'i
    this.trackEvent("analysis_started", {
      total_analyses: this.state.totalAnalyses,
      today_usage: this.state.todayUsage,
    });

    console.log(
      "[ORBIS] Doğrudan analiz başlatıldı (limit/reklam kontrolü yok), bugünkü kullanım:",
      this.state.todayUsage
    );

    if (onSuccess) {
      console.log("[ORBIS] Calling onSuccess...");
      try {
        onSuccess();
        console.log("[ORBIS] onSuccess called successfully");
      } catch (err) {
        console.error("[ORBIS] onSuccess error:", err);
      }
    } else {
      console.error("[ORBIS] onSuccess is not defined!");
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // CAPACITOR BROWSER OAUTH CALLBACK
  // ═══════════════════════════════════════════════════════════════
  //
  // Native Google Sign-In başarısız olduğunda (Play Services yok,
  // SHA-1 uyumsuz vs.) Firebase _signInWithBrowserOAuth fallback'i
  // Capacitor Browser ile OAuth akışı başlatır. Browser OAuth
  // tamamlanıp uygulamaya geri döndüğünde bu listener yakalar.
  //
  initBrowserOAuthCallback() {
    try {
      const isNative =
        typeof Capacitor !== "undefined" && Capacitor.isNativePlatform();
      if (!isNative) return;

      const Browser =
        (Capacitor.Plugins && Capacitor.Plugins.Browser) ||
        (window.Plugins && window.Plugins.Browser);
      if (!Browser) {
        console.warn("[ORBIS] Browser plugin yok, OAuth callback listener kurulamiyor");
        return;
      }

      // 'browserFinished' veya 'appUrlOpen' event'i ile OAuth
      // callback'i handle et. Capacitor 6+'da App.addListener
      // 'appUrlOpen' önerilir.
      if (typeof Capacitor.Plugins.App !== "undefined") {
        const App = Capacitor.Plugins.App;
        App.addListener("appUrlOpen", (event) => {
          console.log("[ORBIS] App URL açıldı (OAuth callback?):", event.url);
          // Firebase signInWithRedirect kendi getRedirectResult()'ı
          // init() zaten handle ediyor (OrbisFirebase.init içinde)
          // Burada ek bir şey yapmamıza gerek yok, sadece log.
        });
        console.log("[ORBIS] App.appUrlOpen listener kuruldu (OAuth callback için)");
      }

      // Browser plugin finished event'i
      Browser.addListener("browserFinished", () => {
        console.log("[ORBIS] Browser kapandı (OAuth tamamlandı veya iptal)");
      });
      Browser.addListener("urlChangeEvent", (event) => {
        console.log("[ORBIS] Browser URL değişti:", event.url);
      });
    } catch (e) {
      console.warn("[ORBIS] initBrowserOAuthCallback hatası:", e);
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // ADMOB
  // ═══════════════════════════════════════════════════════════════

  async initAdMob() {
    if (!this.state.isNative) return;
    if (this.isExemptUser()) {
      console.log("[ORBIS] 🛡️ Geliştirici hesabı - AdMob başlatma atlandı (ceza koruması)");
      return;
    }

    try {
      const { AdMob } = Capacitor.Plugins;
      if (!AdMob) {
        console.warn("[ORBIS] AdMob plugin yüklü değil — native tarafta @capacitor-community/admob kurulu olmalı");
        return;
      }
      const adConfig = this._getAdmob();

      // ⚠️ KRİTİK: AdMob.initialize() zorunlu. Bu çağrılmadan prepare/show
      // sessizce başarısız olur → AdMob panelinde "0 istek" gözükür.
      // initializeForTesting:true, prod reklam yerine test reklamı yükler
      // ve NO_FILL hatasına neden olur — bu yüzden false.
      await AdMob.initialize({
        // initializeForTesting:true → test reklam (NO_FILL)
        // initializeForTesting:false → gerçek reklam (production)
        initializeForTesting: this.CONFIG.IS_TESTING,
        // TagForChildDirectedTreatment: TR mevzuatı gereği çocuk yönelimli
        // değiliz → false. Yanlışlıkla true yapılırsa AdMob tüm reklamları
        // reddeder → 0 etkin kalır.
        tagForChildDirectedTreatment: false,
        // tagForUnderAgeOfConsent: aynı şekilde false
        tagForUnderAgeOfConsent: false,
      });

      console.log("[ORBIS] ✅ AdMob.initialize başarılı (appId=" + adConfig.APP_ID + ")");

      // ⚠️ KRİTİK: AppId sadece AndroidManifest.xml'de tanımlı olur; burada
      // tekrar set etmek gerekmez. Ama config sanity check yapalım:
      if (!adConfig.APP_ID || !adConfig.APP_ID.startsWith("ca-app-pub-")) {
        console.error("[ORBIS] ❌ Geçersiz AdMob APP_ID:", adConfig.APP_ID);
        return;
      }

      // iOS 14+ ATT (App Tracking Transparency) — ayrı method.
      // Android'de silent ignore. iOS'ta popup gösterir.
      // Sadece native iOS'ta çalışır; Android'de plugin "unimplemented" döner.
      try {
        if (typeof AdMob.trackingAuthorizationStatus === "function") {
          const tracking = await AdMob.trackingAuthorizationStatus();
          if (tracking?.status === "notDetermined" && typeof AdMob.requestTrackingAuthorization === "function") {
            await AdMob.requestTrackingAuthorization();
          }
        }
      } catch (e) {
        // iOS dışı platform — silent ignore
        console.log("[ORBIS] ATT atlandı (Android veya unsupported):", e?.message || "");
      }

      // GDPR/KVKK: TR kullanıcıları için non-personalized ads default.
      // consentStatus='NON_PERSONALIZED' veya 'UNKNOWN' ise NPA kullan.
      // (Detaylı consent dialog Options sayfasında gösterilebilir.)
      try {
        if (typeof AdMob.requestConsentInfo === "function") {
          const consent = await AdMob.requestConsentInfo({});
          console.log("[ORBIS] Consent status:", consent?.status);
          this._adConsentStatus = consent?.status || "UNKNOWN";
        }
      } catch (e) {
        console.log("[ORBIS] Consent info atlandı:", e?.message || e);
        this._adConsentStatus = "UNKNOWN";
      }

      // Reklamları önceden yükle
      await this.loadRewardedAd();
      await this.loadInterstitialAd();
      await this.loadBonusRewardedAd();

      // 🆕 App Open reklami (splash ekraninda — Capacitor v6 destegi yoksa no-op)
      this.showAppOpenAd().catch(err => {
        console.log("[ORBIS] App Open ad hatasi (desteklenmiyor olabilir):", err);
      });

      // Premium değilse banner göster
      if (!this.state.isPremium) {
        await this.showBanner();
      }
    } catch (error) {
      console.error("[ORBIS] AdMob başlatma hatası:", error);
    }
  },

  async showBanner() {
    if (!this.state.isNative || this.state.isPremium || this.isExemptUser()) return;

    try {
      const { AdMob } = Capacitor.Plugins;
      const adConfig = this._getAdmob();

      await AdMob.showBanner({
        adId: adConfig.BANNER,
        adSize: "ADAPTIVE_BANNER",
        position: "BOTTOM_CENTER",
        margin: 0,
        isTesting: this.CONFIG.IS_TESTING,
      });

      // Banner için padding (banner 60px + bottom nav 80px = 140px)
      document.body.style.paddingBottom = "140px";

      // Bottom nav'ı yukarı kaydır
      const bottomNav = document.querySelector("nav.fixed.bottom-0");
      if (bottomNav) {
        bottomNav.style.bottom = "60px";
      }

      // GA: Banner gösterildi event'i
      this.trackEvent("ad_impression", {
        ad_type: "banner",
        ad_position: "bottom",
      });

      console.log("[ORBIS] Banner gösterildi");
    } catch (error) {
      console.error("[ORBIS] Banner hatası:", error);
    }
  },

  async hideBanner() {
    if (!this.state.isNative) return;

    try {
      const { AdMob } = Capacitor.Plugins;
      await AdMob.hideBanner();
      document.body.style.paddingBottom = "0";

      // Bottom nav'ı eski konumuna döndür
      const bottomNav = document.querySelector("nav.fixed.bottom-0");
      if (bottomNav) {
        bottomNav.style.bottom = "0";
      }
    } catch (error) {
      console.error("[ORBIS] Banner gizleme hatası:", error);
    }
  },

  // Interstitial (tam ekran) reklam
  async loadInterstitialAd() {
    if (!this.state.isNative || this.isExemptUser()) return;

    try {
      const { AdMob } = Capacitor.Plugins;
      const adConfig = this._getAdmob();

      await AdMob.prepareInterstitial({
        adId: adConfig.INTERSTITIAL,
        isTesting: this.CONFIG.IS_TESTING,
      });

      console.log("[ORBIS] Interstitial yüklendi");
    } catch (error) {
      console.error("[ORBIS] Interstitial yükleme hatası:", error);
    }
  },

  async showInterstitialAd() {
    if (!this.state.isNative || this.state.isPremium || this.isExemptUser()) return;

    // Her X analizde bir göster
    if (this.state.totalAnalyses % this.CONFIG.INTERSTITIAL_INTERVAL !== 0) {
      return;
    }

    try {
      const { AdMob } = Capacitor.Plugins;
      await AdMob.showInterstitial();

      // GA: Interstitial gösterildi event'i
      this.trackEvent("ad_impression", {
        ad_type: "interstitial",
        total_analyses: this.state.totalAnalyses,
      });

      console.log("[ORBIS] Interstitial gösterildi");

      // Yeni interstitial yükle
      this.loadInterstitialAd();
    } catch (error) {
      console.error("[ORBIS] Interstitial gösterme hatası:", error);
    }
  },

  async loadRewardedAd() {
    if (!this.state.isNative || this.isExemptUser()) return;

    try {
      const { AdMob } = Capacitor.Plugins;
      const adConfig = this._getAdmob();

      // 🆕 ANALIZ birimini tercih et, yoksa eski REWARDED kullan
      const rewardedAdId = adConfig.REWARDED_ANALIZ || adConfig.REWARDED;

      await AdMob.prepareRewardVideoAd({
        adId: rewardedAdId,
        isTesting: this.CONFIG.IS_TESTING,
      });

      console.log(`[ORBIS] Rewarded ad yüklendi (ID: ${rewardedAdId})`);
    } catch (error) {
      console.error("[ORBIS] Rewarded ad yükleme hatası:", error);
    }
  },

  /**
   * Bonus Rewarded Interstitial reklami hazirlar.
   * "1 ek AI yorum kazan" kampanyasi icin kullanilir.
   * Analiz sonrasi veya dashboard'da bonus butonu tiklandiginda gosterilir.
   */
  async loadBonusRewardedAd() {
    if (!this.state.isNative || this.isExemptUser()) return;

    try {
      const { AdMob } = Capacitor.Plugins;
      const adConfig = this._getAdmob();

      // Bonus icin ayrilmis rewarded birimini tercih et, yoksa genel rewarded
      const bonusAdId = adConfig.REWARDED_BONUS || adConfig.REWARDED;

      await AdMob.prepareRewardVideoAd({
        adId: bonusAdId,
        isTesting: this.CONFIG.IS_TESTING,
      });

      console.log(`[ORBIS] Bonus rewarded ad hazir (ID: ${bonusAdId})`);
    } catch (error) {
      console.error("[ORBIS] Bonus rewarded ad hazirlama hatasi:", error);
    }
  },

  /**
   * Web platformu için gerçek 15 saniyelik ödüllü video simülasyonu.
   * Kullanıcı 15 saniye dolmadan kapatırsa ödül KESİNLİKLE verilmez.
   * Yalnızca 15 saniyelik süre tamamlandığında resolve({ success: true }) döner.
   */
  showWebRewardedAdPlayer(options = {}) {
    const duration = options.duration || 15;
    const title = options.title || "Ödüllü Reklam";

    return new Promise((resolve) => {
      // Mevcut açık reklam varsa temizle
      const existing = document.getElementById('web-rewarded-player-overlay');
      if (existing) existing.remove();

      let remaining = duration;
      let timerId = null;

      const overlay = document.createElement('div');
      overlay.id = 'web-rewarded-player-overlay';
      overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.88);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);padding:16px;';
      overlay.innerHTML = `
        <div style="width:100%;max-width:390px;background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);border:1px solid rgba(124,58,237,0.35);border-radius:24px;padding:24px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);color:#fff;text-align:center;position:relative;overflow:hidden;font-family:system-ui,-apple-system,sans-serif;">
          <!-- Top progress bar -->
          <div style="position:absolute;top:0;left:0;right:0;height:4px;background:rgba(255,255,255,0.1);">
            <div id="web-ad-progress" style="height:100%;width:0%;background:linear-gradient(90deg,#7c3aed,#ec4899);transition:width 1s linear;"></div>
          </div>

          <!-- Header badge -->
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;margin-top:4px;">
            <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;background:rgba(124,58,237,0.2);color:#c084fc;padding:4px 10px;border-radius:9999px;border:1px solid rgba(124,58,237,0.3);">
              📺 Sponsor Reklamı
            </span>
            <span id="web-ad-timer-badge" style="font-size:12px;font-weight:700;font-family:monospace;background:rgba(255,255,255,0.12);padding:4px 10px;border-radius:9999px;color:#fde047;">
              ⏱️ ${remaining}s
            </span>
          </div>

          <!-- Video Simulation Screen -->
          <div style="width:100%;height:150px;background:linear-gradient(180deg,#090d16 0%,#161329 100%);border-radius:16px;border:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:16px;position:relative;overflow:hidden;">
            <div style="width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#06b6d4);display:grid;place-items:center;box-shadow:0 0 24px rgba(124,58,237,0.6);margin-bottom:10px;">
              <span class="material-icons-round" style="font-size:28px;color:#fff;">play_arrow</span>
            </div>
            <div style="font-size:13px;font-weight:700;color:#f8fafc;letter-spacing:-0.01em;">ORBIS Kozmik Harita & Transitler</div>
            <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Ödüllü Sponsor Yayını</div>
          </div>

          <!-- Information -->
          <h4 id="web-ad-status-title" style="font-size:15px;font-weight:700;margin:0 0 6px;color:#fff;">
            Reklam Oynatılıyor...
          </h4>
          <p id="web-ad-status-desc" style="font-size:12px;color:#94a3b8;margin:0 0 16px;line-height:1.45;">
            Ödülünüzün tanımlanması için lütfen videonun tamamlanmasını bekleyin. Erken kapatırsanız ödül verilmez.
          </p>

          <!-- Action buttons -->
          <div id="web-ad-action-wrap">
            <button id="web-ad-cancel-btn" type="button" style="width:100%;padding:10px 16px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:12px;color:#94a3b8;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;">
              Reklamı Kapat (Ödül İptal)
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);

      const progressEl = document.getElementById('web-ad-progress');
      const timerBadge = document.getElementById('web-ad-timer-badge');
      const statusTitle = document.getElementById('web-ad-status-title');
      const statusDesc = document.getElementById('web-ad-status-desc');
      const cancelBtn = document.getElementById('web-ad-cancel-btn');

      // Erken iptal kontrolü - Ödül KESİNLİKLE verilmez
      const handleEarlyCancel = () => {
        if (timerId) clearInterval(timerId);
        overlay.remove();
        console.warn("[ORBIS] Web reklam erken kapatıldı — ödül verilmedi.");
        resolve({ success: false, reason: "user_closed_early" });
      };

      if (cancelBtn) {
        cancelBtn.addEventListener('click', handleEarlyCancel);
      }

      // Saniye saniye geri sayım
      timerId = setInterval(() => {
        remaining -= 1;
        const pct = Math.min(100, Math.round(((duration - remaining) / duration) * 100));
        if (progressEl) progressEl.style.width = pct + '%';
        if (timerBadge) timerBadge.textContent = '⏱️ ' + remaining + 's';

        if (remaining <= 0) {
          clearInterval(timerId);
          if (progressEl) progressEl.style.width = '100%';
          if (timerBadge) {
            timerBadge.textContent = '✅ Bitti';
            timerBadge.style.color = '#34d399';
          }
          if (statusTitle) {
            statusTitle.innerHTML = '<span style="color:#34d399;">✅ Reklam Tamamlandı!</span>';
          }
          if (statusDesc) {
            statusDesc.textContent = 'Tebrikler! Ödülünüz tanımlanıyor, lütfen bekleyin...';
          }
          const actionWrap = document.getElementById('web-ad-action-wrap');
          if (actionWrap) {
            actionWrap.innerHTML = `
              <div style="padding:10px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);border-radius:12px;color:#34d399;font-size:12px;font-weight:700;">
                ⭐ Ödül Onaylandı!
              </div>
            `;
          }

          setTimeout(() => {
            overlay.remove();
            console.log("[ORBIS] Web reklam tamamlandı — ödül onaylandı.");
            this.trackEvent("ad_impression", { ad_type: "rewarded_web_player" });
            this.trackEvent("ad_reward", { ad_type: "rewarded_web_player" });
            resolve({ success: true, reason: "completed" });
          }, 800);
        }
      }, 1000);
    });
  },

  /**
   * Bonus Rewarded reklami gosterir — analiz sonrasi "ek yorum" kazandirir.
   * @returns {Promise<{success: boolean, reason: string|null}>}
   */
  async showBonusRewardedAd() {
    if (!this.state.isNative) {
      return this.showWebRewardedAdPlayer({ duration: 15, title: "Bonus Ödül Reklamı" });
    }

    return new Promise(async (resolve) => {
      try {
        const { AdMob } = Capacitor.Plugins;
        if (!AdMob) {
          resolve({ success: false, reason: "admob_unavailable" });
          return;
        }

        const adConfig = this._getAdmob();
        const bonusAdId = adConfig.REWARDED_BONUS || adConfig.REWARDED;

        let rewarded = false;
        let resolved = false;
        const safeResolve = (success, reason) => {
          if (resolved) return;
          resolved = true;
          this.loadBonusRewardedAd();
          resolve({ success, reason });
        };

        const cleanupFns = [];
        const cleanup = () => cleanupFns.forEach(fn => { try { fn(); } catch(_){} });

        const rl = await AdMob.addListener("onRewardedVideoAdReward", () => {
          console.log("[ORBIS] Bonus odul kazanildi!");
          rewarded = true;
          this.trackEvent("ad_reward", { ad_type: "rewarded_bonus" });
        });
        cleanupFns.push(() => rl.remove());

        const dl = await AdMob.addListener("onRewardedVideoAdDismissed", () => {
          safeResolve(rewarded, rewarded ? null : "user_dismissed_without_reward");
        });
        cleanupFns.push(() => dl.remove());

        const fl = await AdMob.addListener("onRewardedVideoAdFailedToLoad", (err) => {
          console.warn("[ORBIS] Bonus rewarded yuklenemedi:", err);
          safeResolve(false, "ad_load_failed");
        });
        cleanupFns.push(() => fl.remove());

        const fs = await AdMob.addListener("onRewardedVideoAdFailedToShow", (err) => {
          console.warn("[ORBIS] Bonus rewarded gosterilemedi:", err);
          safeResolve(false, "ad_show_failed");
        });
        cleanupFns.push(() => fs.remove());

        const timeoutId = setTimeout(() => safeResolve(false, "ad_timeout"), 30000);
        cleanupFns.push(() => clearTimeout(timeoutId));

        this.trackEvent("ad_impression", { ad_type: "rewarded_bonus" });
        await AdMob.showRewardVideoAd();
      } catch (e) {
        console.error("[ORBIS] Bonus rewarded hata:", e);
        resolve({ success: false, reason: "exception" });
      }
    });
  },

  /**
   * App Open reklami gosterir (splash ekraninda).
   * NOT: Capacitor @capacitor-community/admob v6'da native App Open destegi yok.
   * Gelecekte native binding ile eklenecek.
   * @returns {Promise<boolean>} - true gosterildi, false desteklenmiyor/hata
   */
  async showAppOpenAd() {
    const adConfig = this._getAdmob();
    const appOpenId = adConfig.appOpenId;

    if (!appOpenId) {
      console.info("[ORBIS] App Open ad unit ID tanimli degil — ozellik devre disi");
      return false;
    }

    if (!this.state.isNative) {
      console.info("[ORBIS] App Open sadece native (Android) icin");
      return false;
    }

    // TODO: Capacitor plugin App Open destegini ekleyince burayi implement et
    // Su an icin native Android tarafinda AdMob SDK'sini dogrudan cagirmak gerekir.
    console.warn("[ORBIS] App Open reklam destegi henuz implement edilmedi (Capacitor plugin v6 limiti)");
    return false;
  },

  /**
   * Native Advanced reklami gosterir (dashboard inline reklam).
   * NOT: Capacitor plugin desteği yok. İleride native binding ile eklenecek.
   * @param {string} containerId - Reklamin yerlesecegi DOM element ID
   * @returns {Promise<boolean>} - true gosterildi, false desteklenmiyor/hata
   */
  async showNativeAdvancedAd(containerId) {
    if (this.isExemptUser()) return false;
    const adConfig = this._getAdmob();
    const nativeId = adConfig.nativeAdvancedId;

    if (!nativeId) {
      console.info("[ORBIS] Native Advanced ad unit ID tanimli degil — ozellik devre disi");
      return false;
    }

    if (!this.state.isNative) {
      console.info("[ORBIS] Native Advanced sadece native (Android) icin");
      return false;
    }

    // TODO: Capacitor plugin Native Advanced destegini ekleyince burayi implement et
    console.warn("[ORBIS] Native Advanced reklam destegi henuz implement edilmedi");
    return false;
  },

  async showRewardedAdFlow() {
    if (this.isExemptUser()) {
      console.log("[ORBIS] 🛡️ Geliştirici hesabı - Rewarded reklam doğrudan onaylandı.");
      return Promise.resolve({ success: true, reason: "exempt_owner" });
    }

    // WEB PLATFORM: modal popup ile reklam deneyimi
    if (!this.state.isNative) {
      console.log("[ORBIS] Web platform - reklam modal gösteriliyor...");
      return await this.showRewardedAd();
    }

    // NATIVE PLATFORM: ADMOB reklamı göster
    console.log("[ORBIS] Native platform - rewarded ad gösteriliyor...");
    return await this.showRewardedAd();
  },

  async showRewardedAd() {
    if (!this.state.isNative) {
      return this.showWebRewardedAdPlayer({ duration: 15, title: "Kozmik Reklam" });
    }

    if (this.isExemptUser()) {
      console.log("[ORBIS] 🛡️ Geliştirici hesabı - Rewarded reklam doğrudan onaylandı.");
      return Promise.resolve({ success: true, reason: "exempt_owner" });
    }

    return new Promise(async (resolve) => {
      try {

        // ═════════════════════════════════════════════════════════
        // NATIVE PLATFORM - Capacitor AdMob ile reklam
        // ═════════════════════════════════════════════════════════
        const { AdMob } = Capacitor.Plugins;
        
        let rewarded = false;
        let notified = false; // resolve'in 2 kere çağrılmasını engelle
        let cleanupFns = [];
        
        const cleanup = () => {
          cleanupFns.forEach(fn => { try { fn(); } catch(e) {} });
          cleanupFns = [];
        };

        // smartResolve: AdMob reason + native-to-web fallback akıllı çözümleyici
        // Başarıda {success:true, reason:null}; başarısızlıkta {success:false, reason}
        // Native AdMob başarısız olduğunda (no-fill / timeout / load error)
        // 1) Önce Interstitial fallback dene (AdMob havuzunda daha sık bulunur)
        // 2) O da başarısızsa web modal fallback
        const smartResolve = (success, reason) => {
          if (notified) return;
          notified = true;
          cleanup();
          // Yeni rewarded reklam yükle
          this.loadRewardedAd();

          // ⚠️ KRİTİK: Native AdMob başarısızsa sırasıyla fallback zinciri:
          //   ad_load_failed / ad_show_failed / ad_timeout durumlarında
          //   1) Interstitial göster (ödülsüz ama AdMob havuzunda daha sık)
          //   2) Interstitial de başarısızsa → web modal fallback
          const isAdLoadFailed = typeof reason === "string" && reason.startsWith("ad_load_failed");
          const isAdShowFailed = typeof reason === "string" && reason.startsWith("ad_show_failed");
          const isAdTimeout = reason === "ad_timeout";

          const needsNativeFallback =
            success === false &&
            this.state.isNative &&
            (isAdLoadFailed || isAdShowFailed || isAdTimeout);

          if (needsNativeFallback) {
            console.log(
              "[ORBIS] Rewarded basarisiz, Interstitial fallback deneniyor. reason:",
              reason
            );
            // Önce Interstitial dene (AdMob policy: ödülsüz reklam — kullanıcıya
            // teşekkür amaçlı kısa reklam, analiz devam eder)
            this.showInterstitialAsRewardFallback(reason)
              .then((interstitialResult) => {
                if (interstitialResult === true) {
                  console.log("[ORBIS] Interstitial fallback basarili, analiz devam ediyor");
                  setTimeout(
                    () => resolve({ success: true, reason: "interstitial_fallback" }),
                    200
                  );
                } else {
                  console.log(
                    "[ORBIS] Interstitial fallback da basarisiz, web modal deneniyor"
                  );
                  // Web modal fallback dene
                  this.showWebRewardedFallback(reason)
                    .then((webResult) => {
                      setTimeout(
                        () => resolve({
                          success: webResult === true,
                          reason: webResult === true ? "web_fallback" : "user_cancelled",
                        }),
                        200
                      );
                    })
                    .catch((err) => {
                      console.error("[ORBIS] Web fallback hata:", err);
                      setTimeout(
                        () => resolve({ success: false, reason }),
                        200
                      );
                    });
                }
              })
              .catch((err) => {
                console.error("[ORBIS] Interstitial fallback hata:", err);
                // Hata durumunda direkt web modal
                this.showWebRewardedFallback(reason)
                  .then((webResult) => {
                    setTimeout(
                      () => resolve({
                        success: webResult === true,
                        reason: webResult === true ? "web_fallback" : "user_cancelled",
                      }),
                      200
                    );
                  });
              });
            return;
          }

          setTimeout(
            () => resolve({ success: success, reason: success ? null : reason }),
            200
          );
        };

        // ═══════════════════════════════════════════════════════════════
        // 3-KATMANLI FALLBACK SİSTEMİ
        // 1) REWARDED_ANALIZ (en yüksek CPM)
        // 2) REWARDED (yedek)
        // 3) Interstitial (son çare - ödülsüz ama AdMob havuzunda daha sık bulunur)
        //
        // Google AdMob politikası: Interstitial "ödüllü" değildir. Bu nedenle
        // success=true set etmiyoruz, sadece kullanıcıya "Yine de Devam Et"
        // seçeneği sunuyoruz. Yine de NO_FILL yoksa interstitial gösterilir ve
        // kullanıcı 5sn bekleyip analize devam eder.
        // ═══════════════════════════════════════════════════════════════
        const rewardedAdId =
          adConfig.REWARDED_ANALIZ || adConfig.REWARDED || "ca-app-pub-2444093901783574/9994253824";

        console.log(`[ORBIS] Rewarded ad hazırlanıyor (ID: ${rewardedAdId})`);
        await AdMob.prepareRewardVideoAd({
          adId: rewardedAdId,
          isTesting: this.CONFIG.IS_TESTING,
        });

        // Ödül kazanıldı
        const rl = await AdMob.addListener("onRewardedVideoAdReward", () => {
          console.log("[ORBIS] ✅ Ödül kazanıldı!");
          rewarded = true;
          this.trackEvent("ad_reward", { ad_type: "rewarded", reward_type: "analysis_credit" });
        });
        cleanupFns.push(() => rl.remove());

        // Reklam kapatıldı
        const dl = await AdMob.addListener("onRewardedVideoAdDismissed", () => {
          console.log("[ORBIS] Reklam kapatıldı, ödül:", rewarded);
          smartResolve(rewarded, rewarded ? null : "user_dismissed_without_reward");
        });
        cleanupFns.push(() => dl.remove());

        // Yüklenemedi
        const fl = await AdMob.addListener("onRewardedVideoAdFailedToLoad", (error) => {
          console.error("[ORBIS] Ad yüklenemedi:", error);
          const code = (error && (error.code !== undefined ? error.code : error)) || "unknown";
          smartResolve(false, "ad_load_failed:" + code);
        });
        cleanupFns.push(() => fl.remove());

        // Gösterilemedi
        const fs = await AdMob.addListener("onRewardedVideoAdFailedToShow", (error) => {
          console.error("[ORBIS] Ad gösterilemedi:", error);
          const code = (error && (error.code !== undefined ? error.code : error)) || "unknown";
          smartResolve(false, "ad_show_failed:" + code);
        });
        cleanupFns.push(() => fs.remove());

        // Timeout güvenliği - 30 saniye sonra timeout
        const timeoutId = setTimeout(() => {
          if (!notified) {
            console.warn("[ORBIS] Ad timeout - 30sn doldu");
            smartResolve(false, "ad_timeout");
          }
        }, 30000);
        cleanupFns.push(() => clearTimeout(timeoutId));

        console.log("[ORBIS] Rewarded video gösteriliyor...");
        this.trackEvent("ad_impression", { ad_type: "rewarded" });
        await AdMob.showRewardVideoAd();

      } catch (error) {
        console.error("[ORBIS] Rewarded ad hatası:", error);
        // Hata durumunda bile web'de bir modal göster
        if (!this.state.isNative) {
          try { document.getElementById('ad-reward-overlay')?.remove(); } catch(e) {}
          // Basit confirm ile dene
          const retry = confirm("📺 Reklam gösterilemedi. Tekrar dene?");
          resolve({ success: retry, reason: retry ? "web_retry" : "user_cancelled" });
        } else {
          if (!notified) {
            // Native throw — fallback dene
            const errMsg = (error && (error.message || String(error))) || "unknown";
            smartResolve(false, "ad_throw:" + errMsg);
          }
        }
      }
    });
  },

  // ═══════════════════════════════════════════════════════════════
  // PREMIUM & KREDİ - KALDIRILDI
  // ═══════════════════════════════════════════════════════════════

  showPremiumPackages() {
    // DEPRECATED: Premium kaldirildi. Uygulama tamamen ucretsiz.
    console.info("[ORBIS] showPremiumPackages called but premium is removed.");
    if (typeof alert !== "undefined") {
      alert("Uygulamamiz tamamen ucretsizdir. Premium satin alma ozellikleri kaldirildi.");
    }
  },

  async purchasePremium(index_or_pkg = 0) {
    // DEPRECATED: Premium satin alma kaldirildi. Uygulama tamamen ucretsiz.
    console.info("[ORBIS] purchasePremium called but premium is removed:", index_or_pkg);
    if (typeof alert !== "undefined") {
      alert("Premium satin alma kaldirildi. Uygulama tamamen ucretsizdir.");
    }
    return false;
  },

  // ═══════════════════════════════════════════════════════════════
  // UI & MODALS
  // ═══════════════════════════════════════════════════════════════

  showLimitReachedModal() {
    // Herkes ucretsiz — sadece reklam izleme uyarisi
    if (typeof alert !== "undefined") {
      alert("Analiz icin lutfen kisa bir reklam izleyin.");
    }
  },

  /**
   * AdMob hata nedenini kullanıcı dostu Türkçe mesaja çevirir.
   * dashboard.html'deki cancelCallback bunu kullanır.
   * @param {string} reason - showRewardedAd'dan dönen reason string
   * @returns {string|null} - Mesaj veya bilinmeyen nedenler için null
   */
  explainAdFail(reason) {
    if (!reason) return null;

    // En yaygın nedenler önce
    if (reason === "ad_timeout") {
      return "Reklam 30 saniye içinde yüklenemedi. İnternet bağlantınızı kontrol edin ve tekrar deneyin.";
    }
    if (reason === "ad_load_failed:3") {
      return "Reklam envanteri şu an bu cihaz için boş. Birkaç saat sonra tekrar deneyin veya Premium'a geçerek reklamsız kullanın.";
    }
    if (reason === "ad_load_failed:0") {
      return "Reklam isteği başarısız oldu. İnternet bağlantınızı kontrol edin.";
    }
    if (reason === "ad_load_failed:1") {
      return "Reklam sunucusundan geçersiz yanıt alındı. Tekrar deneyin.";
    }
    if (reason === "ad_load_failed:2") {
      return "Reklam ağı bağlantısı kurulamadı. İnternet bağlantınızı kontrol edin.";
    }
    if (reason.startsWith("ad_load_failed")) {
      return "Reklam yüklenemedi (kod: " + reason + "). Lütfen tekrar deneyin.";
    }
    if (reason.startsWith("ad_show_failed")) {
      return "Reklam gösterilemedi. Uygulamayı yeniden başlatıp tekrar deneyin.";
    }
    if (reason.startsWith("ad_throw")) {
      return "Reklam sistemi başlatılamadı. Uygulamayı kapatıp yeniden açın.";
    }
    if (reason === "user_cancelled") {
      return null; // Kullanıcı kendisi iptal etti — bilgi gösterme
    }
    if (reason === "user_dismissed_without_reward") {
      return "Reklam tam izlenmedi. Ödül kazanılamadığı için analiz başlatılamadı.";
    }
    if (reason === "premium_chosen") {
      return null; // Premium'a yönlendirildi — bilgi gösterme
    }
    if (reason === "web_retry") {
      return "Reklam gösterilemedi. Tekrar denemek istiyor musunuz?";
    }
    if (reason === "web_fallback") {
      return null; // Web fallback başarılı — bilgi gösterme
    }
    return "Reklam gösterilemedi. Lütfen tekrar deneyin. (kod: " + reason + ")";
  },

  /**
   * Üstten slide-in toast: AdMob hatasını kullanıcıya gösterir.
   * 60 sn sonra otomatik kapanır, kullanıcı da kapatabilir.
   * "Tekrar Dene" butonu formu yeniden submit eder.
   * @param {string} message - explainAdFail'den gelen mesaj
   * @param {string} reason - opsiyonel, console'a log için
   */
  showAdErrorToast(message, reason) {
    try {
      // Mevcut toast varsa kaldır
      const existing = document.getElementById("orbis-ad-error-toast");
      if (existing) existing.remove();

      const toast = document.createElement("div");
      toast.id = "orbis-ad-error-toast";
      toast.style.cssText =
        "position:fixed;top:1rem;left:1rem;right:1rem;z-index:300;transform:translateY(-220%);transition:transform 0.4s ease-out;pointer-events:none";
      toast.innerHTML =
        '<div style="pointer-events:auto" class="bg-red-500/95 backdrop-blur-sm text-white px-4 py-3 rounded-2xl shadow-2xl border border-red-400/30 flex items-center gap-3 max-w-md mx-auto">' +
        '<span class="material-icons-round text-2xl flex-shrink-0">error_outline</span>' +
        '<div class="flex-1 min-w-0">' +
        '<p class="text-sm font-bold leading-tight">Reklam Yüklenemedi</p>' +
        '<p class="text-xs opacity-90 mt-0.5 leading-snug">' +
        String(message).replace(/</g, "&lt;") +
        "</p>" +
        "</div>" +
        '<button id="orbis-toast-retry" class="bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors flex-shrink-0" aria-label="Tekrar Dene">' +
        '<span class="material-icons-round text-sm">refresh</span><span>Tekrar</span>' +
        "</button>" +
        '<button id="orbis-toast-close" class="text-white/70 hover:text-white flex-shrink-0" aria-label="Kapat">' +
        '<span class="material-icons-round text-lg">close</span>' +
        "</button>" +
        "</div>";
      document.body.appendChild(toast);

      // Slide-in (çift rAF ile layout settle olduktan sonra)
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          toast.style.transform = "translateY(0)";
        });
      });

      // Close handler
      const close = () => {
        toast.style.transform = "translateY(-220%)";
        setTimeout(() => {
          if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 400);
      };
      const closeBtn = document.getElementById("orbis-toast-close");
      const retryBtn = document.getElementById("orbis-toast-retry");
      if (closeBtn) closeBtn.addEventListener("click", close);
      if (retryBtn) {
        retryBtn.addEventListener("click", () => {
          close();
          // Form'u yeniden submit et
          const form = document.getElementById("orbisForm");
          if (form) {
            console.log("[ORBIS] Toast retry: form yeniden submit ediliyor");
            form.dispatchEvent(
              new Event("submit", { cancelable: true, bubbles: true })
            );
          }
        });
      }

      // 60 sn sonra otomatik kapat (güvenlik)
      setTimeout(close, 60000);
    } catch (e) {
      console.error("[ORBIS] showAdErrorToast hatası:", e);
      // Son çare: native alert
      try {
        alert("⚠️ " + message);
      } catch (_) {}
    }
  },

  /**
   * Rewarded reklam yuklenemediginde Interstitial (Gecis) reklami fallback
   * olarak gosterir. Interstitial odullu degildir (AdMob policy) ama AdMob
   * havuzunda daha sik bulunur — NO_FILL olma ihtimali dusuktur.
   * Kullanici izledikten sonra success=true doner.
   *
   * NOT: Google AdMob policy geregi "odullu" reklam yerine interstitial
   * gostermek riskli olabilir. Bu nedenle burada kullanicinin
   * rizasini alan bir toast/onay gosterilir.
   *
   * @param {string} reason - smartResolve'den gelen reason
   * @returns {Promise<boolean>} - true = interstitial izlendi, false = basarisiz
   */
  showInterstitialAsRewardFallback(reason) {
    if (this.isExemptUser()) return Promise.resolve(true);

    return new Promise(async (resolve) => {
      if (!this.state.isNative) {
        resolve(false);
        return;
      }

      try {
        const { AdMob } = Capacitor.Plugins;
        if (!AdMob) {
          console.warn("[ORBIS] AdMob plugin yok, interstitial fallback basarisiz");
          resolve(false);
          return;
        }

        const adConfig = this._getAdmob();
        const interstitialId = adConfig.INTERSTITIAL;

        if (!interstitialId) {
          console.warn("[ORBIS] Interstitial ad unit ID yok");
          resolve(false);
          return;
        }

        console.log(`[ORBIS] Interstitial fallback hazirlaniyor (ID: ${interstitialId})`);

        // Interstitial'i hazirla
        await AdMob.prepareInterstitial({
          adId: interstitialId,
          isTesting: this.CONFIG.IS_TESTING,
        });

        // Gosterim tamamlaninca veya hata olunca resolve et
        let resolved = false;
        const safeResolve = (val) => {
          if (resolved) return;
          resolved = true;
          cleanupFns.forEach(fn => { try { fn(); } catch(e) {} });
          resolve(val);
        };

        let cleanupFns = [];

        const dl = await AdMob.addListener("onInterstitialAdDismissed", () => {
          console.log("[ORBIS] Interstitial fallback izlendi");
          this.trackEvent("ad_impression", { ad_type: "interstitial_fallback" });
          safeResolve(true);
        });
        cleanupFns.push(() => dl.remove());

        const fl = await AdMob.addListener("onInterstitialAdFailedToLoad", (err) => {
          console.error("[ORBIS] Interstitial fallback yuklenemedi:", err);
          safeResolve(false);
        });
        cleanupFns.push(() => fl.remove());

        const fs = await AdMob.addListener("onInterstitialAdFailedToShow", (err) => {
          console.error("[ORBIS] Interstitial fallback gosterilemedi:", err);
          safeResolve(false);
        });
        cleanupFns.push(() => fs.remove());

        // Timeout - 10 saniye (interstitial genelde 5sn gosterilir)
        const timeoutId = setTimeout(() => {
          if (!resolved) {
            console.warn("[ORBIS] Interstitial fallback timeout (10sn)");
            safeResolve(false);
          }
        }, 10000);
        cleanupFns.push(() => clearTimeout(timeoutId));

        // 1.5 saniye gecikme: kullanici interstitial'i
        // "yukleniyor" durumunu gorup kafasini karmasmasin
        await new Promise(r => setTimeout(r, 1500));

        if (resolved) return;
        await AdMob.showInterstitial();
      } catch (e) {
        console.error("[ORBIS] Interstitial fallback exception:", e);
        resolve(false);
      }
    });
  },

  /**
   * Native AdMob başarısız olduğunda web modal fallback gösterir.
   * Kullanıcı "Reklam İzle" derse true, "Vazgeç" derse false döner.
   * @param {string} reason - smartResolve'den gelen reason
   * @returns {Promise<boolean|null>} - true/false = kullanıcı seçti, null = modal oluşturulamadı
   */
  showWebRewardedFallback(reason) {
    return new Promise((resolve) => {
      try {
        // Mevcut modal varsa kaldır
        const existing = document.getElementById("ad-reward-overlay");
        if (existing) existing.remove();

        const isNoFill = reason === "ad_load_failed:3";
        const reasonText = isNoFill
          ? "Reklam envanteri şu an bu cihaz için boş. Yine de devam etmek için aşağıdan onaylayın."
          : reason === "ad_timeout"
          ? "Reklam zaman aşımına uğradı. Yine de devam etmek için aşağıdan onaylayın."
          : "Reklam yüklenemedi. Yine de devam etmek için aşağıdan onaylayın.";

        const modal = document.createElement("div");
        modal.id = "ad-reward-overlay";
        modal.style.cssText =
          "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)";
        // Premium kaldirildi: sadece 'Yine de Devam Et' ve 'Vazgeç' butonlari
        modal.innerHTML =
          '<div class="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl p-6 w-full max-w-sm mx-4 border border-white/10 shadow-2xl text-center animate-fade-in">' +
          '<div class="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-amber-500/30 to-orange-500/30 flex items-center justify-center">' +
          '<span class="material-icons-round text-4xl text-amber-400">info</span>' +
          "</div>" +
          '<h3 class="text-xl font-bold text-white mb-2">Reklam Gösterilemedi</h3>' +
          '<p class="text-sm text-slate-400 mb-6 leading-relaxed">' +
          reasonText +
          "</p>" +
          '<div class="flex flex-col gap-3">' +
          '<button id="ad-fallback-confirm" class="w-full py-4 bg-primary hover:bg-primary/90 text-white font-bold rounded-2xl transition-all active:scale-95 flex items-center justify-center gap-2">' +
          '<span class="material-icons-round">play_arrow</span>' +
          "Yine de Devam Et" +
          "</button>" +
          '<button id="ad-fallback-cancel" class="w-full py-3 text-slate-500 hover:text-slate-300 text-sm transition-colors">' +
          "Vazgeç" +
          "</button>" +
          "</div>" +
          "</div>";
        document.body.appendChild(modal);

        const cleanup = () => {
          if (modal.parentNode) modal.parentNode.removeChild(modal);
        };

        const confirmBtn = document.getElementById("ad-fallback-confirm");
        const cancelBtn = document.getElementById("ad-fallback-cancel");

        if (confirmBtn) {
          confirmBtn.addEventListener("click", () => {
            console.log(
              "[ORBIS] Web fallback: kullanıcı 'Yine de Devam Et' seçti"
            );
            this.trackEvent("ad_fallback_used", { reason: reason });
            cleanup();
            resolve(true);
          });
        }
        // Premium butonu kaldirildi. Geriye uyumluluk: varsa no-op.
        const legacyPremiumBtn = document.getElementById("ad-fallback-premium");
        if (legacyPremiumBtn) {
          legacyPremiumBtn.addEventListener("click", () => {
            console.info("[ORBIS] Legacy premium buton ignored (premium removed).");
            cleanup();
            resolve(false);
          });
        }
        if (cancelBtn) {
          cancelBtn.addEventListener("click", () => {
            console.log("[ORBIS] Web fallback: kullanıcı vazgeçti");
            cleanup();
            resolve(false);
          });
        }
      } catch (e) {
        console.error("[ORBIS] showWebRewardedFallback modal hatası:", e);
        resolve(null);
      }
    });
  },

  showPremiumPromo() {
    // DEPRECATED: Premium kaldirildi. Uygulama tamamen ucretsiz.
    // Geriye uyumluluk: sadece bilgilendirme.
    console.info("[ORBIS] showPremiumPromo called but premium is removed.");
    if (typeof alert !== "undefined") {
      alert("Uygulamamiz tamamen ucretsizdir. Premium satin alma kaldirildi.");
    }
  },

  updateUI() {
    // Status bar güncelle (varsa)
    const statusEl = document.getElementById("orbis-status");
    if (statusEl) {
      if (this.state.isPremium) {
        statusEl.innerHTML = `💎 Premium Aktif`;
      } else {
        const remaining = this.getRemainingToday();
        statusEl.innerHTML = `🆓 Ücretsiz | Bugün: ${remaining} hak`;
      }
    }

    // Premium badge (varsa)
    const premiumBadge = document.getElementById("premium-badge");
    if (premiumBadge) {
      premiumBadge.style.display = this.state.isPremium ? "flex" : "none";
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // TEST & DEBUG
  // ═══════════════════════════════════════════════════════════════

  resetAll() {
    if (confirm("⚠️ Tüm veriler sıfırlanacak. Emin misiniz?")) {
      localStorage.removeItem("orbis_monetization");
      location.reload();
    }
  },

  /**
   * Firebase çıkış yapıldığında local state'e dön
   */
  resetToLocal() {
    console.log("[ORBIS] Firebase çıkış - local state sıfırlanıyor");

    // Premium state'ini temizle (localStorage'da kalmış olabilir)
    this.state.isPremium = false;
    this.state.premiumPackageId = null;
    this.state.premiumExpiry = null;
    this.state.credits = 0;
    this.saveState();

    // UI güncelle
    this.updateUI();

    // Premium değilse banner göster
    if (!this.state.isPremium && this.state.isNative) {
      this.showBanner();
    }
  },

  // 🆕 Reklam izlendi - backend'e kaydet
  async recordAdWatchToBackend() {
    const deviceId = this.getDeviceId();
    const email = window.OrbisFirebase?.getCurrentUser()?.email || null;

    try {
      // 1. record_ad_watch endpoint
      const res1 = await fetch('/api/record_ad_watch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId, email: email })
      });
      const data1 = await res1.json();
      console.log("[ORBIS] ✅ Ad watch recorded to backend:", data1);
    } catch (e) {
      console.warn("[ORBIS] ⚠️ record_ad_watch failed:", e.message);
    }

    try {
      // 2. Monetization API
      const res2 = await fetch('/api/monetization/record-usage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId, email: email, feature: 'ad_watch' })
      });
      const data2 = await res2.json();
      console.log("[ORBIS] ✅ Monetization usage recorded:", data2);
    } catch (e) {
      console.warn("[ORBIS] ⚠️ monetization record failed:", e.message);
    }
  },

  addTestCredits(amount = 10) {
    this.state.credits += amount;
    this.saveState();
    this.updateUI();
    console.log(
      `[ORBIS] Test: ${amount} kredi eklendi. Toplam: ${this.state.credits}`
    );
  },

  simulateNewDay() {
    this.state.lastUsageDate = "2000-01-01";
    this.checkDailyReset();
    console.log("[ORBIS] Test: Yeni gün simüle edildi");
  },
};

// Global erişim
window.OrbisBridge = OrbisBridge;

// OrbisRewardedAds alias - results sayfası ve dashboard için uyumluluk
window.OrbisRewardedAds = {
  showForInterpretation: async function() {
    return OrbisBridge.showRewardedAd();
  },
  showForAnalysis: async function() {
    return OrbisBridge.showRewardedAd();
  },
};

// Sayfa yüklendiğinde başlat
document.addEventListener("DOMContentLoaded", async () => {
  await OrbisBridge.init();
  // Analytics: app_open (web PWA + mobile WebView)
  if (window.OrbisAnalytics) window.OrbisAnalytics.event('app_open', { platform: window.Capacitor?.isNativePlatform() ? 'native' : 'web' });
});
