/**
 * 音声機能: Web Speech API (音声認識・音声合成)
 */

// 音声認識の設定
let recognition = null;
let isRecording = false;
let hasReceivedResult = false;  // 結果を受信したかどうか
let recognitionTimeout = null;  // タイムアウト管理用
let restartCount = 0;  // 再起動回数
const MAX_RESTARTS = 3;  // 最大再起動回数
let autoSendTimer = null;  // 自動送信タイマー（発話終了後のバッファ）
const AUTO_SEND_DELAY_MS = 2000;  // 発話終了から送信までの待機時間（ms）

// 音声合成の設定
const synth = window.speechSynthesis;
let currentVoice = null;

// VOICEVOX設定
const VOICEVOX_URL = 'http://localhost:50021';
let voicevoxAvailable = false;
let currentAudio = null;  // 現在再生中の音声
let isSpeaking = false;   // TTS再生中フラグ（マイク無効化制御用）

/**
 * VOICEVOX接続チェック
 */
async function checkVoicevoxConnection() {
    try {
        const response = await fetch(`${VOICEVOX_URL}/version`, {
            method: 'GET',
            timeout: 3000
        });
        if (response.ok) {
            voicevoxAvailable = true;
            console.log('[VOICEVOX] Connected successfully');
            return true;
        }
    } catch (error) {
        voicevoxAvailable = false;
        console.log('[VOICEVOX] Not available, using Web Speech API as fallback');
    }
    return false;
}

/**
 * 音声認識を初期化
 */
