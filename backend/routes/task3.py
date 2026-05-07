from flask import Blueprint, request, jsonify
import pandas as pd
import json
import os
from datetime import datetime
from utils.excel_parser import read_excel_file, normalize_columns

task3_bp = Blueprint("task3", __name__)

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

CHANNELS_FILE = os.path.join(DATA_DIR, "task3_channels.json")
TOP_CHANNELS_FILE = os.path.join(DATA_DIR, "task3_latest_top.json")

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
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "channels": [{"name": ch, "is_default": True} for ch in DEFAULT_CHANNELS],
        "updated_at": datetime.now().isoformat()
    }


def save_channels(data):
    data["updated_at"] = datetime.now().isoformat()
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_top_channels(top10_data):
    data = {
        "updated_at": datetime.now().isoformat(),
        "top_channels": top10_data
    }
    with open(TOP_CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_col(df, keywords):
    for col in df.columns:
        for kw in keywords:
            if col == kw:
                return col
    for col in df.columns:
        for kw in keywords:
            if kw in col:
                return col
    return None


def detect_columns(df):
    cols = {}
    cols["date"] = find_col(df, ["拉新日期", "日期"])
    cols["source"] = find_col(df, ["拉新归属", "归属", "渠道", "来源"])
    cols["count"] = find_col(df, ["拉新人数"])
    cols["duration"] = find_col(df, ["人均使用时长", "使用时长", "消费时长"])

    # 留存率列（百分比格式，如 "次日留存率"）
    for col in df.columns:
        if "次日留存" in col and "率" in col:
            cols["ret_rate_1"] = col
            break
    if "ret_rate_1" not in cols:
        for col in df.columns:
            if "次日留存" in col and "率" not in col:
                cols["ret_rate_1"] = col
                break

    for col in df.columns:
        if "3日留存" in col and "率" in col:
            cols["ret_rate_3"] = col
            break
    if "ret_rate_3" not in cols:
        for col in df.columns:
            if "3日留存" in col and "率" not in col:
                cols["ret_rate_3"] = col
                break

    for col in df.columns:
        if "7日留存" in col and "率" in col:
            cols["ret_rate_7"] = col
            break
    if "ret_rate_7" not in cols:
        for col in df.columns:
            if "7日留存" in col and "率" not in col:
                cols["ret_rate_7"] = col
                break

    for col in df.columns:
        if "14日留存" in col and "率" in col:
            cols["ret_rate_14"] = col
            break
    if "ret_rate_14" not in cols:
        for col in df.columns:
            if "14日留存" in col and "率" not in col:
                cols["ret_rate_14"] = col
                break

    for col in df.columns:
        if "30日留存" in col and "率" in col:
            cols["ret_rate_30"] = col
            break
    if "ret_rate_30" not in cols:
        for col in df.columns:
            if "30日留存" in col and "率" not in col:
                cols["ret_rate_30"] = col
                break

    # 同时检测留存人数列（非率）
    for col in df.columns:
        if "次日留存" in col and "率" not in col:
            cols["ret_count_1"] = col
            break
    for col in df.columns:
        if "3日留存" in col and "率" not in col:
            cols["ret_count_3"] = col
            break
    for col in df.columns:
        if "7日留存" in col and "率" not in col:
            cols["ret_count_7"] = col
            break
    for col in df.columns:
        if "14日留存" in col and "率" not in col:
            cols["ret_count_14"] = col
            break
    for col in df.columns:
        if "30日留存" in col and "率" not in col:
            cols["ret_count_30"] = col
            break

    return cols


def calc_retention_by_channel(df_channel, count_col, cols, days_in_range):
    """
    计算某个渠道的留存率
    逻辑：先计算每天的留存率(留存人数/拉新人数)，再取日均值
    如果有留存人数列：每天留存率 = 留存人数 / 拉新人数，然后取平均
    如果只有留存率列：直接取日均值
    """
    ret_keys = [
        ("ret_count_1", "ret_rate_1", "次留率"),
        ("ret_count_3", "ret_rate_3", "3留率"),
        ("ret_count_7", "ret_rate_7", "7留率"),
        ("ret_count_14", "ret_rate_14", "14留率"),
        ("ret_count_30", "ret_rate_30", "30留率"),
    ]

    results = {}
    for count_key, rate_key, label in ret_keys:
        ret_count_col = cols.get(count_key)
        ret_rate_col = cols.get(rate_key)

        if ret_count_col and ret_count_col in df_channel.columns:
            # 方式1：有留存人数列，计算每天的留存率再取平均
            daily_rates = []
            for _, row in df_channel.iterrows():
                new_count = pd.to_numeric(row[count_col], errors="coerce")
                ret_count = pd.to_numeric(row[ret_count_col], errors="coerce")
                if pd.notna(new_count) and new_count > 0 and pd.notna(ret_count):
                    daily_rate = ret_count / new_count * 100
                    daily_rates.append(daily_rate)
            if daily_rates:
                avg_rate = sum(daily_rates) / len(daily_rates)
                results[label] = round(avg_rate, 2)
            else:
                results[label] = None
        elif ret_rate_col and ret_rate_col in df_channel.columns:
            # 方式2：有留存率列，直接取日均值
            rates = pd.to_numeric(df_channel[ret_rate_col], errors="coerce").dropna()
            # 判断是否是百分比形式（大于1说明已经是百分比）
            if len(rates) > 0:
                if rates.mean() < 1:
                    # 小数形式，如 0.35 表示 35%
                    avg_rate = rates.mean() * 100
                else:
                    # 已经是百分比形式
                    avg_rate = rates.mean()
                results[label] = round(avg_rate, 2)
            else:
                results[label] = None
        else:
            results[label] = None

    return results


def calc_weighted_duration(df_subset, count_col, dur_col):
    if dur_col is None:
        return None
    counts = pd.to_numeric(df_subset[count_col], errors="coerce").fillna(0)
    durations = pd.to_numeric(df_subset[dur_col], errors="coerce").fillna(0)
    total_count = counts.sum()
    if total_count == 0:
        return None
    return round((durations * counts).sum() / total_count, 2)


@task3_bp.route("/channels", methods=["GET"])
def get_channels():
    return jsonify(load_channels())


@task3_bp.route("/channels", methods=["POST"])
def update_channels():
    data = request.json
    save_channels(data)
    return jsonify({"success": True})


@task3_bp.route("/latest_top_channels", methods=["GET"])
def get_latest_top_channels():
    if os.path.exists(TOP_CHANNELS_FILE):
        with open(TOP_CHANNELS_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "尚未执行过社团活动拉新分析", "top_channels": []}), 404


