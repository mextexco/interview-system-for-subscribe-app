"""
設定ファイル: LM Studio URL、キャラクター定義、カテゴリー定義
"""

import os

# LM Studio設定
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
LM_STUDIO_MODEL = "google/gemma-3-4b"

# データ保存先
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")

# キャラクター定義
CHARACTERS = {
    "misaki": {
        "name": "つむぎちゃん",
        "gender": "女性",
        "age": "20代後半",
        "description": "明るく聞き上手な女性",
        "tone": "フレンドリーで優しい",
        "for_user_gender": "女性",
        "expressions": ["normal", "smile", "surprised", "thinking", "empathy", "encourage"]
    },
    "kenta": {
        "name": "青山くん",
        "gender": "男性",
        "age": "30代前半",
        "description": "落ち着いて知的な男性",
        "tone": "穏やかで丁寧",
        "for_user_gender": "男性",
        "expressions": ["normal", "smile", "surprised", "thinking", "empathy", "encourage"]
    },
    "aoi": {
        "name": "ずんだもん",
        "gender": "中性的",
        "age": "20代",
        "description": "親しみやすく中性的なキャラクター",
        "tone": "カジュアルで親しみやすい",
        "for_user_gender": "その他",
        "expressions": ["normal", "smile", "surprised", "thinking", "empathy", "encourage"]
    }
}

# プロファイリングカテゴリー定義
CATEGORIES = {
    "基本プロフィール": {
        "fields": ["名前", "性別", "年齢層", "職業", "家族構成"],
        "description": "基本的な情報"
    },
    "ライフストーリー": {
        "fields": ["学歴", "職歴", "人生の転機", "重要な出来事"],
        "description": "これまでの人生の歩み"
    },
    "現在の生活": {
        "fields": ["1日の過ごし方", "住環境", "生活リズム"],
        "description": "今の日常生活"
    },
    "健康・ライフスタイル": {
        "fields": ["運動習慣", "食事", "睡眠", "健康管理"],
        "description": "健康や生活習慣"
    },
    "趣味・興味・娯楽": {
        "fields": ["趣味", "好きなこと", "エンターテイメント", "休日の過ごし方"],
        "description": "好きなことや楽しみ"
    },
    "学習・成長": {
        "fields": ["学びたいこと", "スキル", "自己啓発", "勉強"],
        "description": "成長や学習への取り組み"
    },
    "人間関係・コミュニティ": {
        "fields": ["友人", "家族関係", "コミュニティ", "人付き合い"],
        "description": "人との繋がり"
    },
    "情報収集・メディア": {
        "fields": ["ニュース", "SNS", "情報源", "メディア利用"],
        "description": "情報との向き合い方"
    },
    "経済・消費": {
        "fields": ["買い物", "お金の使い方", "価値基準", "経済観"],
        "description": "お金や消費に関する考え"
    },
    "価値観・将来": {
        "fields": ["大切にしていること", "将来の夢", "目標", "人生観"],
        "description": "価値観や将来のビジョン"
    }
}