function initSpeechRecognition() {
    // ブラウザ対応チェック
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.warn('このブラウザは音声認識に対応していません');
        return false;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'ja-JP';

    // 継続音声入力モードのチェックボックス状態に応じて設定
    const continuousModeCheckbox = document.getElementById('continuousVoiceMode');
    recognition.continuous = continuousModeCheckbox ? continuousModeCheckbox.checked : false;

    recognition.interimResults = true;  // 中間結果を有効にして即座の終了を防ぐ
    recognition.maxAlternatives = 1;

    // 認識結果のハンドリング
    recognition.onresult = (event) => {
        hasReceivedResult = true;  // 結果を受信した

        // 継続モードの場合、全ての結果を結合
        const continuousModeCheckbox = document.getElementById('continuousVoiceMode');
        const isContinuousMode = continuousModeCheckbox && continuousModeCheckbox.checked;

        let transcript = '';
        let isFinal = false;

        if (isContinuousMode) {
            // 継続モード: 全ての確定結果を結合
            for (let i = 0; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    transcript += event.results[i][0].transcript;
                    isFinal = true;
                }
            }
        } else {
            // 通常モード: 最後の確定結果のみ
            for (let i = event.results.length - 1; i >= 0; i--) {
                if (event.results[i].isFinal) {
                    transcript = event.results[i][0].transcript;
                    isFinal = true;
                    break;
                }
            }
        }

        // 確定結果がない場合は何もしない（中間結果は無視）
        if (!isFinal || !transcript.trim()) {
            return;
        }

        console.log('[Voice] Recognition result (final):', transcript);

        // 認識したテキストを入力欄に設定
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = transcript;

            // 継続モードがOFFの場合のみ自動送信
            // 継続モードがONの場合は、ユーザーがマイクボタンを押して停止するまで待つ
            if (!isContinuousMode) {
                // 発話終了後 AUTO_SEND_DELAY_MS 待ってから送信（追加発話があればタイマーリセット）
                if (autoSendTimer) clearTimeout(autoSendTimer);
                autoSendTimer = setTimeout(() => {
                    autoSendTimer = null;
                    if (messageInput.value.trim()) {
                        sendMessage();
                    }
                }, AUTO_SEND_DELAY_MS);
                console.log(`[Voice] Auto-send scheduled in ${AUTO_SEND_DELAY_MS}ms`);
            } else {
                console.log('[Voice] Continuous mode: text updated, waiting for manual stop');
            }
        }
    };

    recognition.onerror = (event) => {
        console.error('[Voice] Recognition error:', event.error, 'Message:', event.message);
        console.log('[Voice] Error details - Type:', event.error, 'Timestamp:', new Date().toISOString());

        // エラーの種類に応じて処理
        if (event.error === 'no-speech') {
            console.log('[Voice] No speech detected - this might be normal if user hasn\'t spoken yet');
            // no-speechの場合は、再起動ロジックに任せる（stopRecordingを呼ばない）
            return;
        } else if (event.error === 'not-allowed') {
            stopRecording();
            showVoiceError('マイクへのアクセスが許可されていません');
        } else if (event.error === 'audio-capture') {
            stopRecording();
            showVoiceError('マイクからの音声キャプチャに失敗しました');
        } else if (event.error === 'network') {
            stopRecording();
            showVoiceError('ネットワークエラーが発生しました');
        } else {
            stopRecording();
            showVoiceError('音声認識エラー: ' + event.error);
        }
    };

    recognition.onstart = () => {
        console.log('[Voice] Recognition actually started');
    };

    recognition.onend = () => {
        const timestamp = new Date().toISOString();
        console.log(`[Voice] Recognition ended at ${timestamp}`);
        console.log(`[Voice] State: hasReceivedResult=${hasReceivedResult}, restartCount=${restartCount}, isRecording=${isRecording}`);

        // タイムアウトをクリア
        if (recognitionTimeout) {
            clearTimeout(recognitionTimeout);
            recognitionTimeout = null;
        }

        // 継続モードの場合、全ての結果を結合
        const continuousModeCheckbox = document.getElementById('continuousVoiceMode');
        const isContinuousMode = continuousModeCheckbox && continuousModeCheckbox.checked;

        // まだ録音中で結果を受信していない場合は再起動（制限付き）
        if (isRecording && !hasReceivedResult && restartCount < MAX_RESTARTS) {
            restartCount++;
            console.log('[Voice] No result received, restarting recognition... (attempt', restartCount, '/', MAX_RESTARTS, ')');

            // 再起動前に少し待機（連続再起動を防ぐ）
            setTimeout(() => {
                try {
                    console.log('[Voice] Attempting to restart recognition now...');
                    recognition.start();
                } catch (error) {
                    console.error('[Voice] Failed to restart recognition:', error);
                    stopRecording();
                    showVoiceError('音声認識の開始に失敗しました。マイクの設定を確認してください。');
                }
            }, 500);  // 500ms待機
            return;  // 再起動処理を開始したので終了処理はスキップ
        } else if (isRecording && !hasReceivedResult && restartCount >= MAX_RESTARTS) {
            // 再起動制限に達した
            console.log('[Voice] Max restarts reached, stopping...');
            stopRecording();
            showVoiceError('音声が検出されませんでした。マイクが正しく接続されているか確認してください。');
            return;
        }

        if (!isContinuousMode && isRecording) {
            // 通常モード: 自動停止したのでクリーンアップ
            console.log('[Voice] Normal mode: auto-stopping');
            stopRecording();
        } else if (isContinuousMode && isRecording) {
            // 継続モードで isRecording がまだ true の場合（予期しない停止）
            console.log('[Voice] Unexpected end in continuous mode');
            isRecording = false;
            updateMicButton(false);
        }

        // リセット
        if (!isRecording || hasReceivedResult) {
            console.log('[Voice] Resetting restartCount to 0');
            restartCount = 0;
        }
    };

    return true;
}

/**
 * マイクの権限と利用可能性をチェック
 */
async function checkMicrophoneAccess() {
    try {
        console.log('[Voice] Checking microphone access...');

        // マイク権限をリクエスト
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // 権限が取得できたらストリームを閉じる
        stream.getTracks().forEach(track => track.stop());

        console.log('[Voice] Microphone access granted');
        return true;
    } catch (error) {
        console.error('[Voice] Microphone access error:', error);

        if (error.name === 'NotAllowedError') {
            showVoiceError('マイクへのアクセスが拒否されました。ブラウザの設定を確認してください。');
        } else if (error.name === 'NotFoundError') {
            showVoiceError('マイクが見つかりません。マイクが接続されているか確認してください。');
        } else {
            showVoiceError('マイクへのアクセスに失敗しました: ' + error.message);
        }

        return false;
    }
}

/**
 * 音声認識を開始
 */
