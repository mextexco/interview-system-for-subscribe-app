/**
 * チャット機能: メッセージ送受信、表示
 */

// グローバル変数
let currentUserId = null;
let currentSessionId = null;
let currentProfile = null;
let messageCount = 0;
let currentCourse = null;
let selectedGender = null;
let selectedCourseIds = [];   // 複数選択対応
let allCoursesData = {};      // /api/courses の結果をキャッシュ
// API_BASE_URL は visualizer.js で定義されている

/**
 * LM Studio接続チェック
 */
async function checkLMStudioConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();

        const statusText = document.getElementById('lmStatusText');
        const modelName = document.getElementById('modelName');

        const serviceName = data.llm_service || 'LM Studio';
        if (data.lm_studio === 'connected') {
            statusText.textContent = serviceName;
            statusText.classList.add('connected');
            statusText.classList.remove('disconnected');

            // モデル名を表示
            if (data.model) {
                modelName.textContent = data.model;
            }
        } else {
            statusText.textContent = `${serviceName} 未接続`;
            statusText.classList.add('disconnected');
            statusText.classList.remove('connected');
            modelName.textContent = '';
        }
    } catch (error) {
        console.error('Health check error:', error);
        const statusText = document.getElementById('lmStatusText');
        statusText.textContent = 'LLM エラー';
        statusText.classList.add('disconnected');
        document.getElementById('modelName').textContent = '';
    }
}

/**
 * バージョン情報を取得
 */
