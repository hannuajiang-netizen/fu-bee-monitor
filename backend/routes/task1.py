from flask import Blueprint, request, jsonify
import pandas as pd
import io
import os
from datetime import datetime
from utils.excel_parser import read_excel_file, normalize_columns, format_percentage, format_number, find_column
from utils.calculator import calculate_weekly_metrics, calculate_school_count

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
    
    # 检查文件（支持单个或多个文件上传）
    has_user_basic = 'user_basic' in request.files
    has_content_produce = 'content_produce' in request.files
    has_school_detail = 'school_detail' in request.files
    has_hive_data = 'hive_data' in request.files
    
    if not (has_user_basic or has_content_produce or has_school_detail or has_hive_data):
        return jsonify({'error': '请至少上传1个文件'}), 400
    
    try:
        # 保存上传的文件
        upload_dir = f"./uploads/{datetime.now().strftime('%Y-%m-%d')}/task1"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 初始化空的DataFrame
        df_user = pd.DataFrame()
        df_content = pd.DataFrame()
        df_school = pd.DataFrame()
        df_hive = pd.DataFrame()
        
        # 读取用户基本情况文件
        if has_user_basic:
            user_basic_file = request.files['user_basic']
            user_basic_path = os.path.join(upload_dir, user_basic_file.filename)
            user_basic_file.save(user_basic_path)
            df_user = read_excel_file(open(user_basic_path, 'rb').read())
            df_user = normalize_columns(df_user)
            if '日期' in df_user.columns:
                df_user['日期'] = pd.to_datetime(df_user['日期'])
        
        # 读取内容生产情况文件
        if has_content_produce:
            content_produce_file = request.files['content_produce']
            content_produce_path = os.path.join(upload_dir, content_produce_file.filename)
            content_produce_file.save(content_produce_path)
            df_content = read_excel_file(open(content_produce_path, 'rb').read())
            df_content = normalize_columns(df_content)
            if '日期' in df_content.columns:
                df_content['日期'] = pd.to_datetime(df_content['日期'])
        
        # 读取累计单校情况文件
        if has_school_detail:
            school_detail_file = request.files['school_detail']
            school_detail_path = os.path.join(upload_dir, school_detail_file.filename)
            school_detail_file.save(school_detail_path)
            df_school = read_excel_file(open(school_detail_path, 'rb').read())
            df_school = normalize_columns(df_school)
        
        # 读取蜂巢相关数据文件
        if has_hive_data:
            hive_data_file = request.files['hive_data']
            hive_data_path = os.path.join(upload_dir, hive_data_file.filename)
            hive_data_file.save(hive_data_path)
            df_hive = read_excel_file(open(hive_data_path, 'rb').read())
            df_hive = normalize_columns(df_hive)
            # 蜂巢数据可能使用 'day' 或 '日期' 作为日期列名
            if 'day' in df_hive.columns:
                df_hive = df_hive.rename(columns={'day': '日期'})
                df_hive['日期'] = pd.to_datetime(df_hive['日期'])
            elif '日期' in df_hive.columns:
                df_hive['日期'] = pd.to_datetime(df_hive['日期'])
        
        # 调试：打印列名
        print("DEBUG - 用户基本情况列名:", df_user.columns.tolist() if not df_user.empty else "未上传")
        print("DEBUG - 内容生产情况列名:", df_content.columns.tolist() if not df_content.empty else "未上传")
        print("DEBUG - 蜂巢数据列名:", df_hive.columns.tolist() if not df_hive.empty else "未上传")
        
        # 生成14天汇总表
        summary_table = generate_summary_table(df_user, df_content, df_hive)
        print(f"DEBUG - 生成 {len(summary_table)} 条记录")
        if summary_table:
            print(f"DEBUG - 第一条记录: {summary_table[0]}")
        
        # 生成周报文本
        weekly_report = generate_weekly_report(df_user, df_content, df_school)
        
        return jsonify({
            'success': True,
            'summary_table': summary_table,
            'weekly_report': weekly_report
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


def generate_summary_table(df_user: pd.DataFrame, df_content: pd.DataFrame, df_hive: pd.DataFrame = None) -> list:
    """生成近14天汇总表（支持可选的数据文件）"""
    
    # 确定使用哪个DataFrame作为主数据源
    if not df_user.empty:
        merged = df_user.copy()
    elif not df_content.empty:
        merged = df_content.copy()
    elif df_hive is not None and not df_hive.empty:
        merged = df_hive.copy()
    else:
        return []
    
    # 合并内容生产数据（如果有）
    if not df_content.empty and '日期' in df_content.columns:
        if '日期' in merged.columns:
            merged = merged.merge(df_content, on='日期', how='left', suffixes=('', '_c'))
        else:
            # 如果主数据没有日期列，尝试用行索引合并
            merged = pd.concat([merged, df_content], axis=1)
    
    # 合并蜂巢数据（如果有）
    if df_hive is not None and not df_hive.empty and '日期' in df_hive.columns:
        if '日期' in merged.columns:
            merged = merged.merge(df_hive, on='日期', how='left', suffixes=('', '_hive'))
        else:
            merged = pd.concat([merged, df_hive], axis=1)
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
            '人均停留时长(分钟)': {'input': ['人均停留时长[分钟]', '人均停留时长(分钟)', '人均停留时长', '平均停留时长', '停留时长'], 'output': '人均停留时长min'},
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
        
        # 从内容生产情况获取的字段（输出字段名已修改：量->数，用户数->人数）
        content_field_mappings = {
            '当日发布笔记数': {'input': ['当日发布笔记数', '当日发布笔记量', '发布笔记数', '发布笔记量'], 'output': '当日发布笔记数'},
            '当日发布笔记人数': {'input': ['当日发布笔记人数', '当日发布笔记用户数', '发布笔记人数', '发布笔记用户数'], 'output': '当日发布笔记人数'},
            '累计发布笔记数': {'input': ['累计发布笔记数', '累计发布笔记量'], 'output': '累计发布笔记数'},
            '累计发布笔记人数': {'input': ['累计发布笔记人数', '累计发布笔记用户数'], 'output': '累计发布笔记人数'}
        }
        
        for field, mapping in content_field_mappings.items():
            possible_names = mapping['input']
            output_name = mapping['output']
            actual_col = find_column(df_content, possible_names)
            col_name = actual_col + '_c' if actual_col and actual_col + '_c' in row else actual_col
            if col_name and col_name in row:
                value = row[col_name]
                if pd.isna(value):
                    record[output_name] = '⚠️ 数据缺失'
                else:
                    record[output_name] = str(int(value)) if isinstance(value, (int, float)) and value == int(value) else str(value).replace(',', '')
            else:
                record[output_name] = '⚠️ 数据缺失'
        
        # 从蜂巢数据获取的字段
        hive_field_mappings = {
            '活跃在群用户数': ['活跃在群用户数', '群活跃用户数'],
            '群活跃用户数': ['群活跃用户数'],
            '群发言用户数': ['群发言用户数'],
            '活跃在蜂巢用户数': ['活跃在蜂巢用户数', '蜂巢活跃用户数'],
            '蜂巢活跃用户数': ['蜂巢活跃用户数'],
            '发布蜂巢笔记用户数': ['发布蜂巢笔记用户数']
        }
        
        for field, possible_names in hive_field_mappings.items():
            # 先尝试从合并后的数据中获取（可能来自用户基本情况或蜂巢数据）
            actual_col = find_column(df_user, possible_names) if field in ['活跃在群用户数', '群活跃用户数', '群发言用户数'] else None
            if not actual_col and df_hive is not None:
                actual_col = find_column(df_hive, possible_names)
            
            col_name = actual_col
            if not col_name and df_hive is not None:
                # 尝试带后缀的列名
                actual_col_hive = find_column(df_hive, possible_names)
                if actual_col_hive:
                    col_name = actual_col_hive + '_hive'
            
            if col_name and col_name in row:
                value = row[col_name]
                if pd.isna(value):
                    record[field] = '⚠️ 数据缺失'
                else:
                    record[field] = str(int(value)) if isinstance(value, (int, float)) and value == int(value) else str(value).replace(',', '')
            else:
                record[field] = '⚠️ 数据缺失'
        
        # 计算互动人数占比（如果原始数据中没有或需要重新计算）
        # 公式：互动人数占比 = 互动人数 / 活跃用户数 * 100%
        if '互动人数' in record and '活跃用户数' in record:
            try:
                互动人数 = float(str(record['互动人数']).replace(',', ''))
                活跃用户数 = float(str(record['活跃用户数']).replace(',', ''))
                if 活跃用户数 > 0:
                    占比 = (互动人数 / 活跃用户数) * 100
                    record['互动人数占比'] = f"{占比:.2f}%"
            except:
                pass  # 如果计算失败，保持原有值
        
        # 预留字段
        record['预留1'] = ''
        record['预留2'] = ''
        
        result.append(record)
    
    return result


def generate_weekly_report(df_user: pd.DataFrame, df_content: pd.DataFrame, 
                          df_school: pd.DataFrame) -> str:
    """生成周报结论文本（根据上传的文件动态生成）"""
    
    # 检查哪些数据文件已上传
    has_user = not df_user.empty
    has_content = not df_content.empty
    has_school = not df_school.empty
    
    # 如果没有上传任何文件，返回提示
    if not has_user and not has_content and not has_school:
        return "未上传任何数据文件，无法生成周报。"
    
    # 获取日期范围
    if has_user:
        latest_date = df_user['日期'].max()
        this_week_start = latest_date - pd.Timedelta(days=6)
        date_start = this_week_start.strftime('%m.%d')
        date_end = latest_date.strftime('%m.%d')
    elif has_content:
        latest_date = df_content['日期'].max()
        this_week_start = latest_date - pd.Timedelta(days=6)
        date_start = this_week_start.strftime('%m.%d')
        date_end = latest_date.strftime('%m.%d')
    else:
        date_start = "--"
        date_end = "--"
    
    report_lines = [f"近一周（{date_start}-{date_end}）"]
    
    # 用户基本情况相关指标
    if has_user:
        this_week = df_user[df_user['日期'] >= (df_user['日期'].max() - pd.Timedelta(days=6))]
        last_week = df_user[(df_user['日期'] >= (df_user['日期'].max() - pd.Timedelta(days=13))) & 
                           (df_user['日期'] < (df_user['日期'].max() - pd.Timedelta(days=6)))]
        
        # 日均活跃用户数
        this_avg_dau = int(this_week['活跃用户数'].sum() / 7) if not this_week.empty else 0
        last_avg_dau = int(last_week['活跃用户数'].sum() / 7) if not last_week.empty else 0
        report_lines.append(f"日均活跃校园认证用户 {this_avg_dau}（上周 {last_avg_dau}）")
        
        # 人均消费时长
        dur_col = find_column(this_week, ['人均停留时长[分钟]', '人均停留时长(分钟)', '人均停留时长'])
        if dur_col:
            this_avg_dur = round(this_week[dur_col].mean(), 2) if not this_week.empty else 0
            last_avg_dur = round(last_week[dur_col].mean(), 2) if not last_week.empty else 0
            report_lines.append(f"人均消费时长 {this_avg_dur} min（上周 {last_avg_dur}）")
        
        # 次留
        if '次日留存率' in this_week.columns:
            this_ret = this_week['次日留存率'].mean()
            last_ret = last_week['次日留存率'].mean() if not last_week.empty else 0
            if this_ret <= 1:
                this_ret = this_ret * 100
            if last_ret <= 1:
                last_ret = last_ret * 100
            report_lines.append(f"次留 {round(this_ret, 2)}%（上周 {round(last_ret, 2)}%）")
        
        # 日均消费用户数 = 互动人数的周均
        cons_col = find_column(this_week, ['互动人数'])
        if cons_col:
            this_avg_cons = int(this_week[cons_col].sum() / 7) if not this_week.empty else 0
            last_avg_cons = int(last_week[cons_col].sum() / 7) if not last_week.empty else 0
            report_lines.append(f"日均消费用户数 {this_avg_cons}（上周 {last_avg_cons}）")
    
    # 内容生产情况相关指标
    if has_content:
        this_week = df_content[df_content['日期'] >= (df_content['日期'].max() - pd.Timedelta(days=6))]
        last_week = df_content[(df_content['日期'] >= (df_content['日期'].max() - pd.Timedelta(days=13))) & 
                              (df_content['日期'] < (df_content['日期'].max() - pd.Timedelta(days=6)))]
        
        # 调试信息
        print(f"DEBUG - 内容生产情况列名: {df_content.columns.tolist()}")
        
        # 日均生产用户数 = 当日发布笔记数的周均
        prod_col = find_column(this_week, ['当日发布笔记数', '当日发布笔记量'])
        print(f"DEBUG - 找到的列名: {prod_col}")
        if prod_col:
            this_sum = this_week[prod_col].sum()
            last_sum = last_week[prod_col].sum() if not last_week.empty else 0
            this_avg_prod = int(this_sum / 7) if not this_week.empty else 0
            last_avg_prod = int(last_sum / 7) if not last_week.empty else 0
            print(f"DEBUG - 本周{prod_col}总和: {this_sum}, 日均: {this_avg_prod}")
            print(f"DEBUG - 上周{prod_col}总和: {last_sum}, 日均: {last_avg_prod}")
            report_lines.append(f"日均生产用户数 {this_avg_prod}（上周 {last_avg_prod}）")
    
    # 累计单校情况相关指标
    if has_school:
        school_count = calculate_school_count(df_school)
        report_lines.append(f"覆盖 {school_count} 所高校")
    
    return "\n".join(report_lines)