async function startRecording() {
    if (!recognition) {
        if (!initSpeechRecognition()) {
            alert('音声認識が利用できません。ブラウザを確認してください。');
            return;
        }
    }

    // TTS再生中はマイクを起動しない
    if (isSpeaking) {
        console.log('[Voice] Blocked: TTS is still speaking');
        return;
    }

    if (isRecording) {
        stopRecording();
        return;
    }

    // マイクアクセスをチェック
    const hasAccess = await checkMicrophoneAccess();
    if (!hasAccess) {
        console.log('[Voice] Microphone access denied, aborting');
        return;
    }

    try {
        // 録音開始時に継続モードのチェックボックス状態を反映
        const continuousModeCheckbox = document.getElementById('continuousVoiceMode');
        recognition.continuous = continuousModeCheckbox ? continuousModeCheckbox.checked : false;

        hasReceivedResult = false;  // 結果受信フラグをリセット
        restartCount = 0;  // 再起動カウントをリセット

        console.log('[Voice] Starting recognition... (continuous mode:', recognition.continuous, ')');
        recognition.start();
        isRecording = true;
        updateMicButton(true);

        // 15秒後に自動停止（ユーザーが話さない場合のフェイルセーフ）
        recognitionTimeout = setTimeout(() => {
            if (isRecording && !hasReceivedResult) {
                console.log('[Voice] Recognition timeout - no speech detected after 15 seconds');
                stopRecording();
                showVoiceError('音声が検出されませんでした。マイクが正しく動作しているか確認してください。');
            }
        }, 15000);
    } catch (error) {
        console.error('[Voice] Failed to start recording:', error);
        isRecording = false;
        updateMicButton(false);
        showVoiceError('音声認識を開始できませんでした: ' + error.message);
    }
}

/**
 * 音声認識を停止
 */
function stopRecording() {
    if (recognition && isRecording) {
        console.log('[Voice] Stopping recording...');

        // タイムアウトをクリア
        if (recognitionTimeout) {
            clearTimeout(recognitionTimeout);
            recognitionTimeout = null;
        }

        // 自動送信タイマーをクリア（手動停止時はすぐに送信しない）
        if (autoSendTimer) {
            clearTimeout(autoSendTimer);
            autoSendTimer = null;
        }

        recognition.stop();
        isRecording = false;
        updateMicButton(false);

        // 継続モードがONの場合、停止時にメッセージを自動送信
        const continuousModeCheckbox = document.getElementById('continuousVoiceMode');
        const isContinuousMode = continuousModeCheckbox && continuousModeCheckbox.checked;
        const messageInput = document.getElementById('messageInput');
        const messageText = messageInput ? messageInput.value.trim() : '';

        console.log('[Voice] Recording stopped. Continuous mode:', isContinuousMode, ', Message:', messageText);

        if (isContinuousMode && messageInput && messageText) {
            console.log('[Voice] Continuous mode: Auto-sending message...');
            // 少し遅延を入れて確実にUIが更新されてから送信
            setTimeout(() => {
                if (typeof sendMessage === 'function') {
                    sendMessage();
                    console.log('[Voice] Message sent successfully');
                } else {
                    console.error('[Voice] sendMessage function not found');
                }
            }, 100);
        } else {
            if (isContinuousMode) {
                console.log('[Voice] Continuous mode enabled but no message to send');
            }
        }
    } else {
        console.log('[Voice] stopRecording called but not recording (isRecording:', isRecording, ')');
    }
}

/**
 * マイクボタンの表示を更新
 */
function updateMicButton(recording) {
    const micButton = document.getElementById('micButton');
    if (!micButton) return;

    if (recording) {
        micButton.classList.add('recording');
        micButton.textContent = '🎤';
        micButton.title = '録音中...（クリックで停止）';
    } else {
        micButton.classList.remove('recording');
        micButton.textContent = '🎙️';
        micButton.title = '音声入力を開始';
    }
}

/**
 * 音声エラーメッセージを表示
 */
function showVoiceError(message) {
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        const originalPlaceholder = messageInput.placeholder;
        messageInput.placeholder = message;
        setTimeout(() => {
            messageInput.placeholder = originalPlaceholder;
        }, 3000);
    }
}

/**
 * テキストを音声で読み上げ（VOICEVOX → Google TTS → Web Speech API の順で試みる）
 */
