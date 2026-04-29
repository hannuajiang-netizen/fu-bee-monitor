from flask import Blueprint, request, jsonify
import pandas as pd
import json
import os
from datetime import datetime
from utils.excel_parser import read_excel_file, normalize_columns

task3_bp = Blueprint('task3', __name__)

DATA_DIR = './data'
os.makedirs(DATA_DIR, exist_ok=True)

CHANNELS_FILE = os.path.join(DATA_DIR, 'task3_channels.json')
TOP_CHANNELS_FILE = os.path.join(DATA_DIR, 'task3_latest_top.json')

# 预置渠道列表
DEFAULT_CHANNELS = [
    "userteam_26H1社团活动-专",
    "userteam_26年H1拉新-李（社团、职引、AI）",
    "userteam_26年H1拉新-左1",
    "userteam_12月公益任务页面-芙",
    "userteam_26年H1拉新-左3",
    "userteam_26H1通用社团活动",
    "userteam_26年H1拉新-左2",
    "userteam_26年H1拉新-左4",
    "userteam_社团活动拉新用户分组",
    "act_white_社团活动",
    "group_校园社团进群",
    "search_社团活动",
    "userteam_社团入驻邀请-高",
    "userteam_校园合作-观看视频流程",
    "userteam_社团活动拉新用户分组-信息收集",
    "userteam_社团功能-文联",
    "userteam_12月公益任务页面—左3",
    "group_创意星球-河北工艺美术职业学院",
    "group_创意星球-广东科学技术职业学院",
]


def load_channels():
    """加载渠道列表"""
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'channels': [{'name': ch, 'is_default': True} for ch in DEFAULT_CHANNELS],
        'updated_at': datetime.now().isoformat()
    }


def save_channels(data):
    """保存渠道列表"""
    data['updated_at'] = datetime.now().isoformat()
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_top_channels(top10_df):
    """保存TOP渠道结果"""
    result = top10_df.to_dict(orient='records')
    data = {
        'updated_at': datetime.now().isoformat(),
        'top_channels': result
    }
    with open(TOP_CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@task3_bp.route('/channels', methods=['GET'])
def get_channels():
    """获取渠道列表"""
    return jsonify(load_channels())


@task3_bp.route('/channels', methods=['POST'])
def update_channels():
    """更新渠道列表"""
    data = request.json
    save_channels(data)
    return jsonify({'success': True})


@task3_bp.route('/latest_top_channels', methods=['GET'])
def get_latest_top_channels():
    """获取最近一次TOP渠道（供任务二联动）"""
    if os.path.exists(TOP_CHANNELS_FILE):
        with open(TOP_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'error': '尚未执行过社团活动拉新分析', 'top_channels': []}), 404


