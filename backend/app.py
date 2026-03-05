"""
Flask メインアプリケーション: REST API エンドポイント
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import threading

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(__file__))

from profile_manager import ProfileManager
from interviewer import Interviewer
from gamification import GamificationManager
from config import CHARACTERS, BADGES, RANDOM_EVENTS, INTERVIEW_COURSES, merge_courses
from logger import get_logger

# ロガー初期化
log_system = get_logger('System')
log_api = get_logger('API')
log_data = get_logger('Data')
log_async = get_logger('Async')
log_correction = get_logger('Correction')
log_undo = get_logger('Undo')

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# マネージャーインスタンス
profile_manager = ProfileManager()
interviewer = Interviewer()
gamification = GamificationManager()


@app.route('/')
def index():
    """メインページ"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    from config import LM_STUDIO_MODEL
    lm_studio_connected = interviewer.check_lm_studio_connection()
    return jsonify({
        'status': 'ok',
        'lm_studio': 'connected' if lm_studio_connected else 'disconnected',
        'model': LM_STUDIO_MODEL
    })


@app.route('/api/version', methods=['GET'])
def get_version():
    """バージョン情報を取得"""
    return jsonify({
        'backend_version': '5.0',
        'data_structure_version': '5.0',
        'description': '5階層データ構造対応'
    })


@app.route('/api/characters', methods=['GET'])
def get_characters():
    """キャラクター一覧を取得"""
    return jsonify(CHARACTERS)


@app.route('/api/courses', methods=['GET'])
def get_courses():
    """ヒアリングコース一覧を取得"""
    return jsonify(INTERVIEW_COURSES)


@app.route('/api/user/create', methods=['POST'])
def create_user():
    """新規ユーザーを作成"""
    data = request.json
    name = data.get('name', '名無し')
    gender = data.get('gender', 'その他')

    # 性別からキャラクターを選択（修正版）
    character_map = {
        '男性': 'kenta',      # 青山（男性キャラ）
        '女性': 'misaki',     # つむぎ（女性キャラ）
        'その他': 'aoi'        # ずんだもん（中性的）
    }
    character = character_map.get(gender, 'aoi')

    # ユーザー作成
    profile = profile_manager.create_user(name, gender, character)

    return jsonify({
        'success': True,
        'user_id': profile['user_id'],
        'profile': profile
    })


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """ユーザープロファイルを取得"""
    profile = profile_manager.get_user(user_id)
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    # カテゴリー別データ数を取得
    category_counts = profile_manager.get_category_data_count(user_id)

    # 総データ数を計算してプロファイルに追加（リアルタイム計算）
    profile['total_data_count'] = sum(category_counts.values())

    return jsonify({
        'profile': profile,
        'category_counts': category_counts
    })


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """新規セッションを作成"""
    data = request.json
    user_id = data.get('user_id')

    # 複数コース対応: course_ids(配列) または course_id(後方互換)
    course_ids = data.get('course_ids')
    if not course_ids:
        single = data.get('course_id', 'basic_info')
        course_ids = [single]

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    # コース検証
    for cid in course_ids:
        if cid not in INTERVIEW_COURSES:
            return jsonify({'error': f'Invalid course_id: {cid}'}), 400

    # プロファイル確認
    profile = profile_manager.get_user(user_id)
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    # セッション作成
    session = profile_manager.create_session(user_id)

    # コース設定をマージしてセッションに保存
    course_config = merge_courses(course_ids)
    session['course_ids'] = course_ids
    session['course_id'] = course_ids[0]  # 後方互換
    session['course'] = course_config
    profile_manager.update_session(session['session_id'], session)

    # 挨拶メッセージ
    character_id = profile['character']
    user_name = profile.get('name')
    if user_name == '名無し':
        user_name = None
    greeting = interviewer.generate_greeting(character_id, user_name)
    first_question = interviewer.generate_first_question(character_id)

    combined_message = f"{greeting}\n{first_question}"
    profile_manager.add_message(session['session_id'], 'assistant', combined_message, 'smile')

    # ランダムイベントチェック（コースが許可している場合のみ）
    event = None
    if course_config.get('enable_random_events', True):
        event = gamification.should_trigger_event()
        if event:
            session['events_triggered'].append(event['name'])
            profile_manager.update_session(session['session_id'], session)

    session = profile_manager.get_session(session['session_id'])

    return jsonify({
        'success': True,
        'session': session,
        'event': event,
        'course': course_config
    })


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """セッションを取得"""
    session = profile_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({'session': session})


