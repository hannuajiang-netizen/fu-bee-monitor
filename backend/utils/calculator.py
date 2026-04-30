import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from utils.excel_parser import find_column


def calculate_weighted_average(df: pd.DataFrame, value_col: str, weight_col: str) -> float:
    """计算加权平均值"""
    if df.empty or weight_col not in df.columns or value_col not in df.columns:
        return 0.0
    
    total_weight = df[weight_col].sum()
    if total_weight == 0:
        return 0.0
    
    weighted_sum = (df[value_col] * df[weight_col]).sum()
    return round(weighted_sum / total_weight, 2)


def calculate_school_count(df_school: pd.DataFrame) -> tuple:
    """
    从「累计单校情况」表中计算覆盖高校数
    
    表结构：3列
    - 第1列：日期
    - 第2列：活跃人数（区间标识，如 =0、>0、>= 15、>= 100、>= 800、>= 2000）
    - 第3列：学校数（该区间对应的学校数量）
    
    返回：(本周覆盖高校数, 上周覆盖高校数)
    """
    if df_school.empty:
        return 0, 0
    
    # 智能识别列名（去空格）
    df_school.columns = df_school.columns.str.strip()
    
    # 假设第1列是日期，第3列是学校数
    date_col = df_school.columns[0]
    value_col = df_school.columns[2]
    
    # 确保日期列为 datetime 格式
    df_school[date_col] = pd.to_datetime(df_school[date_col])
    
    # 确保学校数列为数值
    df_school[value_col] = pd.to_numeric(df_school[value_col], errors='coerce').fillna(0)
    
    # 找到数据中的最新日期（本周基准日）
    latest_date = df_school[date_col].max()
    
    # 本周覆盖高校数 = 最新日期那天的所有行「学校数」之和
    this_week_data = df_school[df_school[date_col] == latest_date]
    this_school_count = int(this_week_data[value_col].sum())
    
    # 上周覆盖高校数 = 最新日期 - 7天 那天的所有行「学校数」之和
    last_week_date = latest_date - pd.Timedelta(days=7)
    last_week_data = df_school[df_school[date_col] == last_week_date]
    
    if last_week_data.empty:
        # 如果恰好 -7天没有数据，找最接近的更早日期
        earlier_dates = df_school[df_school[date_col] < latest_date - pd.Timedelta(days=6)][date_col].unique()
        if len(earlier_dates) > 0:
            last_week_date = max(earlier_dates)
            last_week_data = df_school[df_school[date_col] == last_week_date]
            last_school_count = int(last_week_data[value_col].sum())
        else:
            last_school_count = 0
    else:
        last_school_count = int(last_week_data[value_col].sum())
    
    print(f"DEBUG - 本周({latest_date.date()}): {this_school_count}, 上周({last_week_date.date()}): {last_school_count}")
    return this_school_count, last_school_count


def get_week_boundaries(df: pd.DataFrame, date_col: str = '日期') -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """
    获取本周和上周的日期边界
    本周 = 数据中最新日期往前推7天（含当天共7天）
    """
    latest_date = df[date_col].max()
    this_week_start = latest_date - pd.Timedelta(days=6)
    last_week_end = this_week_start - pd.Timedelta(days=1)
    last_week_start = last_week_end - pd.Timedelta(days=6)
    
    return this_week_start, latest_date, last_week_start, last_week_end


def calculate_weekly_metrics(df_user: pd.DataFrame, df_content: pd.DataFrame, 
                            df_school: pd.DataFrame) -> Dict[str, Any]:
    """计算周报所需的各项指标"""
    
    # 合并用户和内容的日期数据
    merged = df_user.merge(df_content, on='日期', how='left', suffixes=('', '_c'))
    merged = merged.sort_values('日期', ascending=True)
    
    # 获取本周和上周的日期范围
    this_week_start, latest_date, last_week_start, last_week_end = get_week_boundaries(merged, '日期')
    
    # 筛选本周和上周数据
    this_week = merged[(merged['日期'] >= this_week_start) & (merged['日期'] <= latest_date)]
    last_week = merged[(merged['日期'] >= last_week_start) & (merged['日期'] <= last_week_end)]
    
    # 计算指标
    metrics = {}
    
    # 日均活跃用户数 = 7天合计 / 7，取整
    metrics['this_avg_dau'] = int(this_week['活跃用户数'].sum() / 7) if not this_week.empty else 0
    metrics['last_avg_dau'] = int(last_week['活跃用户数'].sum() / 7) if not last_week.empty else 0
    
    # 人均消费时长 = 7天人均停留时长的算术平均，保留2位小数
    dur_col = find_column(this_week, ['人均停留时长[分钟]', '人均停留时长(分钟)', '人均停留时长', '平均停留时长', '停留时长'])
    if dur_col:
        metrics['this_avg_dur'] = round(this_week[dur_col].mean(), 2) if not this_week.empty else 0
        metrics['last_avg_dur'] = round(last_week[dur_col].mean(), 2) if not last_week.empty else 0
    else:
        metrics['this_avg_dur'] = 0
        metrics['last_avg_dur'] = 0
    
    # 次留 = 7天次日留存率的算术平均，保留2位小数
    # 注意：如果原始数据是 0.xx 格式需 ×100
    def calc_retention_rate(week_df):
        if week_df.empty or '次日留存率' not in week_df.columns:
            return 0.0
        avg = week_df['次日留存率'].mean()
        # 判断是否需要乘以100
        if avg <= 1:
            avg = avg * 100
        return round(avg, 2)
    
    metrics['this_avg_ret'] = calc_retention_rate(this_week)
    metrics['last_avg_ret'] = calc_retention_rate(last_week)
    
    # 日均生产用户数 = 7天「当日发布笔记数」合计 / 7（注意：是笔记数，不是用户数）
    prod_col = find_column(this_week, ['当日发布笔记数', '当日发布笔记量'])
    if prod_col:
        metrics['this_avg_prod'] = int(this_week[prod_col].sum() / 7) if not this_week.empty else 0
        metrics['last_avg_prod'] = int(last_week[prod_col].sum() / 7) if not last_week.empty else 0
    else:
        metrics['this_avg_prod'] = 0
        metrics['last_avg_prod'] = 0
    
    # 日均消费用户数 = 7天「互动人数」合计 / 7
    cons_col = find_column(this_week, ['互动人数'])
    if cons_col:
        metrics['this_avg_cons'] = int(this_week[cons_col].sum() / 7) if not this_week.empty else 0
        metrics['last_avg_cons'] = int(last_week[cons_col].sum() / 7) if not last_week.empty else 0
    else:
        metrics['this_avg_cons'] = 0
        metrics['last_avg_cons'] = 0
    
    # 覆盖高校数
    metrics['this_school_count'] = calculate_school_count(df_school, 'this_week')
    metrics['last_school_count'] = calculate_school_count(df_school, 'last_week')
    
    # 日期字符串
    metrics['date_start'] = this_week_start.strftime('%m.%d')
    metrics['date_end'] = latest_date.strftime('%m.%d')
    
    return metrics