async function speakText(text, characterId = 'aoi') {
    // 絵文字を除去
    const cleanedText = removeEmojis(text);

    // 空文字列の場合は読み上げない
    if (!cleanedText.trim()) {
        console.log('[Voice] No text to speak after emoji removal');
        return;
    }

    // 1. VOICEVOXが利用可能な場合はVOICEVOXを使用（ローカル環境）
    if (voicevoxAvailable) {
        console.log('[Voice] Using VOICEVOX for synthesis');
        const success = await speakWithVoicevox(cleanedText, characterId);
        if (success) return;
        console.log('[Voice] VOICEVOX failed, falling back to Google TTS');
    }

    // 2. Google TTS（クラウド環境）
    console.log('[Voice] Trying Google TTS');
    const googleOk = await speakWithGoogleTTS(cleanedText, characterId);
    if (googleOk) return;

    // 3. フォールバック: Web Speech API
    console.log('[Voice] Using Web Speech API as final fallback');
    speakWithWebSpeechAPI(cleanedText, characterId);
}

/**
 * Google Cloud TTSで音声合成（バックエンドプロキシ経由）
 */
async function speakWithGoogleTTS(text, characterId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, character: characterId })
        });

        if (!response.ok) {
            console.log(`[GoogleTTS] Endpoint returned ${response.status}, skipping`);
            return false;
        }

        const data = await response.json();
        if (!data.audioContent) return false;

        // base64 → Blob → Audio
        const audioBytes = atob(data.audioContent);
        const buffer = new ArrayBuffer(audioBytes.length);
        const view = new Uint8Array(buffer);
        for (let i = 0; i < audioBytes.length; i++) {
            view[i] = audioBytes.charCodeAt(i);
        }
        const audioBlob = new Blob([buffer], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);

        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        currentAudio = new Audio(audioUrl);

        currentAudio.onplay = () => {
            console.log('[GoogleTTS] Playback started');
            isSpeaking = true;
            updateSpeakerIcon(true);
            setMicButtonDisabled(true);
            if (isRecording) {
                recognition.stop();
                isRecording = false;
                updateMicButton(false);
            }
        };

        currentAudio.onended = () => {
            console.log('[GoogleTTS] Playback ended');
            isSpeaking = false;
            updateSpeakerIcon(false);
            setMicButtonDisabled(false);
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
            if (!isRecording) startRecording();
        };

        currentAudio.onerror = (e) => {
            console.error('[GoogleTTS] Playback error:', e);
            isSpeaking = false;
            updateSpeakerIcon(false);
            setMicButtonDisabled(false);
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
            if (!isRecording) startRecording();
        };

        await currentAudio.play();
        return true;

    } catch (error) {
        console.error('[GoogleTTS] Failed:', error);
        return false;
    }
}

/**
 * Web Speech APIで読み上げ
 */
function speakWithWebSpeechAPI(text, characterId) {
    if (!synth) {
        console.warn('このブラウザは音声合成に対応していません');
        return;
    }

    // 既存の音声を停止
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';

    // キャラクターごとの音声設定
    const voiceSettings = getVoiceSettings(characterId);
    utterance.pitch = voiceSettings.pitch;
    utterance.rate = voiceSettings.rate;
    utterance.volume = voiceSettings.volume;

    // 利用可能な日本語音声を取得
    const voices = synth.getVoices();
    const japaneseVoice = voices.find(voice => voice.lang.startsWith('ja'));
    if (japaneseVoice) {
        utterance.voice = japaneseVoice;
    }

    // 読み上げ開始・終了イベント
    utterance.onstart = () => {
        console.log('[Voice] Speech started');
        isSpeaking = true;
        updateSpeakerIcon(true);
        setMicButtonDisabled(true);
        // 音声読み上げ中は音声認識を停止（AIの音声を拾わないため）
        if (isRecording) {
            recognition.stop();
            isRecording = false;
            updateMicButton(false);
            console.log('[Voice] Recognition paused during speech');
        }
    };

    utterance.onend = () => {
        console.log('[Voice] Speech ended');
        isSpeaking = false;
        updateSpeakerIcon(false);
        setMicButtonDisabled(false);
        if (!isRecording) startRecording();
    };

    utterance.onerror = (event) => {
        console.error('[Voice] Speech error:', event.error);
        isSpeaking = false;
        updateSpeakerIcon(false);
        setMicButtonDisabled(false);
        if (!isRecording) startRecording();
    };

    synth.speak(utterance);
}

/**
 * テキストから絵文字を除去
 */
