/**
 * ステータス表示: カテゴリー別プログレスバー、統計情報
 */

// API_BASE_URL は index.html で定義されている

const CATEGORIES = [
    "基本プロフィール",
    "ライフストーリー",
    "現在の生活",
    "健康・ライフスタイル",
    "趣味・興味・娯楽",
    "学習・成長",
    "人間関係・コミュニティ",
    "情報収集・メディア",
    "経済・消費",
    "価値観・将来"
];

/**
 * ステータス表示を更新
 */
async function updateStatusDisplay(profile) {
    try {
        // カテゴリー別データ数を取得
        const response = await fetch(`${API_BASE_URL}/user/${profile.user_id}`);
        const data = await response.json();

        const categoryCounts = data.category_counts;

        // プログレスバーを更新
        updateProgressBars(categoryCounts);

        // 統計情報を更新
        document.getElementById('sessionCount').textContent = profile.sessions.length;
        document.getElementById('totalDataCount').textContent = profile.total_data_count || 0;

        // バッジ表示を更新
        updateBadgesDisplay(profile.badges);

        // プロファイルビジュアライザーを更新
        updateProfileVisualizer(profile);

    } catch (error) {
        console.error('Update status error:', error);
    }
}

/**
 * プロファイルビジュアライザーを更新
 */
async function updateProfileVisualizer(profile) {
    try {
        if (!window.profileVisualizer) {
            console.log('[Visualizer] Profile visualizer not initialized yet');
            return;
        }

        // 最新のセッションを取得
        if (!profile.sessions || profile.sessions.length === 0) {
            console.log('[Visualizer] No sessions yet');
            return;
        }

        const latestSessionId = profile.sessions[profile.sessions.length - 1];
        const sessionResponse = await fetch(`${API_BASE_URL}/session/${latestSessionId}`);
        const sessionData = await sessionResponse.json();

        // セッションの extracted_data を取得
        const extractedData = sessionData.extracted_data || {};

        // ユーザー名を取得（基本プロフィールから）
        let userName = '-';
        const basicProfile = extractedData['基本プロフィール'] || [];
        const nameItem = basicProfile.find(item => item.key === '名前');
        if (nameItem) {
            userName = typeof nameItem.value === 'object' ? nameItem.value.original : nameItem.value;
        }

        // Reactコンポーネントを更新
        window.profileVisualizer.update(extractedData, userName);
        console.log('[Visualizer] Profile visualizer updated with data:', extractedData);

    } catch (error) {
        console.error('[Visualizer] Update profile visualizer error:', error);
    }
}

/**
 * プログレスバーを更新
 */
function updateProgressBars(categoryCounts) {
    const statusBars = document.getElementById('statusBars');
    statusBars.innerHTML = '';

    const maxCount = 10; // プログレスバーの最大値

    CATEGORIES.forEach(category => {
        const count = categoryCounts[category] || 0;
        const percentage = Math.min((count / maxCount) * 100, 100);

        const barDiv = document.createElement('div');
        barDiv.className = 'status-bar';

        const labelDiv = document.createElement('div');
        labelDiv.className = 'status-bar-label';

        const categorySpan = document.createElement('span');
        categorySpan.textContent = category;

        const countSpan = document.createElement('span');
        countSpan.textContent = `${count}件`;

        labelDiv.appendChild(categorySpan);
        labelDiv.appendChild(countSpan);

        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';

        const progressFill = document.createElement('div');
        progressFill.className = 'progress-fill';
        progressFill.style.width = `${percentage}%`;

        progressBar.appendChild(progressFill);

        barDiv.appendChild(labelDiv);
        barDiv.appendChild(progressBar);

        statusBars.appendChild(barDiv);
    });
}

/**
 * バッジ表示を更新
 */
function updateBadgesDisplay(badges) {
    const container = document.getElementById('badgesContainer');
    container.innerHTML = '';

    if (badges.length === 0) {
        const noBadges = document.createElement('p');
        noBadges.className = 'no-badges';
        noBadges.textContent = 'まだバッジがありません';
        container.appendChild(noBadges);
    } else {
        badges.forEach(badgeName => {
            const badgeItem = document.createElement('div');
            badgeItem.className = 'badge-item';

            const icon = document.createElement('span');
            icon.className = 'badge-icon';
            icon.textContent = BADGE_ICONS[badgeName] || '🏆';

            const name = document.createElement('p');
            name.className = 'badge-name';
            name.textContent = badgeName;

            badgeItem.appendChild(icon);
            badgeItem.appendChild(name);
            container.appendChild(badgeItem);
        });
    }

    updateBadgeCount();
}
