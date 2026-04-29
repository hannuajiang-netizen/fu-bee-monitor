from flask import Blueprint, request, jsonify
import pandas as pd
import io
import os
from datetime import datetime
from utils.excel_parser import read_excel_file, normalize_columns, format_percentage, format_number, find_column
from utils.calculator import calculate_weekly_metrics

task1_bp = Blueprint('task1', __name__)

# 25个字段的定义
TASK1_COLUMNS = [
    ('日期', '用户基本情况'),
    ('活跃用户数', '用户基本情况'),
    ('人均停留时长(分钟)', '用户基本情况'),
    ('互动次数', '用户基本情况'),
    ('互动人数', '用户基本情况'),
    ('互动人数占比', '用户基本情况'),
    ('分享人数', '用户基本情况'),
    ('关注人数', '用户基本情况'),
    ('次日留存率', '用户基本情况'),
    ('3留率', '用户基本情况'),
    ('7留率', '用户基本情况'),
    ('14留率', '用户基本情况'),
    ('30日留率', '用户基本情况'),
    ('当日发布笔记量', '内容生产情况'),
    ('当日发布笔记用户数', '内容生产情况'),
    ('累计发布笔记量', '内容生产情况'),
    ('累计发布笔记用户数', '内容生产情况'),
    ('活跃在群用户数', '用户基本情况'),
    ('群活跃用户数', '用户基本情况'),
    ('群发言用户数', '用户基本情况'),
    ('活跃在蜂巢用户数', '用户基本情况'),
    ('蜂巢活跃用户数', '用户基本情况'),
    ('发布蜂巢笔记用户数', '用户基本情况或内容生产情况'),
    ('预留1', '—'),
    ('预留2', '—'),
]


