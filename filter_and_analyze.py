#!/usr/bin/env python3
"""
品質フィルタリング付き面接セッション分析スクリプト
Interview Session Analysis Script with Quality Filtering

低品質なセッションを除外して分析を行います。
Filters out low-quality sessions before analysis.
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

# セッションディレクトリ / Session directory
SESSIONS_DIR = Path("data/sessions")
OUTPUT_DIR = Path("analyzed_sessions")

# フィルタリング基準 / Filtering criteria
MIN_USER_MESSAGES = 3  # 最低ユーザーメッセージ数
MIN_EXTRACTED_ITEMS = 1  # 最低抽出データ数（OR条件）
MIN_CONVERSATION_TURNS = 5  # 最低会話ターン数

def load_all_sessions():
    """全セッションファイルを読み込む / Load all session files"""
    sessions = []
    session_files = sorted(SESSIONS_DIR.glob("*.json"))

    print(f"📁 Found {len(session_files)} session files")

    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                sessions.append(session_data)
        except Exception as e:
            print(f"⚠️ Error reading {session_file.name}: {e}")

    return sessions

def calculate_session_quality(session):
    """セッションの品質スコアを計算 / Calculate session quality score"""
    conv = session.get('conversation', [])
    user_messages = [msg for msg in conv if msg.get('role') == 'user']

    extracted = session.get('extracted_data', {})
    total_extracted = sum(len(items) for items in extracted.values())

    # 品質スコア計算
    quality_score = 0
    quality_score += len(user_messages) * 1  # ユーザーメッセージ数
    quality_score += total_extracted * 5  # 抽出データ数（重み大）
    quality_score += len(conv) * 0.5  # 総会話数

    return {
        'session_id': session.get('session_id'),
        'date': session.get('date'),
        'user_messages': len(user_messages),
        'total_messages': len(conv),
        'extracted_items': total_extracted,
        'quality_score': quality_score,
        'session': session
    }

def filter_sessions(sessions, criteria='balanced'):
    """
    セッションをフィルタリング / Filter sessions

    criteria:
        'strict': 厳格な基準（ユーザーメッセージ5以上 AND 抽出データ3以上）
        'balanced': バランス基準（ユーザーメッセージ3以上 OR 抽出データ1以上）
        'minimal': 最小基準（会話が成立しているもの）
    """

    all_quality = [calculate_session_quality(s) for s in sessions]
    all_quality_sorted = sorted(all_quality, key=lambda x: x['quality_score'], reverse=True)

    filtered = []

    if criteria == 'strict':
        filtered = [
            q for q in all_quality_sorted
            if q['user_messages'] >= 5 and q['extracted_items'] >= 3
        ]
    elif criteria == 'balanced':
        filtered = [
            q for q in all_quality_sorted
            if q['user_messages'] >= MIN_USER_MESSAGES or q['extracted_items'] >= MIN_EXTRACTED_ITEMS
        ]
    elif criteria == 'minimal':
        filtered = [
            q for q in all_quality_sorted
            if q['total_messages'] >= MIN_CONVERSATION_TURNS
        ]
    else:
        # デフォルトはバランス基準
        filtered = [
            q for q in all_quality_sorted
            if q['user_messages'] >= MIN_USER_MESSAGES or q['extracted_items'] >= MIN_EXTRACTED_ITEMS
        ]

    return filtered, all_quality_sorted

def analyze_session_distribution(all_quality):
    """セッションの分布を分析 / Analyze session distribution"""

    print("\n📊 セッション品質分布 / Session Quality Distribution")
    print("=" * 70)

    # 日付別の集計
    by_date = defaultdict(list)
    for q in all_quality:
        date_str = q['date'][:10] if q['date'] else 'Unknown'
        by_date[date_str].append(q)

    print("\n日付別セッション数と平均品質スコア:")
    for date in sorted(by_date.keys()):
        sessions = by_date[date]
        avg_score = sum(s['quality_score'] for s in sessions) / len(sessions)
        avg_extracted = sum(s['extracted_items'] for s in sessions) / len(sessions)
        print(f"  {date}: {len(sessions):2d}セッション, "
              f"平均スコア={avg_score:6.1f}, 平均抽出数={avg_extracted:4.1f}")

    # 品質レベル別の分類
    excellent = [q for q in all_quality if q['quality_score'] >= 50]
    good = [q for q in all_quality if 20 <= q['quality_score'] < 50]
    fair = [q for q in all_quality if 5 <= q['quality_score'] < 20]
    poor = [q for q in all_quality if q['quality_score'] < 5]

    print(f"\n品質レベル別:")
    print(f"  🌟 Excellent (スコア≥50): {len(excellent)}セッション")
    print(f"  ✅ Good (20-49): {len(good)}セッション")
    print(f"  ⚠️  Fair (5-19): {len(fair)}セッション")
    print(f"  ❌ Poor (<5): {len(poor)}セッション")

    return {
        'by_date': by_date,
        'excellent': excellent,
        'good': good,
        'fair': fair,
        'poor': poor
    }

def show_filtering_preview(all_quality, filtered_quality):
    """フィルタリング結果のプレビュー / Preview filtering results"""

    print("\n🔍 フィルタリング結果 / Filtering Results")
    print("=" * 70)
    print(f"総セッション数: {len(all_quality)}")
    print(f"フィルタ後: {len(filtered_quality)}")
    print(f"除外数: {len(all_quality) - len(filtered_quality)}")
    print(f"保持率: {len(filtered_quality)/len(all_quality)*100:.1f}%")

    print("\n✅ 保持されるセッション (上位10件):")
    print(f"{'SessionID':<12} {'Date':<12} {'UserMsg':<8} {'Extracted':<10} {'Score':<8}")
    print("-" * 70)
    for q in filtered_quality[:10]:
        session_id_short = q['session_id'][:8]
        date_short = q['date'][:10] if q['date'] else 'Unknown'
        print(f"{session_id_short}... {date_short} "
              f"{q['user_messages']:<8} {q['extracted_items']:<10} {q['quality_score']:<8.1f}")

    excluded = [q for q in all_quality if q not in filtered_quality]
    if excluded:
        print(f"\n❌ 除外されるセッション (最初の10件):")
        print(f"{'SessionID':<12} {'Date':<12} {'UserMsg':<8} {'Extracted':<10} {'Score':<8}")
        print("-" * 70)
        for q in excluded[:10]:
            session_id_short = q['session_id'][:8]
            date_short = q['date'][:10] if q['date'] else 'Unknown'
            print(f"{session_id_short}... {date_short} "
                  f"{q['user_messages']:<8} {q['extracted_items']:<10} {q['quality_score']:<8.1f}")

def analyze_extracted_data(sessions):
    """抽出データを分析 / Analyze extracted data"""

    category_stats = defaultdict(lambda: {
        'total_items': 0,
        'sessions_with_data': 0,
        'unique_keys': set(),
        'all_entries': []
    })

    total_sessions = len(sessions)
    sessions_with_data = 0
    sessions_without_data = 0

    for session_quality in sessions:
        session = session_quality['session']
        extracted = session.get('extracted_data', {})
        has_data = False

        for category, items in extracted.items():
            if items:
                has_data = True
                category_stats[category]['total_items'] += len(items)
                category_stats[category]['sessions_with_data'] += 1

                for item in items:
                    if isinstance(item, dict):
                        key = item.get('key', '')
                        value = item.get('value', '')
                        timestamp = item.get('timestamp', '')

                        category_stats[category]['unique_keys'].add(key)
                        category_stats[category]['all_entries'].append({
                            'key': key,
                            'value': value,
                            'timestamp': timestamp,
                            'session_id': session.get('session_id'),
                            'user_id': session.get('user_id')
                        })

        if has_data:
            sessions_with_data += 1
        else:
            sessions_without_data += 1

    return {
        'category_stats': category_stats,
        'total_sessions': total_sessions,
        'sessions_with_data': sessions_with_data,
        'sessions_without_data': sessions_without_data
    }

def generate_profiling_insights(category_stats):
    """プロファイリングの洞察を生成 / Generate profiling insights"""

    insights = []

    for category, stats in sorted(category_stats.items(),
                                   key=lambda x: x[1]['total_items'],
                                   reverse=True):
        if stats['total_items'] > 0:
            insights.append({
                'category': category,
                'total_items': stats['total_items'],
                'sessions_covered': stats['sessions_with_data'],
                'unique_keys': len(stats['unique_keys']),
                'keys_list': sorted(list(stats['unique_keys'])),
                'sample_entries': stats['all_entries'][:5]
            })

    return insights

def generate_recommendations(analysis_results, filter_type):
    """改善提案を生成 / Generate recommendations"""

    recommendations = []

    category_stats = analysis_results['category_stats']

    # 1. フィルタリング効果
    recommendations.append({
        'type': 'フィルタリング効果 / Filtering Impact',
        'priority': 'INFO',
        'description': f'フィルタリング基準: {filter_type}',
        'details': [
            f"分析対象セッション: {analysis_results['total_sessions']}",
            f"データ抽出成功: {analysis_results['sessions_with_data']}",
            f"抽出率: {analysis_results['sessions_with_data']/analysis_results['total_sessions']*100:.1f}%"
        ]
    })

    # 2. データ品質
    recommendations.append({
        'type': 'データ品質 / Data Quality',
        'priority': 'HIGH',
        'description': '抽出データの品質向上のための提案',
        'details': [
            'keyの命名規則を統一する',
            'データの検証ルールを追加する',
            'タイムスタンプの正確性を確保する',
            '重複データの排除メカニズムを実装する'
        ]
    })

    # 3. カテゴリカバレッジ
    low_coverage = []
    for cat, stats in category_stats.items():
        coverage = (stats['sessions_with_data'] / analysis_results['total_sessions']) * 100
        if 0 < coverage < 50:
            low_coverage.append(f"{cat}: {coverage:.1f}%")

    if low_coverage:
        recommendations.append({
            'type': '低カバレッジカテゴリ / Low Coverage Categories',
            'priority': 'MEDIUM',
            'description': 'カバレッジを向上させるべきカテゴリ',
            'details': low_coverage
        })

    return recommendations

def save_filtered_report(all_quality, filtered_quality, analysis_results,
                        insights, recommendations, filter_type):
    """フィルタリング付きレポートを保存 / Save filtered report"""

    OUTPUT_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # JSONレポート
    report = {
        'generated_at': datetime.now().isoformat(),
        'filter_type': filter_type,
        'filtering_summary': {
            'total_sessions': len(all_quality),
            'filtered_sessions': len(filtered_quality),
            'excluded_sessions': len(all_quality) - len(filtered_quality),
            'retention_rate': f"{len(filtered_quality)/len(all_quality)*100:.1f}%"
        },
        'summary': {
            'total_sessions': analysis_results['total_sessions'],
            'sessions_with_data': analysis_results['sessions_with_data'],
            'sessions_without_data': analysis_results['sessions_without_data'],
            'data_extraction_rate': f"{(analysis_results['sessions_with_data'] / analysis_results['total_sessions'] * 100):.1f}%"
        },
        'category_insights': insights,
        'recommendations': recommendations,
        'filtered_session_ids': [q['session_id'] for q in filtered_quality],
        'excluded_session_ids': [q['session_id'] for q in all_quality if q not in filtered_quality]
    }

    report_file = OUTPUT_DIR / f"filtered_analysis_{filter_type}_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ JSONレポートを保存しました: {report_file}")

    # マークダウンレポート
    md_content = generate_markdown_report(all_quality, filtered_quality,
                                          analysis_results, insights,
                                          recommendations, filter_type)
    md_file = OUTPUT_DIR / f"filtered_analysis_{filter_type}_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"✅ マークダウンレポートを保存しました: {md_file}")

    return report_file, md_file

def generate_markdown_report(all_quality, filtered_quality, analysis_results,
                            insights, recommendations, filter_type):
    """マークダウン形式のレポートを生成 / Generate markdown report"""

    md = []
    md.append("# 面接セッション分析レポート（フィルタリング済）")
    md.append("# Interview Session Analysis Report (Filtered)\n")
    md.append(f"**生成日時 / Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**フィルタリング基準 / Filter Type:** {filter_type}\n")
    md.append("---\n")

    # フィルタリングサマリー
    md.append("## 🔍 フィルタリングサマリー / Filtering Summary\n")
    excluded_count = len(all_quality) - len(filtered_quality)
    retention_rate = len(filtered_quality) / len(all_quality) * 100
    md.append(f"- **総セッション数 / Total Sessions:** {len(all_quality)}")
    md.append(f"- **分析対象 / Analyzed:** {len(filtered_quality)}")
    md.append(f"- **除外 / Excluded:** {excluded_count}")
    md.append(f"- **保持率 / Retention Rate:** {retention_rate:.1f}%\n")

    # データ抽出サマリー
    md.append("## 📊 データ抽出サマリー / Data Extraction Summary\n")
    md.append(f"- **データあり / Sessions with Data:** {analysis_results['sessions_with_data']}")
    md.append(f"- **データなし / Sessions without Data:** {analysis_results['sessions_without_data']}")
    rate = (analysis_results['sessions_with_data'] / analysis_results['total_sessions'] * 100)
    md.append(f"- **抽出率 / Extraction Rate:** {rate:.1f}%\n")

    # カテゴリ別分析
    md.append("## 📋 カテゴリ別分析 / Category Analysis\n")

    for insight in insights:
        md.append(f"### {insight['category']}\n")
        md.append(f"- **抽出アイテム数 / Total Items:** {insight['total_items']}")
        md.append(f"- **カバーするセッション数 / Sessions Covered:** {insight['sessions_covered']}")
        coverage = (insight['sessions_covered'] / analysis_results['total_sessions'] * 100)
        md.append(f"- **カバレッジ / Coverage:** {coverage:.1f}%")
        md.append(f"- **ユニークキー数 / Unique Keys:** {insight['unique_keys']}")
        md.append(f"- **キー一覧 / Keys:** {', '.join(insight['keys_list'])}\n")

        if insight['sample_entries']:
            md.append("**サンプルデータ / Sample Data:**\n")
            for i, entry in enumerate(insight['sample_entries'][:3], 1):
                md.append(f"{i}. **{entry['key']}:** {entry['value']}")
            md.append("")

    # トップセッション
    md.append("## 🌟 トップセッション / Top Sessions\n")
    md.append("| SessionID | Date | UserMsg | Extracted | Score |")
    md.append("|---|---|---|---|---|")

    for q in filtered_quality[:10]:
        session_id_short = q['session_id'][:8]
        date_short = q['date'][:10] if q['date'] else 'Unknown'
        md.append(f"| {session_id_short}... | {date_short} | {q['user_messages']} | {q['extracted_items']} | {q['quality_score']:.1f} |")

    md.append("")

    # 改善提案
    md.append("## 💡 改善提案 / Recommendations\n")

    for rec in recommendations:
        priority_emoji = {
            'CRITICAL': '🔴',
            'HIGH': '🟡',
            'MEDIUM': '🟢',
            'LOW': '⚪',
            'INFO': 'ℹ️'
        }.get(rec['priority'], '⚪')

        md.append(f"### {priority_emoji} {rec['type']} (優先度: {rec['priority']})\n")
        md.append(f"{rec['description']}\n")

        if isinstance(rec['details'], list):
            for detail in rec['details']:
                md.append(f"- {detail}")
        md.append("")

    return "\n".join(md)

def main():
    """メイン処理 / Main process"""

    print("🚀 品質フィルタリング付き面接セッション分析を開始します...")
    print("🚀 Starting interview session analysis with quality filtering...\n")

    # セッション読み込み
    print("📖 セッションファイルを読み込んでいます...")
    sessions = load_all_sessions()
    print(f"✅ {len(sessions)} セッションを読み込みました\n")

    # 品質分析とフィルタリング
    print("🔍 セッション品質を分析しています...")
    filtered_quality, all_quality = filter_sessions(sessions, criteria='balanced')

    # 分布分析
    distribution = analyze_session_distribution(all_quality)

    # フィルタリングプレビュー
    show_filtering_preview(all_quality, filtered_quality)

    # フィルタ後のセッションで分析
    print("\n📊 フィルタリング済みセッションを分析しています...")
    analysis_results = analyze_extracted_data(filtered_quality)
    print("✅ データ分析完了\n")

    # インサイト生成
    print("💡 プロファイリングインサイトを生成しています...")
    insights = generate_profiling_insights(analysis_results['category_stats'])
    print("✅ インサイト生成完了\n")

    # 改善提案生成
    print("📝 改善提案を生成しています...")
    recommendations = generate_recommendations(analysis_results, 'balanced')
    print("✅ 改善提案生成完了\n")

    # レポート保存
    print("💾 レポートを保存しています...")
    report_file, md_file = save_filtered_report(
        all_quality, filtered_quality, analysis_results,
        insights, recommendations, 'balanced'
    )

    print("\n" + "="*70)
    print("🎉 分析完了！ / Analysis Complete!")
    print("="*70)
    print(f"\n📄 レポートファイル:")
    print(f"   - JSON: {report_file}")
    print(f"   - Markdown: {md_file}")
    print("\n")

if __name__ == "__main__":
    main()
