#!/bin/bash
# 用法：bash run_stress.sh [逐月|只含各區合計]
# 對 stress_data/ 裡每份 CSV，依 SKILL.md 步驟建立成果包並執行 01–05，列出「完整跑完／中文說明後停止／程式當掉」。
HERE="$(cd "$(dirname "$0")" && pwd)"; SK="$HERE/../screening-positivity-analysis"; OUT="$HERE/stress_out"; MODE="${1:-只含各區合計}"
rm -rf "$OUT"; mkdir -p "$OUT"; python3 "$HERE/gen_stress_data.py" "$HERE/stress_data" >/dev/null
ok=0; stop=0; crash=0
for csv in "$HERE"/stress_data/*.csv; do
  n=$(basename "$csv" .csv); D="$OUT/$n"; mkdir -p "$D/00_分析計畫" "$D/01_原始資料" "$D/03_程式碼"
  cp "$csv" "$D/01_原始資料/"; cp "$SK"/scripts/*.py "$D/03_程式碼/"
  python3 - "$SK/assets/報告設定範本.json" "$D/00_分析計畫/報告設定.json" "$MODE" <<'PY'
import json, sys
c = json.load(open(sys.argv[1], encoding="utf-8"))
c.update({"標題": "測試報告", "頁首註記": "測試", "情境": "測試", "頁尾": "測試", "報告資料細節": sys.argv[3]})
json.dump(c, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
PY
  status="完整跑完"
  for f in 01_clean 02_descriptive 03_inferential 04_report 05_package; do
    (cd "$D" && python3 03_程式碼/$f.py > "$OUT/$n.$f.log" 2>&1); rc=$?
    if [ $rc -ne 0 ]; then
      if grep -q Traceback "$OUT/$n.$f.log"; then status="程式當掉@$f"; else status="中文說明後停止@$f"; fi; break
    fi
  done
  case "$status" in 完整*) ok=$((ok+1));; 中文*) stop=$((stop+1));; *) crash=$((crash+1));; esac
  echo "$n | $status"
done
echo "合計：完整跑完 $ok、中文說明後停止 $stop、程式當掉 $crash"
