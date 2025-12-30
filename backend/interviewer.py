"""
インタビューロジック: LM Studioとの対話、プロンプト生成
"""

import requests
import json
import re
from typing import Dict, List, Optional
from config import (
    LM_STUDIO_URL, LM_STUDIO_MODEL, CHARACTERS, CATEGORIES
)
from key_normalizer import KeyNormalizer


class Interviewer:
    """インタビューを管理するクラス"""

    def __init__(self):
        self.lm_studio_url = LM_STUDIO_URL

    def check_lm_studio_connection(self) -> bool:
        """LM Studioへの接続確認"""
        try:
            # 簡単なテストリクエスト
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": LM_STUDIO_MODEL,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                },
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"LM Studio connection error: {e}")
            return False

    def _detect_current_category(self, session_data: Dict) -> Optional[str]:
        """直近の会話から現在掘り下げ中のカテゴリーを検出"""
        if not session_data or 'conversation' not in session_data:
            return None

        conversation = session_data['conversation']
        if len(conversation) < 2:
            return None

        # 最後のAI質問を取得
        last_assistant_msg = None
        for msg in reversed(conversation):
            if msg.get('role') == 'assistant':
                last_assistant_msg = msg.get('content', '')
                break

        if not last_assistant_msg:
            return None

        # カテゴリーごとのキーワードマッピング
        category_keywords = {
            '基本プロフィール': ['名前', '年齢', '性別', '誕生日', '出身'],
            '現在の生活': ['仕事', '職業', '勤務', '会社', '職場', '働', '学校', '学生', '住ん', '一人暮らし', '実家'],
            '趣味・興味・娯楽': ['趣味', '好き', '楽しみ', '遊び', 'ゲーム', '映画', '音楽', 'スポーツ', '読書'],
            '健康・ライフスタイル': ['健康', '運動', '睡眠', '起きる', '寝る', '食事', '朝食', '昼食', '夕食'],
            '学習・成長': ['勉強', '学', 'スキル', '資格', '本', '学び'],
            '人間関係・コミュニティ': ['友達', '家族', '恋人', '結婚', 'パートナー', '人付き合い', 'コミュニティ'],
            '情報収集・メディア': ['ニュース', 'SNS', 'YouTube', 'テレビ', 'ネット', '情報'],
            '経済・消費': ['買い物', 'お金', '給料', '収入', '貯金', '投資', '買', '欲しい'],
            '価値観・将来': ['夢', '目標', '将来', '大事', '価値観', 'こだわり', '信念'],
            'ライフストーリー': ['昔', '子供の頃', '学生時代', '過去', '思い出', '経験']
        }

        # キーワードマッチングでカテゴリーを判定
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in last_assistant_msg:
                    print(f"[Category Detection] Current topic: {category} (keyword: {keyword})")
                    return category

        return None

    def generate_system_prompt(self, character_id: str, profile: Dict,
                               category_counts: Dict[str, int],
                               empty_categories: List[str],
                               greeting_already_sent: bool = False,
                               session_data: Dict = None) -> str:
        """システムプロンプトを生成"""
        character = CHARACTERS.get(character_id, CHARACTERS["aoi"])

        # 現在掘り下げ中のカテゴリーを検出
        current_category = self._detect_current_category(session_data)

        # カテゴリー情報を整形
        categories_info = "\n".join([
            f"- {cat}: {CATEGORIES[cat]['description']}"
            for cat in CATEGORIES.keys()
        ])

        # 収集済みデータの概要
        collected_summary = ", ".join([
            f"{cat}({count}件)"
            for cat, count in category_counts.items() if count > 0
        ])

        # データがまだない場合
        has_data = bool(collected_summary)
        if not collected_summary:
            collected_summary = "まだありません"

        # 空白カテゴリー（データが既にある場合のみ表示）
        if has_data:
            empty_cats = ", ".join(empty_categories) if empty_categories else "全カテゴリー収集済み"
        else:
            empty_cats = None  # 初期状態では表示しない

        # 名前が既に取得されているかチェック（セッションデータから）
        user_name = None
        if session_data and 'extracted_data' in session_data:
            basic_profile = session_data['extracted_data'].get('基本プロフィール', [])
            for item in basic_profile:
                if item.get('key') == '名前' and item.get('value'):
                    user_name = item['value']
                    print(f"[DEBUG] Found user name in session data: {user_name}")
                    break

        # 名前がまだない場合、直前の会話から推測
        if not user_name and session_data and 'conversation' in session_data:
            conversation = session_data['conversation']
            if len(conversation) >= 2:
                # 最後から2番目がAI（名前を聞いた）、最後がユーザー（名前を答えた）
                last_assistant = conversation[-2] if conversation[-2].get('role') == 'assistant' else None
                last_user = conversation[-1] if conversation[-1].get('role') == 'user' else None

                if last_assistant and last_user:
                    # AIが「名前」について聞いているか
                    if '名前' in last_assistant.get('content', ''):
                        # ユーザーの返答が短い（名前の可能性）
                        user_response = last_user.get('content', '').strip()
                        if len(user_response) <= 20 and user_response:
                            user_name = user_response
                            print(f"[DEBUG] Inferred user name from conversation: {user_name}")


        # 会話履歴から同じトピックの連続質問数をカウント
        consecutive_questions = self._count_consecutive_questions(session_data)

        # 会話戦略部分を条件分岐
        if user_name:
            # 名前が既に分かっている場合
            topic_change_strategy = ""
            if consecutive_questions >= 3:
                topic_change_strategy = f"""
【重要: 話題転換のタイミング】
同じトピックで{consecutive_questions}回連続して質問しています。
次のいずれかの対応をしてください：
1. 別の話題に自然に移行する（「そういえば〜」「ところで〜」）
2. ユーザーに選択肢を提示：「このまま掘り下げる？それとも別の話題にする？」
3. 一旦まとめて、新しいカテゴリーの質問をする

単調な質問の連続を避け、会話に変化を持たせましょう。"""

            conversation_strategy = f"""【重要】
相手の名前は「{user_name}」です。すでに名前を知っています。
絶対に名前を聞き直したり、確認したりしないでください。
{topic_change_strategy}
【会話戦略】
- 自然な会話でプロファイリングを続ける
- 🚫 名前や回答に対する不自然なコメント（「楽しそう」「面白い」など）は避ける
- ⚠️ 一時的な情報を聞かない：「今日の気分」「今日の予定」など一時的な状態は避け、継続的・習慣的な情報を聞く
  - ❌ 「今日の気分は？」「今日何した？」
  - ✅ 「普段どんな趣味がありますか？」「いつも何時に起きますか？」
- 空白カテゴリーがあれば軽く振る（「そういえば〜」）
- ユーザーが話したいことを優先
- 同じ話題で3-4回質問したら、話題を変えるか相手に聞く
- 相手の発言に共感しながら進める
- 1語回答の場合は具体例を示して掘り下げる
  例: 「IT」→「ITのどんなお仕事ですか？開発、インフラ、営業など」
- 曖昧な回答には選択肢を提示
  例: 「普通」→「朝型ですか？夜型ですか?」
- 会話にメリハリをつけ、単調にならないよう工夫する"""
        elif greeting_already_sent:
            # 挨拶だけ送った直後（名前はまだ分かっていない）
            conversation_strategy = """【会話戦略】
- あなたはすでに自己紹介をして、相手に名前を尋ねました
- 相手は今その返答をしています
- 🚫 名前への不自然なコメント禁止：「楽しそう」「面白い」「珍しい」などのコメントは不要
- ✅ 名前への応答例：「〜さんですね！」「よろしく、〜さん！」のようにシンプルに
- その後、自然に次の話題へ（趣味、好きなこと、仕事など）
- ⚠️ 一時的な情報を聞かない：継続的・習慣的な情報を聞く（「今日の〜」ではなく「普段の〜」「いつも〜」）
- 自然な会話でプロファイリングを続ける
- 空白カテゴリーがあれば軽く振る（「そういえば〜」）
- ユーザーが話したいことを優先
- 無理に質問を続けない（3回短い回答なら話題を変える）
- 相手の発言に共感しながら進める
- 1語回答の場合は具体例を示して掘り下げる
  例: 「IT」→「ITのどんなお仕事ですか？開発、インフラ、営業など」
- 曖昧な回答には選択肢を提示
  例: 「普通」→「朝型ですか？夜型ですか?」"""
        else:
            conversation_strategy = """【会話戦略】
- まず相手の名前を聞く（初回のみ）
- その後、自然な会話でプロファイリング
- ⚠️ 一時的な情報を聞かない：継続的・習慣的な情報を聞く（「今日の〜」ではなく「普段の〜」「いつも〜」）
- 空白カテゴリーがあれば軽く振る（「そういえば〜」）
- ユーザーが話したいことを優先
- 無理に質問を続けない（3回短い回答なら話題を変える）
- 相手の発言に共感しながら進める
- 1語回答の場合は具体例を示して掘り下げる
  例: 「IT」→「ITのどんなお仕事ですか？開発、インフラ、営業など」
- 曖昧な回答には選択肢を提示
  例: 「普通」→「朝型ですか？夜型ですか?」"""

        # 空白カテゴリーの行（データがある場合のみ）
        empty_cats_line = f"\n- 空白カテゴリー: {empty_cats}" if empty_cats else ""

        # 抽出済みデータの詳細を整形（データがある場合のみ）
        extracted_details = ""
        if session_data and 'extracted_data' in session_data and has_data:
            details_lines = []
            for category, items in session_data['extracted_data'].items():
                if items:  # 空でないカテゴリーのみ
                    details_lines.append(f"\n{category}:")
                    for item in items:
                        key = item.get('key', '不明')
                        value = item.get('value', '不明')
                        details_lines.append(f"  - {key}: {value}")

            if details_lines:
                extracted_details = f"""

【収集済み情報の詳細】
以下の情報は既に収集済みです。同じことを再度聞かないでください。
既知の情報に基づいて、自然に掘り下げたり、関連する質問をしてください。
{''.join(details_lines)}"""
                print(f"[DEBUG] Extracted data added to system prompt: {len(details_lines)} items")

        system_prompt = f"""あなたは{character['name']}、{character['description']}です。

【あなたの役割】
⚠️ あなたは質問する側です。相手の代わりに回答を生成することは絶対禁止です。
- あなた：質問をする（例：「お仕事は何ですか？」）
- 相手：回答する（例：「エンジニアです」）
- 🚫 絶対禁止：相手の代わりに回答を捏造すること

【会話スタイル】
- 1発言は15-25文字程度
- 質問は1つずつ、簡潔に
- 口語的でフレンドリーに（{character['tone']}）
- 長い説明や前置きは不要
- テンポ良く進める
- 自然な会話を心がける

【重要な注意事項】
- 地理・地名・距離などの事実を正確に扱う
- 不確かな知識で推測や想像の発言をしない
- 知らないことは素直に認める
- 相手の発言に基づいて会話する（勝手な前提を作らない）
- 🚫 相手の代わりに回答を生成しない（質問だけする）

{conversation_strategy}

【プロファイリングカテゴリー】
{categories_info}

【現在の状況】
- 収集済み情報: {collected_summary}{empty_cats_line}
- セッション回数: {len(profile.get('sessions', []))}{extracted_details}

{f'''【重要: 現在の会話コンテキスト】
現在は「{current_category}」について掘り下げています。
ユーザーの回答は、基本的に「{current_category}」カテゴリーの情報として扱われます。
別のカテゴリーの情報だと明らかな場合のみ、別カテゴリーに分類してください。''' if current_category else ''}

日本語で対話してください。短く、フレンドリーに！"""

        return system_prompt

    def get_response(self, messages: List[Dict], character_id: str,
                    profile: Dict, category_counts: Dict[str, int],
                    empty_categories: List[str],
                    max_tokens: int = 100,
                    greeting_already_sent: bool = False,
                    session_data: Dict = None) -> Optional[str]:
        """
        LM Studioからレスポンスを取得
        Args:
            messages: 会話履歴 [{"role": "user/assistant", "content": "..."}]
            character_id: キャラクターID
            profile: ユーザープロファイル
            category_counts: カテゴリー別データ数
            empty_categories: 空のカテゴリーリスト
            max_tokens: 最大トークン数
            greeting_already_sent: 初回挨拶が既に送信されたか
            session_data: セッションデータ（extracted_data含む）
        Returns:
            AIの応答テキスト
        """
        try:
            # システムプロンプトを生成
            system_prompt = self.generate_system_prompt(
                character_id, profile, category_counts, empty_categories, greeting_already_sent, session_data
            )

            # メッセージリストを構築
            full_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages

            # LM Studioにリクエスト
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": LM_STUDIO_MODEL,
                    "messages": full_messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.6,  # 事実性向上のため0.8→0.6に変更
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                assistant_message = result["choices"][0]["message"]["content"]

                # デバッグ: 元のメッセージを出力
                print(f"[DEBUG] LM Studio raw response: {assistant_message[:200]}")

                # 内部コメントを除去
                cleaned_message = self._clean_response(assistant_message)

                # デバッグ: クリーン後のメッセージを出力
                print(f"[DEBUG] Cleaned response: {cleaned_message[:200]}")
                print(f"[DEBUG] Response length - raw: {len(assistant_message)}, cleaned: {len(cleaned_message)}")

                # 空の応答をチェック
                final_message = cleaned_message.strip()
                if not final_message:
                    print(f"[WARNING] Cleaned message is empty! Raw response was: {assistant_message[:500]}")
                    return None

                return final_message
            else:
                print(f"[ERROR] LM Studio error: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"[ERROR] LM Studio error detail: {error_detail}")
                except:
                    print(f"[ERROR] LM Studio error body: {response.text[:500]}")

                # システムプロンプトの長さをチェック
                print(f"[DEBUG] System prompt length: {len(system_prompt)} characters")
                print(f"[DEBUG] Total messages: {len(full_messages)}")
                print(f"[DEBUG] System prompt preview: {system_prompt[:300]}...")

                return None

        except Exception as e:
            print(f"Error getting response: {e}")
            return None

    def _count_consecutive_questions(self, session_data: Dict) -> int:
        """
        会話履歴から同じトピックの連続質問数をカウント
        直近の抽出データを分析して、同じカテゴリーが連続している回数を数える
        """
        if not session_data or 'extracted_data' not in session_data:
            return 0

        extracted_data = session_data['extracted_data']
        if not extracted_data:
            return 0

        # 全カテゴリーのデータをタイムスタンプ順にソート（最新データは配列の最後）
        all_items = []
        for category, items in extracted_data.items():
            for item in items:
                all_items.append({
                    'category': category,
                    'item': item
                })

        if len(all_items) < 2:
            return 0

        # 最新のカテゴリーを取得
        latest_category = all_items[-1]['category']

        # 後ろから数えて同じカテゴリーが何回連続しているか
        consecutive_count = 0
        for i in range(len(all_items) - 1, -1, -1):
            if all_items[i]['category'] == latest_category:
                consecutive_count += 1
            else:
                break

        print(f"[ConversationFlow] Latest category: {latest_category}, Consecutive: {consecutive_count}")
        return consecutive_count

    def _clean_response(self, text: str) -> str:
        """AI応答から内部コメントや不要な記号を除去"""
        import re

        # 各種内部コメントパターンを削除
        patterns = [
            r'\[思考:.*?\]',           # [思考: ...]
            r'\[内部:.*?\]',           # [内部: ...]
            r'\(思考:.*?\)',           # (思考: ...)
            r'\(内部:.*?\)',           # (内部: ...)
            r'<!--.*?-->',              # <!-- ... -->
            r'\{思考:.*?\}',           # {思考: ...}
            r'\{内部:.*?\}',           # {内部: ...}
            r'<thinking>.*?</thinking>',  # <thinking>...</thinking>
            r'\[Note:.*?\]',           # [Note: ...]
            r'\(Note:.*?\)',           # (Note: ...)
        ]

        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 連続する空白を1つに
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()

    def generate_greeting(self, character_id: str, user_name: str = None) -> str:
        """挨拶メッセージを生成"""
        character = CHARACTERS.get(character_id, CHARACTERS["aoi"])

        if user_name:
            return f"こんにちは{user_name}さん！今日もお話しましょう！"
        else:
            # キャラクターごとの初対面の挨拶
            greetings = {
                'misaki': "初めまして！つむぎです。今日はよろしくお願いします！",
                'kenta': "初めまして。青山です。",
                'aoi': "こんにちはずんだもんなのだ。よろしくなのだ！"
            }
            return greetings.get(character_id, "こんにちは！よろしくお願いします！")

    def generate_first_question(self, character_id: str) -> str:
        """最初の質問を生成"""
        return "お名前を教えてもらえますか？"

    def extract_user_name(self, message: str) -> Optional[str]:
        """ユーザーメッセージから名前を抽出（簡易版）"""
        # 簡易的な実装
        # 「〜です」「〜といいます」などのパターンから抽出
        patterns = ["です", "だよ", "といいます", "っていいます", "と申します"]

        for pattern in patterns:
            if pattern in message:
                # パターンの前の部分を取得
                parts = message.split(pattern)
                if parts[0]:
                    # 最後の単語を名前として取得
                    name_candidate = parts[0].strip().split()[-1]
                    # 短すぎる・長すぎる名前は除外
                    if 1 <= len(name_candidate) <= 10:
                        return name_candidate

        # パターンマッチしない場合、メッセージ全体が短ければそれを名前とする
        if len(message) <= 10 and not any(c in message for c in "。、！？"):
            return message.strip()

        return None

    def suggest_next_topic(self, empty_categories: List[str],
                          character_id: str) -> Optional[str]:
        """次の話題を提案"""
        if not empty_categories:
            return None

        # ランダムに1つ選ぶ
        import random
        category = random.choice(empty_categories)

        # カテゴリーに応じた質問例
        questions = {
            "基本プロフィール": "お仕事は何してます？",
            "ライフストーリー": "これまでどんな人生を？",
            "現在の生活": "普段どんな生活してる？",
            "健康・ライフスタイル": "運動とかしてる？",
            "趣味・興味・娯楽": "趣味は何ですか？",
            "学習・成長": "何か学んでることある？",
            "人間関係・コミュニティ": "友達とはよく会う？",
            "情報収集・メディア": "ニュースとか見る？",
            "経済・消費": "買い物好き？",
            "価値観・将来": "将来の夢とかある？"
        }

        return questions.get(category, "他に何か教えて！")

    def extract_profile_data(self, user_message: str, assistant_response: str,
                             conversation_history: List[Dict]) -> List[Dict]:
        """
        会話からプロファイリングデータを抽出
        Returns: [{"category": "基本プロフィール", "key": "職業", "value": "エンジニア"}, ...]
        """
        max_retries = 2

        for attempt in range(max_retries):
            try:
                # データ抽出用プロンプト
                extraction_prompt = self._create_extraction_prompt(
                    user_message, assistant_response, conversation_history
                )

                # 直前のアシスタント質問を取得
                # conversation_history[-1] = 今追加されたアシスタント応答
                # conversation_history[-2] = ユーザーメッセージ
                # conversation_history[-3] = 前のアシスタント質問
                previous_question = ""
                if len(conversation_history) >= 3:
                    prev_msg = conversation_history[-3]
                    if prev_msg.get('role') == 'assistant':
                        previous_question = prev_msg.get('content', '')

                # デバッグ: 会話履歴を確認
                print(f"[Extraction] Conversation history length: {len(conversation_history)}")
                if len(conversation_history) >= 3:
                    print(f"[Extraction] Last 3 messages:")
                    print(f"  [-3] {conversation_history[-3].get('role')}: {conversation_history[-3].get('content', '')[:80]}")
                    print(f"  [-2] {conversation_history[-2].get('role')}: {conversation_history[-2].get('content', '')[:80]}")
                    print(f"  [-1] {conversation_history[-1].get('role')}: {conversation_history[-1].get('content', '')[:80]}")

                # LLMに送るユーザーメッセージを構築（最小限）
                if previous_question:
                    print(f"[Extraction] Previous question detected: {previous_question[:100]}")
                    llm_user_message = f"""Q:{previous_question}
A:{user_message}"""
                else:
                    print(f"[Extraction] No previous question detected")
                    llm_user_message = user_message

                print(f"[Extraction] LLM user message: {llm_user_message[:200]}")

                # LM Studioにリクエスト
                response = requests.post(
                    self.lm_studio_url,
                    json={
                        "model": LM_STUDIO_MODEL,
                        "messages": [
                            {"role": "system", "content": extraction_prompt},
                            {"role": "user", "content": llm_user_message}
                        ],
                        "max_tokens": 200,  # 短くしてJSON配列のみを返すように
                        "temperature": 0.1,  # さらに低くして正確性を重視
                        "stream": False
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    extracted_text = result["choices"][0]["message"]["content"]

                    # デバッグ: 生のレスポンスを出力
                    print(f"[Extraction] LM Studio response: {extracted_text}")

                    # JSON形式でパース
                    extracted_data = self._parse_extracted_data(extracted_text)
                    print(f"[Extraction] Found {len(extracted_data)} data points")

                    # 複数項目を自動分割
                    extracted_data = self._split_multiple_items(extracted_data)
                    print(f"[Extraction] After splitting: {len(extracted_data)} data points")

                    # 質問文からの誤抽出をチェック
                    if previous_question:
                        extracted_data = self._filter_question_contamination(
                            extracted_data, user_message, previous_question
                        )
                        print(f"[Extraction] After filtering: {len(extracted_data)} data points")

                    # キー正規化を適用 / Apply key normalization
                    normalizer = KeyNormalizer()
                    normalized_data = normalizer.normalize_batch(extracted_data)

                    # 正規化統計をログ出力
                    stats = normalizer.get_normalization_stats()
                    if stats["total_normalizations"] > 0:
                        print(f"[Normalization] Normalized {stats['total_normalizations']} keys")
                        for category, data in stats['by_category'].items():
                            for raw, normalized in data['mappings'].items():
                                print(f"[Normalization]   {category}/{raw} → {normalized}")

                    # デバッグ: 抽出されたデータを出力
                    for data in normalized_data:
                        print(f"[Extraction] Data: {data}")

                    # データが抽出できた、または最後の試行の場合は結果を返す
                    if normalized_data:
                        return normalized_data

                    # 最後の試行の場合は空のリストを返す
                    if attempt == max_retries - 1:
                        print(f"[Extraction] All retries exhausted, returning empty list")
                        return []

                    # データが空で、まだリトライ可能な場合
                    print(f"[Extraction] No data extracted (possibly filtered out), retry {attempt + 1}/{max_retries}")
                    continue
                else:
                    print(f"[Extraction] LM Studio error: {response.status_code}")
                    if attempt < max_retries - 1:
                        print(f"[Extraction] Retrying... ({attempt + 1}/{max_retries})")
                        continue
                    return []

            except requests.exceptions.Timeout:
                print(f"[Extraction] Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    print(f"[Extraction] Retrying...")
                    continue
                return []
            except Exception as e:
                print(f"[Extraction] Error: {e}")
                if attempt < max_retries - 1:
                    print(f"[Extraction] Retrying... ({attempt + 1}/{max_retries})")
                    continue
                return []

        return []

    def _create_extraction_prompt(self, user_message: str, assistant_response: str,
                                  conversation_history: List[Dict]) -> str:
        """データ抽出用のプロンプトを生成"""
        categories_desc = "\n".join([
            f"- {cat}: {CATEGORIES[cat]['description']}"
            for cat in CATEGORIES.keys()
        ])

        # 現在掘り下げ中のカテゴリーを検出
        session_data_mock = {'conversation': conversation_history}
        current_category = self._detect_current_category(session_data_mock)

        # 会話コンテキストを追加（直近5メッセージ）
        recent_context = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        context_text = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}"
            for msg in recent_context
        ])

        # 直前のアシスタントメッセージ（質問）を抽出して分析
        # conversation_history[-1] = 今追加されたアシスタント応答
        # conversation_history[-2] = ユーザーメッセージ
        # conversation_history[-3] = 前のアシスタント質問
        previous_assistant_question = ""
        question_analysis = ""
        if len(conversation_history) >= 3:
            prev_msg = conversation_history[-3]
            if prev_msg.get('role') == 'assistant':
                previous_assistant_question = prev_msg.get('content', '')

                # 質問内容の分析（優先度順）
                question_lower = previous_assistant_question.lower()

                # 名前
                if '名前' in question_lower or 'なまえ' in question_lower or 'お名前' in question_lower:
                    question_analysis = "【重要】直前の質問は「名前」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「名前」として抽出してください。"

                # 年齢
                elif '年齢' in question_lower or 'とし' in question_lower or '何歳' in question_lower or 'いくつ' in question_lower or '歳' in question_lower:
                    question_analysis = "【重要】直前の質問は「年齢」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「年齢」として抽出してください。"

                # 職業・仕事
                elif '仕事' in question_lower or '職業' in question_lower or 'しごと' in question_lower or '働' in question_lower or 'お仕事' in question_lower:
                    question_analysis = "【重要】直前の質問は「職業」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「職業」として抽出してください。"

                # 住所・居住地
                elif '住' in question_lower or '住所' in question_lower or 'どこ' in question_lower or '居' in question_lower or 'どちら' in question_lower:
                    question_analysis = "【重要】直前の質問は「住所」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「住所」として抽出してください。"

                # 趣味
                elif '趣味' in question_lower or 'しゅみ' in question_lower:
                    question_analysis = "【重要】直前の質問は「趣味」について聞いています。ユーザーの回答は「趣味・興味・娯楽」カテゴリーの「趣味」として抽出してください。"

                # 好きなこと・もの
                elif '好き' in question_lower or 'すき' in question_lower:
                    question_analysis = "【重要】直前の質問は好みについて聞いています。「趣味・興味・娯楽」または「健康・ライフスタイル」カテゴリーで適切に抽出してください。"

                # 運動・健康
                elif '運動' in question_lower or 'スポーツ' in question_lower or '健康' in question_lower:
                    question_analysis = "【重要】直前の質問は「運動」や「健康」について聞いています。ユーザーの回答は「健康・ライフスタイル」カテゴリーとして抽出してください。"

                # 学習・勉強
                elif '学' in question_lower or '勉強' in question_lower or '学習' in question_lower:
                    question_analysis = "【重要】直前の質問は学習について聞いています。ユーザーの回答は「学習・成長」カテゴリーとして抽出してください。"

                # 家族
                elif '家族' in question_lower or 'かぞく' in question_lower:
                    question_analysis = "【重要】直前の質問は「家族」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「家族構成」または「人間関係・コミュニティ」カテゴリーとして抽出してください。"

                if question_analysis:
                    print(f"[Extraction] Question detected: {previous_assistant_question[:50]}")
                    print(f"[Extraction] Analysis: {question_analysis}")

        # 標準キー名のリスト
        standard_keys_desc = """
基本プロフィール: 名前, 年齢, 性別, 職業, 住所, 家族構成, 住居状況
ライフストーリー: 学歴, 職歴, 人生の転機, 出身地, 習慣, 活動, 経験
現在の生活: 住居, 生活リズム, 食事, 睡眠, 通勤
健康・ライフスタイル: 運動習慣, 食事好み, 健康状態, 医療
趣味・興味・娯楽: 趣味, 音楽, 食べ物, 旅行, 活動
学習・成長: 学習内容, 分野, 活動, 目標, スキル
人間関係・コミュニティ: 友人, 家族関係, 所属, 活動
情報収集・メディア: 情報源, SNS, プラットフォーム, 関心事
経済・消費: 年収, 財政状況, 投資, 消費
価値観・将来: 価値観, 夢, 人生観, 理想"""

        # 質問コンテキストセクション（簡潔版 - 例を一切含まない）
        question_context_section = ""
        if question_analysis:
            question_context_section = f"""
【質問コンテキスト】
{question_analysis}
質問: {previous_assistant_question}
"""

        # 現在のカテゴリーコンテキスト
        category_context_section = ""
        if current_category:
            category_context_section = f"""
【重要: 会話コンテキスト】
現在の会話は「{current_category}」について掘り下げています。
特に理由がない限り、ユーザーの回答は「{current_category}」カテゴリーの情報として扱ってください。
例: 仕事の話をしている流れで「AIプロダクトサービス」→「現在の生活」の「業務内容」として抽出（趣味ではない）
"""

        prompt = f"""⚠️⚠️⚠️ 重要 ⚠️⚠️⚠️
回答(A:)に書かれていない情報は絶対に抽出しないでください。
質問文(Q:)の例や選択肢を抽出することは厳禁です。

🚫 絶対禁止:
- 質問文の例・選択肢を抽出すること
- 回答に含まれない情報の捏造
- 曖昧・不十分な回答の無理な解釈

✅ 出力: JSON配列のみ

{question_context_section}{category_context_section}

【抽出対象】安定的・継続的な個人特徴のみ
✅ 抽出すべき情報:
- 趣味・習慣（「釣りに行った」→趣味として抽出）
- 継続的な活動・パターン
- 中長期的な特徴（「最近ずっと〜」）
- 基本情報（名前、年齢、職業、住所など）
- 具体的で明確な回答のみ

❌ 抽出してはいけない情報:
- 質問文に含まれる例や選択肢（「甘いもの、しょっぱいもの」など）
- 曖昧・不十分な回答（「うまいもの」「いろいろ」など）→ []
- 一時的な気分・感情（「今日お疲れ」「今朝だるい」など）
- その日限りの状態（「今日バタバタ」「今日は忙しい」など）
- 短期的な変化（天気、今日の予定など）
- UI・システムの説明、質問、挨拶
→ これらは [] を返す

【カテゴリー】
{categories_desc}

【標準キー名】
{standard_keys_desc}

【ルール】
1. ⚠️ 回答(A:)に明示的に書かれている情報のみ抽出
   - 質問文(Q:)の例・選択肢は絶対に抽出しない
   - 推測・解釈・補完は禁止
2. ✅ 複数項目は必ず個別に分割（最重要！）
   - 「AとB」→ "A"と"B"の2件（「AとB」という1件ではない）
   - 「AとBとC」→ "A"と"B"と"C"の3件
   - 「A、B」→ "A"と"B"の2件
   - 🚫 間違い：「AとB」という値を1つのデータとして出力
   - ✅ 正解：「と」「、」などのセパレーターを含まない、個別の値として出力
3. 曖昧・不十分な回答は抽出しない（「うまいもの」「いろいろ」→[]）
4. 不正な値は使わない（空配列"[]"、空文字、記号のみは禁止）

【出力形式】
各項目は別々のJSONオブジェクトとして出力してください。
[{{"category": "カテゴリー", "key": "項目", "value": "値"}}]

情報なし→[]

⚠️ 最終確認：
1. 回答(A:)に書かれている情報のみを抽出していますか？
2. 複数の項目がある場合、個別に分割していますか？
3. 「と」「、」などのセパレーターを含む値を出力していませんか？（含んでいたら分割し直してください）"""

        return prompt

    def _split_multiple_items(self, extracted_data: List[Dict]) -> List[Dict]:
        """
        セパレーターを含む値を自動分割
        LLMが分割していない場合でも、バックエンドで確実に分割する
        """
        result = []
        separators = ['、', '，', 'と', ',', '・', ' ']

        for item in extracted_data:
            value = str(item.get('value', '')).strip()

            # 空の値はスキップ
            if not value:
                continue

            # セパレーターを含むかチェック
            contains_separator = any(sep in value for sep in separators)

            if contains_separator:
                # セパレーターで分割
                print(f"[Extraction] Auto-splitting: '{value}'")
                parts = [value]

                # 各セパレーターで分割
                for sep in separators:
                    new_parts = []
                    for part in parts:
                        new_parts.extend([p.strip() for p in part.split(sep) if p.strip()])
                    parts = new_parts

                # 各パーツを個別のアイテムとして追加
                for part in parts:
                    if part:  # 空でない場合のみ
                        new_item = item.copy()
                        new_item['value'] = part
                        result.append(new_item)
                        print(f"[Extraction]   → Split item: '{part}'")
            else:
                # セパレーターがない場合はそのまま追加
                result.append(item)

        return result

    def _filter_question_contamination(self, extracted_data: List[Dict],
                                        user_message: str, previous_question: str) -> List[Dict]:
        """
        質問文からの誤抽出をフィルタリング
        ユーザーメッセージに含まれない情報が抽出されている場合、除外する
        """
        filtered = []
        for item in extracted_data:
            value = str(item.get('value', '')).strip()

            # 空の値はスキップ
            if not value:
                continue

            # 値がユーザーメッセージに含まれているか確認
            # 1. 完全一致または部分一致（「いちご」は「いちごレモン」に含まれる）
            if value in user_message:
                filtered.append(item)
                continue

            # 2. より柔軟なマッチング：主要な文字が含まれているか
            # 例：「米作り」→「米」と「作」が両方含まれていればOK
            # 2文字以上の値の場合、半分以上の文字がユーザーメッセージに含まれていればOK
            if len(value) >= 2:
                # 値を1文字ずつに分解
                chars_in_message = [c for c in value if c in user_message]
                match_ratio = len(chars_in_message) / len(value)

                if match_ratio >= 0.5:  # 50%以上の文字が一致
                    print(f"[Extraction] Partial match accepted: '{value}' (match ratio: {match_ratio:.1%})")
                    filtered.append(item)
                    continue

            # ユーザーメッセージに含まれていない
            print(f"[Extraction] Value '{value}' not found in user message '{user_message}'")
            print(f"[Extraction] Rejected (not in user message): {item}")

        return filtered

    def _parse_extracted_data(self, text: str) -> List[Dict]:
        """抽出されたテキストからJSONデータをパース"""
        try:
            print(f"[Extraction] Parsing text: {text[:500]}")

            # JSONブロックを抽出
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print(f"[Extraction] JSON string: {json_str[:300]}")

                data = json.loads(json_str)

                # バリデーション
                valid_data = []
                for item in data:
                    if not isinstance(item, dict):
                        print(f"[Extraction] Invalid item (not dict): {item}")
                        continue

                    if not all(k in item for k in ["category", "key", "value"]):
                        print(f"[Extraction] Invalid item (missing keys): {item}")
                        continue

                    if item["category"] not in CATEGORIES:
                        print(f"[Extraction] Invalid category: {item['category']}")
                        continue

                    # 不正な値をフィルタリング
                    value = str(item["value"]).strip()
                    if not value:
                        print(f"[Extraction] Invalid item (empty value): {item}")
                        continue

                    # 不正な値パターン
                    invalid_patterns = ["[]", "{}", "()", "null", "none", "undefined"]
                    if value.lower() in invalid_patterns:
                        print(f"[Extraction] Invalid item (invalid value pattern): {item}")
                        continue

                    # 長さ1文字以下の記号のみは除外（ただし数字とひらがな・カタカナ・漢字は許可）
                    if len(value) <= 1 and not value.isalnum():
                        print(f"[Extraction] Invalid item (single symbol): {item}")
                        continue

                    # 有効なデータとして追加
                    valid_data.append(item)

                return valid_data
            else:
                print(f"[Extraction] No JSON array found in text")
                return []
        except json.JSONDecodeError as e:
            print(f"[Extraction] JSON parse error: {e}")
            print(f"[Extraction] Problematic text: {text[:500]}")
            return []
        except Exception as e:
            print(f"[Extraction] Parse error: {e}")
            return []

    def detect_correction(self, user_message: str, conversation_history: List[Dict]) -> bool:
        """
        ユーザーが前の回答を訂正しているかどうかを検出
        Detect if the user is correcting their previous response
        """
        # 訂正を示すキーワード
        correction_keywords = [
            'ではなく', 'じゃなくて', 'ではない', 'じゃない',
            '訂正', '間違い', '違う', '違います',
            '正しくは', 'ちがう', 'ちがいます'
        ]

        # ユーザーメッセージに訂正キーワードが含まれているかチェック
        user_message_lower = user_message.lower()
        for keyword in correction_keywords:
            if keyword in user_message_lower:
                print(f"[Correction] Detected correction keyword: {keyword}")
                return True

        # 会話履歴をチェック（最後の2つのメッセージを確認）
        if len(conversation_history) >= 2:
            last_assistant = conversation_history[-1]
            second_last_user = conversation_history[-2] if len(conversation_history) >= 2 else None

            # アシスタントが訂正を認識した表現をしているかチェック
            if last_assistant.get('role') == 'assistant':
                assistant_content = last_assistant.get('content', '')
                correction_acknowledgments = [
                    '承知しました', 'わかりました', '了解',
                    '訂正します', '修正します'
                ]

                for ack in correction_acknowledgments:
                    if ack in assistant_content:
                        # 同時に前のユーザー発言への言及がある場合
                        if second_last_user and second_last_user.get('role') == 'user':
                            print(f"[Correction] Detected correction acknowledgment: {ack}")
                            return True

        return False

    def detect_deletion_request(self, user_message: str) -> bool:
        """
        ユーザーが前の回答の削除を要求しているかどうかを検出
        Detect if the user is requesting to delete their previous response
        """
        # 削除を示すキーワード
        deletion_keywords = [
            '削除', 'さくじょ',
            'やめます', 'やめる', 'やめて',
            '取り消し', '取り消して', 'とりけし',
            'なかったこと', 'なしで', '無しで',
            'キャンセル', 'きゃんせる',
            '忘れて', 'わすれて'
        ]

        # 「今の」「前の」などの対象を示す言葉
        target_keywords = ['今の', 'いまの', '前の', 'まえの', 'さっきの']

        user_message_lower = user_message.lower()

        # 削除キーワードが含まれているかチェック
        has_deletion_keyword = any(keyword in user_message_lower for keyword in deletion_keywords)

        # 対象キーワードが含まれているか、または短いメッセージの場合
        has_target_keyword = any(keyword in user_message_lower for keyword in target_keywords)
        is_short_message = len(user_message.strip()) <= 30  # 短いメッセージは削除リクエストの可能性が高い

        if has_deletion_keyword and (has_target_keyword or is_short_message):
            print(f"[Deletion] Detected deletion request in message: {user_message}")
            return True

        return False