# 標準キーマッピング / Standard Key Mappings
# 類似キーを標準キーに正規化するためのマッピング
STANDARD_KEYS = {
    "基本プロフィール": {
        "名前": ["名前", "氏名", "フルネーム", "呼び名"],
        "年齢": ["年齢", "年代", "歳", "年齢層"],
        "性別": ["性別", "ジェンダー"],
        "職業": ["職業", "仕事", "業種", "職種", "勤務先"],
        "住所": ["住所", "居住地", "住まい", "居住場所"],
        "家族構成": ["家族構成", "家族", "世帯構成", "家族人数"],
        "住居状況": ["住居状況", "住居形態", "住宅"]
    },
    "ライフストーリー": {
        "学歴": ["学歴", "卒業校", "出身校", "最終学歴"],
        "職歴": ["職歴", "経歴", "キャリア", "仕事経験"],
        "人生の転機": ["人生の転機", "転機", "重要な出来事", "転換点"],
        "出身地": ["出身地", "地元", "故郷", "生まれた場所"],
        "習慣": ["習慣", "日課", "ルーティン", "行動パターン"],
        "活動": ["活動", "行動", "取り組み", "アクション"],  # 重複解消: 行動→活動
        "経験": ["経験", "体験", "過去の経験"],
        "目的": ["目的", "目標", "狙い"],
        "旅行先": ["旅行先", "旅行", "訪問地"],
        "子供の活動": ["子供の活動", "子供の習い事", "子供の趣味"],
        "子供の年齢層": ["子供の年齢層", "子供の年齢", "子供の学年"],
        "部活経験": ["部活経験", "部活", "クラブ活動"]
    },
    "現在の生活": {
        "住居": ["住居", "住まい", "家", "自宅", "部屋"],
        "生活リズム": ["生活リズム", "1日の過ごし方", "日常", "ライフスタイル"],
        "食事": ["食事", "食事時間", "食生活", "食事習慣"],
        "睡眠": ["睡眠", "睡眠時間", "就寝時間", "起床時間"],
        "通勤": ["通勤", "通勤場所", "勤務地", "通勤時間"],
        "外見": ["外見", "見た目", "身なり"]
    },
    "健康・ライフスタイル": {
        "運動習慣": ["運動習慣", "運動", "エクササイズ", "スポーツ"],
        "食事好み": ["食事好み", "好きな食べ物", "嫌いな食べ物", "食の好み"],
        "健康状態": ["健康状態", "健康", "体調", "身体状況"],
        "医療": ["医療", "医療機関", "通院", "治療"],
        "症状": ["症状", "体の不調", "痛み"],
        "精神状態": ["精神状態", "メンタル", "心の状態", "気持ち"]
    },
    "趣味・興味・娯楽": {
        "趣味": ["趣味", "好きなこと", "ハマっていること"],
        "音楽": ["音楽", "音楽ジャンル", "好きな音楽"],
        "食べ物": ["食べ物", "好きな食べ物", "グルメ"],
        "旅行": ["旅行", "旅行先", "観光"],
        "活動": ["活動", "娯楽活動", "レジャー"],
        "プラットフォーム": ["プラットフォーム", "SNS", "使用アプリ"],
        "興味": ["興味", "関心", "興味のあること"],
        "服装": ["服装", "ファッション", "着たい服"]
    },
    "学習・成長": {
        "学習内容": ["学習内容", "勉強", "学んでいること"],
        "分野": ["分野", "専門", "領域"],
        "活動": ["活動", "学習活動", "取り組み"],
        "目標": ["目標", "目指すもの", "ゴール"],
        "興味": ["興味", "関心分野", "興味のある分野"],
        "スキル": ["スキル", "能力", "技術"]
    },
    "人間関係・コミュニティ": {
        "友人": ["友人", "友達", "仲間"],
        "家族関係": ["家族関係", "家族との関係", "親子関係"],
        "所属": ["所属", "所属団体", "コミュニティ"],
        "活動": ["活動", "交流活動", "社会活動"],
        "部活": ["部活", "クラブ", "サークル"]
    },
    "情報収集・メディア": {
        "情報源": ["情報源", "ニュース源", "メディア"],
        "SNS": ["SNS", "ソーシャルメディア", "使用SNS"],
        "プラットフォーム": ["プラットフォーム", "使用プラットフォーム", "メディア利用"],
        "関心事": ["関心事", "興味のあるニュース", "関心のある話題"]
    },
    "経済・消費": {
        "年収": ["年収", "収入", "給料", "所得"],
        "財政状況": ["財政状況", "お金の状況", "経済状況"],
        "投資": ["投資", "投資スタイル", "資産運用"],
        "消費": ["消費", "買い物", "支出"]
    },
    "価値観・将来": {
        "価値観": ["価値観", "大切にしていること", "信条"],
        "夢": ["夢", "将来の夢", "やりたいこと"],
        "人生観": ["人生観", "人生ビジョン", "人生の目標"],
        "理想": ["理想", "理想の生活", "理想像"],
        "成長観": ["成長観", "成長への考え", "自己啓発"]
    }
}


