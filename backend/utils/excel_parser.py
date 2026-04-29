import pandas as pd
import io
from typing import Dict, List, Any


def read_excel_file(file_bytes: bytes) -> pd.DataFrame:
    """读取 Excel 文件并返回 DataFrame"""
    return pd.read_excel(io.BytesIO(file_bytes))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化列名：去除空格，统一括号"""
    df.columns = df.columns.str.strip()
    # 统一括号类型（中文括号转英文括号）
    df.columns = df.columns.str.replace('（', '(', regex=False).str.replace('）', ')', regex=False)
    return df


def find_column(df: pd.DataFrame, possible_names: list) -> str:
    """根据可能的列名列表，找到实际存在的列名"""
    columns = list(df.columns)
    for name in possible_names:
        if name in columns:
            return name
        # 尝试模糊匹配
        for col in columns:
            if name in col or col in name:
                return col
    return None


def parse_date_column(df: pd.DataFrame, date_col: str = '日期') -> pd.DataFrame:
    """解析日期列"""
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
    return df


def remove_thousand_separator(value) -> str:
    """去除千位分隔符"""
    if pd.isna(value):
        return ''
    s = str(value)
    return s.replace(',', '').replace('，', '')


def format_percentage(value, decimals: int = 2) -> str:
    """格式化百分比"""
    if pd.isna(value):
        return ''
    # 如果值已经是 0-1 范围，转换为百分比
    if isinstance(value, (int, float)):
        if 0 <= value <= 1:
            value = value * 100
        return f"{value:.{decimals}f}%"
    return str(value)


def format_number(value, decimals: int = 2) -> str:
    """格式化数字，无千位分隔符"""
    if pd.isna(value):
        return ''
    if isinstance(value, (int, float)):
        if decimals == 0:
            return str(int(value))
        return f"{value:.{decimals}f}"
    s = str(value).replace(',', '').replace('，', '')
    return s