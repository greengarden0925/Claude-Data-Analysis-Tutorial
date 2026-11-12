"""共用設定：資料夾位置、Wilson 信賴區間、中文字型。所有資料皆為虛構。"""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]          # 成果包最上層資料夾
RAW_DIR = ROOT / "01_原始資料"
CLEAN_DIR = ROOT / "02_清理後資料"
TABLE_DIR = ROOT / "04_結果表格"
FIG_DIR = ROOT / "05_圖表"
for d in (CLEAN_DIR, TABLE_DIR, FIG_DIR):
    d.mkdir(exist_ok=True)

RAW_FILE = RAW_DIR / "demo_fictional_screening_dirty.csv"
CLEAN_FILE = CLEAN_DIR / "分析用資料.csv"
LOG_FILE = CLEAN_DIR / "修正與排除紀錄.csv"


def wilson(x, n, z=1.96):
    """Wilson 95% 信賴區間，回傳百分比（下限, 上限）。"""
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h) * 100, (c + h) * 100


def use_chinese_font():
    """找一個系統內可用的中文字型給 matplotlib；找不到時圖上中文可能變成方塊。"""
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    wanted = ["Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC", "Noto Sans TC",
              "WenQuanYi Zen Hei", "Heiti TC", "Arial Unicode MS"]
    have = {f.name for f in fm.fontManager.ttflist}
    for name in wanted:
        if name in have:
            plt.rcParams["font.family"] = name
            return name
    print("提醒：找不到中文字型，圖上的中文可能顯示成方塊。")
    return None
