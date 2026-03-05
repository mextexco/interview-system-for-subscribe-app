(function () {
    function isMobile() {
        return window.innerWidth <= 768;
    }

    function switchMobileTab(tab) {
        if (!isMobile()) return;
        const leftPane = document.querySelector('.left-pane');
        const rightPane = document.querySelector('.right-pane');
        document.querySelectorAll('.mobile-tab').forEach(function (t) {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        if (tab === 'chat') {
            leftPane.classList.remove('mobile-hidden');
            rightPane.classList.remove('mobile-active');
        } else {
            leftPane.classList.add('mobile-hidden');
            rightPane.classList.add('mobile-active');
        }
    }

    function updateProfileBadge(count) {
        var badge = document.getElementById('profileTabBadge');
        if (badge) badge.textContent = count > 0 ? count : '';
    }

    function initMobileTabs() {
        document.querySelectorAll('.mobile-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                switchMobileTab(btn.dataset.tab);
            });
        });
        if (isMobile()) switchMobileTab('chat');
    }

    document.addEventListener('DOMContentLoaded', initMobileTabs);

    window.switchMobileTab = switchMobileTab;
    window.updateProfileBadge = updateProfileBadge;
    window.isMobile = isMobile;
})();