def _calc_progress(session, course_config, category_counts):
    """進捗データを計算して返す（フロントのプログレスバー用）"""
    target_cats = course_config.get('target_categories', [])
    phases = []

    if '基本プロフィール' in target_cats:
        covered = len(interviewer._get_covered_basic_fields(session))
        phases.append({'label': '基本情報', 'icon': '👤', 'current': min(covered, 5), 'total': 5})

    question_topics = course_config.get('question_topics', [])
    non_basic = [c for c in target_cats if c != '基本プロフィール']
    if non_basic:
        name = course_config.get('name', 'ヒアリング')
        icon = course_config.get('icon', '💬')
        if question_topics:
            # スクリプト式コース: 質問数ベースで進捗を計算
            total = len(question_topics)
            current = min(session.get('course_question_index', 0), total)
            phases.append({'label': name, 'icon': icon, 'current': current, 'total': total})
        else:
            # フリーフォームコース: 抽出データ件数ベース（旧方式）
            current = sum(category_counts.get(c, 0) for c in non_basic)
            threshold = course_config.get('completion_threshold', len(non_basic) * 4)
            if '基本プロフィール' in target_cats:
                threshold = max(threshold - 5, len(non_basic) * 3)
            phases.append({'label': name, 'icon': icon, 'current': min(current, threshold), 'total': threshold})

    return phases