def merge_courses(course_ids: list) -> dict:
    """複数コースIDをマージして1つのコース設定を返す"""
    if not course_ids:
        return INTERVIEW_COURSES['basic_info']
    if len(course_ids) == 1:
        return INTERVIEW_COURSES.get(course_ids[0], INTERVIEW_COURSES['basic_info'])

    # カテゴリーを順序を保ちながらマージ（重複除去）
    merged_cats = []
    seen = set()
    for cid in course_ids:
        course = INTERVIEW_COURSES.get(cid, {})
        for cat in course.get('target_categories', []):
            if cat not in seen:
                merged_cats.append(cat)
                seen.add(cat)

    # フォーカス文をマージ
    focuses = [INTERVIEW_COURSES[cid].get('extra_focus') for cid in course_ids
               if INTERVIEW_COURSES.get(cid, {}).get('extra_focus')]
    merged_focus = '／'.join(focuses) if focuses else None

    # 名前をマージ
    names = [INTERVIEW_COURSES[cid]['name'] for cid in course_ids if cid in INTERVIEW_COURSES]
    merged_name = ' + '.join(names)

    # 時間目安（最大値を使用）
    times = [INTERVIEW_COURSES[cid].get('estimated_time', '') for cid in course_ids if cid in INTERVIEW_COURSES]

    # completion_threshold: カテゴリー数 × 4 を目安に
    threshold = max(len(merged_cats) * 4, 8)

    # question_topics をマージ（基本プロフィールコースを除いたコースのトピックを結合）
    merged_topics = []
    merged_hints = []
    for cid in course_ids:
        if cid != 'basic_info':
            merged_topics.extend(INTERVIEW_COURSES.get(cid, {}).get('question_topics', []))
            hint = INTERVIEW_COURSES.get(cid, {}).get('extraction_hints')
            if hint:
                merged_hints.append(hint)

    return {
        'name': merged_name,
        'description': f'{len(course_ids)}コース合算',
        'icon': '🔀',
        'catchcopy': f'{merged_name}について聞かせてください',
        'estimated_time': times[-1] if times else '15〜30分',
        'target_categories': merged_cats,
        'completion_threshold': threshold,
        'enable_random_events': any(
            INTERVIEW_COURSES.get(cid, {}).get('enable_random_events', True)
            for cid in course_ids
        ),
        'extra_focus': merged_focus,
        'question_topics': merged_topics,
        'extraction_hints': '\n\n'.join(merged_hints) if merged_hints else None,
    }


def get_standard_key(category: str, raw_key: str) -> str:
    """
    Get standardized key name for a raw key
    生のキー名を標準キー名に変換

    Args:
        category: カテゴリー名
        raw_key: 変換前のキー名

    Returns:
        標準化されたキー名（マッピングがない場合は元のキー名）
    """
    if category not in STANDARD_KEYS:
        return raw_key

    for standard_key, variations in STANDARD_KEYS[category].items():
        if raw_key in variations:
            return standard_key

    # マッピングが見つからない場合は元のキーを返す
    return raw_key


