/**
 * Monetization Module
 * - Kullanim takibi (sadece reklam destekli)
 * - PREMIUM KALDIRILDI: Uygulama tamamen ucretsiz.
 * - Geriye uyumluluk: isPremium() her zaman false dondurur.
 */

class MonetizationManager {
    constructor() {
        this.deviceId = this.getOrCreateDeviceId();
        this.usageData = null;
        this.API_BASE = '/api/monetization';
    }

    // Benzersiz cihaz ID'si olustur/al
    getOrCreateDeviceId() {
        let deviceId = localStorage.getItem('astro_device_id');
        if (!deviceId) {
            deviceId = 'dev_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('astro_device_id', deviceId);
        }
        return deviceId;
    }

    // Kullanim durumunu kontrol et
    async checkUsage() {
        try {
            const response = await fetch(`${this.API_BASE}/check-usage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: this.deviceId })
            });
            this.usageData = await response.json();
            return this.usageData;
        } catch (error) {
            console.error('Kullanim kontrolu hatasi:', error);
            return null;
        }
    }

    // Ozellik kullanilabilir mi?
    async canUseFeature(feature = 'interpretation') {
        const usage = await this.checkUsage();
        if (!usage) return { allowed: true }; // Hata durumunda izin ver
        return usage.can_use;
    }

    // Kullanimi kaydet
    async recordUsage(feature = 'interpretation') {
        try {
            const response = await fetch(`${this.API_BASE}/record-usage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    feature: feature
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Kullanim kaydi hatasi:', error);
            return null;
        }
    }

    // DEPRECATED: Premium kaldirildi. Her zaman false dondurur (geriye uyumluluk).
    async isPremium() {
        return false;
    }

    // DEPRECATED: Premium kaldirildi. Her zaman Infinity dondurur.
    async getRemainingUsage() {
        return Infinity;
    }

    // DEPRECATED: Premium kaldirildi. No-op (geriye uyumluluk).
    showPremiumPopup(message) {
        console.info('[Monetization] showPremiumPopup called but premium is removed:', message);
    }

    // DEPRECATED: Premium satin alma kaldirildi. No-op.
    async purchase(productId) {
        console.info('[Monetization] purchase called but premium is removed:', productId);
        return { success: false, message: 'Premium kaldirildi. Uygulama tamamen ucretsizdir.' };
    }

    // Kullanim UI'ini guncelle (premium kaldirildi: sadece reklam uyarisi)
    async updateUsageUI() {
        const usageBar = document.getElementById('usage-bar');
        const usageText = document.getElementById('usage-text');

        if (!usageBar || !usageText) return;

        // Tum kullanicilar ucretsiz — her analiz icin reklam izleme zorunlulugu
        usageText.textContent = 'Ucretsiz uygulama - Her analiz icin reklam izleyin';
        usageBar.style.width = '100%';
        usageBar.classList.remove('premium');
    }
}

// Global instance
const monetization = new MonetizationManager();

// Sayfa yuklendiginde kullanimi kontrol et
document.addEventListener('DOMContentLoaded', () => {
    monetization.updateUsageUI();
});