@app.route('/api/chat', methods=['POST'])
def chat():
    """チャットメッセージを送信"""
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')
    force_finish = data.get('force_finish', False)

    if not session_id or not user_message:
        return jsonify({'error': 'session_id and message required'}), 400

    # セッション取得（1回のみ）
    session = profile_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # ユーザー取得
    user_id = session['user_id']
    profile = profile_manager.get_user(user_id)
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    # 強制終了リクエスト（フロントの「終了する」ボタン）
    if force_finish:
        finish_msg = "ありがとうございました！ヒアリングを終了します😊 教えていただいた内容はしっかり活用させていただきます。"
        profile_manager.add_message(session_id, 'user', user_message)
        profile_manager.add_message(session_id, 'assistant', finish_msg, 'smile')
        profile_manager.update_session(session_id, {'basic_info_phase_done': True})
        course_ids_f = session.get('course_ids') or [session.get('course_id', 'basic_info')]
        course_config_f = merge_courses(course_ids_f)
        category_counts_f = profile_manager.get_category_data_count(user_id)
        return jsonify({
            'success': True,
            'response': finish_msg,
            'expression': 'smile',
            'reaction': 'none',
            'badges': [],
            'profile': profile,
            'correction_detected': False,
            'force_finished': True,
            'progress': _calc_progress(session, course_config_f, category_counts_f)
        })

    # 削除リクエスト検出（「今の削除して」「やめます」など）
    is_deletion_request = interviewer.detect_deletion_request(user_message)

    if is_deletion_request:
        log_correction.info("User requested deletion - auto-undoing last turn")
        # 前のターンを自動的に取り消す
        undo_result = profile_manager.undo_last_turn(session_id)

        if undo_result['success']:
            log_correction.info(f"Auto-undo successful, removed {undo_result['removed_data_count']} data points")

            # 更新されたプロファイルを取得
            profile = profile_manager.get_user(user_id)

            # 削除リクエストメッセージ自体は保存せず、確認メッセージのみ返す
            return jsonify({
                'success': True,
                'response': '承知しました！前の回答を削除しました。',
                'expression': 'smile',
                'reaction': 'none',
                'badges': [],
                'profile': profile,
                'deletion_request': True,  # 削除リクエストフラグ
                'removed_count': undo_result['removed_data_count']
            })
        else:
            return jsonify({
                'success': False,
                'error': undo_result['message']
            }), 400

    # 訂正検出（ユーザーが前の回答を訂正している場合）
    is_correction = interviewer.detect_correction(user_message, session['conversation'])

    if is_correction:
        log_correction.info("User is correcting previous response - auto-undoing last turn")
        # 前のターンを自動的に取り消す
        undo_result = profile_manager.undo_last_turn(session_id)
        if undo_result['success']:
            log_correction.info(f"Auto-undo successful, removed {undo_result['removed_data_count']} data points")
        else:
            log_correction.warning(f"Auto-undo failed: {undo_result['message']}")

    # ユーザーメッセージを保存
    profile_manager.add_message(session_id, 'user', user_message)

    # セッションを再取得（ユーザーメッセージが追加された最新の状態を取得）
    session = profile_manager.get_session(session_id)

    # メッセージ分析
    message_analysis = gamification.analyze_message_for_data(user_message)

    # リアクション判定
    reaction_tier = gamification.determine_reaction(user_message, message_analysis)

    # セッションにリアクション記録
    if reaction_tier != "none":
        session['reactions'][reaction_tier] = session['reactions'].get(reaction_tier, 0) + 1
        profile_manager.update_session(session_id, session)

    # 表情選択
    expression = gamification.get_expression_for_reaction(reaction_tier, message_analysis)

    # カテゴリー別データ数と空カテゴリーを取得
    category_counts = profile_manager.get_category_data_count(user_id)
    empty_categories = profile_manager.get_empty_categories(user_id)

    # 会話履歴を構築（最新のsessionオブジェクトを使用）
    messages = []
    greeting_already_sent = False
    for i, msg in enumerate(session['conversation']):
        role = msg['role']
        content = msg['content']

        # 最初のメッセージがassistantの場合はスキップ（LM Studioは user から始まる必要がある）
        if i == 0 and role == 'assistant':
            log_api.debug("Skipping first assistant message for LM Studio compatibility")
            greeting_already_sent = True
            continue

        messages.append({'role': role, 'content': content})

    # LM Studioからレスポンス取得
    log_api.debug(f"Calling get_response with {len(messages)} messages, character: {profile['character']}")
    log_api.debug(f"Category counts: {category_counts}, Empty categories: {empty_categories}")

    # コース情報を取得（複数コース対応）
    course_ids = session.get('course_ids') or [session.get('course_id', 'basic_info')]
    course_config = merge_courses(course_ids)

    # === 基本プロフィールを含む全コース: 基本情報フェーズ処理 ===
    target_categories = course_config.get('target_categories', [])
    is_basic_only = (target_categories == ['基本プロフィール'])
    basic_phase_done = session.get('basic_info_phase_done', False)

    # === 全コース共通: 基本プロフィールなしコースも名前だけ収集 ===
    if '基本プロフィール' not in target_categories and not basic_phase_done:
        last_field = interviewer._get_last_asked_field(session)
        if last_field == '名前':
            validation = interviewer._validate_basic_field_answer('名前', user_message)
            if validation['valid']:
                clean_name = interviewer._clean_saved_value('名前', user_message)
                try:
                    profile_manager.add_extracted_data(
                        session_id, '基本プロフィール', '名前', clean_name, subcategory1='名前')
                    log_data.info(f"[name_only] Saved name for non-basic course: {clean_name}")
                except Exception as e:
                    log_data.error(f"[name_only] Error saving name: {e}")
        profile_manager.update_session(session_id, {'basic_info_phase_done': True})
        log_api.info(f"[name_only] Name phase done, proceeding to LLM for course={course_ids}")
        # Fall through to LLM

    if '基本プロフィール' in target_categories and not basic_phase_done:
        next_basic_field = interviewer._get_next_basic_field(session)
        is_collecting = (next_basic_field is not None)

        if is_collecting or is_basic_only:
            # スクリプト処理（収集中 or basic_infoコース完了時の締め括り）
            scripted = interviewer.generate_basic_info_response(session, user_message, course_config)
            assistant_response = scripted['response']
            expression = 'smile'
            log_api.info(f"[basic_info_phase] course={course_ids}, next={next_basic_field}, reask={scripted['reask']}, response={assistant_response[:60]}")
            profile_manager.add_message(session_id, 'assistant', assistant_response, expression)

            # スクリプトが検証済みフィールドを直接保存（LLM抽出は使わない → 誤抽出防止）
            saved = scripted.get('saved_field')
            if saved and not scripted['reask']:
                _field_to_key = {
                    '名前': ('名前', '名前'),
                    '年齢': ('年齢', '年齢'),
                    '性別': ('性別', '性別'),
                    '職業': ('職業名', '職業'),
                    '家族構成': ('家族構成', '家族構成'),
                }
                data_key, subcat = _field_to_key.get(saved, (saved, saved))
                try:
                    profile_manager.add_extracted_data(
                        session_id, '基本プロフィール', data_key,
                        scripted.get('saved_value', user_message),
                        subcategory1=subcat)
                    log_data.info(f"[basic_info] Saved directly: {data_key} = {scripted.get('saved_value')}")
                except Exception as e:
                    log_data.error(f"[basic_info] Direct save error: {e}")

            # basic_infoコースの完了時にフラグをセット
            if is_basic_only and next_basic_field is None and not scripted['reask']:
                profile_manager.update_session(session_id, {'basic_info_phase_done': True})
                log_api.info(f"[basic_info_phase] Completed and flagged done")

            # セッションを再取得して進捗を計算（直接保存後の最新状態）
            session_after = profile_manager.get_session(session_id)
            profile = profile_manager.get_user(user_id)
            return jsonify({
                'success': True,
                'response': assistant_response,
                'expression': expression,
                'reaction': 'none',
                'badges': [],
                'profile': profile,
                'correction_detected': False,
                'progress': _calc_progress(session_after or session, course_config, category_counts)
            })
        else:
            # 他コース: basic_info完了 → LLMフェーズへ（トピックインデックスを0から開始）
            if session.get('course_question_index') is None:
                profile_manager.update_session(session_id, {'course_question_index': 0})
            log_api.info(f"[basic_info_phase] Basic info complete, switching to LLM for course={course_ids}")

    # コースのターゲットカテゴリーの収集数合計（完了判定用）
    target_cats = course_config.get('target_categories', [])
    course_total_count = sum(category_counts.get(cat, 0) for cat in target_cats)

    # === スクリプト式トピック誘導: 現在のトピックを取得してインデックスを進める ===
    question_topics = course_config.get('question_topics', [])
    course_q_idx = session.get('course_question_index', 0)
    forced_topic = question_topics[course_q_idx] if course_q_idx < len(question_topics) else None

    # === スクリプト全問完了時: LLMを呼ばず即座に完了メッセージを返す ===
    if question_topics and forced_topic is None:
        course_name = course_config.get('name', '')
        finish_msg = f"以上で{course_name}のヒアリングは全て完了です😊 教えていただいた内容はしっかり活用させていただきます！"
        profile_manager.add_message(session_id, 'assistant', finish_msg, 'smile')
        # 最後の回答からもデータ抽出をバックグラウンドで実行
        def _extract_final():
            try:
                updated_session = profile_manager.get_session(session_id)
                extracted_data = interviewer.extract_profile_data(
                    user_message, finish_msg, updated_session['conversation'],
                    course_config=course_config
                )
                for dp in extracted_data:
                    profile_manager.add_extracted_data(
                        session_id, dp['category'], dp['key'], dp['value'],
                        subcategory1=dp.get('subcategory1'), subcategory2=dp.get('subcategory2')
                    )
            except Exception as e:
                log_async.error(f"Error in final extraction: {e}", exc_info=True)
        threading.Thread(target=_extract_final, daemon=True).start()
        category_counts_now = profile_manager.get_category_data_count(user_id)
        log_api.info(f"[topic_script] All {len(question_topics)} topics done → completion message sent")
        return jsonify({
            'success': True,
            'response': finish_msg,
            'expression': 'smile',
            'reaction': 'none',
            'badges': [],
            'profile': profile,
            'correction_detected': False,
            'force_finished': True,
            'progress': _calc_progress(session, course_config, category_counts_now)
        })

    if forced_topic is not None:
        profile_manager.update_session(session_id, {'course_question_index': course_q_idx + 1})
        log_api.info(f"[topic_script] topic[{course_q_idx}] → {forced_topic[:50]}")

    try:
        assistant_response = interviewer.get_response(
            messages,
            profile['character'],
            profile,
            category_counts,
            empty_categories,
            greeting_already_sent=greeting_already_sent,
            session_data=session,
            course_config=course_config,
            course_total_count=course_total_count,
            forced_topic=forced_topic
        )
        log_api.debug(f"get_response returned: {'OK' if assistant_response else 'EMPTY/NONE'}")
    except Exception as e:
        log_api.error(f"get_response failed with exception: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'LM Studioとの接続でエラーが発生しました。LM Studioが起動しているか確認してください。'
        }), 503

    if not assistant_response:
        log_api.error("No response from LM Studio")
        # LM Studio接続確認
        if not interviewer.check_lm_studio_connection():
            return jsonify({
                'success': False,
                'error': 'LM Studioとの接続が切れました。LM Studioが起動しているか確認してください。'
            }), 503
        else:
            return jsonify({
                'success': False,
                'error': 'LM Studioから応答がありませんでした。モデルが読み込まれているか確認してください。'
            }), 500

    # === スクリプト質問をLLM相槌の後に直接連結 ===
    # LLMが相槌だけ生成し、実際の質問文はバックエンドが確実に追記する
    if forced_topic:
        # LLMが質問文を混入させていた場合は除去して相槌のみ残す
        ack = assistant_response.strip()
        # 「？」で終わる文が混入していれば手前まで切り捨て
        if '？' in ack:
            ack = ack[:ack.index('？')].rsplit('。', 1)[0].rsplit('！', 1)[0].strip()
        if not ack:
            import random
            ack = random.choice(['なるほど！', 'そうなんですね。', 'わかりました！', 'たしかに！', 'それはいいですね！'])
        # TTS対応: ackが句読点で終わっていない場合は補完する
        if ack and ack[-1] not in ('。', '！', '？', '、'):
            ack += '。'
        assistant_response = f"{ack}\n{forced_topic}"
        log_api.info(f"[topic_script] Final response: ack='{ack}' + question='{forced_topic[:40]}'")

    # アシスタントメッセージを保存
    profile_manager.add_message(session_id, 'assistant', assistant_response, expression)

    # バッジチェック（軽量処理なので同期的に実行）
    # 🔧 DEBUG: 一時的に無効化してデータ抽出をテスト
    newly_earned_badges = []  # gamification.check_badges(profile, message_analysis)
    # for badge_name in newly_earned_badges:
    #     profile_manager.add_badge(user_id, badge_name)

    # 更新されたプロファイルを取得
    profile = profile_manager.get_user(user_id)

    # 🚀 非同期処理: データ抽出をバックグラウンドで実行
    def extract_data_async():
        """バックグラウンドでデータ抽出を実行"""
        try:
            # 最新のセッションデータを取得
            updated_session = profile_manager.get_session(session_id)

            # UNDOされていないか確認（undoされるとassistant_responseがconversationから消える）
            conv = updated_session.get('conversation', [])
            asst_msgs = [m for m in conv if m.get('role') == 'assistant']
            if not asst_msgs or asst_msgs[-1].get('content') != assistant_response:
                log_async.info(f"Skipping extraction: turn was undone (session={session_id})")
                return

            # プロファイリングデータ抽出
            extracted_data = interviewer.extract_profile_data(
                user_message,
                assistant_response,
                updated_session['conversation'],
                course_config=course_config
            )

            # 抽出したデータを保存（5階層対応）
            for data_point in extracted_data:
                try:
                    # subcategory1とsubcategory2を取得
                    subcategory1 = data_point.get('subcategory1')
                    subcategory2 = data_point.get('subcategory2')
                    profile_manager.add_extracted_data(
                        session_id,
                        data_point['category'],
                        data_point['key'],
                        data_point['value'],
                        subcategory1=subcategory1,
                        subcategory2=subcategory2
                    )
                    # パス表示用
                    path_parts = [data_point['category']]
                    if subcategory1:
                        path_parts.append(subcategory1)
                    if subcategory2:
                        path_parts.append(subcategory2)
                    path_parts.append(data_point['key'])
                    path_str = " > ".join(path_parts)
                    log_data.info(f"Saved: {path_str} = {data_point['value']}")
                except Exception as e:
                    log_data.error(f"Error saving data point: {e}")

            log_async.info(f"Data extraction completed for session {session_id}")
        except Exception as e:
            log_async.error(f"Error in background data extraction: {e}", exc_info=True)

    # バックグラウンドスレッドでデータ抽出を開始
    extraction_thread = threading.Thread(target=extract_data_async, daemon=True)
    extraction_thread.start()
    log_async.debug(f"Started background data extraction for session {session_id}")

    # すぐにレスポンスを返す（データ抽出の完了を待たない）
    return jsonify({
        'success': True,
        'response': assistant_response,
        'expression': expression,
        'reaction': reaction_tier,
        'badges': newly_earned_badges,
        'profile': profile,
        'correction_detected': is_correction,
        'progress': _calc_progress(session, course_config, category_counts)
    })


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """edge-tts による音声合成（無料・APIキー不要）"""
    import asyncio
    import base64
    import edge_tts

    data = request.json
    text = data.get('text', '')
    character = data.get('character', 'aoi')

    if not text:
        return jsonify({'error': 'text required'}), 400

    # キャラクター別音声（Microsoft Edge Neural 音声）
    voice_map = {
        'misaki': {'voice': 'ja-JP-NanamiNeural', 'rate': '+20%'},
        'kenta':  {'voice': 'ja-JP-KeitaNeural',  'rate': '+30%'},
        'aoi':    {'voice': 'ja-JP-NanamiNeural', 'rate': '+20%'},
    }
    v = voice_map.get(character, voice_map['aoi'])

    async def _synth():
        communicate = edge_tts.Communicate(text, v['voice'], rate=v['rate'])
        audio_data = b''
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_data += chunk['data']
        return audio_data

    def _run_in_thread():
        """gunicornとasyncioの競合を避けるため専用スレッドで実行"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_synth())
        finally:
            loop.close()

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_thread)
            audio_data = future.result(timeout=15)
    except Exception as e:
        log_api.error(f'edge-tts failed: {e}', exc_info=True)
        return jsonify({'error': 'TTS failed', 'detail': str(e)}), 502

    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
    return jsonify({'audioContent': audio_b64})


@app.route('/api/session/<session_id>/export', methods=['GET'])
def export_session(session_id):
    """セッションデータをJSONファイルとしてダウンロード"""
    session = profile_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    response = jsonify(session)
    response.headers['Content-Disposition'] = \
        f'attachment; filename="session_{session_id[:8]}.json"'
    return response


@app.route('/api/badges', methods=['GET'])
def get_badges():
    """バッジ一覧を取得"""
    return jsonify(BADGES)


@app.route('/api/events', methods=['GET'])
def get_events():
    """ランダムイベント一覧を取得"""
    return jsonify(RANDOM_EVENTS)


@app.route('/api/undo', methods=['POST'])
def undo_last_turn():
    """最後のやりとりを取り消す"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    try:
        result = profile_manager.undo_last_turn(session_id)

        if not result['success']:
            return jsonify(result), 400

        # 更新されたプロファイルを取得
        session = result['session']
        profile = profile_manager.get_user(session['user_id'])

        return jsonify({
            'success': True,
            'message': result['message'],
            'removed_data_count': result['removed_data_count'],
            'session': session,
            'profile': profile
        })

    except Exception as e:
        log_undo.error(f"Undo failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    log_system.info("=" * 50)
    log_system.info("Interview System Backend Starting...")
    log_system.info("=" * 50)
    log_system.info(f"LM Studio URL: {interviewer.lm_studio_url}")
    log_system.info("Checking LM Studio connection...")

    if interviewer.check_lm_studio_connection():
        log_system.info("✓ LM Studio is connected!")
    else:
        log_system.warning("✗ LM Studio is NOT connected!")
        log_system.warning("Please start LM Studio at http://localhost:1234")

    log_system.info("=" * 50)
    log_system.info("Server starting at http://localhost:5001")
    log_system.info("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5001)