@task1_bp.route('/analyze', methods=['POST'])
def analyze():
    """任务一：校园认证用户DAU监控分析"""
    
    # 检查文件
    if 'user_basic' not in request.files:
        return jsonify({'error': '缺少用户基本情况文件'}), 400
    if 'content_produce' not in request.files:
        return jsonify({'error': '缺少内容生产情况文件'}), 400
    if 'school_detail' not in request.files:
        return jsonify({'error': '缺少累计单校情况文件'}), 400
    
    try:
        # 读取文件
        user_basic_file = request.files['user_basic']
        content_produce_file = request.files['content_produce']
        school_detail_file = request.files['school_detail']
        
        # 保存上传的文件
        upload_dir = f"./uploads/{datetime.now().strftime('%Y-%m-%d')}/task1"
        os.makedirs(upload_dir, exist_ok=True)
        
        user_basic_path = os.path.join(upload_dir, user_basic_file.filename)
        content_produce_path = os.path.join(upload_dir, content_produce_file.filename)
        school_detail_path = os.path.join(upload_dir, school_detail_file.filename)
        
        user_basic_file.save(user_basic_path)
        content_produce_file.save(content_produce_path)
        school_detail_file.save(school_detail_path)
        
        # 读取Excel
        df_user = read_excel_file(open(user_basic_path, 'rb').read())
        df_content = read_excel_file(open(content_produce_path, 'rb').read())
        df_school = read_excel_file(open(school_detail_path, 'rb').read())
        
        # 标准化列名
        df_user = normalize_columns(df_user)
        df_content = normalize_columns(df_content)
        df_school = normalize_columns(df_school)
        
        # 调试：打印列名
        print("DEBUG - 用户基本情况列名:", df_user.columns.tolist())
        print("DEBUG - 内容生产情况列名:", df_content.columns.tolist())
        
        # 解析日期
        df_user['日期'] = pd.to_datetime(df_user['日期'])
        df_content['日期'] = pd.to_datetime(df_content['日期'])
        
        # 生成14天汇总表
        summary_table = generate_summary_table(df_user, df_content)
        
        # 生成周报文本
        weekly_report = generate_weekly_report(df_user, df_content, df_school)
        
        return jsonify({
            'success': True,
            'summary_table': summary_table,
            'weekly_report': weekly_report
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_summary_table(df_user: pd.DataFrame, df_content: pd.DataFrame) -> list:
    """生成近14天汇总表"""
    
    # 合并数据
    merged = df_user.merge(df_content, on='日期', how='left', suffixes=('', '_c'))
    merged = merged.sort_values('日期', ascending=False)
    
    # 取近14天
    latest_date = merged['日期'].max()
    date_14_days_ago = latest_date - pd.Timedelta(days=13)
    recent_data = merged[merged['日期'] >= date_14_days_ago]
    recent_data = recent_data.sort_values('日期', ascending=True)
    
    # 构建结果
    result = []
    for _, row in recent_data.iterrows():
        record = {}
        
        # 日期
        record['日期'] = row['日期'].strftime('%Y-%m-%d')
        
        # 从用户基本情况获取的字段（支持多种可能的列名）
        # 格式: '输出字段名': {'input': [可能的输入列名], 'output': '输出时显示的列名'}
        user_field_mappings = {
            '活跃用户数': {'input': ['活跃用户数', '活跃用户', 'DAU', 'dau'], 'output': '活跃用户数'},
            '人均停留时长(分钟)': {'input': ['人均停留时长(分钟)', '人均停留时长', '平均停留时长', '停留时长'], 'output': '人均停留时长min'},
            '互动次数': {'input': ['互动次数', '互动量'], 'output': '互动次数'},
            '互动人数': {'input': ['互动人数'], 'output': '互动人数'},
            '互动人数占比': {'input': ['互动人数占比', '互动占比'], 'output': '互动人数占比'},
            '分享人数': {'input': ['分享人数'], 'output': '分享人数'},
            '关注人数': {'input': ['关注人数'], 'output': '关注人数'},
            '次日留存率': {'input': ['次日留存率', '次留率', '次日留存'], 'output': '次日留存率'},
            '3留率': {'input': ['3留率', '3日留存率', '三日留存率'], 'output': '3留率'},
            '7留率': {'input': ['7留率', '7日留存率', '七日留存率'], 'output': '7留率'},
            '14留率': {'input': ['14留率', '14日留存率', '十四日留存率'], 'output': '14留率'},
            '30日留率': {'input': ['30日留率', '30日留存率', '三十日留存率'], 'output': '30日留率'},
            '活跃在群用户数': {'input': ['活跃在群用户数', '群活跃用户数'], 'output': '活跃在群用户数'},
            '群活跃用户数': {'input': ['群活跃用户数'], 'output': '群活跃用户数'},
            '群发言用户数': {'input': ['群发言用户数'], 'output': '群发言用户数'},
            '活跃在蜂巢用户数': {'input': ['活跃在蜂巢用户数', '蜂巢活跃用户数'], 'output': '活跃在蜂巢用户数'},
            '蜂巢活跃用户数': {'input': ['蜂巢活跃用户数'], 'output': '蜂巢活跃用户数'},
            '发布蜂巢笔记用户数': {'input': ['发布蜂巢笔记用户数'], 'output': '发布蜂巢笔记用户数'}
        }
        
        for field, mapping in user_field_mappings.items():
            possible_names = mapping['input']
            output_name = mapping['output']
            actual_col = find_column(df_user, possible_names)
            if field == '人均停留时长(分钟)':
                print(f"DEBUG - 查找字段: {field}, 可能的名称: {possible_names}, 实际找到的列: {actual_col}")
            if actual_col and actual_col in row:
                value = row[actual_col]
                if pd.isna(value):
                    record[output_name] = '⚠️ 数据缺失'
                elif '率' in output_name or '占比' in output_name:
                    # 百分比处理
                    if isinstance(value, (int, float)):
                        if value <= 1:
                            value = value * 100
                        record[output_name] = f"{value:.2f}%"
                    else:
                        record[output_name] = str(value)
                else:
                    # 数值处理
                    if isinstance(value, (int, float)):
                        record[output_name] = str(int(value)) if isinstance(value, (int, float)) and value == int(value) else str(value)
                    else:
                        record[output_name] = str(value).replace(',', '')
            else:
                record[output_name] = '⚠️ 数据缺失'
        
        # 从内容生产情况获取的字段
        content_field_mappings = {
            '当日发布笔记量': ['当日发布笔记量', '发布笔记量'],
            '当日发布笔记用户数': ['当日发布笔记用户数', '发布笔记用户数'],
            '累计发布笔记量': ['累计发布笔记量'],
            '累计发布笔记用户数': ['累计发布笔记用户数']
        }
        
        for field, possible_names in content_field_mappings.items():
            actual_col = find_column(df_content, possible_names)
            col_name = actual_col + '_c' if actual_col and actual_col + '_c' in row else actual_col
            if col_name and col_name in row:
                value = row[col_name]
                if pd.isna(value):
                    record[field] = '⚠️ 数据缺失'
                else:
                    record[field] = str(int(value)) if isinstance(value, (int, float)) and value == int(value) else str(value).replace(',', '')
            else:
                record[field] = '⚠️ 数据缺失'
        
        # 发布蜂巢笔记用户数
        if '发布蜂巢笔记用户数' in row:
            value = row['发布蜂巢笔记用户数']
            record['发布蜂巢笔记用户数'] = str(int(value)) if not pd.isna(value) else '⚠️ 数据缺失'
        else:
            record['发布蜂巢笔记用户数'] = '⚠️ 数据缺失'
        
        # 预留字段
        record['预留1'] = ''
        record['预留2'] = ''
        
        result.append(record)
    
    return result


def generate_weekly_report(df_user: pd.DataFrame, df_content: pd.DataFrame, 
                          df_school: pd.DataFrame) -> str:
    """生成周报结论文本"""
    
    metrics = calculate_weekly_metrics(df_user, df_content, df_school)
    
    school_diff = metrics['this_school_count'] - metrics['last_school_count']
    school_diff_str = f"+{school_diff}" if school_diff >= 0 else f"{school_diff}"
    
    report = f"""近一周（{metrics['date_start']}-{metrics['date_end']}）
日均活跃校园认证用户 {metrics['this_avg_dau']}（上周 {metrics['last_avg_dau']}）
人均消费时长 {metrics['this_avg_dur']} min（上周 {metrics['last_avg_dur']}）
次留 {metrics['this_avg_ret']}%（上周 {metrics['last_avg_ret']}%）
日均生产用户数 {metrics['this_avg_prod']}（上周 {metrics['last_avg_prod']}）
日均消费用户数 {metrics['this_avg_cons']}（上周 {metrics['last_avg_cons']}）
覆盖 {metrics['this_school_count']} 所高校（{school_diff_str}）"""
    
    return report