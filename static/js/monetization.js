/**
 * ORBIS Monetization & Rewards Module - Kozmik Kredi & 24h Reklamsız Pass
 * 
 * - Kullanıcı odaklı değer takası (Value Exchange)
 * - 1 Rewarded Video = +2 Kozmik Kredi
 * - 2 Rewarded Video = 24 Saat Tüm Uygulama Reklamsız
 * - PWA ve Native tam uyumlu
 */

class MonetizationManager {
    constructor() {
        this.deviceId = this.getOrCreateDeviceId();
        this.usageData = null;
        this.API_BASE = '/api/monetization';
        this.credits = 2;
        this.isAdFree = false;
        this.adFreeSeconds = 0;
        this._passTimer = null;
    }

    getOrCreateDeviceId() {
        let deviceId = localStorage.getItem('astro_device_id') || localStorage.getItem('orbis_device_id');
        if (!deviceId) {
            deviceId = 'dev_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('astro_device_id', deviceId);
            localStorage.setItem('orbis_device_id', deviceId);
        }
        return deviceId;
    }

    getUserEmail() {
        try {
            return window.OrbisFirebase?.getCurrentUser()?.email || null;
        } catch (e) {
            return null;
        }
    }

    async checkUsage() {
        try {
            const response = await fetch(`${this.API_BASE}/check-usage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    email: this.getUserEmail()
                })
            });
            const data = await response.json();
            this.usageData = data;

            const u = data.usage || {};
            this.credits = typeof u.cosmic_credits === 'number' ? u.cosmic_credits : (data.cosmic_credits ?? 2);
            this.isAdFree = Boolean(u.is_ad_free || data.is_ad_free);
            this.adFreeSeconds = u.ad_free_seconds || data.ad_free_seconds || 0;

            this.updateBadgeUI();
            this._startPassCountdown();
            this.initTeasers();
            return data;
        } catch (error) {
            console.error('[Monetization] checkUsage error:', error);
            return null;
        }
    }

    _startPassCountdown() {
        if (this._passTimer) clearInterval(this._passTimer);
        if (!this.isAdFree || this.adFreeSeconds <= 0) return;

        this._passTimer = setInterval(() => {
            this.adFreeSeconds = Math.max(0, this.adFreeSeconds - 1);
            if (this.adFreeSeconds <= 0) {
                this.isAdFree = false;
                clearInterval(this._passTimer);
                this.updateBadgeUI();
            } else {
                // Her dakika badge etiketini güncelle
                if (this.adFreeSeconds % 60 === 0) {
                    this.updateBadgeUI();
                }
            }
        }, 1000);
    }

    formatRemainingTime(seconds) {
        if (seconds <= 0) return '0d';
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        if (hours > 0) return `${hours}s ${mins}d`;
        return `${mins}d`;
    }

    updateBadgeUI() {
        const pill = document.getElementById('cosmic-credit-pill');
        const countEl = document.getElementById('cosmic-credit-count');
        const labelEl = document.getElementById('cosmic-credit-label');
        const iconEl = pill ? pill.querySelector('.material-icons-round') : null;

        if (!pill || !countEl) return;

        if (this.isAdFree) {
            // Reklamsız Mod Rozeti (Canlı Yeşil/Cyan Kalkan)
            pill.className = 'h-9 px-3 rounded-full bg-gradient-to-r from-emerald-500/20 via-teal-500/20 to-cyan-500/20 border border-emerald-400/40 flex items-center gap-1.5 text-emerald-300 hover:text-white transition-all active:scale-95 shadow-lg shadow-emerald-500/10 cursor-pointer';
            if (iconEl) {
                iconEl.textContent = 'verified_user';
                iconEl.className = 'material-icons-round text-base text-emerald-400';
            }
            countEl.textContent = 'Reklamsız';
            countEl.className = 'text-[11px] font-bold text-emerald-300';
            if (labelEl) {
                labelEl.textContent = `(${this.formatRemainingTime(this.adFreeSeconds)})`;
                labelEl.className = 'text-[9px] font-mono text-emerald-400/80';
            }
        } else {
            // Kozmik Kredi Rozeti (Altın/Mor Yıldız)
            pill.className = 'h-9 px-3 rounded-full bg-gradient-to-r from-amber-500/20 via-primary/20 to-amber-500/10 border border-amber-500/30 flex items-center gap-1.5 text-amber-300 hover:text-white hover:border-amber-400 transition-all active:scale-95 shadow-sm shadow-amber-500/10 cursor-pointer';
            if (iconEl) {
                iconEl.textContent = 'stars';
                iconEl.className = 'material-icons-round text-base text-amber-400 animate-pulse';
            }
            countEl.textContent = this.credits;
            countEl.className = 'text-xs font-bold font-mono text-amber-300';
            if (labelEl) {
                labelEl.textContent = 'Kredi';
                labelEl.className = 'text-[9px] font-bold uppercase tracking-wider text-amber-200/80 hidden sm:inline';
            }
        }
    }

    async claimReward(rewardType = 'credits') {
        try {
            const res = await fetch(`${this.API_BASE}/claim-reward`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    reward_type: rewardType,
                    email: this.getUserEmail()
                })
            });
            const data = await res.json();
            if (data.success) {
                this.credits = data.cosmic_credits;
                this.isAdFree = data.is_ad_free;
                this.adFreeSeconds = data.ad_free_seconds || 0;
                this.updateBadgeUI();
                this._startPassCountdown();
                if (typeof window.showToast === 'function') {
                    window.showToast(data.message || 'Ödül tanımlandı!', 'success');
                } else {
                    alert(data.message || 'Tebrikler, ödülünüz tanımlandı!');
                }
            }
            return data;
        } catch (e) {
            console.error('[Monetization] claimReward error:', e);
            return { success: false, error: e.message };
        }
    }

    async spendCredit(amount = 1, feature = 'analysis') {
        try {
            const res = await fetch(`${this.API_BASE}/spend-credit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    amount: amount,
                    feature: feature,
                    email: this.getUserEmail()
                })
            });
            const data = await res.json();
            if (data.success) {
                this.credits = data.cosmic_credits;
                this.isAdFree = data.is_ad_free;
                this.updateBadgeUI();
            }
            return data;
        } catch (e) {
            console.error('[Monetization] spendCredit error:', e);
            return { success: false, error: e.message };
        }
    }

    // Modal aç/kapat
    showCreditModal() {
        const modal = document.getElementById('cosmic-credit-modal');
        if (!modal) return;
        this.updateModalContent();
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    closeCreditModal() {
        const modal = document.getElementById('cosmic-credit-modal');
        if (!modal) return;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    updateModalContent() {
        const curCredits = document.getElementById('modal-credit-current');
        const adFreeInfo = document.getElementById('modal-adfree-current');
        if (curCredits) curCredits.textContent = this.credits;
        if (adFreeInfo) {
            if (this.isAdFree) {
                adFreeInfo.innerHTML = `<span class="text-emerald-400 font-semibold flex items-center gap-1 justify-center"><span class="material-icons-round text-sm">verified_user</span> Aktif (${this.formatRemainingTime(this.adFreeSeconds)} kaldı)</span>`;
            } else {
                adFreeInfo.innerHTML = `<span class="text-slate-400">Pasif</span>`;
            }
        }
    }

    // Video izleyerek kredi kazan aksiyonu
    async watchForCredits() {
        const btn = document.getElementById('btn-watch-credits');
        if (btn) btn.disabled = true;

        try {
            let rewarded = true;
            if (window.MobileBridge && typeof window.MobileBridge.showBonusRewardedAd === 'function') {
                const adRes = await window.MobileBridge.showBonusRewardedAd();
                rewarded = adRes && adRes.success;
            } else if (window.MobileBridge && typeof window.MobileBridge.showRewardedAd === 'function') {
                rewarded = await window.MobileBridge.showRewardedAd();
            }

            if (rewarded) {
                await this.claimReward('credits');
                this.updateModalContent();
            } else {
                console.warn('[Monetization] Reklam tamamlanmadı veya kapatıldı.');
            }
        } catch (err) {
            console.error('[Monetization] watchForCredits error:', err);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // 2 Video izleyerek 24 saat reklamsız mod aksiyonu
    async watchForAdFreePass() {
        const btn = document.getElementById('btn-watch-adfree');
        if (btn) btn.disabled = true;

        try {
            let firstOk = true;
            if (window.MobileBridge && typeof window.MobileBridge.showBonusRewardedAd === 'function') {
                const res1 = await window.MobileBridge.showBonusRewardedAd();
                firstOk = res1 && res1.success;
            } else if (window.MobileBridge && typeof window.MobileBridge.showRewardedAd === 'function') {
                firstOk = await window.MobileBridge.showRewardedAd();
            }

            if (!firstOk) {
                alert('İlk reklam tamamlanmadı. Reklamsız mod için 2 reklam izlenmelidir.');
                if (btn) btn.disabled = false;
                return;
            }

            // İkinci reklam öncesi kısa bilgilendirme
            alert('Harika! 1/2 tamamlandı. Şimdi son reklamı izleyerek 24 saatlik Reklamsız Modunuzu aktifleştirin.');

            let secondOk = true;
            if (window.MobileBridge && typeof window.MobileBridge.showBonusRewardedAd === 'function') {
                const res2 = await window.MobileBridge.showBonusRewardedAd();
                secondOk = res2 && res2.success;
            } else if (window.MobileBridge && typeof window.MobileBridge.showRewardedAd === 'function') {
                secondOk = await window.MobileBridge.showRewardedAd();
            }

            if (secondOk) {
                await this.claimReward('ad_free_24h');
                this.updateModalContent();
                this.initTeasers();
            } else {
                alert('İkinci reklam tamamlanamadı.');
            }
        } catch (err) {
            console.error('[Monetization] watchForAdFreePass error:', err);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // FAZ 2: MERAK UYANDIRICI KİLİTLİ İÇERİK (BLUR TEASER & UNLOCK)
    // ═══════════════════════════════════════════════════════════════

    getUnlockedTeasers() {
        const today = new Date().toISOString().split('T')[0];
        try {
            const raw = localStorage.getItem(`orbis_unlocked_teasers_${today}`);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    markTeaserUnlocked(teaserId) {
        const today = new Date().toISOString().split('T')[0];
        const list = this.getUnlockedTeasers();
        if (!list.includes(teaserId)) {
            list.push(teaserId);
            try {
                localStorage.setItem(`orbis_unlocked_teasers_${today}`, JSON.stringify(list));
            } catch (e) {}
        }
    }

    initTeasers() {
        const unlockedList = this.getUnlockedTeasers();
        document.querySelectorAll('.teaser-box').forEach(box => {
            const id = box.id;
            if (this.isAdFree || unlockedList.includes(id)) {
                box.classList.add('teaser-unlocked');
            }
        });
    }

    async unlockTeaser(teaserId) {
        const box = document.getElementById(teaserId);
        if (!box) return;

        // 1. Reklamsız mod aktifse hemen aç
        if (this.isAdFree) {
            box.classList.add('teaser-unlocked');
            this.markTeaserUnlocked(teaserId);
            if (typeof window.showToast === 'function') {
                window.showToast('Reklamsız mod aktif olduğu için kilit doğrudan açıldı!', 'success');
            }
            return;
        }

        // 2. Kredisi varsa kullanıcıya sorarak 1 kredi harca veya video izle
        if (this.credits > 0) {
            const useCredit = confirm(`Bu gizli kozmik analizin kilidini 1 Kozmik Kredi harcayarak hemen açmak ister misiniz?\n(Mevcut Krediniz: ${this.credits})`);
            if (useCredit) {
                const spendRes = await this.spendCredit(1, `teaser_${teaserId}`);
                if (spendRes && spendRes.success) {
                    box.classList.add('teaser-unlocked');
                    this.markTeaserUnlocked(teaserId);
                    if (typeof window.showToast === 'function') {
                        window.showToast('Kozmik Kredi kullanıldı, kilit açıldı! 🔓', 'success');
                    }
                    return;
                }
            }
        }

        // 3. Kredisi yoksa veya video ile açmak isterse: Rewarded video izlet
        try {
            let rewarded = true;
            if (window.MobileBridge && typeof window.MobileBridge.showBonusRewardedAd === 'function') {
                const adRes = await window.MobileBridge.showBonusRewardedAd();
                rewarded = adRes && adRes.success;
            } else if (window.MobileBridge && typeof window.MobileBridge.showRewardedAd === 'function') {
                rewarded = await window.MobileBridge.showRewardedAd();
            }

            if (rewarded) {
                box.classList.add('teaser-unlocked');
                this.markTeaserUnlocked(teaserId);
                if (typeof window.showToast === 'function') {
                    window.showToast('Tebrikler! Özel kozmik analizin kilidi açıldı! 🔓', 'success');
                } else {
                    alert('Tebrikler! Özel kozmik analizin kilidi açıldı! 🔓');
                }
            }
        } catch (err) {
            console.error('[Monetization] unlockTeaser error:', err);
        }
    }
}

// Global instance
window.monetization = new MonetizationManager();

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    window.monetization.checkUsage();
});