@task3_bp.route("/extract_channels", methods=["POST"])
def extract_channels():
    """渠道分析：从Excel中提取渠道列表，返回新增渠道"""
    if "excel_file" not in request.files:
        return jsonify({"error": "缺少Excel文件"}), 400
    try:
        file = request.files["excel_file"]
        file_bytes = file.read()
        df = read_excel_file(file_bytes)
        df = normalize_columns(df)
        cols = detect_columns(df)
        source_col = cols.get("source")
        if source_col is None:
            return jsonify({"error": "未找到渠道归属列"}), 400

        all_channels = df[source_col].dropna().unique().tolist()
        all_channels = [str(ch).strip() for ch in all_channels if str(ch).strip()]

        # 找出新增渠道
        channels_data = load_channels()
        existing_names = [ch["name"] for ch in channels_data.get("channels", [])]
        new_channels = [ch for ch in all_channels if ch not in existing_names]

        # 将新渠道添加到渠道列表（但不勾选）
        if new_channels:
            for ch_name in new_channels:
                channels_data["channels"].append({
                    "name": ch_name,
                    "is_default": False,
                    "is_new": True
                })
            save_channels(channels_data)

        return jsonify({
            "success": True,
            "all_channels": sorted(all_channels),
            "new_channels": sorted(new_channels),
            "new_count": len(new_channels),
            "total": len(all_channels),
            "detected_columns": {k: v for k, v in cols.items() if v is not None}
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@task3_bp.route("/analyze", methods=["POST"])
def analyze():
    if "excel_file" not in request.files:
        return jsonify({"error": "缺少Excel文件"}), 400

    try:
        params = json.loads(request.form.get("params", "{}"))
        start_date = pd.to_datetime(params.get("start_date", "2025-04-01"))
        end_date = pd.to_datetime(params.get("end_date", datetime.now().strftime("%Y-%m-%d")))
        selected_channels = params.get("selected_channels", [])

        file = request.files["excel_file"]
        upload_dir = f"./uploads/{datetime.now().strftime('%Y-%m-%d')}/task3"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)

        df = read_excel_file(open(file_path, "rb").read())
        df = normalize_columns(df)

        cols = detect_columns(df)
        date_col = cols.get("date")
        source_col = cols.get("source")
        count_col = cols.get("count")
        dur_col = cols.get("duration")

        if not all([date_col, source_col, count_col]):
            missing = []
            if not date_col: missing.append("日期")
            if not source_col: missing.append("渠道归属")
            if not count_col: missing.append("拉新人数")
            return jsonify({
                "error": f"未找到必要列: {', '.join(missing)}，检测到的列: {list(df.columns)}"
            }), 400

        df[date_col] = pd.to_datetime(df[date_col])
        df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0).astype(int)

        if dur_col:
            df[dur_col] = pd.to_numeric(df[dur_col], errors="coerce").fillna(0)

        # ====== TOP10（使用用户筛选的时间范围和渠道范围） ======
        df_range = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
        df_top10_source = df_range[df_range[source_col].isin(selected_channels)]

        top10_names = (df_top10_source.groupby(source_col)[count_col]
                       .sum()
                       .sort_values(ascending=False)
                       .head(10)
                       .index.tolist())

        top10_list = []
        for rank, ch_name in enumerate(top10_names, 1):
            ch_data = df_top10_source[df_top10_source[source_col] == ch_name]
            ch_count = int(ch_data[count_col].sum())

            # 计算次留率（日均）
            ret_results = calc_retention_by_channel(ch_data, count_col, cols, None)
            ret_1 = ret_results.get("次留率")
            ret_str = f"{ret_1:.2f}%" if ret_1 is not None else "-"

            top10_list.append({
                "排名": rank,
                "渠道名称": ch_name,
                "拉新总人数": ch_count,
                "次留率": ret_str
            })

        save_top_channels(top10_list)

        # ====== 筛选渠道整体汇总 ======
        df_range = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
        df_selected = df_range[df_range[source_col].isin(selected_channels)]

        total_new = int(df_selected[count_col].sum())
        overall_summary = {}
        channel_detail = []

        if total_new > 0:
            avg_dur = calc_weighted_duration(df_selected, count_col, dur_col)
            avg_dur_str = f"{avg_dur:.2f} min" if avg_dur is not None else "-"

            # 整体留存率：计算所有选中渠道数据的日均留存率
            overall_ret = calc_retention_by_channel(df_selected, count_col, cols, None)

            overall_summary = {
                "拉新总量": total_new,
                "人均消费时长": avg_dur_str,
                "次留率": f"{overall_ret['次留率']:.2f}%" if overall_ret.get("次留率") is not None else "-",
                "3留率": f"{overall_ret['3留率']:.2f}%" if overall_ret.get("3留率") is not None else "-",
                "7留率": f"{overall_ret['7留率']:.2f}%" if overall_ret.get("7留率") is not None else "-",
                "14留率": f"{overall_ret['14留率']:.2f}%" if overall_ret.get("14留率") is not None else "-",
                "30留率": f"{overall_ret['30留率']:.2f}%" if overall_ret.get("30留率") is not None else "-",
            }

            # ====== 各渠道明细 ======
            for ch_name in selected_channels:
                ch_data = df_selected[df_selected[source_col] == ch_name]
                if len(ch_data) == 0:
                    continue
                ch_count = int(ch_data[count_col].sum())
                if ch_count == 0:
                    continue

                ch_dur = calc_weighted_duration(ch_data, count_col, dur_col)
                ch_dur_str = f"{ch_dur:.2f}" if ch_dur is not None else "-"

                ch_ret = calc_retention_by_channel(ch_data, count_col, cols, None)

                channel_detail.append({
                    "渠道名称": ch_name,
                    "拉新总量": ch_count,
                    "人均时长": ch_dur_str,
                    "次留率": f"{ch_ret['次留率']:.2f}%" if ch_ret.get("次留率") is not None else "-",
                    "3留率": f"{ch_ret['3留率']:.2f}%" if ch_ret.get("3留率") is not None else "-",
                    "7留率": f"{ch_ret['7留率']:.2f}%" if ch_ret.get("7留率") is not None else "-",
                    "14留率": f"{ch_ret['14留率']:.2f}%" if ch_ret.get("14留率") is not None else "-",
                    "30留率": f"{ch_ret['30留率']:.2f}%" if ch_ret.get("30留率") is not None else "-",
                })

            channel_detail.sort(key=lambda x: x["拉新总量"], reverse=True)

        return jsonify({
            "success": True,
            "top10": top10_list,
            "overall_summary": overall_summary,
            "channel_detail": channel_detail,
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "detected_columns": {k: v for k, v in cols.items() if v is not None}
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500