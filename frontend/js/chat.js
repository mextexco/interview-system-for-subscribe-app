/**
 * チャット機能: メッセージ送受信、表示
 */

// グローバル変数
let currentUserId = null;
let currentSessionId = null;
let currentProfile = null;
let messageCount = 0;
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

        if (data.lm_studio === 'connected') {
            statusText.textContent = 'LM Studio';
            statusText.classList.add('connected');
            statusText.classList.remove('disconnected');

            // モデル名を表示
            if (data.model) {
                modelName.textContent = data.model;
            }
        } else {
            statusText.textContent = 'LM Studio 未接続';
            statusText.classList.add('disconnected');
            statusText.classList.remove('connected');
            modelName.textContent = '';
        }
    } catch (error) {
        console.error('Health check error:', error);
        const statusText = document.getElementById('lmStatusText');
        statusText.textContent = 'LM Studio エラー';
        statusText.classList.add('disconnected');
        document.getElementById('modelName').textContent = '';
    }
}

/**
 * スタートモーダルを表示
 */
function showStartModal() {
    const modal = document.getElementById('startModal');
    modal.classList.remove('hidden');

    // 性別ボタンにイベントリスナー
    const genderButtons = document.querySelectorAll('.gender-btn');
    genderButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const gender = btn.dataset.gender;
            startInterview(gender);
        });
    });
}

/**
 * インタビュー開始
 */
async function startInterview(gender) {
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
            body: JSON.stringify({ user_id: currentUserId })
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

        // プロファイル更新
        currentProfile = data.profile;
        if (typeof updateStatusDisplay === 'function') {
            updateStatusDisplay(currentProfile, currentSessionId);
        } else {
            console.warn('[Chat] updateStatusDisplay not available yet');
        }

        // 取り消しボタンを有効化
        const undoButton = document.getElementById('undoButton');
        if (undoButton) {
            undoButton.disabled = false;
        }

        // メッセージカウントを増やす
        messageCount++;

        // 🚀 バックグラウンドデータ抽出の完了を待って自動更新
        // 戦略: 2秒で早期チェック（50%カバー）→ 5秒で確実チェック（100%カバー）

        // 現在のデータ数をキャプチャ（この時点での値）
        let autoUpdateBaselineCount = currentProfile.total_data_count || 0;

        const checkForNewData = async (timing) => {
            try {
                console.log(`[AutoUpdate] Checking for new data at ${timing}...`);

                // ユーザーデータを再取得
                const response = await fetch(`${API_BASE_URL}/user/${currentUserId}`);
                const data = await response.json();

                const updatedProfile = data.profile;
                const newDataCount = updatedProfile.total_data_count || 0;

                if (newDataCount > autoUpdateBaselineCount) {
                    console.log(`[AutoUpdate] ✅ NEW DATA DETECTED at ${timing}! (+${newDataCount - autoUpdateBaselineCount} items)`);

                    // プロファイルを更新
                    currentProfile = updatedProfile;
                    autoUpdateBaselineCount = newDataCount;  // ベースラインを更新（次回チェックのため）

                    // UI更新
                    if (typeof updateStatusDisplay === 'function') {
                        updateStatusDisplay(currentProfile, currentSessionId);
                        console.log(`[AutoUpdate] UI updated with new data`);
                    }
                } else {
                    console.log(`[AutoUpdate] No new data at ${timing}`);
                }
            } catch (error) {
                console.error(`[AutoUpdate] Failed at ${timing}:`, error);
            }
        };

        // 2秒後: 早期チェック（約50%のケースで成功）
        setTimeout(() => checkForNewData('2s'), 2000);

        // 5秒後: 確実チェック（残りのケースをカバー）
        setTimeout(() => checkForNewData('5s'), 5000);

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
        alert('取り消せるメッセージがありません');
        return;
    }

    // 確認ダイアログ
    if (!confirm('最後のやりとりを取り消しますか？\n（抽出されたデータも削除されます）')) {
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

        // 通知
        alert(`取り消しました（${data.removed_data_count}件のデータを削除）`);

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