# ヒアリングコース定義
INTERVIEW_COURSES = {
    "basic_info": {
        "name": "基本情報のみ",
        "description": "名前・年齢・職業などの基本情報のみ",
        "icon": "👤",
        "catchcopy": "まずはあなたのことを少しだけ教えてください",
        "estimated_time": "3〜5分",
        "target_categories": ["基本プロフィール"],
        "completion_threshold": 4,
        "enable_random_events": False,
        "extra_focus": None
    },
    "health_wellness": {
        "name": "健康・ウェルネス",
        "description": "健康・体・メンタルについてヒアリング",
        "icon": "🏥",
        "catchcopy": "あなたの体と心の声を、丁寧に聞かせてください",
        "estimated_time": "15〜20分",
        "target_categories": ["基本プロフィール", "健康・ライフスタイル", "現在の生活"],
        "completion_threshold": 8,
        "enable_random_events": True,
        "extra_focus": "慢性的な悩み・未病領域、かかりつけ医との関係、メンタルヘルスへの意識とセルフケア方法を重点的に聞くこと",
        "extraction_hints": (
            "これは【健康・ウェルネス】コースのヒアリングです。\n"
            "・体調・病気・痛みの話 → 「健康・ライフスタイル」\n"
            "・運動・スポーツの習慣 → 「健康・ライフスタイル」\n"
            "・食事・睡眠・ストレス → 「健康・ライフスタイル」\n"
            "・サプリ・薬・医療サービス → 「健康・ライフスタイル」\n"
            "・地名・場所が出ても「住所」に分類しない（通院先・ジムの場所など）"
        ),
        "question_topics": [
            "最近、体調で気になっていることや、慢性的な悩みはありますか？",
            "運動は何かしていますか？",
            "食事は外食派ですか？自炊派ですか？",
            "普段の睡眠時間はどのくらいですか？",
            "ストレスを感じるのはどんなときですか？",
            "健康のために意識してやっていることはありますか？",
        ]
    },
    "entertainment_deep": {
        "name": "エンタメ・趣味 深掘り",
        "description": "趣味・エンタメ・好きなものを深く掘り下げ",
        "icon": "🎬",
        "catchcopy": "あなたの\"好き\"を、もっと深く知りたい",
        "estimated_time": "15〜20分",
        "target_categories": ["基本プロフィール", "趣味・興味・娯楽", "情報収集・メディア"],
        "completion_threshold": 8,
        "enable_random_events": True,
        "extra_focus": "視聴スタイル（ながら消費 vs 没入型）、一人 vs 誰かと共有、好きなTV番組・動画・音楽・ゲーム・本の具体名を重点的に聞くこと",
        "extraction_hints": (
            "これは【エンタメ・趣味 深掘り】コースのヒアリングです。\n"
            "・動画・YouTube・映画・ドラマ → 「趣味・興味・娯楽」> 動画\n"
            "・音楽・アーティスト・ジャンル → 「趣味・興味・娯楽」> 音楽\n"
            "・ゲーム・タイトル・ジャンル → 「趣味・興味・娯楽」> ゲーム\n"
            "・本・漫画・読書 → 「趣味・興味・娯楽」> 読書\n"
            "・視聴スタイル・楽しみ方 → 「趣味・興味・娯楽」\n"
            "・SNS・ニュースサイト・情報収集 → 「情報収集・メディア」\n"
            "・地名が出ても「住所」に分類しない（ライブ会場・出身地の言及など）"
        ),
        "question_topics": [
            "今一番ハマっている趣味や好きなことは何ですか？",
            "よく見るYouTubeや動画配信のジャンルを教えてください。",
            "好きな音楽のジャンルを教えてください。",
            "ゲームはしますか？",
            "本や漫画は読みますか？",
            "コンテンツを楽しむとき、ながら見が多いですか？それとも集中して見る派ですか？",
        ]
    },
    "travel_explorer": {
        "name": "旅行・おでかけ",
        "description": "旅行・外出・移動スタイルをヒアリング",
        "icon": "✈️",
        "catchcopy": "あなたが次に行きたい場所は、もう決まっていますか？",
        "estimated_time": "12〜18分",
        "target_categories": ["基本プロフィール", "趣味・興味・娯楽", "経済・消費"],
        "completion_threshold": 8,
        "enable_random_events": True,
        "extra_focus": "行きたい場所リスト・旅行スタイル（計画型 vs 行き当たり）、普段の外出先・移動手段の好み・旅行の障壁（時間/お金/同行者）を重点的に聞くこと",
        "extraction_hints": (
            "これは【旅行・おでかけ】コースのヒアリングです。\n"
            "・訪問した国・都市・観光地 → 「趣味・興味・娯楽」> 旅行 > 訪問地（「住所」「現在の生活」には絶対分類しない）\n"
            "・行きたい場所・バケットリスト → 「趣味・興味・娯楽」> 旅行 > 行きたい場所\n"
            "・旅行スタイル（計画型・行き当たり）→ 「趣味・興味・娯楽」> 旅行 > スタイル\n"
            "・旅行の障壁（お金・時間・同行者）→ 「経済・消費」> 旅行費用 または「趣味・興味・娯楽」> 旅行 > 障壁\n"
            "・近場のお気に入りスポット → 「趣味・興味・娯楽」> おでかけ\n"
            "・移動手段（電車・車・自転車）→ 「趣味・興味・娯楽」> 移動スタイル\n"
            "⚠️ 地名は必ず「旅行先」として扱い、居住地・現住所として扱わないこと"
        ),
        "question_topics": [
            "最近、旅行はしましたか？",
            "次に行ってみたい場所はありますか？",
            "旅行するとき、計画を立てる派ですか？それとも行き当たりばったり派ですか？",
            "旅行に行くときに、一番障壁になるのは何ですか？",
            "休日によく行く近場のお気に入りスポットはありますか？",
            "普段よく使う移動手段は何ですか？",
        ]
    },
    "subscription_audit": {
        "name": "サブスク棚卸し",
        "description": "現在契約中のサービスや満足度をヒアリング",
        "icon": "📱",
        "catchcopy": "毎月何に払ってる？サブスクを棚卸ししよう",
        "estimated_time": "15〜20分",
        "target_categories": ["経済・消費", "価値観・将来"],
        "completion_threshold": 8,
        "enable_random_events": False,
        "extra_focus": "契約中のサービス名・満足度・継続理由、解約経験とその理由、乗り換え検討中のサービス、「なんとなく払い続けている」サービスの有無を重点的に聞くこと",
        "extraction_hints": (
            "これは【サブスク棚卸し】コースのヒアリングです。\n"
            "・Netflix・Spotify・Amazon等のサービス名 → 「経済・消費」> サブスクリプション\n"
            "・解約したサービス → 「経済・消費」> サブスクリプション > 解約済み\n"
            "・使っていないのに払っているもの → 「経済・消費」> サブスクリプション > 未活用\n"
            "・月額の総支出・金額感 → 「経済・消費」> 支出管理\n"
            "・乗り換え検討中のサービス → 「価値観・将来」> サービス志向\n"
            "・サービスへの満足度・不満 → 「経済・消費」> サブスクリプション"
        ),
        "question_topics": [
            "今お金を払っているサブスクやアプリを教えてください。",
            "その中で一番よく使っているサービスはどれですか？",
            "逆に、ほとんど使っていないのに払い続けているサービスはありますか？",
            "最近解約したサービスはありますか？",
            "今後試してみたい、または乗り換えたいサービスはありますか？",
            "毎月サブスクにどのくらい払っているか、だいたい把握していますか？",
        ]
    },
    "daily_pain": {
        "name": "日常のモヤモヤ発見",
        "description": "日常の不満・困りごとを掘り起こす",
        "icon": "😮‍💨",
        "catchcopy": "言葉にできなかった\"ちょっとした困った\"を一緒に見つけよう",
        "estimated_time": "15〜20分",
        "target_categories": ["現在の生活", "健康・ライフスタイル", "経済・消費"],
        "completion_threshold": 8,
        "enable_random_events": False,
        "extra_focus": "毎日やってるけど本当はやりたくないこと、お金を払っているのに使いきれていないサービス、試したけどやめてしまったことと理由を重点的に聞くこと",
        "extraction_hints": (
            "これは【日常のモヤモヤ発見】コースのヒアリングです。\n"
            "・やりたくない・面倒な日課 → 「現在の生活」> 日常の不満\n"
            "・使いきれていないサービス・物 → 「経済・消費」> 未活用サービス\n"
            "・やめてしまったアプリ・サービス・習慣 → 「経済・消費」> 解約・離脱\n"
            "・不便に感じること → 「現在の生活」> 生活の不便\n"
            "・時間の無駄と感じること → 「現在の生活」> 時間管理\n"
            "・買ったが使っていないもの → 「経済・消費」> 未活用購入品\n"
            "・趣味・好きなことの話が出ても「趣味・興味・娯楽」ではなく「現在の生活」に分類する"
        ),
        "question_topics": [
            "毎日やっているけど、本当はやりたくない・面倒だと感じることはありますか？",
            "お金を払っているのに、使いきれていないサービスや物はありますか？",
            "試してみたけどやめてしまったアプリやサービスはありますか？",
            "普段の生活で「もっとこうだったらいいのに」と感じることはありますか？",
            "毎日していて「これ時間の無駄かも」と感じることはありますか？",
            "買ったはいいが、ほとんど使っていないものはありますか？",
        ]
    },
    "spending_behavior": {
        "name": "消費行動診断",
        "description": "購買行動・消費スタイルを診断",
        "icon": "💳",
        "catchcopy": "何を買うかより、なぜ買うかを知りたい",
        "estimated_time": "15〜20分",
        "target_categories": ["経済・消費", "趣味・興味・娯楽", "価値観・将来"],
        "completion_threshold": 8,
        "enable_random_events": True,
        "extra_focus": "衝動買い派 vs 計画購買派、購買意思決定の影響源、「体験にお金を使う」vs「モノにお金を使う」傾向を重点的に聞くこと",
        "extraction_hints": (
            "これは【消費行動診断】コースのヒアリングです。\n"
            "・購買スタイル（衝動・計画）→ 「経済・消費」> 購買スタイル\n"
            "・購買の参考にするもの（SNS・口コミ等）→ 「経済・消費」> 購買意思決定\n"
            "・体験 vs モノへの支出傾向 → 「価値観・将来」> お金の使い方\n"
            "・満足した買い物・失敗した買い物 → 「経済・消費」> 購買体験\n"
            "・節約意識・ブランド重視 → 「価値観・将来」> 消費価値観\n"
            "・よく使うショップ・サイト → 「経済・消費」> 購買チャネル\n"
            "・趣味の話が出ても文脈が「お金の使い方」なら「経済・消費」に分類"
        ),
        "question_topics": [
            "買い物するとき、衝動買い派ですか？それとも計画を立てて買う派ですか？",
            "何かを買う時に参考にするものは何ですか？",
            "体験にお金を使うのと、モノを買うのではどちらが好きですか？",
            "最近で一番満足した買い物は何ですか？",
            "節約を意識していますか？それとも価格より質を重視しますか？",
            "よく使うショッピングサイトやお気に入りのお店はありますか？",
        ]
    },
    "career_growth": {
        "name": "キャリア・仕事",
        "description": "キャリア・スキルアップ・将来への意識をヒアリング",
        "icon": "💼",
        "catchcopy": "今の仕事、5年後の自分、どちらも話してみませんか？",
        "estimated_time": "15〜20分",
        "target_categories": ["学習・成長", "価値観・将来", "経済・消費"],
        "completion_threshold": 8,
        "enable_random_events": True,
        "extra_focus": "スキルアップの動機、副業・独立への関心度、AI・テクノロジー変化への不安 vs 期待感を重点的に聞くこと",
        "extraction_hints": (
            "これは【キャリア・仕事】コースのヒアリングです。\n"
            "・習得したいスキル・勉強中のこと → 「学習・成長」> スキルアップ\n"
            "・副業・独立・転職への関心 → 「価値観・将来」> キャリア志向\n"
            "・AIやテクノロジーへの意識 → 「価値観・将来」> テクノロジー観\n"
            "・将来のビジョン・なりたい自分 → 「価値観・将来」> 将来像\n"
            "・仕事の悩み・課題 → 「学習・成長」> 課題\n"
            "・収入・給料の話 → 「経済・消費」> 収入\n"
            "・職業名が出ても「基本プロフィール」ではなく文脈で判断（すでに登録済みの場合は省略）"
        ),
        "question_topics": [
            "今の仕事や職場に満足していますか？",
            "今身につけたいスキルや、最近勉強していることはありますか？",
            "副業・独立・転職に興味はありますか？",
            "AIなどテクノロジーの変化に対して、不安を感じていますか？それとも期待していますか？",
            "5年後、どんな自分でいたいですか？",
            "キャリアで今一番悩んでいることはありますか？",
        ]
    },
    "daily_rhythm": {
        "name": "一日のリズム",
        "description": "生活リズム・時間の使い方をヒアリング",
        "icon": "⏰",
        "catchcopy": "あなたの24時間が、サービスを変える",
        "estimated_time": "10〜15分",
        "target_categories": ["現在の生活", "健康・ライフスタイル", "情報収集・メディア"],
        "completion_threshold": 6,
        "enable_random_events": True,
        "extra_focus": "スマホを触る「ゴールデンタイム」、平日 vs 休日の差、意思決定が多い時間帯 vs ぼーっとしたい時間帯を重点的に聞くこと",
        "extraction_hints": (
            "これは【一日のリズム】コースのヒアリングです。\n"
            "・起床・就寝時刻 → 「健康・ライフスタイル」> 睡眠リズム\n"
            "・朝のルーティン → 「現在の生活」> 朝の習慣\n"
            "・スマホを触る時間帯 → 「情報収集・メディア」> スマホ利用時間\n"
            "・集中できる時間帯・ぼーっとする時間帯 → 「現在の生活」> 時間帯別行動\n"
            "・平日と休日の違い → 「現在の生活」> 生活リズム\n"
            "・就寝前の行動 → 「現在の生活」> 就寝前習慣\n"
            "・時刻・時間帯の回答を「趣味・興味・娯楽」や「経済・消費」に分類しないこと"
        ),
        "question_topics": [
            "普段、何時ごろに起きていますか？",
            "朝起きてからまず何をしますか？",
            "スマホを一番よく触る時間帯はいつですか？",
            "一日で一番集中できる時間帯はいつですか？",
            "平日と休日で生活リズムは大きく変わりますか？",
            "寝る前によくすることは何ですか？",
        ]
    },
    "learning_curiosity": {
        "name": "学習・知的好奇心",
        "description": "学び方・知的興味・成長意欲をヒアリング",
        "icon": "📚",
        "catchcopy": "あなたが\"面白い！\"と感じる瞬間を教えてください",
        "estimated_time": "10〜15分",
        "target_categories": ["学習・成長", "趣味・興味・娯楽", "情報収集・メディア"],
        "completion_threshold": 6,
        "enable_random_events": True,
        "extra_focus": "学び方のスタイル（動画/本/体験/対話）、スキマ時間 vs まとまった時間、挫折しやすい学習ジャンルとその原因を重点的に聞くこと",
        "extraction_hints": (
            "これは【学習・知的好奇心】コースのヒアリングです。\n"
            "・学び方のスタイル（動画・本・体験）→ 「学習・成長」> 学習スタイル\n"
            "・勉強中のこと・興味を持った分野 → 「学習・成長」> 学習内容\n"
            "・学ぶ時間の使い方（スキマ・まとまり）→ 「学習・成長」> 学習時間\n"
            "・やめてしまった勉強・習い事 → 「学習・成長」> 挫折経験\n"
            "・面白いと感じるテーマ → 「学習・成長」> 知的関心 または「趣味・興味・娯楽」\n"
            "・身につけたいスキル → 「学習・成長」> 目標スキル\n"
            "・ニュース・情報収集の方法が出たら → 「情報収集・メディア」"
        ),
        "question_topics": [
            "何かを学ぶとき、動画・本・人から聞くなど、どの方法が一番好きですか？",
            "最近、新しく興味を持ったことや勉強していることはありますか？",
            "スキマ時間にちょっとずつ学ぶ派ですか？まとまった時間で集中して学ぶ派ですか？",
            "途中でやめてしまった勉強や習い事はありますか？",
            "「これ面白い！」と感じるのはどんなテーマですか？",
            "今後身につけたいスキルや、いつか学んでみたいことはありますか？",
        ]
    }
}