function removeEmojis(text) {
    // 絵文字の範囲を網羅する正規表現
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F000}-\u{1F02F}\u{1F0A0}-\u{1F0FF}\u{1F100}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2300}-\u{23FF}\u{2B50}\u{2B55}\u{231A}\u{231B}\u{2328}\u{23CF}\u{23E9}-\u{23F3}\u{23F8}-\u{23FA}\u{25AA}\u{25AB}\u{25B6}\u{25C0}\u{25FB}-\u{25FE}\u{2600}-\u{2604}\u{260E}\u{2611}\u{2614}\u{2615}\u{2618}\u{261D}\u{2620}\u{2622}\u{2623}\u{2626}\u{262A}\u{262E}\u{262F}\u{2638}-\u{263A}\u{2640}\u{2642}\u{2648}-\u{2653}\u{2660}\u{2663}\u{2665}\u{2666}\u{2668}\u{267B}\u{267F}\u{2692}-\u{2697}\u{2699}\u{269B}\u{269C}\u{26A0}\u{26A1}\u{26AA}\u{26AB}\u{26B0}\u{26B1}\u{26BD}\u{26BE}\u{26C4}\u{26C5}\u{26C8}\u{26CE}\u{26CF}\u{26D1}\u{26D3}\u{26D4}\u{26E9}\u{26EA}\u{26F0}-\u{26F5}\u{26F7}-\u{26FA}\u{26FD}\u{2702}\u{2705}\u{2708}-\u{270D}\u{270F}\u{2712}\u{2714}\u{2716}\u{271D}\u{2721}\u{2728}\u{2733}\u{2734}\u{2744}\u{2747}\u{274C}\u{274E}\u{2753}-\u{2755}\u{2757}\u{2763}\u{2764}\u{2795}-\u{2797}\u{27A1}\u{27B0}\u{27BF}\u{2934}\u{2935}\u{2B05}-\u{2B07}\u{2B1B}\u{2B1C}\u{2B50}\u{2B55}\u{3030}\u{303D}\u{3297}\u{3299}]/gu;

    return text.replace(emojiRegex, '').trim();
}

/**
 * キャラクターごとの音声設定を取得
 */
function getVoiceSettings(characterId) {
    const settings = {
        'misaki': {
            pitch: 1.2,  // 高め（女性）
            rate: 1.3,   // やや速め（1.0 → 1.3）
            volume: 1.0,
            voicevoxSpeaker: 8,  // 春日部つむぎ（明るい女性）
            voicevoxSpeed: 1.2
        },
        'kenta': {
            pitch: 0.8,  // 低め（男性）
            rate: 1.5,   // 1.5倍速（0.95 → 1.25 → 1.5）
            volume: 1.0,
            voicevoxSpeaker: 13,  // 青山龍星（落ち着いた男性）
            voicevoxSpeed: 1.5   // 1.5倍速
        },
        'aoi': {
            pitch: 1.0,  // 標準（中性）
            rate: 1.3,   // やや速め（1.0 → 1.3）
            volume: 1.0,
            voicevoxSpeaker: 3,  // ずんだもん（中性的）
            voicevoxSpeed: 1.2
        }
    };

    return settings[characterId] || settings['aoi'];
}

/**
 * VOICEVOXで音声合成
 */
