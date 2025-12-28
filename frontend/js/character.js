/**
 * キャラクター表示と表情差分管理
 */

// キャラクター画像パスマッピング（VOICEVOX対応）
const CHARACTER_IMAGES = {
    'misaki': {
        'normal': 'images/characters/tsumugi_normal.png',
        'smile': 'images/characters/tsumugi_smile.png',
        'name': '春日部つむぎ'
    },
    'kenta': {
        'normal': 'images/characters/ryusei_normal.png',
        'smile': 'images/characters/ryusei_smile.png',
        'name': '青山龍星'
    },
    'aoi': {
        'normal': 'images/characters/zundamon_normal.png',
        'smile': 'images/characters/zundamon_smile.png',
        'name': 'ずんだもん'
    }
};

const CHARACTER_EMOJIS = {
    'misaki': '👩',
    'kenta': '👨',
    'aoi': '🧑'
};

const EXPRESSION_EMOJIS = {
    'normal': '😊',
    'smile': '😄',
    'surprised': '😲',
    'thinking': '🤔',
    'empathy': '🥺',
    'encourage': '💪'
};

/**
 * キャラクターのセットアップ
 */
function setupCharacter(characterId) {
    const characterData = getCharacterData(characterId);
    const characterImages = CHARACTER_IMAGES[characterId];

    // ヘッダーにキャラクター名を表示
    document.getElementById('characterName').textContent = characterData.name;

    // アバターエリアにキャラクター画像を表示
    const avatarEmoji = document.getElementById('avatarEmoji');

    if (characterImages) {
        // 絵文字を画像に置き換え
        avatarEmoji.innerHTML = `<img src="${characterImages.normal}" alt="${characterImages.name}" class="character-image" />`;
    } else {
        // フォールバック：絵文字
        avatarEmoji.textContent = CHARACTER_EMOJIS[characterId] || '👤';
    }

    const characterNameDisplay = document.getElementById('characterNameDisplay');
    characterNameDisplay.textContent = characterData.name;
}

/**
 * 表情を更新
 */
function updateCharacterExpression(expression) {
    const avatarEmoji = document.getElementById('avatarEmoji');
    const characterId = currentProfile?.character || 'aoi';
    const characterImages = CHARACTER_IMAGES[characterId];

    if (characterImages) {
        // 画像の場合：smile表情なら笑顔画像、それ以外は通常画像
        const imagePath = (expression === 'smile') ? characterImages.smile : characterImages.normal;
        avatarEmoji.innerHTML = `<img src="${imagePath}" alt="${characterImages.name}" class="character-image" />`;

        // smile表情の場合、3秒後に通常に戻す
        if (expression === 'smile') {
            setTimeout(() => {
                avatarEmoji.innerHTML = `<img src="${characterImages.normal}" alt="${characterImages.name}" class="character-image" />`;
            }, 3000);
        }
    } else {
        // フォールバック：絵文字
        const emojiMap = EXPRESSION_EMOJIS;

        if (emojiMap[expression]) {
            avatarEmoji.textContent = emojiMap[expression];

            // 3秒後に元に戻す
            setTimeout(() => {
                avatarEmoji.textContent = CHARACTER_EMOJIS[characterId] || '👤';
            }, 3000);
        }
    }
}

/**
 * キャラクターデータを取得（仮実装）
 */
function getCharacterData(characterId) {
    const characters = {
        'misaki': {
            name: 'つむぎちゃん',
            description: '明るく聞き上手な女性'
        },
        'kenta': {
            name: '青山くん',
            description: '落ち着いて知的な男性'
        },
        'aoi': {
            name: 'ずんだもん',
            description: '親しみやすく中性的'
        }
    };

    return characters[characterId] || characters['aoi'];
}
