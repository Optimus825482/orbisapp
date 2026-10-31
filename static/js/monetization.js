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

    EXEMPT_EMAILS = [
        'ikinciyenikitap54@gmail.com',
        'erkanerdem8254@gmail.com',
        'djerkan8254@gmail.com'
    ];

    getUserEmail() {
        try {
            const stored = (localStorage.getItem('orbis_user_email') || '').trim().toLowerCase();
            if (stored) return stored;
            if (window.OrbisFirebase?.getCurrentUser()?.email) {
                return window.OrbisFirebase.getCurrentUser().email.toLowerCase().trim();
            }
            if (window.firebaseAuth?.user?.email) {
                return window.firebaseAuth.user.email.toLowerCase().trim();
            }
        } catch (e) {
            return null;
        }
        return null;
    }

    isExemptUser() {
        const email = (this.getUserEmail() || '').trim().toLowerCase();
        return this.EXEMPT_EMAILS.includes(email);
    }

    async checkUsage() {
        if (this.isExemptUser()) {
            this.credits = 9999;
            this.isAdFree = true;
            this.adFreeSeconds = 99999999;
            this.updateBadgeUI();
            this.initTeasers();
            return { is_exempt: true, is_ad_free: true, show_ads: false, cosmic_credits: 9999 };
        }

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

        // In-feed Native Ads: Reklamsız modda gizle, normalde göster
        document.querySelectorAll('.in-feed-ad-card').forEach(el => {
            el.style.display = this.isAdFree ? 'none' : 'block';
        });
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
            if (this.isAdFree || this.isExemptUser() || unlockedList.includes(id)) {
                box.classList.add('teaser-unlocked');
            }
        });

        // Reklamsız modda veya geliştirici hesabında in-feed reklam kartlarını gizle
        if (this.isAdFree || this.isExemptUser()) {
            document.querySelectorAll('.in-feed-ad-card').forEach(el => {
                el.style.display = 'none';
            });
        }
    }

    async unlockTeaser(teaserId) {
        const box = document.getElementById(teaserId);
        if (!box) return;

        // 1. Reklamsız mod veya geliştirici hesabı aktifse hemen aç
        if (this.isAdFree || this.isExemptUser()) {
            box.classList.add('teaser-unlocked');
            this.markTeaserUnlocked(teaserId);
            if (typeof window.showToast === 'function') {
                window.showToast('Geliştirici hesabı / Reklamsız mod: Kilit doğrudan açıldı! 🔓', 'success');
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

    // ═══════════════════════════════════════════════════════════════
    // FAZ 4: INSTAGRAM STORY KARTI (9:16) EXPORT SİSTEMİ
    // ═══════════════════════════════════════════════════════════════

    async openStoryExportModal() {
        const modal = document.getElementById('cosmic-story-modal');
        if (!modal) return;

        modal.classList.remove('hidden');
        modal.classList.add('flex');

        const spinner = document.getElementById('story-generating-spinner');
        if (spinner) spinner.classList.remove('hidden');

        // Canlı önizleme canvas'ını çiz
        setTimeout(async () => {
            try {
                const canvas = await this.renderStoryCanvas();
                const previewCanvas = document.getElementById('story-preview-canvas');
                if (previewCanvas && canvas) {
                    previewCanvas.width = canvas.width;
                    previewCanvas.height = canvas.height;
                    const pctx = previewCanvas.getContext('2d');
                    pctx.drawImage(canvas, 0, 0);
                }
            } catch (err) {
                console.error('[StoryExport] Preview render error:', err);
            } finally {
                if (spinner) spinner.classList.add('hidden');
            }
            this.updateStoryModalActions();
        }, 100);
    }

    closeStoryModal() {
        const modal = document.getElementById('cosmic-story-modal');
        if (!modal) return;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    updateStoryModalActions() {
        const container = document.getElementById('story-modal-actions');
        if (!container) return;

        const isFree = this.isAdFree || this.isExemptUser();

        if (isFree) {
            container.innerHTML = `
                <button type="button" onclick="window.monetization?.executeStoryUnlock('free')"
                    class="w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-xl transition-all active:scale-95 shadow-lg shadow-emerald-500/25 flex items-center justify-center gap-2 cursor-pointer">
                    <span class="material-icons-round text-base">download</span>
                    <span>Story Kartını İndir & Paylaş (Ücretsiz)</span>
                </button>
            `;
            return;
        }

        let html = '';
        if (this.credits > 0) {
            html += `
                <button type="button" onclick="window.monetization?.executeStoryUnlock('credit')"
                    class="w-full py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-xl transition-all active:scale-95 shadow-lg shadow-amber-500/25 flex items-center justify-center gap-2 cursor-pointer">
                    <span class="material-icons-round text-base">stars</span>
                    <span>1 Kozmik Kredi ile İndir (Mevcut: ${this.credits})</span>
                </button>
            `;
        }

        html += `
            <button type="button" onclick="window.monetization?.executeStoryUnlock('video')"
                class="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition-all active:scale-95 shadow-lg shadow-purple-900/40 flex items-center justify-center gap-2 cursor-pointer">
                <span class="material-icons-round text-base">play_circle</span>
                <span>1 Kısa Video İzle & Ücretsiz İndir</span>
            </button>
        `;

        container.innerHTML = html;
    }

    async executeStoryUnlock(method) {
        if (method === 'free') {
            await this.downloadOrShareStory();
            this.closeStoryModal();
            return;
        }

        if (method === 'credit') {
            const spend = await this.spendCredit(1, 'story_export');
            if (spend && spend.success) {
                await this.downloadOrShareStory();
                this.closeStoryModal();
                if (typeof window.showToast === 'function') {
                    window.showToast('Story kartınız başarıyla indirildi! 📸', 'success');
                }
            } else {
                alert('Kredi harcanamadı veya yetersiz kredi.');
            }
            return;
        }

        if (method === 'video') {
            let rewarded = true;
            if (window.MobileBridge && typeof window.MobileBridge.showBonusRewardedAd === 'function') {
                const res = await window.MobileBridge.showBonusRewardedAd();
                rewarded = res && res.success;
            } else if (window.MobileBridge && typeof window.MobileBridge.showRewardedAd === 'function') {
                rewarded = await window.MobileBridge.showRewardedAd();
            }

            if (rewarded) {
                await this.downloadOrShareStory();
                this.closeStoryModal();
                if (typeof window.showToast === 'function') {
                    window.showToast('Tebrikler! Story kartınız oluşturuldu! 📸', 'success');
                }
            }
        }
    }

    async renderStoryCanvas() {
        const width = 1080;
        const height = 1920;
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        // 1. Arka Plan: Koyu Kozmik Gradyan
        const bgGrad = ctx.createLinearGradient(0, 0, width, height);
        bgGrad.addColorStop(0, '#060515');
        bgGrad.addColorStop(0.35, '#120b2e');
        bgGrad.addColorStop(0.7, '#1f0d3d');
        bgGrad.addColorStop(1, '#09071c');
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, width, height);

        // 2. Nebula Işıltısı (Radial Glow)
        const radGlow1 = ctx.createRadialGradient(width / 2, 600, 50, width / 2, 600, 600);
        radGlow1.addColorStop(0, 'rgba(147, 51, 234, 0.25)');
        radGlow1.addColorStop(0.5, 'rgba(236, 72, 153, 0.1)');
        radGlow1.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = radGlow1;
        ctx.fillRect(0, 0, width, height);

        // 3. Prosedürel Yıldız Alanı (Starfield)
        ctx.fillStyle = '#ffffff';
        for (let i = 0; i < 160; i++) {
            const x = (i * 397 + 123) % width;
            const y = (i * 853 + 456) % height;
            const size = (i % 3 === 0) ? 2.5 : ((i % 5 === 0) ? 3.5 : 1.5);
            const alpha = 0.2 + ((i % 10) / 10) * 0.7;
            ctx.save();
            ctx.globalAlpha = alpha;
            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        // 4. Kutsal Geometri / Astroloji Çemberi
        const centerX = width / 2;
        const centerY = 980;
        ctx.save();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(centerX, centerY, 380, 0, Math.PI * 2);
        ctx.stroke();

        ctx.strokeStyle = 'rgba(245, 158, 11, 0.25)';
        ctx.setLineDash([8, 12]);
        ctx.beginPath();
        ctx.arc(centerX, centerY, 420, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();

        // Veri okuma
        const astro = window.astroData || {};
        const natal = astro.natal_planet_positions || {};
        const sunSign = natal.Sun?.sign || 'Bilinmiyor';
        const moonSign = natal.Moon?.sign || 'Bilinmiyor';
        const ascSign = natal.Ascendant?.sign || 'Bilinmiyor';
        const rawName = astro.user_name || astro.birth_info?.name || 'Kozmik Yolcu';
        const userName = (rawName.length > 22 ? rawName.substring(0, 22) + '...' : rawName).toUpperCase();

        const ZODIAC_MAP = {
            'Koç': '♈︎', 'Aries': '♈︎',
            'Boğa': '♉︎', 'Taurus': '♉︎',
            'İkizler': '♊︎', 'Gemini': '♊︎',
            'Yengeç': '♋︎', 'Cancer': '♋︎',
            'Aslan': '♌︎', 'Leo': '♌︎',
            'Başak': '♍︎', 'Virgo': '♍︎',
            'Terazi': '♎︎', 'Libra': '♎︎',
            'Akrep': '♏︎', 'Scorpio': '♏︎',
            'Yay': '♐︎', 'Sagittarius': '♐︎',
            'Oğlak': '♑︎', 'Capricorn': '♑︎',
            'Kova': '♒︎', 'Aquarius': '♒︎',
            'Balık': '♓︎', 'Pisces': '♓︎'
        };

        // 5. Üst Başlık & Marka Rozeti
        ctx.textAlign = 'center';
        ctx.fillStyle = 'rgba(216, 180, 254, 0.85)';
        ctx.font = 'bold 24px monospace';
        ctx.letterSpacing = '6px';
        ctx.fillText('✦  O R B I S   A S T R O L O G Y  ✦', centerX, 180);

        // Kullanıcı Adı
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 64px sans-serif';
        ctx.shadowColor = 'rgba(168, 85, 247, 0.6)';
        ctx.shadowBlur = 24;
        ctx.fillText(userName, centerX, 270);
        ctx.shadowBlur = 0;

        ctx.fillStyle = 'rgba(251, 191, 36, 0.9)';
        ctx.font = '600 28px sans-serif';
        ctx.fillText('Kozmik Profil & Doğum Haritası Özeti', centerX, 330);

        // 6. Üçlü Kozmik Kartlar (Güneş, Ay, Yükselen)
        const drawCard = (x, y, w, h, glyph, role, sign, desc, strokeColor, glowColor) => {
            ctx.save();
            ctx.fillStyle = 'rgba(15, 12, 35, 0.75)';
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 3;
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 20;

            // Yuvarlak kenar
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(x, y, w, h, 24);
            } else {
                ctx.rect(x, y, w, h);
            }
            ctx.fill();
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Glif / İkon
            ctx.fillStyle = strokeColor;
            ctx.font = 'bold 52px serif';
            ctx.textAlign = 'center';
            ctx.fillText(glyph, x + w / 2, y + 80);

            // Rol Başlığı
            ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
            ctx.font = 'bold 20px monospace';
            ctx.fillText(role, x + w / 2, y + 125);

            // Burç Adı
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 36px sans-serif';
            ctx.fillText(sign, x + w / 2, y + 175);

            // Alt Açıklama
            ctx.fillStyle = 'rgba(203, 213, 225, 0.8)';
            ctx.font = '500 20px sans-serif';
            ctx.fillText(desc, x + w / 2, y + 225);
            ctx.restore();
        };

        // Kart 1: Güneş (Sol Üst)
        const sunGlyph = ZODIAC_MAP[sunSign] ? `☉ ${ZODIAC_MAP[sunSign]}` : '☉';
        drawCard(100, 430, 410, 270, sunGlyph, 'GÜNEŞ BURCU', sunSign, 'Öz Benlik & Yaşam Gücü', '#f59e0b', 'rgba(245, 158, 11, 0.3)');

        // Kart 2: Ay (Sağ Üst)
        const moonGlyph = ZODIAC_MAP[moonSign] ? `☾ ${ZODIAC_MAP[moonSign]}` : '☾';
        drawCard(570, 430, 410, 270, moonGlyph, 'AY BURCU', moonSign, 'Duygusal Dünya & Ruh', '#06b6d4', 'rgba(6, 182, 212, 0.3)');

        // Kart 3: Yükselen (Geniş Orta)
        const ascGlyph = ZODIAC_MAP[ascSign] ? `↑ ${ZODIAC_MAP[ascSign]}` : '↑';
        drawCard(100, 740, 880, 260, ascGlyph, 'YÜKSELEN BURÇ (ASC)', ascSign, 'Dünyaya Yansıyan Işığınız & Sosyal Enerjiniz', '#ec4899', 'rgba(236, 72, 153, 0.3)');

        // 7. İlham Verici Kozmik Alıntı Kutusu
        ctx.save();
        ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(100, 1060, 880, 220, 20);
        } else {
            ctx.rect(100, 1060, 880, 220);
        }
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#f8fafc';
        ctx.font = 'italic 28px Georgia, serif';
        ctx.textAlign = 'center';
        ctx.fillText('"Yıldızlar sadece yolu aydınlatır,', centerX, 1140);
        ctx.fillText('kendi kaderini adımlarınla sen yazarsın."', centerX, 1190);
        ctx.restore();

        // 8. Alt Bilgi & Doğum Detayı
        const bInfo = astro.birth_info || {};
        const dateStr = bInfo.date ? `Doğum Tarihi: ${bInfo.date} • ${bInfo.time || ''}` : 'Kaderin Geometrisi Analizi';
        ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
        ctx.font = '22px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(dateStr, centerX, 1720);

        // 9. Alt Footer / URL
        ctx.fillStyle = '#a855f7';
        ctx.font = 'bold 26px monospace';
        ctx.fillText('orbisapp.com  •  @orbisapp', centerX, 1780);

        return canvas;
    }

    async downloadOrShareStory() {
        try {
            const canvas = await this.renderStoryCanvas();
            const dataUrl = canvas.toDataURL('image/png');

            // Web Share API dosya paylaşımı dene (Mobile Safari / Chrome)
            if (navigator.canShare && typeof fetch === 'function') {
                try {
                    const blob = await (await fetch(dataUrl)).blob();
                    const file = new File([blob], 'ORBIS_Kozmik_Story.png', { type: 'image/png' });
                    if (navigator.canShare({ files: [file] })) {
                        await navigator.share({
                            files: [file],
                            title: 'ORBIS Kozmik Kimlik Kartım',
                            text: 'Kozmik Profilimi keşfedin! 🌌'
                        });
                        return;
                    }
                } catch (shareErr) {
                    console.log('[StoryExport] Share API fallback to download:', shareErr);
                }
            }

            // Doğrudan dosya indirme fallback
            const link = document.createElement('a');
            link.download = 'ORBIS_Kozmik_Kimlik.png';
            link.href = dataUrl;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (e) {
            console.error('[StoryExport] download error:', e);
            alert('Görsel oluşturulurken bir hata oluştu.');
        }
    }
}

// Global instance
window.monetization = new MonetizationManager();

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    window.monetization.checkUsage();
});
