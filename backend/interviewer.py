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
from logger import get_logger

# ロガー初期化
log_lm = get_logger('LMStudio')
log_extract = get_logger('Extraction')
log_correction = get_logger('Correction')
log_debug = get_logger('Debug')


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
            log_lm.debug(f"LM Studio connection error: {e}")
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
                    log_debug.debug(f"Current topic: {category} (keyword: {keyword})")
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
                    log_debug.debug(f"Found user name in session data: {user_name}")
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
                            log_debug.debug(f"Inferred user name from conversation: {user_name}")


        # 会話履歴から同じトピック（サブカテゴリー1レベル）の連続質問数をカウント
        consecutive_info = self._count_consecutive_questions(session_data)
        consecutive_count = consecutive_info['count']
        current_topic = consecutive_info['topic_identifier']

        # 会話戦略部分を条件分岐
        if user_name:
            # 名前が既に分かっている場合
            topic_change_strategy = ""
            if consecutive_count >= 3:
                # ユーザーのエンゲージメントレベルを分析
                engagement = self._analyze_user_engagement(session_data)

                log_debug.info(f"⚠️ Topic switch required: {consecutive_count} consecutive on '{current_topic}' (engagement: {engagement})")
                log_debug.debug(f"Adding topic change instructions to system prompt with {engagement} engagement strategy")

                if engagement == 'high':
                    # 高エンゲージメント: 自然な移行を推奨
                    topic_change_strategy = f"""
【🚨 必須指示: 話題転換が必要です】
現在「{current_topic}」について{consecutive_count}回連続で質問しています。
この話題はここまでとします。

**必ず次の質問で別のトピックに切り替えてください。**

推奨される切り替え方法（自然な移行）:
1. 現在の話題を簡単にまとめる（1文程度）
2. 「ところで」「そういえば」などで自然に別の話題に移行
3. 空白カテゴリーまたは未掘り下げのトピックから質問を選ぶ

例:
「{current_topic}、楽しそうですね！ところで、普段どんなお仕事をされてますか？」

⚠️ 注意: 同じ「{current_topic}」について続けて質問することは禁止です。
別のカテゴリーまたは別のサブトピックに必ず切り替えてください。"""
                else:
                    # 低エンゲージメント: 明示的な切り替えを推奨
                    topic_change_strategy = f"""
【🚨 必須指示: 話題転換が必要です】
現在「{current_topic}」について{consecutive_count}回連続で質問しています。
ユーザーの回答が短いため、この話題はここまでとします。

**必ず次の質問で別のトピックに切り替えてください。**

推奨される切り替え方法（明示的な切り替え）:
1. 「なるほど、ありがとうございます！」と締めくくる
2. 「では、別の話題に移りますね」と明示的に宣言
3. 全く異なるカテゴリーから質問を選ぶ

例:
「なるほど、ありがとうございます！では、普段の生活リズムについて聞いてもいいですか？」

⚠️ 注意: 同じ「{current_topic}」について続けて質問することは禁止です。
別のカテゴリーまたは別のサブトピックに必ず切り替えてください。"""

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
                log_debug.debug(f"Extracted data added to system prompt: {len(details_lines)} items")

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
            # 話題切り替えが必要かチェック
            consecutive_info = self._count_consecutive_questions(session_data)
            consecutive_count = consecutive_info['count']
            current_topic = consecutive_info['topic_identifier']

            topic_switch_required = consecutive_count >= 3

            if topic_switch_required:
                log_debug.info(f"⚠️ Topic switch required: {consecutive_count} consecutive on '{current_topic}'")

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
                log_lm.debug(f"LM Studio raw response: {assistant_message[:100]}...")

                # 内部コメントを除去
                cleaned_message = self._clean_response(assistant_message)

                # デバッグ: クリーン後のメッセージを出力
                log_lm.debug(f"Response length - raw: {len(assistant_message)}, cleaned: {len(cleaned_message)}")

                # 空の応答をチェック
                final_message = cleaned_message.strip()
                if not final_message:
                    log_lm.warning(f"Cleaned message is empty! Raw response was: {assistant_message[:500]}")
                    return None

                # ⚙️ 話題切り替え検証（必要な場合のみ）
                if topic_switch_required and current_topic:
                    log_debug.info(f"Verifying topic switch from '{current_topic}'...")

                    # LLMが実際に話題を切り替えたか検証
                    switch_successful = self._verify_topic_switch(
                        final_message,
                        current_topic,
                        session_data
                    )

                    if not switch_successful:
                        log_debug.warning(f"LLM failed to switch topic, forcing regeneration...")

                        # 強制的に話題を切り替えた質問を再生成
                        forced_message = self._force_topic_change(
                            messages,
                            character_id,
                            profile,
                            category_counts,
                            empty_categories,
                            current_topic,
                            session_data
                        )

                        log_debug.info(f"📊 Topic switch completed via forced regeneration from '{current_topic}'")
                        return forced_message
                    else:
                        log_debug.info(f"✅ Topic switch verification passed - LLM successfully moved away from '{current_topic}'")
                        log_debug.info(f"📊 Topic switch completed naturally from '{current_topic}'")

                return final_message
            else:
                log_lm.error(f"LM Studio error: {response.status_code}")
                try:
                    error_detail = response.json()
                    log_lm.error(f"LM Studio error detail: {error_detail}")
                except:
                    log_lm.error(f"LM Studio error body: {response.text[:500]}")

                # システムプロンプトの長さをチェック
                log_debug.debug(f"System prompt length: {len(system_prompt)} characters")
                log_debug.debug(f"Total messages: {len(full_messages)}")

                return None

        except Exception as e:
            log_lm.error(f"Error getting response: {e}")
            return None

    def _count_consecutive_questions(self, session_data: Dict) -> Dict:
        """
        会話履歴から同じトピック（サブカテゴリー1レベル）の連続質問数をカウント
        直近の抽出データを分析して、同じカテゴリー+サブカテゴリー1が連続している回数を数える

        Returns:
            dict: {
                'count': 連続質問数,
                'category': 最新のカテゴリー,
                'subcategory1': 最新のサブカテゴリー1（なければNone）,
                'topic_identifier': トピック識別子（表示用）
            }
        """
        default_result = {
            'count': 0,
            'category': None,
            'subcategory1': None,
            'topic_identifier': None
        }

        if not session_data or 'extracted_data' not in session_data:
            return default_result

        extracted_data = session_data['extracted_data']
        if not extracted_data:
            return default_result

        # 全カテゴリーのデータをタイムスタンプ順にソート（最新データは配列の最後）
        all_items = []
        for category, items in extracted_data.items():
            for item in items:
                all_items.append({
                    'category': category,
                    'item': item
                })

        if len(all_items) < 2:
            return default_result

        # 最新のアイテムを取得
        latest_item = all_items[-1]
        latest_category = latest_item['category']
        latest_subcategory1 = latest_item['item'].get('subcategory1')

        # subcategory1がない場合は、カテゴリーレベルにフォールバック
        if not latest_subcategory1:
            log_debug.debug("No subcategory1 found, falling back to category-level counting")

            # 後ろから数えて同じカテゴリーが何回連続しているか
            consecutive_count = 0
            for i in range(len(all_items) - 1, -1, -1):
                if all_items[i]['category'] == latest_category:
                    consecutive_count += 1
                else:
                    break

            topic_identifier = latest_category
        else:
            # サブカテゴリー1レベルでカウント
            consecutive_count = 0
            for i in range(len(all_items) - 1, -1, -1):
                item = all_items[i]
                item_category = item['category']
                item_subcat1 = item['item'].get('subcategory1')

                # カテゴリーとサブカテゴリー1の両方が一致する場合のみカウント
                if item_category == latest_category and item_subcat1 == latest_subcategory1:
                    consecutive_count += 1
                else:
                    break

            topic_identifier = f"{latest_category}/{latest_subcategory1}"

        log_debug.debug(f"Consecutive count: {consecutive_count} for topic '{topic_identifier}'")

        return {
            'count': consecutive_count,
            'category': latest_category,
            'subcategory1': latest_subcategory1,
            'topic_identifier': topic_identifier
        }

    def _analyze_user_engagement(self, session_data: Dict) -> str:
        """
        ユーザーのエンゲージメントレベルを分析
        直近3回のユーザーメッセージの平均長から、積極的に会話しているかを判定

        Returns:
            'high': 積極的に会話している（平均20文字以上）
            'low': 短い回答が続いている（平均20文字未満）
        """
        if not session_data or 'conversation' not in session_data:
            return 'low'

        conversation = session_data['conversation']

        # 最後から6メッセージを取得し、userメッセージのみ抽出（最大3件）
        recent_user_messages = [
            msg['content'] for msg in conversation[-6:]
            if msg.get('role') == 'user'
        ][-3:]

        if not recent_user_messages:
            return 'low'

        # 平均文字数を計算
        avg_length = sum(len(msg) for msg in recent_user_messages) / len(recent_user_messages)

        # しきい値: 20文字
        engagement_level = 'high' if avg_length >= 20 else 'low'

        log_debug.debug(f"User engagement: {engagement_level} (avg message length: {avg_length:.1f} chars)")

        return engagement_level

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

    def _verify_topic_switch(self, assistant_response: str,
                            forbidden_topic: str,
                            session_data: Dict) -> bool:
        """
        アシスタントの応答が禁止トピックから切り替わったかを検証

        Args:
            assistant_response: AIの生成した応答
            forbidden_topic: 避けるべきトピック（例: "趣味・興味・娯楽/ゲーム"）
            session_data: セッションデータ

        Returns:
            True: 話題切り替え成功, False: まだ同じ話題
        """
        if not forbidden_topic:
            return True

        log_debug.debug(f"🔍 Starting topic switch verification for forbidden topic: '{forbidden_topic}'")

        # 禁止トピックからカテゴリーとサブカテゴリー1を抽出
        if '/' in forbidden_topic:
            forbidden_category, forbidden_subcat1 = forbidden_topic.split('/', 1)
        else:
            forbidden_category = forbidden_topic
            forbidden_subcat1 = None

        # サブカテゴリー1ごとのキーワードマッピング
        subcategory_keywords = {
            # 趣味・興味・娯楽
            'ゲーム': ['ゲーム', 'プレイ', 'ゲーマー', 'RPG', 'アクション', 'パズル', 'ストラテジー', 'シミュレーション', 'eスポーツ', 'ソシャゲ', 'コンシューマー'],
            'スポーツ': ['スポーツ', '運動', 'サッカー', '野球', 'バスケ', 'テニス', 'ジム', 'トレーニング', '筋トレ', 'ランニング', 'マラソン', '試合', 'チーム'],
            '読書': ['読書', '本', '小説', 'マンガ', '漫画', '雑誌', '書籍', '文庫', '図書', '著者', '作家', 'ページ'],
            '映画': ['映画', 'ムービー', 'シネマ', '監督', '俳優', '女優', '作品', '劇場', 'DVD', 'Netflix', '配信'],
            '音楽': ['音楽', '曲', 'アーティスト', 'バンド', 'ライブ', 'コンサート', '歌', '楽器', 'フェス', 'Spotify', 'プレイリスト'],
            'アニメ': ['アニメ', 'アニメーション', '声優', 'オタク', '作画', 'キャラ', 'キャラクター', '2期', 'クール'],
            '料理': ['料理', '調理', 'レシピ', '食材', '包丁', 'キッチン', '味付け', '自炊', 'クッキング'],
            '旅行': ['旅行', '観光', '旅', 'ツアー', '旅先', '宿', 'ホテル', '海外', '国内', '旅館', '温泉'],
            'グルメ': ['グルメ', '食事', 'レストラン', '飲食', '食べ歩き', '美食', 'カフェ', '外食'],
            'お酒': ['お酒', '飲酒', 'ビール', 'ワイン', '日本酒', '焼酎', 'カクテル', 'バー', '居酒屋', '酒'],
            'ペット': ['ペット', '犬', '猫', '動物', '飼育', '散歩', 'わんこ', 'にゃんこ'],
            'ドライブ': ['ドライブ', '運転', '車', 'カー', '自動車', 'クルマ', 'ドライブ'],
            'アウトドア': ['アウトドア', 'キャンプ', '登山', 'ハイキング', '釣り', 'バーベキュー', 'BBQ', '山', 'テント'],
            'インドア': ['インドア', '家', '部屋', '室内', 'おうち時間', '在宅'],

            # 基本プロフィール・仕事
            '仕事': ['仕事', '職業', '勤務', '会社', '職場', '業務', 'プロジェクト', '出勤', 'ビジネス', '勤め'],
            '職歴': ['職歴', '転職', 'キャリア', '経歴', '社会人', '就職', '入社'],

            # 学習・成長
            '学習': ['学習', '勉強', '資格', 'スキル', '習得', 'トレーニング', '学校', '教育', '講座'],
            '学歴': ['学歴', '学校', '大学', '高校', '専門', '卒業', '進学'],

            # 健康・ライフスタイル
            '健康': ['健康', '体調', '病気', '医療', '診察', '治療', '症状', '病院', '通院'],
            '睡眠': ['睡眠', '寝る', '起床', '就寝', '眠り', '寝付き', '寝不足', '朝'],
            '食事': ['食事', '朝食', '昼食', '夕食', '栄養', '食べる', '食生活', '食習慣'],
            '運動': ['運動', 'エクササイズ', '体操', 'ヨガ', 'ストレッチ', '身体', '体力'],

            # 現在の生活
            '住環境': ['住環境', '住まい', '家', '部屋', 'マンション', 'アパート', '引っ越し', '賃貸', '持ち家'],
            '生活リズム': ['生活リズム', '生活パターン', '1日', 'ルーティン', '習慣', 'スケジュール'],

            # 人間関係・コミュニティ
            '家族': ['家族', '親', '父', '母', '兄弟', '姉妹', '子供', '夫', '妻', 'パートナー', '息子', '娘'],
            '友人': ['友人', '友達', '仲間', 'フレンド', '知人', '付き合い'],
            'コミュニティ': ['コミュニティ', 'グループ', 'サークル', '集まり', 'つながり', '団体'],

            # 情報収集・メディア
            'SNS': ['SNS', 'Twitter', 'Instagram', 'Facebook', 'TikTok', 'LINE', 'ソーシャル', '投稿', 'フォロー'],
            'ニュース': ['ニュース', '報道', '新聞', 'ネット', '情報', 'メディア', 'Web'],

            # 経済・消費
            '買い物': ['買い物', 'ショッピング', '購入', '通販', 'Amazon', '楽天', 'お買い物'],
            'お金': ['お金', '貯金', '貯蓄', '資産', '投資', '金融', '経済', '節約', 'マネー'],

            # 価値観・将来
            '夢': ['夢', '目標', '志', 'やりたいこと', '憧れ', '理想'],
            '目標': ['目標', 'ゴール', '達成', '計画', '将来'],
            '人生観': ['人生観', '価値観', '考え方', '信念', '哲学', '大切', '重視'],
        }

        # 禁止トピックのキーワードをチェック
        if forbidden_subcat1 and forbidden_subcat1 in subcategory_keywords:
            keywords = subcategory_keywords[forbidden_subcat1]
            response_lower = assistant_response.lower()

            # キーワードマッチ数をカウント
            matched_keywords = [kw for kw in keywords if kw.lower() in response_lower]
            matches = len(matched_keywords)

            # 2個以上のキーワードが見つかった場合、まだ同じ話題
            if matches >= 2:
                log_debug.warning(f"❌ Topic switch FAILED: found {matches} keywords for '{forbidden_subcat1}': {matched_keywords[:5]}")
                return False
            elif matches == 1:
                log_debug.debug(f"Found 1 keyword for '{forbidden_subcat1}': {matched_keywords}, allowing switch")

        # 話題切り替え成功
        log_debug.info(f"✅ Topic switch SUCCESSFUL: moved away from '{forbidden_topic}'")
        return True

    def _choose_next_topic(self, category_counts: Dict[str, int],
                          empty_categories: List[str],
                          forbidden_category: str,
                          session_data: Dict) -> str:
        """
        次のトピックを戦略的に選択

        優先順位:
        1. 空カテゴリー（未収集のカテゴリー）
        2. データ数が最も少ないカテゴリー
        3. 禁止カテゴリー以外のランダムカテゴリー

        Args:
            category_counts: カテゴリーごとのデータ数
            empty_categories: 空カテゴリーのリスト
            forbidden_category: 避けるべきカテゴリー
            session_data: セッションデータ

        Returns:
            次のトピック名（例: "現在の生活", "健康・ライフスタイル"）
        """
        import random

        # 優先度1: 空カテゴリー（禁止カテゴリーを除く）
        available_empty = [cat for cat in empty_categories if cat != forbidden_category]
        if available_empty:
            chosen = random.choice(available_empty)
            log_debug.debug(f"Chose empty category: {chosen}")
            return chosen

        # 優先度2: データ数が最も少ないカテゴリー（禁止カテゴリーを除く）
        sorted_categories = sorted(
            [(cat, count) for cat, count in category_counts.items() if cat != forbidden_category],
            key=lambda x: x[1]
        )

        if sorted_categories:
            # 下位3カテゴリーからランダムに選択（バリエーションを持たせる）
            candidates = sorted_categories[:min(3, len(sorted_categories))]
            chosen = random.choice(candidates)
            log_debug.debug(f"Chose least-explored category: {chosen[0]} ({chosen[1]} items)")
            return chosen[0]

        # 優先度3: 禁止カテゴリー以外のランダムカテゴリー
        all_categories = list(CATEGORIES.keys())
        available = [cat for cat in all_categories if cat != forbidden_category]

        if available:
            chosen = random.choice(available)
            log_debug.debug(f"Chose random available category: {chosen}")
            return chosen

        # フォールバック: 最初のカテゴリー
        fallback = list(CATEGORIES.keys())[0]
        log_debug.warning(f"Using fallback category: {fallback}")
        return fallback

    def _force_topic_change(self, messages: List[Dict], character_id: str,
                           profile: Dict, category_counts: Dict[str, int],
                           empty_categories: List[str],
                           forbidden_topic: str,
                           session_data: Dict) -> str:
        """
        話題切り替えに失敗した場合、強制的に別のトピックで質問を再生成

        Args:
            messages: 会話履歴
            character_id: キャラクターID
            profile: ユーザープロファイル
            category_counts: カテゴリーごとのデータ数
            empty_categories: 空カテゴリーのリスト
            forbidden_topic: 避けるべきトピック
            session_data: セッションデータ

        Returns:
            新しい質問（別のトピック）
        """
        # 禁止トピックからカテゴリーを抽出
        if '/' in forbidden_topic:
            forbidden_category, forbidden_subcat1 = forbidden_topic.split('/', 1)
        else:
            forbidden_category = forbidden_topic
            forbidden_subcat1 = None

        # 次のトピックを選択
        next_topic = self._choose_next_topic(
            category_counts,
            empty_categories,
            forbidden_category,
            session_data
        )

        log_debug.info(f"🔄 Forcing topic change: '{forbidden_topic}' → '{next_topic}'")

        # キャラクター情報を取得
        character = CHARACTERS.get(character_id, CHARACTERS["aoi"])

        # 強制的なシステムプロンプトを生成
        forced_prompt = f"""あなたは{character['name']}、{character['description']}です。

【🚨 緊急指示】
前の話題「{forbidden_topic}」の掘り下げを終了します。
今から必ず「{next_topic}」について質問してください。

指示:
1. 前の話題を簡単に締めくくる（1文、または省略可）
2. 「では」「ところで」などで切り替える
3. 「{next_topic}」に関する質問を1つする
4. 質問は簡潔に（15-30文字程度）

例:
「なるほど！では、普段のお仕事について教えてください。」
「ところで、健康面で気をつけていることはありますか？」

必ず日本語で、{character['tone']}に応答してください。
絶対に「{forbidden_topic}」について質問しないでください。"""

        try:
            # LM Studioに強制リクエスト
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": LM_STUDIO_MODEL,
                    "messages": [
                        {"role": "system", "content": forced_prompt},
                        {"role": "user", "content": messages[-1]['content']}  # 最後のユーザーメッセージ
                    ],
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                forced_response = result["choices"][0]["message"]["content"]
                cleaned_response = self._clean_response(forced_response)

                log_debug.info(f"✅ Forced topic change successful: '{forbidden_topic}' → '{next_topic}'")
                return cleaned_response

            # レスポンス取得失敗
            log_debug.warning(f"Forced LLM call failed with status {response.status_code}")

        except Exception as e:
            log_debug.error(f"Error in forced topic change: {e}")

        # フォールバック: suggest_next_topicを使用
        log_debug.warning("Forced LLM call failed, using fallback question")
        fallback_question = self.suggest_next_topic(empty_categories, character_id)

        if fallback_question:
            return fallback_question
        else:
            # 最終フォールバック
            return "他に何か教えていただけますか？"

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
                # パターン1: conversation_history[-1] = 今追加されたアシスタント応答, [-2] = ユーザー, [-3] = 前の質問
                # パターン2: conversation_history[-1] = ユーザーメッセージ, [-2] = 前の質問（まだアシスタント応答が追加されていない）
                previous_question = ""

                # デバッグ: 会話履歴を確認
                log_extract.debug(f"Conversation history length: {len(conversation_history)}")

                # 最後のメッセージがuserの場合（アシスタント応答がまだ追加されていない）
                if len(conversation_history) >= 2 and conversation_history[-1].get('role') == 'user':
                    # [-2] が前のアシスタント質問
                    prev_msg = conversation_history[-2]
                    if prev_msg.get('role') == 'assistant':
                        previous_question = prev_msg.get('content', '')
                # 最後のメッセージがassistantの場合（アシスタント応答が既に追加されている）
                elif len(conversation_history) >= 3 and conversation_history[-1].get('role') == 'assistant':
                    # [-3] が前のアシスタント質問
                    prev_msg = conversation_history[-3]
                    if prev_msg.get('role') == 'assistant':
                        previous_question = prev_msg.get('content', '')

                # LLMに送るユーザーメッセージを構築（最小限）
                if previous_question:
                    # 質問文から挨拶部分を除去（改行で分割して最後の行のみ使用）
                    # 例: "初めまして。青山です。\nお名前を教えてもらえますか？" → "お名前を教えてもらえますか？"
                    question_lines = previous_question.strip().split('\n')
                    clean_question = question_lines[-1].strip()  # 最後の行のみ

                    log_extract.debug(f"Previous question detected: {previous_question[:100]}")
                    llm_user_message = f"""Q:{clean_question}
A:{user_message}"""
                else:
                    log_extract.debug(f" No previous question detected")
                    llm_user_message = user_message

                log_extract.debug(f" LLM user message: {llm_user_message[:200]}")

                # LM Studioにリクエスト
                response = requests.post(
                    self.lm_studio_url,
                    json={
                        "model": LM_STUDIO_MODEL,
                        "messages": [
                            {"role": "system", "content": extraction_prompt},
                            {"role": "user", "content": llm_user_message}
                        ],
                        "max_tokens": 500,  # 増やして完全なJSONを返すように
                        "temperature": 0.0,  # 0にして完全に決定論的に
                        "stream": False
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    extracted_text = result["choices"][0]["message"]["content"]

                    # デバッグ: 生のレスポンスを出力
                    log_extract.debug(f" LM Studio response: {extracted_text}")

                    # JSON形式でパース
                    extracted_data = self._parse_extracted_data(extracted_text)
                    log_extract.debug(f" Found {len(extracted_data)} data points")

                    # 複数項目を自動分割
                    extracted_data = self._split_multiple_items(extracted_data)
                    log_extract.debug(f" After splitting: {len(extracted_data)} data points")

                    # 質問文からの誤抽出をチェック
                    if previous_question:
                        extracted_data = self._filter_question_contamination(
                            extracted_data, user_message, previous_question
                        )
                        log_extract.debug(f" After filtering: {len(extracted_data)} data points")

                    # キー正規化を適用 / Apply key normalization
                    normalizer = KeyNormalizer()
                    normalized_data = normalizer.normalize_batch(extracted_data)

                    # 正規化統計をログ出力
                    stats = normalizer.get_normalization_stats()
                    if stats["total_normalizations"] > 0:
                        log_extract.debug(f"Normalized {stats['total_normalizations']} keys")
                        for category, data in stats['by_category'].items():
                            for raw, normalized in data['mappings'].items():
                                log_extract.debug(f"  {category}/{raw} → {normalized}")

                    # デバッグ: 抽出されたデータを出力
                    for data in normalized_data:
                        log_extract.debug(f" Data: {data}")

                    # データが抽出できた、または最後の試行の場合は結果を返す
                    if normalized_data:
                        return normalized_data

                    # 最後の試行の場合は空のリストを返す
                    if attempt == max_retries - 1:
                        log_extract.debug(f" All retries exhausted, returning empty list")
                        return []

                    # データが空で、まだリトライ可能な場合
                    log_extract.debug(f" No data extracted (possibly filtered out), retry {attempt + 1}/{max_retries}")
                    continue
                else:
                    log_extract.debug(f" LM Studio error: {response.status_code}")
                    if attempt < max_retries - 1:
                        log_extract.debug(f" Retrying... ({attempt + 1}/{max_retries})")
                        continue
                    return []

            except requests.exceptions.Timeout:
                log_extract.debug(f" Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    log_extract.debug(f" Retrying...")
                    continue
                return []
            except Exception as e:
                log_extract.debug(f" Error: {e}")
                if attempt < max_retries - 1:
                    log_extract.debug(f" Retrying... ({attempt + 1}/{max_retries})")
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
        # extract_profile_data() と同じロジックを使用
        previous_assistant_question = ""
        question_analysis = ""

        # 最後のメッセージがuserの場合（アシスタント応答がまだ追加されていない）
        if len(conversation_history) >= 2 and conversation_history[-1].get('role') == 'user':
            # [-2] が前のアシスタント質問
            prev_msg = conversation_history[-2]
            if prev_msg.get('role') == 'assistant':
                previous_assistant_question = prev_msg.get('content', '')
        # 最後のメッセージがassistantの場合（アシスタント応答が既に追加されている）
        elif len(conversation_history) >= 3 and conversation_history[-1].get('role') == 'assistant':
            # [-3] が前のアシスタント質問
            prev_msg = conversation_history[-3]
            if prev_msg.get('role') == 'assistant':
                previous_assistant_question = prev_msg.get('content', '')

        # 質問が取得できた場合のみ分析
        if previous_assistant_question:
            # 質問内容の分析（優先度順）
            question_lower = previous_assistant_question.lower()

            # 名前
            if '名前' in question_lower or 'なまえ' in question_lower or 'お名前' in question_lower:
                question_analysis = "【重要】直前の質問は「名前」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「名前」として抽出してください。"

            # 年齢
            elif '年齢' in question_lower or 'とし' in question_lower or '何歳' in question_lower or 'いくつ' in question_lower or '歳' in question_lower:
                question_analysis = "【重要】直前の質問は「年齢」について聞いています。ユーザーの回答は「基本プロフィール」カテゴリーの「年齢」として抽出してください。"

            # 業務内容・仕事の詳細
            elif '業務' in question_lower or '担当' in question_lower or '何をして' in question_lower or '何やって' in question_lower or 'どんなこと' in question_lower:
                question_analysis = "【重要】直前の質問は「業務内容」について聞いています。ユーザーの回答は「現在の生活」カテゴリーの「仕事 > 業務内容」として抽出してください。職業名ではなく、具体的な業務内容です。"

            # 職業・仕事（職業名）
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
                log_extract.debug(f" Question detected: {previous_assistant_question[:50]}")
                log_extract.debug(f" Analysis: {question_analysis}")

        # 5階層データ構造の説明と例
        hierarchy_explanation = """
【5階層データ構造】
category（固定カテゴリー） > subcategory1（サブカテゴリー1） > subcategory2（サブカテゴリー2） > key（キー） > value（値）

⚠️ 階層の一貫性ルール（重要！）:
同じトピック（例：ゲーム、スポーツ、読書など）の情報は、必ず同じ階層構造で整理してください。
subcategory1として「趣味」「興味」などの抽象的な名前は避け、具体的なトピック名を使用してください。

✅ 良い例（一貫した階層）:
- カテゴリー: 趣味・興味・娯楽
  - サブカテゴリー1: ゲーム
    - サブカテゴリー2: ロールプレイングゲーム
      - キー: 好きなタイトル → 値: ファイナルファンタジー
    - サブカテゴリー2: アクションゲーム
      - キー: 好きなタイトル → 値: スーパーマリオ
    - サブカテゴリー2: パズルゲーム
      - キー: 好きなタイトル → 値: テトリス

❌ 悪い例（一貫性のない階層）:
- カテゴリー: 趣味・興味・娯楽
  - サブカテゴリー1: 趣味          ← 抽象的すぎる！
    - サブカテゴリー2: ゲーム
      - キー: 種類 → 値: ビデオゲーム
  - サブカテゴリー1: ゲーム        ← 上と重複！
    - サブカテゴリー2: ロールプレイングゲーム
      - キー: 好きなタイトル → 値: ファイナルファンタジー

✅ その他の良い例:
- カテゴリー: 趣味・興味・娯楽
  - サブカテゴリー1: スポーツ
    - サブカテゴリー2: サッカー
      - キー: 好きなチーム → 値: マンチェスター・ユナイテッド
      - キー: 好きな選手 → 値: クリスティアーノ・ロナウド
    - サブカテゴリー2: 格闘技
      - キー: 種類 → 値: ムエタイ
      - キー: 経験年数 → 値: 3年
  - サブカテゴリー1: 乗り物
    - サブカテゴリー2: バイク
      - キー: 車種 → 値: ハーレーダビッドソン
      - キー: 排気量 → 値: 1200cc

- カテゴリー: 現在の生活
  - サブカテゴリー1: 仕事
    - サブカテゴリー2: 業務内容
      - キー: 担当業務 → 値: AIプロダクト開発
      - キー: 使用言語 → 値: Python
      - キー: 業務 → 値: トイレの掃除（具体的な業務なので抽出すべき）
      - キー: 業務 → 値: データ入力（具体的な業務なので抽出すべき）
    - サブカテゴリー2: 勤務先
      - キー: 企業タイプ → 値: スタートアップ
      - キー: 従業員数 → 値: 50人

⚠️ 階層統一の原則:
1. subcategory1には具体的なトピック名（ゲーム、スポーツ、読書、料理など）を使用
2. 「趣味」「興味」「活動」などの抽象的な名前をsubcategory1に使わない
3. 同じトピックの情報は必ず同じsubcategory1配下に配置
4. subcategory2で詳細なジャンルや分類を表現

可能な限り5階層で詳細に抽出し、階層の一貫性を保ってください。"""

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

        prompt = f"""⚠️⚠️⚠️ 最重要指示 ⚠️⚠️⚠️
出力: JSON配列のみを返してください。
説明文、確認メッセージ、例は一切不要です。
「了解しました」「指示に従い」などの返答は不要です。
JSON配列 [] だけを出力してください。

回答(A:)に書かれていない情報は絶対に抽出しないでください。
質問文(Q:)の例や選択肢を抽出することは厳禁です。

🚫 絶対禁止:
- 質問文の例・選択肢を抽出すること
- 回答に含まれない情報の捏造
- 曖昧・不十分な回答の無理な解釈
- 確認メッセージや説明文の出力

{question_context_section}{category_context_section}

【抽出対象】安定的・継続的な個人特徴のみ
✅ 抽出すべき情報:
- 趣味・習慣（「釣りに行った」→趣味として抽出）
- 継続的な活動・パターン
- 中長期的な特徴（「最近ずっと〜」）
- 基本情報（名前、年齢、職業、住所など）
- 業務内容・仕事の詳細（「トイレの掃除」「データ入力」「接客」など）
- 具体的で明確な回答（1単語以上の具体的な内容）

❌ 抽出してはいけない情報:
- 質問文に含まれる例や選択肢（「甘いもの、しょっぱいもの」など）
- 本当に曖昧な回答（「うまいもの」「いろいろ」「よくわからない」など）
  ⚠️ 注意：「トイレの掃除」「接客」などは具体的なので抽出すべき！
- 一時的な気分・感情（「今日お疲れ」「今朝だるい」など）
- その日限りの状態（「今日バタバタ」「今日は忙しい」など）
- 短期的な変化（天気、今日の予定など）
- UI・システムの説明、質問、挨拶
→ これらは [] を返す

【カテゴリー】
{categories_desc}

{hierarchy_explanation}

【⚠️⚠️⚠️ カテゴリー分類の優先順位ルール ⚠️⚠️⚠️】
同じ情報を複数のカテゴリーに重複して登録することは絶対に禁止です！
以下の情報は必ず「基本プロフィール」カテゴリーに分類してください：

必須：基本プロフィールに分類すべき情報
- 名前、氏名、呼び名、ニックネーム → 基本プロフィール > 名前
- 年齢、生年月日、誕生日、何歳 → 基本プロフィール > 年齢
- 職業、仕事（職業名そのもの）→ 基本プロフィール > 職業
  例：「エンジニア」「医者」「会社員」「学生」「八百屋」など
- 住所、居住地、住んでいる場所、出身地 → 基本プロフィール > 住所
- 性別 → 基本プロフィール > 性別
- 家族構成、続柄（父、母、兄弟など）→ 基本プロフィール > 家族構成
- 学歴、最終学歴、卒業した学校 → 基本プロフィール > 学歴

⚠️ 重複禁止の例：
❌ 間違い：
  職業「エンジニア」を「基本プロフィール」と「現在の生活」の両方に登録
❌ 間違い：
  住所「横浜市」を「基本プロフィール」と「現在の生活」の両方に登録

✅ 正しい分類：
  - 職業名「エンジニア」→ 基本プロフィール > 職業 > 職業名 のみ
  - 業務内容「AIプロダクト開発」→ 現在の生活 > 仕事 > 業務内容（職業名ではないので別）
  - 住所「横浜市保土ヶ谷区」→ 基本プロフィール > 住所 > 地域 のみ

✅ 職業関連の詳細情報の分類方法：
  - 職業名そのもの（エンジニア、医者など）→ 基本プロフィール > 職業
  - 業務内容、仕事の詳細、担当業務 → 現在の生活 > 仕事 > 業務内容
  - 勤務先名、会社名、職場名 → 現在の生活 > 仕事 > 勤務先
  - 勤務時間、働き方、勤務形態 → 現在の生活 > 仕事 > 勤務形態
  - 職場環境、同僚との関係 → 人間関係・コミュニティ > 職場

【ルール】
1. ⚠️ 回答(A:)に明示的に書かれている情報のみ抽出
   - 質問文(Q:)の例・選択肢は絶対に抽出しない
   - 推測・解釈・補完は禁止
2. ✅ 情報の詳細度に応じて適切な階層を選択
   - 詳細な分類が可能な場合のみsubcategory1やsubcategory2を使用
   - ⚠️ 重要：「その他」などの無意味なサブカテゴリーは作らない
   - 適切なサブカテゴリー名がない場合は、その階層を省略する
   - 例1（5階層）: 「サッカーが好きで、マンチェスター・ユナイテッドのファン」
     → category: 趣味・興味・娯楽, subcategory1: スポーツ, subcategory2: サッカー, key: 好きなチーム, value: マンチェスター・ユナイテッド
   - 例2（3階層）: 「名前は田中です」
     → category: 基本プロフィール, subcategory1: 名前, key: 氏名, value: 田中
     （subcategory2は不要なので省略）
   - 例3（3階層）: 「趣味は読書です」
     → category: 趣味・興味・娯楽, subcategory1: 読書, key: 趣味, value: 読書
     （subcategory2は不要なので省略）
3. ⚠️⚠️⚠️ 階層の一貫性を保つ（超重要！）
   - 同じトピック（ゲーム、スポーツなど）は必ず同じsubcategory1を使用
   - subcategory1には「趣味」「興味」などの抽象的な名前を使わない
   - 具体的なトピック名（ゲーム、スポーツ、読書、料理など）をsubcategory1に使用
   - 例: ゲーム関連は全て「subcategory1: ゲーム」配下に統一
4. ✅ 複数項目は必ず個別に分割（最重要！）
   - 「AとB」→ "A"と"B"の2件（「AとB」という1件ではない）
   - 「AとBとC」→ "A"と"B"と"C"の3件
   - 「A、B」→ "A"と"B"の2件
   - 🚫 間違い：「AとB」という値を1つのデータとして出力
   - ✅ 正解：「と」「、」などのセパレーターを含まない、個別の値として出力
   - ⚠️ 例外：名前（人名）は固有名詞として1つのまま保存
     - 「イーロンマスク」→ 1件（分割しない）
     - 「山田太郎」→ 1件（分割しない）
     - 名前に「と」が含まれていても分割しない（例：「佐藤と鈴木」は2人の名前なら分割するが、「伊藤」は1人の姓）
5. ⚠️⚠️⚠️ 同じ情報を複数のカテゴリーに重複登録することは絶対禁止！
   - 1つの情報は1つのカテゴリーのみに分類
   - 特に基本プロフィール情報（名前、年齢、職業、住所）は基本プロフィールのみ
6. 曖昧・不十分な回答は抽出しない（「うまいもの」「いろいろ」→[]）
7. 不正な値は使わない（空配列"[]"、空文字、記号のみは禁止）

【出力形式】
各項目は別々のJSONオブジェクトとして出力してください。

5階層（推奨）:
[{{"category": "カテゴリー", "subcategory1": "サブカテゴリー1", "subcategory2": "サブカテゴリー2", "key": "キー", "value": "値"}}]

4階層:
[{{"category": "カテゴリー", "subcategory1": "サブカテゴリー1", "subcategory2": "サブカテゴリー2", "value": "値"}}]

3階層:
[{{"category": "カテゴリー", "subcategory1": "サブカテゴリー1", "key": "キー", "value": "値"}}]

2階層（詳細情報が少ない場合のみ）:
[{{"category": "カテゴリー", "key": "キー", "value": "値"}}]

情報なし→[]

⚠️ 最終確認：
1. 回答(A:)に書かれている情報のみを抽出していますか？
2. ⚠️ 「その他」などの無意味なサブカテゴリーを作っていませんか？（適切な名前がなければ省略）
3. 情報の詳細度に応じて適切な階層数（2〜5階層）を選択していますか？
4. ⚠️⚠️⚠️ 同じトピック（ゲーム、スポーツなど）は全て同じsubcategory1を使用していますか？
5. subcategory1に「趣味」「興味」などの抽象的な名前を使っていませんか？（具体的なトピック名を使用）
6. 複数の項目がある場合、個別に分割していますか？
7. 「と」「、」などのセパレーターを含む値を出力していませんか？（含んでいたら分割し直してください）"""

        return prompt

    def _split_multiple_items(self, extracted_data: List[Dict]) -> List[Dict]:
        """
        セパレーターを含む値を自動分割
        LLMが分割していない場合でも、バックエンドで確実に分割する
        """
        result = []
        # スペースを除外（固有名詞「イーロンマスク」「旧twitterX」などを保護）
        separators = ['、', '，', 'と', ',', '・']

        for item in extracted_data:
            value = str(item.get('value', '')).strip()

            # 空の値はスキップ
            if not value:
                continue

            # 名前関連のフィールドは分割しない（固有名詞として扱う）
            key = item.get('key', '').lower()
            category = item.get('category', '')
            is_name_field = (
                key in ['名前', '氏名', 'name', 'なまえ'] or
                (category == '基本プロフィール' and '名前' in key)
            )

            if is_name_field:
                # 名前は分割せずそのまま追加
                result.append(item)
                continue

            # セパレーターを含むかチェック
            contains_separator = any(sep in value for sep in separators)

            if contains_separator:
                # セパレーターで分割
                log_extract.debug(f" Auto-splitting: '{value}'")
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
                        log_extract.debug(f"   → Split item: '{part}'")
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
                    log_extract.debug(f" Partial match accepted: '{value}' (match ratio: {match_ratio:.1%})")
                    filtered.append(item)
                    continue

            # ユーザーメッセージに含まれていない
            log_extract.debug(f" Value '{value}' not found in user message '{user_message}'")
            log_extract.debug(f" Rejected (not in user message): {item}")

        return filtered

    def _parse_extracted_data(self, text: str) -> List[Dict]:
        """抽出されたテキストからJSONデータをパース"""
        try:
            log_extract.debug(f" Parsing text: {text[:500]}")

            # JSONブロックを抽出
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                log_extract.debug(f" JSON string: {json_str[:300]}")

                data = json.loads(json_str)

                # バリデーション
                valid_data = []
                for item in data:
                    if not isinstance(item, dict):
                        log_extract.debug(f" Invalid item (not dict): {item}")
                        continue

                    if not all(k in item for k in ["category", "key", "value"]):
                        log_extract.debug(f" Invalid item (missing keys): {item}")
                        continue

                    if item["category"] not in CATEGORIES:
                        log_extract.debug(f" Invalid category: {item['category']}")
                        continue

                    # 不正な値をフィルタリング
                    value = str(item["value"]).strip()
                    if not value:
                        log_extract.debug(f" Invalid item (empty value): {item}")
                        continue

                    # 不正な値パターン
                    invalid_patterns = ["[]", "{}", "()", "null", "none", "undefined"]
                    if value.lower() in invalid_patterns:
                        log_extract.debug(f" Invalid item (invalid value pattern): {item}")
                        continue

                    # 長さ1文字以下の記号のみは除外（ただし数字とひらがな・カタカナ・漢字は許可）
                    if len(value) <= 1 and not value.isalnum():
                        log_extract.debug(f" Invalid item (single symbol): {item}")
                        continue

                    # 有効なデータとして追加
                    valid_data.append(item)

                return valid_data
            else:
                log_extract.debug(f" No JSON array found in text")
                return []
        except json.JSONDecodeError as e:
            log_extract.debug(f" JSON parse error: {e}")
            log_extract.debug(f" Problematic text: {text[:500]}")
            return []
        except Exception as e:
            log_extract.debug(f" Parse error: {e}")
            return []

    def detect_correction(self, user_message: str, conversation_history: List[Dict]) -> bool:
        """
        ユーザーが前の回答を訂正しているかどうかを検出
        Detect if the user is correcting their previous response

        重要: 現在のユーザーメッセージに訂正キーワードが含まれている場合のみ訂正と判定
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
                log_correction.debug(f"Detected correction keyword in user message: {keyword}")
                return True

        # 訂正キーワードがない場合は訂正ではない
        # 注意: 以前の実装では会話履歴の「承知しました」などで判定していたが、
        # これは誤検出の原因となるため削除
        return False

    def detect_deletion_request(self, user_message: str) -> bool:
        """
        ユーザーが前の回答の削除を要求しているかどうかを検出
        Detect if the user is requesting to delete their previous response

        重要: 削除キーワードとターゲットキーワードの両方が必須
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

        # 対象キーワードが含まれているかチェック
        has_target_keyword = any(keyword in user_message_lower for keyword in target_keywords)

        # 削除リクエストと判定するには、削除キーワードとターゲットキーワードの両方が必要
        # 注意: 以前は「短いメッセージ」でも判定していたが、誤検出の原因となるため削除
        if has_deletion_keyword and has_target_keyword:
            log_correction.info(f"Detected deletion request in message: {user_message}")
            return True

        return False