async function fetchVersionInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/version`);
        const data = await response.json();

        const backendVersionEl = document.getElementById('backendVersion');
        if (backendVersionEl && data.backend_version) {
            backendVersionEl.textContent = data.backend_version;
        }
    } catch (error) {
        console.error('Version fetch error:', error);
        const backendVersionEl = document.getElementById('backendVersion');
        if (backendVersionEl) {
            backendVersionEl.textContent = 'Error';
        }
    }
}

/**
 * スタートモーダルを表示
 */
async function showStartModal() {
    const modal = document.getElementById('startModal');
    modal.classList.remove('hidden');

    // ステップ1: キャラクター選択（選択状態をビジュアル表示）
    const genderButtons = document.querySelectorAll('.gender-btn');
    genderButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // 選択状態を切り替え
            genderButtons.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedGender = btn.dataset.gender;
            // 少し間を置いてから次ステップへ
            setTimeout(() => showCourseStep(), 200);
        });
    });

    // 開始ボタン
    document.getElementById('startInterviewBtn').addEventListener('click', () => {
        if (selectedCourseIds.length === 0) return;
        startInterview(selectedGender, selectedCourseIds);
    });

    // コース一覧を読み込んでカードを生成
    await loadCoursesIntoGrid();
}

/**
 * コース選択ステップを表示
 */
function showCourseStep() {
    document.getElementById('stepCharacter').classList.add('hidden');
    document.getElementById('stepCourse').classList.remove('hidden');
}

/**
 * コース一覧をAPIから取得してグリッドに描画（複数選択対応）
 */
async function loadCoursesIntoGrid() {
    try {
        const response = await fetch(`${API_BASE_URL}/courses`);
        allCoursesData = await response.json();
        const grid = document.getElementById('courseGrid');
        grid.innerHTML = '';
        selectedCourseIds = [];

        const courseOrder = [
            'basic_info', 'health_wellness', 'entertainment_deep', 'travel_explorer',
            'subscription_audit', 'daily_pain', 'spending_behavior', 'career_growth',
            'daily_rhythm', 'learning_curiosity'
        ];

        courseOrder.forEach(courseId => {
            const course = allCoursesData[courseId];
            if (!course) return;
            const card = document.createElement('div');
            card.className = 'course-card';
            card.dataset.courseId = courseId;
            card.innerHTML = `
                <div class="course-card-check">✓</div>
                <div class="course-icon">${course.icon}</div>
                <div class="course-info">
                    <div class="course-name">${course.name}</div>
                </div>
            `;
            card.addEventListener('click', () => toggleCourseSelection(courseId, card));
            grid.appendChild(card);
        });
    } catch (error) {
        console.error('[LoadCourses] Error:', error);
    }
}

/**
 * コースの選択状態をトグル
 */
function toggleCourseSelection(courseId, card) {
    const idx = selectedCourseIds.indexOf(courseId);
    if (idx === -1) {
        selectedCourseIds.push(courseId);
        card.classList.add('selected');
    } else {
        selectedCourseIds.splice(idx, 1);
        card.classList.remove('selected');
    }
    updateCourseStartBar();
}

/**
 * 開始バーの状態を更新
 */
function updateCourseStartBar() {
    const btn = document.getElementById('startInterviewBtn');
    const label = document.getElementById('selectedCountLabel');
    if (selectedCourseIds.length === 0) {
        label.textContent = 'コースを選んでください';
        btn.disabled = true;
    } else {
        const names = selectedCourseIds.map(id => allCoursesData[id]?.name || id);
        label.textContent = `選択中: ${names.join(' + ')}`;
        btn.disabled = false;
    }
}

/**
 * インタビュー開始
 */
async function startInterview(gender, courseIds = ['basic_info']) {
    // courseIds は配列
    if (!Array.isArray(courseIds)) courseIds = [courseIds];
    // マージ後のコース情報をUIに使う（最初のコースを代表として使用）
    currentCourse = allCoursesData[courseIds[0]] || null;
    try {
        // ユーザー作成
        const createResponse = await fetch(`${API_BASE_URL}/user/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gender: gender })
        });

        if (!createResponse.ok) {
            const errorText = await createResponse.text();
            console.error('[StartInterview] User creation error:', createResponse.status, errorText);
            alert(`ユーザー作成に失敗しました (${createResponse.status})`);
            return;
        }

        const createData = await createResponse.json();
        if (!createData.success) {
            console.error('[StartInterview] User creation failed:', createData);
            alert('ユーザー作成に失敗しました');
            return;
        }

        currentUserId = createData.user_id;
        currentProfile = createData.profile;

        // セッション作成
        const sessionResponse = await fetch(`${API_BASE_URL}/session/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUserId, course_ids: courseIds })
        });

        if (!sessionResponse.ok) {
            const errorText = await sessionResponse.text();
            console.error('[StartInterview] Session creation error:', sessionResponse.status, errorText);
            alert(`セッション作成に失敗しました (${sessionResponse.status})`);
            return;
        }

        const sessionData = await sessionResponse.json();
        if (!sessionData.success) {
            console.error('[StartInterview] Session creation failed:', sessionData);
            alert('セッション作成に失敗しました');
            return;
        }

        currentSessionId = sessionData.session.session_id;

        // メッセージカウントをリセット
        messageCount = 0;

        // キャラクター設定
        setupCharacter(currentProfile.character);

        // モーダルを閉じる
        document.getElementById('startModal').classList.add('hidden');

        // 進捗バーエリアを表示（コース開始時）
        const progressBarArea = document.getElementById('progressBarArea');
        if (progressBarArea) progressBarArea.classList.remove('hidden');

        // モーダルを閉じた後、少し遅延してメッセージを表示・読み上げ
        setTimeout(() => {
            // 初期メッセージを表示
            const conversation = sessionData.session.conversation;
            console.log('[Chat] Displaying initial messages:', conversation.length);
            conversation.forEach(msg => {
                displayMessage(msg.role, msg.content, msg.expression);
            });

            // 初期メッセージを音声で読み上げ
            if (conversation.length > 0 && conversation[0].role === 'assistant') {
                const firstMessage = conversation[0].content;
                console.log('[Chat] Speaking initial message:', firstMessage);
                if (typeof speakText === 'function') {
                    speakText(firstMessage, currentProfile.character);
                } else {
                    console.error('[Chat] speakText function not available');
                }
            }
        }, 100);

        // 入力を有効化
        document.getElementById('messageInput').disabled = false;
        document.getElementById('sendButton').disabled = false;

        // 送信ボタンイベント
        setupSendButton();

        // 取り消しボタンイベント
        setupUndoButton();

        // 音声ボタンイベント
        setupVoiceButton();

        // ビジュアライゼーション初期化
        if (typeof updateStatusDisplay === 'function') {
            updateStatusDisplay(currentProfile, currentSessionId);
        } else {
            console.warn('[Chat] updateStatusDisplay not available yet');
        }

    } catch (error) {
        console.error('[StartInterview] Error:', error);

        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            alert('サーバーに接続できません。バックエンドサーバーが起動しているか確認してください。');
        } else {
            alert(`エラーが発生しました: ${error.message}`);
        }
    }
}

/**
 * 送信ボタンのセットアップ
 */
function setupSendButton() {
    const sendButton = document.getElementById('sendButton');
    const messageInput = document.getElementById('messageInput');

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

/**
 * 取り消しボタンのセットアップ
 */
function setupUndoButton() {
    const undoButton = document.getElementById('undoButton');
    if (undoButton) {
        undoButton.addEventListener('click', undoLastTurn);
    }
}

/**
 * 進捗バーを更新
 * @param {Array} phases - [{label, icon, current, total}, ...]
 */
function updateProgressBar(phases) {
    const area = document.getElementById('progressBarArea');
    const container = document.getElementById('progressPhases');
    if (!area || !container || !phases) return;

    area.classList.remove('hidden');
    container.innerHTML = '';

    phases.forEach(phase => {
        const pct = phase.total > 0 ? Math.min((phase.current / phase.total) * 100, 100) : 0;
        const done = phase.current >= phase.total;
        const el = document.createElement('div');
        el.className = 'progress-phase' + (done ? ' done' : '');
        el.innerHTML = `
            <span class="progress-phase-label">${phase.icon} ${phase.label}</span>
            <div class="progress-track">
                <div class="progress-fill" style="width:${pct}%"></div>
            </div>
            <span class="progress-count">${phase.current}/${phase.total}</span>
        `;
        container.appendChild(el);
    });
}

/**
 * ファイルをダウンロード
 */
function _triggerDownload(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

/**
 * ダウンロードボタン（メニュー付き）のセットアップ
 */
function setupDownloadButton() {
    const btn = document.getElementById('downloadBtn');
    const menu = document.getElementById('downloadMenu');
    const jsonBtn = document.getElementById('downloadJsonBtn');
    const reportBtn = document.getElementById('downloadReportBtn');
    if (!btn || !menu) return;

    // メニュー開閉
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.classList.toggle('hidden');
    });

    // 外クリックで閉じる
    document.addEventListener('click', () => menu.classList.add('hidden'));

    // JSON ダウンロード
    jsonBtn.addEventListener('click', () => {
        if (!currentSessionId) return;
        _triggerDownload(
            `${API_BASE_URL}/session/${currentSessionId}/export`,
            `session_${currentSessionId.slice(0, 8)}.json`
        );
        menu.classList.add('hidden');
    });

    // レポート（MD）ダウンロード
    reportBtn.addEventListener('click', () => {
        if (!currentSessionId) return;
        _triggerDownload(
            `${API_BASE_URL}/session/${currentSessionId}/report`,
            `report_${currentSessionId.slice(0, 8)}.md`
        );
        menu.classList.add('hidden');
    });
}

/**
 * 終了ボタンのセットアップ
 */
function setupFinishButton() {
    const btn = document.getElementById('finishBtn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        if (!currentSessionId) return;
        btn.disabled = true;
        try {
            const res = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message: '終了します',
                    force_finish: true
                })
            });
            const data = await res.json();
            if (data.success) {
                displayMessage('user', '終了します');
                displayMessage('assistant', data.response, data.expression);
                if (typeof speakText === 'function') speakText(data.response, currentProfile?.character);
                // 入力を無効化
                document.getElementById('messageInput').disabled = true;
                document.getElementById('sendButton').disabled = true;
                document.getElementById('micButton').disabled = true;
                btn.textContent = '終了済み';
            }
        } catch (e) {
            console.error('[FinishBtn] Error:', e);
            btn.disabled = false;
        }
    });
}

/**
 * 音声ボタンのセットアップ
 */
function setupVoiceButton() {
    const micButton = document.getElementById('micButton');
    if (micButton) {
        micButton.addEventListener('click', () => {
            startRecording();
        });
    }
}

/**
 * メッセージ送信
 */
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (!message) return;

    // ユーザーメッセージを表示
    displayMessage('user', message);

    // 入力をクリア
    messageInput.value = '';

    // ボタンを無効化（レスポンス待ち）
    const sendButton = document.getElementById('sendButton');
    sendButton.disabled = true;
    messageInput.disabled = true;

    try {
        // チャットAPIにリクエスト
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message
            })
        });

        // レスポンスのステータスコードをチェック
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Chat] Server error:', response.status, errorText);

            if (response.status === 500) {
                displayErrorMessage('サーバーエラーが発生しました。しばらく待ってから再度お試しください。');
            } else if (response.status === 503) {
                displayErrorMessage('LM Studioとの接続が切れました。LM Studioが起動しているか確認してください。');
            } else {
                displayErrorMessage(`サーバーエラー (${response.status}): 接続に問題が発生しました。`);
            }
            return;
        }

        const data = await response.json();

        if (!data.success) {
            console.error('[Chat] Response error:', data);

            // エラーの詳細をチャットに表示
            if (data.error) {
                if (data.error.includes('LM Studio') || data.error.includes('connection')) {
                    displayErrorMessage('LM Studioとの接続が切れました。LM Studioが起動しているか確認してください。');
                } else {
                    displayErrorMessage(data.error);
                }
            } else {
                displayErrorMessage('メッセージ送信に失敗しました。');
            }
            return;
        }

        // 削除リクエストが検出された場合
        if (data.deletion_request) {
            console.log('[Chat] Deletion request detected - removing previous exchange from UI');
            const chatContainer = document.getElementById('chatContainer');
            const messages = chatContainer.querySelectorAll('.message');

            // 最後から2つ目と1つ目のメッセージを削除（user + assistant）
            // 注意: 削除リクエストメッセージ（最後のuser）は既に表示されているので、それも削除
            if (messages.length >= 3) {
                const messagesToRemove = [
                    messages[messages.length - 3],  // 前のuser
                    messages[messages.length - 2],  // 前のassistant
                    messages[messages.length - 1]   // 削除リクエストメッセージ（current user）
                ];
                messagesToRemove.forEach(msg => {
                    if (msg) {
                        msg.remove();
                    }
                });
            }

            // 確認メッセージを表示
            displayMessage('assistant', data.response, data.expression);

            // 音声で読み上げ
            if (typeof speakText === 'function') {
                speakText(data.response, currentProfile.character);
            }

            // プロファイル更新
            currentProfile = data.profile;
            if (typeof updateStatusDisplay === 'function') {
                updateStatusDisplay(currentProfile, currentSessionId);
            }

            return;  // 削除リクエストの場合はここで終了
        }

        // レスポンスが空の場合
        if (!data.response || data.response.trim() === '') {
            console.error('[Chat] Empty response from server');
            displayErrorMessage('LM Studioから応答がありませんでした。接続を確認してください。');
            return;
        }

        // 訂正が検出された場合、UIから前の2つのメッセージを削除
        if (data.correction_detected) {
            console.log('[Chat] Correction detected - removing previous exchange from UI');
            const chatContainer = document.getElementById('chatContainer');
            const messages = chatContainer.querySelectorAll('.message');

            // 最後から3つ目と2つ目のメッセージを削除（current userメッセージの前のuser + assistant）
            if (messages.length >= 3) {
                // 削除するのは: messages[length-3] (前のuser) と messages[length-2] (前のassistant)
                // messages[length-1] は現在のuserメッセージなので残す
                const messagesToRemove = [messages[messages.length - 3], messages[messages.length - 2]];
                messagesToRemove.forEach(msg => {
                    if (msg) {
                        msg.remove();
                    }
                });
            }
        }

        // アシスタントメッセージを表示
        displayMessage('assistant', data.response, data.expression);

        // 音声で読み上げ
        if (typeof speakText === 'function') {
            speakText(data.response, currentProfile.character);
        }

        // リアクション演出
        if (data.reaction && data.reaction !== 'none') {
            triggerReaction(data.reaction);
        }

        // バッジ獲得
        if (data.badges && data.badges.length > 0) {
            for (const badgeName of data.badges) {
                showBadgeModal(badgeName);
            }
        }

        // 全問完了: 入力を無効化して終了状態にする
        if (data.force_finished) {
            document.getElementById('messageInput').disabled = true;
            document.getElementById('sendButton').disabled = true;
            const micBtn = document.getElementById('micButton');
            if (micBtn) micBtn.disabled = true;
            const finishBtn = document.getElementById('finishInterviewBtn');
            if (finishBtn) { finishBtn.disabled = true; finishBtn.textContent = '終了済み'; }
            if (data.progress) updateProgressBar(data.progress);
            return;
        }

        // 🚀 バックグラウンドデータ抽出の完了を待って自動更新
        // 戦略: 2秒 → +3秒(合計5秒) → +3秒(合計8秒)

        // プロファイル更新
        currentProfile = data.profile;
        if (typeof updateStatusDisplay === 'function') {
            updateStatusDisplay(currentProfile, currentSessionId);
        } else {
            console.warn('[Chat] updateStatusDisplay not available yet');
        }

        // 進捗バー更新
        if (data.progress) {
            updateProgressBar(data.progress);
        }

        // 取り消しボタンを有効化
        const undoButton = document.getElementById('undoButton');
        if (undoButton) {
            undoButton.disabled = false;
        }

        // メッセージカウントを増やす
        messageCount++;

        // 【重要】ベースラインをセッションから直接取得（より確実）
        let autoUpdateBaselineCount = 0;
        try {
            const baselineSessionResponse = await fetch(`${API_BASE_URL}/session/${currentSessionId}`);
            const baselineSessionData = await baselineSessionResponse.json();
            const baselineSession = baselineSessionData.session || baselineSessionData;
            const baselineExtractedData = baselineSession.extracted_data || {};
            Object.values(baselineExtractedData).forEach(items => {
                autoUpdateBaselineCount += (items && items.length) || 0;
            });
            console.log(`[AutoUpdate] 🎯 Baseline count from session: ${autoUpdateBaselineCount}`);
        } catch (error) {
            console.error('[AutoUpdate] Failed to get baseline from session:', error);
            autoUpdateBaselineCount = 0;
        }

        const checkForNewData = async (timing) => {
            try {
                console.log(`[AutoUpdate] Checking for new data at ${timing}...`);
                console.log(`[AutoUpdate] Current baseline: ${autoUpdateBaselineCount}`);

                // セッションデータを直接取得（より確実）
                const sessionResponse = await fetch(`${API_BASE_URL}/session/${currentSessionId}`);
                const sessionData = await sessionResponse.json();
                const session = sessionData.session || sessionData;

                // extracted_data から実際のアイテム数をカウント
                const extractedData = session.extracted_data || {};
                let actualItemCount = 0;
                Object.values(extractedData).forEach(items => {
                    actualItemCount += (items && items.length) || 0;
                });

                console.log(`[AutoUpdate] Actual item count from session: ${actualItemCount}`);

                if (actualItemCount > autoUpdateBaselineCount) {
                    console.log(`[AutoUpdate] ✅ NEW DATA DETECTED at ${timing}! (+${actualItemCount - autoUpdateBaselineCount} items)`);

                    // ユーザープロファイルも更新
                    const userResponse = await fetch(`${API_BASE_URL}/user/${currentUserId}`);
                    const userData = await userResponse.json();
                    currentProfile = userData.profile;
                    autoUpdateBaselineCount = actualItemCount;  // ベースラインを更新

                    // UI更新
                    if (typeof updateStatusDisplay === 'function') {
                        updateStatusDisplay(currentProfile, currentSessionId);
                        console.log(`[AutoUpdate] 🔄 UI updated with new data`);
                    }

                    return true;  // データが見つかった
                } else {
                    console.log(`[AutoUpdate] No new data at ${timing} (baseline: ${autoUpdateBaselineCount}, actual: ${actualItemCount})`);
                    return false;  // データが見つからなかった
                }
            } catch (error) {
                console.error(`[AutoUpdate] Failed at ${timing}:`, error);
                return false;
            }
        };

        // 1回目のチェック: 2秒後
        setTimeout(async () => {
            const found1 = await checkForNewData('2s');

            if (!found1) {
                console.log('[AutoUpdate] No data at 2s, scheduling check at 5s...');

                // 2回目のチェック: さらに3秒後（合計5秒後）
                setTimeout(async () => {
                    const found2 = await checkForNewData('5s (2s + 3s)');

                    if (!found2) {
                        console.log('[AutoUpdate] No data at 5s, scheduling check at 8s...');

                        // 3回目のチェック: さらに3秒後（合計8秒後）
                        setTimeout(async () => {
                            const found3 = await checkForNewData('8s (2s + 3s + 3s)');

                            if (!found3) {
                                console.log('[AutoUpdate] No data at 8s, scheduling check at 12s...');

                                // 4回目のチェック: さらに4秒後（合計12秒後）
                                setTimeout(async () => {
                                    const found4 = await checkForNewData('12s (2s + 3s + 3s + 4s)');

                                    if (!found4) {
                                        console.log('[AutoUpdate] No data at 12s, scheduling check at 16s...');

                                        // 5回目のチェック: さらに4秒後（合計16秒後）
                                        setTimeout(() => {
                                            checkForNewData('16s (2s + 3s + 3s + 4s + 4s)');
                                        }, 4000);
                                    } else {
                                        console.log('[AutoUpdate] Data found at 12s, stopping polling');
                                    }
                                }, 4000);
                            } else {
                                console.log('[AutoUpdate] Data found at 8s, stopping polling');
                            }
                        }, 3000);
                    } else {
                        console.log('[AutoUpdate] Data found at 5s, stopping polling');
                    }
                }, 3000);
            } else {
                console.log('[AutoUpdate] Data found at 2s, stopping polling');
            }
        }, 2000);

        // ランダムイベント判定
        if (typeof shouldTriggerEvent === 'function' && shouldTriggerEvent(messageCount)) {
            // 少し遅らせて表示（アシスタントの返答の後）
            setTimeout(() => {
                const event = selectRandomEvent();
                showEventModal(event);
            }, 1000);
        }

    } catch (error) {
        console.error('[Chat] Send message error:', error);

        // ネットワークエラーの詳細をチャットに表示
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            displayErrorMessage('サーバーに接続できません。バックエンドサーバーが起動しているか確認してください。');
        } else if (error.name === 'AbortError') {
            displayErrorMessage('リクエストがタイムアウトしました。');
        } else {
            displayErrorMessage(`通信エラーが発生しました: ${error.message}`);
        }
    } finally {
        // ボタンを再有効化
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

/**
 * 最後のやりとりを取り消す
 */
async function undoLastTurn() {
    if (!currentSessionId) {
        alert('セッションが見つかりません');
        return;
    }

    const undoButton = document.getElementById('undoButton');
    const chatContainer = document.getElementById('chatContainer');
    const messages = chatContainer.querySelectorAll('.message');

    // 最初のメッセージしかない場合は取り消せない
    if (messages.length <= 1) {
        displaySystemMessage('取り消せるメッセージがありません');
        return;
    }

    // ボタンを無効化
    undoButton.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/undo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Undo] Server error:', response.status, errorText);
            displayErrorMessage(`取り消しに失敗しました (${response.status})`);
            return;
        }

        const data = await response.json();

        if (!data.success) {
            console.error('[Undo] Response error:', data);
            displayErrorMessage(data.message || '取り消しに失敗しました');
            return;
        }

        console.log(`[Undo] Removed ${data.removed_data_count} data points`);

        // UIから最後の2つのメッセージを削除（user + assistant）
        const messagesToRemove = Array.from(messages).slice(-2);
        messagesToRemove.forEach(msg => msg.remove());

        // プロファイルを更新
        currentProfile = data.profile;
        if (typeof updateStatusDisplay === 'function') {
            updateStatusDisplay(currentProfile, currentSessionId);
        } else {
            console.warn('[Chat] updateStatusDisplay not available yet');
        }

        // チャット欄に削除完了メッセージを表示
        displaySystemMessage('最後のやりとりを削除しました');

    } catch (error) {
        console.error('[Undo] Error:', error);
        displayErrorMessage(`取り消し中にエラーが発生しました: ${error.message}`);
    } finally {
        // ボタンを再有効化
        undoButton.disabled = false;
    }
}

/**
 * メッセージを表示
 */
function displayMessage(role, content, expression = 'normal') {
    const chatContainer = document.getElementById('chatContainer');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = content;

    messageDiv.appendChild(bubbleDiv);
    chatContainer.appendChild(messageDiv);

    // スクロール
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // アシスタントメッセージの場合、表情を更新
    if (role === 'assistant' && expression) {
        updateCharacterExpression(expression);
    }
}

/**
 * システムエラーメッセージを表示（赤色）
 */
function displayErrorMessage(errorMessage) {
    const chatContainer = document.getElementById('chatContainer');

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-error';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = `⚠️ エラー: ${errorMessage}`;

    messageDiv.appendChild(bubbleDiv);
    chatContainer.appendChild(messageDiv);

    // スクロール
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * システム通知メッセージをチャット欄に表示（グレー・中央）
 */
function displaySystemMessage(message) {
    const chatContainer = document.getElementById('chatContainer');
    const div = document.createElement('div');
    div.className = 'message system-notice';
    div.textContent = message;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * ステータス折りたたみのセットアップ
 */
function setupStatusToggle() {
    const statusToggle = document.getElementById('statusToggle');
    const statusContent = document.getElementById('statusContent');
    const statusIcon = statusToggle.querySelector('.toggle-icon');

    statusToggle.addEventListener('click', () => {
        statusContent.classList.toggle('collapsed');
        statusIcon.classList.toggle('rotated');
    });

    // バッジセクション折りたたみのセットアップ
    const badgesToggle = document.getElementById('badgesToggle');
    const badgesContent = document.getElementById('badgesContent');
    const badgesIcon = badgesToggle.querySelector('.toggle-icon');

    // デフォルトで折りたたんでおく（プロファイルマップを最大化）
    badgesContent.classList.add('collapsed');
    badgesIcon.classList.add('rotated');

    badgesToggle.addEventListener('click', () => {
        badgesContent.classList.toggle('collapsed');
        badgesIcon.classList.toggle('rotated');
    });
}