# バッジ定義
BADGES = {
    "オープンハート": {
        "description": "感情的な話を3回以上共有した",
        "condition": "emotional_count >= 3",
        "icon": "💖"
    },
    "ストーリーテラー": {
        "description": "人生の転機について語った",
        "condition": "has_life_event",
        "icon": "📖"
    },
    "多趣味": {
        "description": "5つ以上の趣味を持っている",
        "condition": "hobby_count >= 5",
        "icon": "🎨"
    },
    "哲学者": {
        "description": "価値観について深く語った",
        "condition": "philosophy_depth >= 3",
        "icon": "🤔"
    },
    "継続は力なり": {
        "description": "3日連続でセッションを行った",
        "condition": "consecutive_days >= 3",
        "icon": "🔥"
    },
    "夜更かし": {
        "description": "深夜0時以降に会話した",
        "condition": "late_night_session",
        "icon": "🌙"
    },
    "長い付き合い": {
        "description": "10回以上のセッションを完了",
        "condition": "session_count >= 10",
        "icon": "🏆"
    },
    "サプライズ": {
        "description": "予想外の一面を見せた",
        "condition": "has_surprise",
        "icon": "✨"
    },
    "思索者": {
        "description": "深い思考を共有した",
        "condition": "deep_thought_count >= 3",
        "icon": "💭"
    },
    "記憶の守護者": {
        "description": "幼少期の記憶を共有した",
        "condition": "has_childhood_memory",
        "icon": "🎈"
    }
}

# ランダムイベント定義
RANDOM_EVENTS = {
    "クイックトーク": {
        "prompt": "好きな食べ物ベスト3を教えて！",
        "category": "趣味・興味・娯楽",
        "trigger_rate": 0.15
    },
    "もしもトーク": {
        "prompt": "もし宝くじで1億円当たったら何する？",
        "category": "価値観・将来",
        "trigger_rate": 0.10
    },
    "思い出タイム": {
        "prompt": "子供の頃の一番楽しかった思い出は？",
        "category": "ライフストーリー",
        "trigger_rate": 0.15
    }
}

# リアクション設定
REACTION_TIERS = {
    "small": {
        "threshold": 20,  # 文字数
        "sound": "pop.mp3",
        "effect": "expression_change"
    },
    "medium": {
        "threshold": 50,
        "sound": "chime.mp3",
        "effect": "particles"
    },
    "large": {
        "threshold": 100,
        "sound": "success.mp3",
        "effect": "flash"
    }
}
