"""步驟 5：檢查資料夾並打包成 zip（虛構資料）

檢查 00–06 資料夾與 README.md 是否齊全，印出樹狀圖，並把整個成果包打包成 zip。
寫出：與成果包同一層的「<成果包資料夾名稱>.zip」（檔名含中文時以 UTF-8 記錄）
提醒：成果包含原始資料與逐列資料；真實資料打包後，請依單位規定存放與傳遞，給主管通常只需要 06_報告。
執行方式（在成果包最上層資料夾）：python 03_程式碼/05_package.py
"""
import zipfile
from pathlib import Path

# ===== 輸入與輸出：看程式碼時先檢查這裡 =====
ROOT = Path(__file__).resolve().parents[1]                 # 【輸入】整個成果包資料夾（只讀）
ZIP = ROOT.parent / f"{ROOT.name}.zip"                      # 【輸出】zip 檔

need = ["00_分析計畫", "01_原始資料", "02_清理後資料", "03_程式碼", "04_結果表格", "05_圖表", "06_報告"]
missing = [d for d in need if not (ROOT / d).is_dir()] + ([] if (ROOT / "README.md").exists() else ["README.md"])
print("缺少：" + "、".join(missing) if missing else "資料夾與 README.md 齊全")
print(f"{ROOT.name}/")
for p in sorted(ROOT.rglob("*")):
    if "__pycache__" in p.parts:
        continue
    depth = len(p.relative_to(ROOT).parts)
    print("    " * depth + p.name + ("/" if p.is_dir() else ""))
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:                # 【寫出】zip
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            z.write(p, Path(ROOT.name) / p.relative_to(ROOT))
print(f"已打包：{ZIP.name}")