@task3_bp.route('/analyze', methods=['POST'])
def analyze():
    """任务三：社团活动拉新监控分析"""
    
    # 检查文件
    if 'excel_file' not in request.files:
        return jsonify({'error': '缺少Excel文件'}), 400
    
    try:
        # 获取参数
        params = json.loads(request.form.get('params', '{}'))
        start_date = pd.to_datetime(params.get('start_date', '2025-04-01'))
        end_date = pd.to_datetime(params.get('end_date', datetime.now().strftime('%Y-%m-%d')))
        selected_channels = params.get('selected_channels', [])
        
        # 读取Excel
        file = request.files['excel_file']
        
        # 保存文件
        upload_dir = f"./uploads/{datetime.now().strftime('%Y-%m-%d')}/task3"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        
        # 读取数据
        df = read_excel_file(open(file_path, 'rb').read())
        df = normalize_columns(df)
        df['拉新日期'] = pd.to_datetime(df['拉新日期'])
        
        # 检测新渠道
        all_channels_in_excel = df['拉新归属'].unique().tolist()
        channels_data = load_channels()
        existing_names = [ch['name'] for ch in channels_data.get('channels', [])]
        new_channels = [ch for ch in all_channels_in_excel if ch not in existing_names]
        
        # ====== 输出1：近一周拉新 TOP10 渠道 ======
        today = pd.Timestamp.now().normalize()
        week_start = today - pd.Timedelta(days=7)
        df_week = df[(df['拉新日期'] >= week_start) & (df['拉新日期'] <= today)]
        
        top10 = (df_week.groupby('拉新归属')['拉新人数']
                 .sum()
                 .sort_values(ascending=False)
                 .head(10)
                 .reset_index())
        top10.columns = ['渠道名称', '拉新人数']
        top10['排名'] = range(1, len(top10) + 1)
        
        # 保存TOP渠道结果供任务二联动
        save_top_channels(top10)
        
        # ====== 输出2：勾选渠道汇总数据 ======
        df_range = df[(df['拉新日期'] >= start_date) & (df['拉新日期'] <= end_date)]
        df_selected = df_range[df_range['拉新归属'].isin(selected_channels)]
        
        # 整体汇总
        total_new = df_selected['拉新人数'].sum()
        
        overall_summary = {}
        channel_detail = []
        
        if total_new > 0:
            # 人均消费时长 = 按拉新人数加权平均
            avg_duration = round(
                (df_selected['人均使用时长'] * df_selected['拉新人数']).sum() / total_new, 2
            ) if '人均使用时长' in df_selected.columns else 0
            
            # 留存率 = 总留存人数 / 总拉新人数（加权平均）
            retention_cols = ['次日留存', '3日留存', '7日留存', '14日留存', '30日留存']
            retention_rates = {}
            
            for col in retention_cols:
                if col in df_selected.columns:
                    rate = round(df_selected[col].sum() / total_new * 100, 2)
                    retention_rates[col] = rate
                else:
                    retention_rates[col] = 0
            
            overall_summary = {
                '拉新总量': int(total_new),
                '人均消费时长': f"{avg_duration} min",
                '加权次留': f"{retention_rates.get('次日留存', 0)}%",
                '加权3留': f"{retention_rates.get('3日留存', 0)}%",
                '加权7留': f"{retention_rates.get('7日留存', 0)}%",
                '加权14留': f"{retention_rates.get('14日留存', 0)}%",
                '加权30留': f"{retention_rates.get('30日留存', 0)}%"
            }
            
            # 各渠道明细
            agg_dict = {'拉新人数': 'sum'}
            for col in retention_cols:
                if col in df_selected.columns:
                    agg_dict[col] = 'sum'
            
            channel_agg = df_selected.groupby('拉新归属').agg(agg_dict).reset_index()
            
            # 计算各渠道的留存率
            for col in retention_cols:
                if col in channel_agg.columns:
                    rate_col = col.replace('留存', '留')
                    channel_agg[rate_col] = (channel_agg[col] / channel_agg['拉新人数'] * 100).round(2)
            
            # 人均时长（按渠道加权平均）
            if '人均使用时长' in df_selected.columns:
                dur_agg = df_selected.groupby('拉新归属').apply(
                    lambda g: round((g['人均使用时长'] * g['拉新人数']).sum() / g['拉新人数'].sum(), 2)
                    if g['拉新人数'].sum() > 0 else 0
                ).reset_index(name='人均时长')
                channel_agg = channel_agg.merge(dur_agg, on='拉新归属', how='left')
            else:
                channel_agg['人均时长'] = 0
            
            channel_agg = channel_agg.sort_values('拉新人数', ascending=False)
            
            # 转换为字典列表
            for _, row in channel_agg.iterrows():
                detail = {
                    '渠道名称': row['拉新归属'],
                    '拉新人数': int(row['拉新人数']),
                    '人均时长': f"{row.get('人均时长', 0):.2f}",
                    '次留': f"{row.get('次留', 0):.2f}%",
                    '3留': f"{row.get('3留', 0):.2f}%",
                    '7留': f"{row.get('7留', 0):.2f}%",
                    '14留': f"{row.get('14留', 0):.2f}%",
                    '30留': f"{row.get('30留', 0):.2f}%",
                }
                channel_detail.append(detail)
        
        return jsonify({
            'success': True,
            'top10': top10.to_dict(orient='records'),
            'overall_summary': overall_summary,
            'channel_detail': channel_detail,
            'new_channels_found': new_channels
        })
        
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500