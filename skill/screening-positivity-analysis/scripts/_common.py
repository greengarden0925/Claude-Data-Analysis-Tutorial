"""共用小工具：Wilson 信賴區間、中文字型。所有資料皆為虛構。"""
import math


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


def newcombe_diff(x1, n1, x2, n2):
    """兩比例差（p1−p2）的 95% 信賴區間，Newcombe 混合 Wilson 法（陽性數為 0 時也能計算）。回傳百分點。"""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = (v / 100 for v in wilson(x1, n1))
    l2, u2 = (v / 100 for v in wilson(x2, n2))
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return lo * 100, hi * 100
