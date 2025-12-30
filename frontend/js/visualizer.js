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
async function updateStatusDisplay(profile, sessionId = null) {
    try {
        // カテゴリー別データ数を取得
        const response = await fetch(`${API_BASE_URL}/user/${profile.user_id}`);
        const data = await response.json();

        const categoryCounts = data.category_counts;

        // プログレスバーを更新
        updateProgressBars(categoryCounts);

        // 統計情報を更新
        const sessionCount = profile.sessions ? profile.sessions.length : 0;
        document.getElementById('sessionCount').textContent = sessionCount;
        document.getElementById('totalDataCount').textContent = profile.total_data_count || 0;

        // バッジ表示を更新
        updateBadgesDisplay(profile.badges);

        // プロファイルビジュアライザーを更新（sessionIdを渡す）
        updateProfileVisualizer(profile, sessionId);

        // 最近の抽出データを更新（sessionIdを渡す）
        if (sessionId) {
            updateRecentData(sessionId);
        }

    } catch (error) {
        console.error('Update status error:', error);
    }
}

/**
 * プロファイルビジュアライザーを更新
 */
async function updateProfileVisualizer(profile, sessionId = null) {
    try {
        if (!window.profileVisualizer) {
            console.log('[Visualizer] Profile visualizer not initialized yet');
            return;
        }

        // sessionId が渡されているかチェック
        if (!sessionId) {
            console.log('[Visualizer] No session ID provided');
            return;
        }

        console.log('[Visualizer] Fetching session data for session:', sessionId);

        const sessionResponse = await fetch(`${API_BASE_URL}/session/${sessionId}`);
        const sessionData = await sessionResponse.json();

        console.log('[Visualizer] Session data received:', sessionData);

        // セッションの extracted_data を取得（APIレスポンスは {session: {...}} の構造）
        const session = sessionData.session || sessionData;
        console.log('[Visualizer] Session object:', session);
        console.log('[Visualizer] Session keys:', Object.keys(session));

        const extractedData = session.extracted_data || {};

        console.log('[Visualizer] Extracted data:', extractedData);
        console.log('[Visualizer] Extracted data keys:', Object.keys(extractedData));

        // ユーザー名を取得（基本プロフィールから）
        let userName = '-';
        const basicProfile = extractedData['基本プロフィール'] || [];
        console.log('[Visualizer] Basic profile data:', basicProfile);

        const nameItem = basicProfile.find(item => item.key === '名前');
        console.log('[Visualizer] Name item found:', nameItem);

        if (nameItem) {
            // Check for original_value first (if normalization occurred), otherwise use value
            userName = nameItem.original_value || nameItem.value;
        }

        console.log('[Visualizer] Updating visualizer with userName:', userName);

        // Reactコンポーネントを更新
        window.profileVisualizer.update(extractedData, userName);
        console.log('[Visualizer] Profile visualizer updated successfully');

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

// 前回のデータを記憶（新規アイテム検出用）
let previousRecentDataTimestamps = [];

/**
 * 最近の抽出データを更新
 */
async function updateRecentData(sessionId) {
    try {
        if (!sessionId) {
            console.log('[RecentData] No session ID provided');
            return;
        }

        console.log('[RecentData] Fetching session data for session:', sessionId);

        const sessionResponse = await fetch(`${API_BASE_URL}/session/${sessionId}`);
        const sessionData = await sessionResponse.json();
        const session = sessionData.session || sessionData;
        const extractedData = session.extracted_data || {};

        // 全てのデータポイントを配列に変換
        let allDataPoints = [];
        Object.entries(extractedData).forEach(([category, items]) => {
            items.forEach(item => {
                allDataPoints.push({
                    category: category,
                    key: item.key,
                    value: item.value,
                    timestamp: item.timestamp || Date.now()
                });
            });
        });

        // タイムスタンプでソート（新しい順）
        allDataPoints.sort((a, b) => {
            return new Date(b.timestamp) - new Date(a.timestamp);
        });

        // 最新5件を取得（リバース表示なので、配列の先頭5件を逆順にする）
        const recentData = allDataPoints.slice(0, 5).reverse();

        console.log('[RecentData] Recent data points:', recentData);

        // 新しいアイテムを検出
        const currentTimestamps = recentData.map(item => item.timestamp);
        const newTimestamps = currentTimestamps.filter(ts => !previousRecentDataTimestamps.includes(ts));
        console.log('[RecentData] New items:', newTimestamps.length);

        // 表示を更新
        const listContainer = document.getElementById('recentDataList');

        if (recentData.length === 0) {
            listContainer.innerHTML = '<p class="no-data">まだデータがありません</p>';
        } else {
            listContainer.innerHTML = '';
            recentData.forEach(item => {
                // valueがオブジェクトの場合の処理
                let displayValue = item.value;
                if (typeof item.value === 'object' && item.value !== null) {
                    // originalフィールドがあればそれを使用
                    displayValue = item.value.original || JSON.stringify(item.value);
                }

                const itemDiv = document.createElement('div');
                itemDiv.className = 'recent-data-item';

                // 新しいアイテムかチェック
                const isNew = newTimestamps.includes(item.timestamp);
                if (isNew) {
                    itemDiv.classList.add('new-item');
                    console.log('[RecentData] New item detected:', item.key);

                    // 3秒後にnew-itemクラスを削除
                    setTimeout(() => {
                        itemDiv.classList.remove('new-item');
                    }, 3000);
                }

                itemDiv.innerHTML = `
                    <span class="category-key">${item.category} - ${item.key}:</span>
                    <span class="value">${displayValue}</span>
                `;
                listContainer.appendChild(itemDiv);
            });
        }

        // 今回のタイムスタンプを保存
        previousRecentDataTimestamps = currentTimestamps;

    } catch (error) {
        console.error('[RecentData] Update recent data error:', error);
    }
}

