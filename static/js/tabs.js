// Tab Bileşenleri için JavaScript Fonksiyonları
document.addEventListener('DOMContentLoaded', function() {
    // Tab işlevselliğini başlat
    initTabs();

    // Sayfa yüklendiğinde URLdeki hash parametresine göre tabı ayarla
    checkTabFromHash();

    // Hash değişikliklerini dinle
    window.addEventListener('hashchange', checkTabFromHash);
});

/**
 * Sayfa URL'indeki hash değerine göre aktif tabı belirler
 */
function checkTabFromHash() {
    const hash = window.location.hash;
    if (hash && hash.startsWith('#tab-')) {
        const tabId = hash.replace('#tab-', '');
        switchTab(tabId);
    }
}

/**
 * Tab geçiş işlevini başlatır
 */
function initTabs() {
    // Tüm tab butonlarını seç
    const tabItems = document.querySelectorAll('.tab-item');
    
    tabItems.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);
            
            // URL hash'i güncelle (sayfa geçmişi için)
            window.location.hash = `tab-${tabId}`;
        });
    });
}

/**
 * Tab değiştirme fonksiyonu
 * @param {string} tabId - Aktif edilecek tab ID'si
 */
function switchTab(tabId) {
    // Tüm tab butonlarını seç
    const tabItems = document.querySelectorAll('.tab-item');
    // Tüm tab panellerini seç
    const tabPanels = document.querySelectorAll('.tab-panel');
    
    // Tüm sekmelerin active sınıfını kaldır
    tabItems.forEach(item => {
        item.classList.remove('active');
    });
    
    // Tüm sekme içeriklerinin active sınıfını kaldır
    tabPanels.forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Aktif sekmeye ve içeriğe active sınıfını ekle
    const activeTab = document.querySelector(`.tab-item[data-tab="${tabId}"]`);
    const activePanel = document.querySelector(`.tab-panel[data-tab="${tabId}"]`);
    
    if (activeTab) activeTab.classList.add('active');
    if (activePanel) activePanel.classList.add('active');
} 