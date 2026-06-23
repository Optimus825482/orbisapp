/**
 * Monetization Module
 * Kullanım takibi ve premium kontrolü
 */

class MonetizationManager {
    constructor() {
        this.deviceId = this.getOrCreateDeviceId();
        this.usageData = null;
        this.API_BASE = '/api/monetization';
    }

    // Benzersiz cihaz ID'si oluştur/al
    getOrCreateDeviceId() {
        let deviceId = localStorage.getItem('astro_device_id');
        if (!deviceId) {
            deviceId = 'dev_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('astro_device_id', deviceId);
        }
        return deviceId;
    }

    // Kullanım durumunu kontrol et
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
            console.error('Kullanım kontrolü hatası:', error);
            return null;
        }
    }

    // Özellik kullanılabilir mi?
    async canUseFeature(feature = 'interpretation') {
        const usage = await this.checkUsage();
        if (!usage) return { allowed: true }; // Hata durumunda izin ver
        return usage.can_use;
    }

    // Kullanımı kaydet
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
            console.error('Kullanım kaydı hatası:', error);
            return null;
        }
    }

    // Premium durumunu kontrol et
    async isPremium() {
        const usage = await this.checkUsage();
        return usage?.usage?.is_premium || false;
    }

    // Kalan kullanım sayısı
    async getRemainingUsage() {
        const usage = await this.checkUsage();
        if (usage?.usage?.is_premium) return Infinity;
        return usage?.usage?.remaining || 0;
    }

    // Premium popup göster
    showPremiumPopup(message = 'Günlük ücretsiz limitiniz doldu!') {
        const popup = document.createElement('div');
        popup.className = 'premium-popup-overlay';
        popup.innerHTML = `
            <div class="premium-popup">
                <div class="premium-popup-header">
                    <span class="premium-icon">⭐</span>
                    <h3>Premium'a Geç</h3>
                </div>
                <p class="premium-message">${message}</p>
                <div class="premium-features">
                    <div class="feature-item">✓ Sınırsız AI yorumu</div>
                    <div class="feature-item">✓ Detaylı natal analiz</div>
                    <div class="feature-item">✓ Transit yorumları</div>
                    <div class="feature-item">✓ Reklamsız deneyim</div>
                </div>
                <div class="premium-pricing">
                    <button class="btn-premium-monthly" onclick="monetization.purchase('premium_daily')">
                        Günlük - ₺30
                    </button>
                    <button class="btn-premium-monthly" onclick="monetization.purchase('premium_monthly')">
                        Aylık - ₺300 <span class="badge">🔥 İndirim</span>
                    </button>
                    <button class="btn-premium-yearly" onclick="monetization.purchase('premium_yearly')">
                        Yıllık - ₺3000 <span class="badge">2 ay hediye!</span>
                    </button>
                </div>
                <button class="btn-close" onclick="this.closest('.premium-popup-overlay').remove()">
                    Daha sonra
                </button>
            </div>
        `;
        document.body.appendChild(popup);
    }

    // Satın alma başlat (TWA/Capacitor ile)
    async purchase(productId) {
        // Android'de Google Play Billing ile entegre olacak
        if (window.Android && window.Android.purchase) {
            window.Android.purchase(productId);
        } else {
            // Web'de alternatif ödeme (Stripe/PayPal)
            alert('Satın alma özelliği yakında aktif olacak!');
        }
    }

    // Kullanım UI'ını güncelle
    async updateUsageUI() {
        const usage = await this.checkUsage();
        const usageBar = document.getElementById('usage-bar');
        const usageText = document.getElementById('usage-text');
        
        if (!usageBar || !usageText) return;
        
        if (usage?.usage?.is_premium) {
            usageText.textContent = '⭐ Premium - Sınırsız';
            usageBar.style.width = '100%';
            usageBar.classList.add('premium');
        } else {
            // Ücretsiz kullanıcı = Her analiz için reklam zorunlu
            usageText.textContent = '📺 Reklam izleyerek sınırsız analiz yapın';
            usageBar.style.width = '100%';
        }
    }
}

// Global instance
const monetization = new MonetizationManager();

// Sayfa yüklendiğinde kullanımı kontrol et
document.addEventListener('DOMContentLoaded', () => {
    monetization.updateUsageUI();
});