async function speakWithVoicevox(text, characterId) {
    const voiceSettings = getVoiceSettings(characterId);
    const speaker = voiceSettings.voicevoxSpeaker;
    const speed = voiceSettings.voicevoxSpeed;

    try {
        console.log(`[VOICEVOX] Synthesizing with speaker ${speaker}, speed ${speed}`);

        // Step 1: 音声合成用のクエリを作成
        const queryResponse = await fetch(
            `${VOICEVOX_URL}/audio_query?text=${encodeURIComponent(text)}&speaker=${speaker}`,
            { method: 'POST' }
        );

        if (!queryResponse.ok) {
            throw new Error(`Query failed: ${queryResponse.status}`);
        }

        const audioQuery = await queryResponse.json();

        // 速度を設定
        audioQuery.speedScale = speed;

        // Step 2: 音声データを生成
        const synthesisResponse = await fetch(
            `${VOICEVOX_URL}/synthesis?speaker=${speaker}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(audioQuery)
            }
        );

        if (!synthesisResponse.ok) {
            throw new Error(`Synthesis failed: ${synthesisResponse.status}`);
        }

        // Step 3: 音声データを再生
        const audioBlob = await synthesisResponse.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        // 既存の音声を停止
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        currentAudio = new Audio(audioUrl);

        currentAudio.onplay = () => {
            console.log('[VOICEVOX] Playback started');
            isSpeaking = true;
            updateSpeakerIcon(true);
            setMicButtonDisabled(true);
            // 音声再生中は音声認識を停止
            if (isRecording) {
                recognition.stop();
                isRecording = false;
                updateMicButton(false);
                console.log('[VOICEVOX] Recognition paused during speech');
            }
        };

        currentAudio.onended = () => {
            console.log('[VOICEVOX] Playback ended');
            isSpeaking = false;
            updateSpeakerIcon(false);
            setMicButtonDisabled(false);
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
            if (!isRecording) startRecording();
        };

        currentAudio.onerror = (error) => {
            console.error('[VOICEVOX] Playback error:', error);
            isSpeaking = false;
            updateSpeakerIcon(false);
            setMicButtonDisabled(false);
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
            if (!isRecording) startRecording();
        };

        await currentAudio.play();
        return true;

    } catch (error) {
        console.error('[VOICEVOX] Synthesis failed:', error);
        return false;
    }
}

/**
 * スピーカーアイコンの表示を更新
 */
function updateSpeakerIcon(speaking) {
    const speakerIcon = document.getElementById('speakerIcon');
    if (!speakerIcon) return;

    if (speaking) {
        speakerIcon.textContent = '🔊';
        speakerIcon.classList.add('speaking');
    } else {
        speakerIcon.textContent = '🔇';
        speakerIcon.classList.remove('speaking');
    }
}

/**
 * 音声合成を停止
 */
function stopSpeaking() {
    // VOICEVOX音声を停止
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    // Web Speech API音声を停止
    if (synth) {
        synth.cancel();
    }

    isSpeaking = false;
    updateSpeakerIcon(false);
    setMicButtonDisabled(false);
}

/**
 * マイクボタンのdisabled状態を設定（TTS再生中の誤録音防止）
 */
function setMicButtonDisabled(disabled) {
    const micButton = document.getElementById('micButton');
    if (!micButton) return;
    micButton.disabled = disabled;
    if (disabled) {
        micButton.style.opacity = '0.4';
        micButton.title = '音声再生中...';
    } else {
        micButton.style.opacity = '';
        micButton.title = isRecording ? '録音中...（クリックで停止）' : '音声入力を開始';
    }
}

/**
 * 音声機能の初期化（ページ読み込み時）
 */
async function initVoiceFeatures() {
    // VOICEVOX接続チェック
    await checkVoicevoxConnection();

    // 音声認識の初期化
    initSpeechRecognition();

    // 音声合成の準備（音声リストを読み込む）
    if (synth) {
        // Chromeでは最初に getVoices() を呼ぶ必要がある
        synth.getVoices();

        // 音声リストが非同期で読み込まれる場合に対応
        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = () => {
                console.log('[Voice] Available voices loaded:', synth.getVoices().length);
            };
        }
    }

    // スペースキーでマイクオンオフ
    setupSpacebarControl();

    if (voicevoxAvailable) {
        console.log('[Voice] Voice features initialized with VOICEVOX 🎵');
    } else {
        console.log('[Voice] Voice features initialized with Web Speech API');
    }
}

/**
 * スペースキーでマイクをオンオフする機能を設定
 */
function setupSpacebarControl() {
    document.addEventListener('keydown', (event) => {
        // スペースキーが押された場合
        if (event.code === 'Space' || event.key === ' ') {
            // 入力フィールドにフォーカスがある場合は何もしない
            const activeElement = document.activeElement;
            if (activeElement && (
                activeElement.tagName === 'INPUT' ||
                activeElement.tagName === 'TEXTAREA' ||
                activeElement.isContentEditable
            )) {
                return;
            }

            // デフォルトのスペース動作（スクロール）を防ぐ
            event.preventDefault();

            // TTS再生中はスペースキーでもマイク起動しない
            if (isSpeaking) {
                console.log('[Voice] Spacebar blocked: TTS is speaking');
                return;
            }

            // マイクをトグル
            console.log('[Voice] Spacebar pressed - toggling microphone');
            startRecording();
        }
    });
}

// ページ読み込み時に音声機能を初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoiceFeatures);
} else {
    initVoiceFeatures();
}
