"""產生「互動圖表」參考範例（單一 HTML 檔，資料內嵌、不連外部網路）。全部為虛構資料。
輸入：docs/sample-data/demo_fictional_screening_analysis_91rows.csv
輸出：docs/prebuilt/demo_fictional_interactive_dashboard.html
所有數字都在瀏覽器端由內嵌的 91 列資料計算（與講義提示詞的要求一致）。
用法：先跑 make_sample_data.py，再 python3 scripts/make_interactive_demo.py
"""
import json
import pandas as pd

df = pd.read_csv("docs/sample-data/demo_fictional_screening_analysis_91rows.csv")
rows = [[r["月份"], r["行政區"], int(r["篩檢人數"]), int(r["陽性數"])] for _, r in df.iterrows()]

HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>互動圖表參考範例（虛構資料）</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#5b6675;--line:#e3e7ed;--brand:#0f766e;--warnbg:#fef3c7;--warn:#92400e}
@media (prefers-color-scheme:dark){:root{--bg:#10151b;--card:#18202a;--ink:#e8edf3;--mute:#9aa6b5;--line:#2a3441;--brand:#2dd4bf;--warnbg:#3a2e10;--warn:#fcd34d}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,"Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif;overflow-wrap:anywhere}
main{max-width:980px;margin:auto;padding:16px}
h1{font-size:clamp(20px,4vw,28px);margin:8px 0 4px}
.banner{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:8px 12px;font-size:14px;font-weight:600;margin:0 0 8px}
.sub{color:var(--mute);margin:0 0 14px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.big b{display:block;font-size:28px;color:var(--brand);line-height:1.2}
.big span{color:var(--mute);font-size:13px}
.row{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin:0 0 10px;font-size:14px}
.row label{display:inline-flex;align-items:center;gap:8px;min-height:40px;cursor:pointer}
input[type=checkbox]{width:22px;height:22px;accent-color:var(--brand)}
select{font:inherit;min-height:40px;padding:4px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
svg{display:block;width:100%;height:auto}
svg text{fill:var(--ink);font-size:13px;font-family:inherit}
.ax{stroke:var(--line)}
.bar{fill:var(--brand);cursor:pointer}
.bar.sel{stroke:var(--ink);stroke-width:2}
g.b:focus{outline:none}g.b:focus .bar{stroke:var(--ink);stroke-width:2}
.ln{fill:none;stroke:var(--brand);stroke-width:2.5}.dot{fill:var(--brand)}
.hit{fill:transparent;cursor:pointer}.hit:focus{outline:none;stroke:var(--ink);stroke-width:2}
.err{stroke:var(--ink);stroke-width:1.3}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);border-radius:8px;padding:6px 10px;font-size:13px;line-height:1.5;display:none;z-index:5;max-width:240px}
.warn{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;font-size:14px;margin-top:14px}
.warn ul{margin:4px 0 0;padding-left:20px}
.note{color:var(--mute);font-size:13px;margin:6px 0 0}
</style>
</head>
<body>
<main>
<h1>各行政區篩檢陽性率（互動圖表）</h1>
<p class="banner">篩檢項目＝虛構的成人健康篩檢｜對象＝30 歲以上成人｜資料期間＝2025 年 1–12 月｜資料截止日＝2026-01-31｜虛構資料。篩檢陽性率不等於盛行率，詳見頁面下方資料限制。</p>
<p class="sub">分析用 91 列（已排除缺值與待查列）。滑鼠移到長條上（手機點一下）看細節；點長條或用下拉選單看該區每月趨勢。長條顏色不代表風險等級。</p>
<div class="cards">
<div class="card big"><b id="c1">–</b><span>總篩檢人數</span></div>
<div class="card big"><b id="c2">–</b><span>總陽性數</span></div>
<div class="card big"><b id="c3">–</b><span>整體篩檢陽性率</span></div>
</div>
<div class="card">
<div class="row"><b>各區篩檢陽性率</b>
<label>排序 <select id="ord"><option value="code">依區代碼</option><option value="rate">依陽性率由高到低</option></select></label>
<label><input type="checkbox" id="ci" checked> 顯示 95% 信賴區間</label></div>
<div id="bars"></div>
</div>
<div class="card" style="margin-top:12px">
<div class="row"><b>每月趨勢</b>
<label>行政區 <select id="sel"></select></label></div>
<p id="meta" class="note" style="margin:0 0 6px"></p>
<div id="line"></div>
<p class="note">× ＝ 該月無有效資料（缺值或待查而被排除，不是 0，也未補值）。各區縱軸範圍一致（0–__YMAX__%）。每月只有數百至兩千多人，折線起伏多為隨機波動；單月 95% 信賴區間約寬 2–6 個百分點，不宜過度解讀。</p>
</div>
<div class="warn"><b>資料限制</b>
<ul>
<li>篩檢對象非隨機抽樣；篩檢陽性率不等於區內盛行率。</li>
<li>陽性為初篩結果，未含確診。</li>
<li>未做年齡標準化；各區納入月數不同（標示在區名後方）。</li>
<li>信賴區間為 Wilson 法，未考慮月別群聚；其他方法算出的數字會略有不同，實際不確定性比圖上更大。</li>
<li>本頁為電腦隨機產生的虛構資料（A–H 區為代號），不代表任何真實地區或個案。</li>
</ul></div>
</main>
<div id="tip" role="status"></div>
<script>
var DATA=__DATA__; /* [月份, 行政區, 篩檢人數, 陽性數] */
var YMAX=__YMAX__;
(function(){
 var $=function(s){return document.querySelector(s)},NS="http://www.w3.org/2000/svg";
 function el(n,a,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;return e}
 function wilson(x,n){var z=1.96,p=x/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [(c-h)*100,(c+h)*100]}
 var fmt=function(v){return v.toLocaleString()};
 /* 注意：下方 tooltip 以 innerHTML 組字串，目前只放程式內部算出的數字與固定文字。
    若日後改成讓使用者匯入自己的資料，請先對字串做 HTML 跳脫（escape）。 */
 var by={},tot={s:0,p:0};
 DATA.forEach(function(r){var d=by[r[1]]||(by[r[1]]={name:r[1],s:0,p:0,m:{}});d.s+=r[2];d.p+=r[3];d.m[r[0]]={s:r[2],p:r[3]};tot.s+=r[2];tot.p+=r[3]});
 var ds=Object.keys(by).map(function(k){var d=by[k];d.rate=d.p/d.s*100;var w=wilson(d.p,d.s);d.lo=w[0];d.hi=w[1];d.months=Object.keys(d.m).length;return d});
 $("#c1").textContent=fmt(tot.s);$("#c2").textContent=fmt(tot.p);$("#c3").textContent=(tot.p/tot.s*100).toFixed(2)+"%";
 var tip=$("#tip"),rebuilding=false;
 function showTip(html,x,y){tip.innerHTML=html;tip.style.display="block";var w=tip.offsetWidth,h=tip.offsetHeight;
  var left=Math.max(8,Math.min(innerWidth-w-8,x+12)),top=y+14;if(top+h>innerHeight-8)top=Math.max(8,y-h-14);tip.style.left=left+"px";tip.style.top=top+"px"}
 function hideTip(){tip.style.display="none"}
 var sel=$("#sel");ds.slice().sort(function(a,b){return a.name<b.name?-1:1}).forEach(function(d){var o=document.createElement("option");o.value=d.name;o.textContent=d.name;sel.appendChild(o)});
 var cur=sel.value=ds.slice().sort(function(a,b){return b.rate-a.rate})[0].name;
 var cw=function(id){return Math.max(300,Math.floor($(id).clientWidth||600))};
 function pick(name,x,y,html){cur=name;sel.value=cur;rebuilding=true;bars();line();rebuilding=false;if(x!=null)showTip(html,x,y)}
 function bars(){
  var W=cw("#bars"),small=W<520,L=small?112:128,rowH=small?38:36,order=$("#ord").value;
  var arr=ds.slice().sort(order==="rate"?function(a,b){return b.rate-a.rate}:function(a,b){return a.name<b.name?-1:1});
  var H=arr.length*rowH+34,svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,role:"img","aria-label":"各行政區篩檢陽性率長條圖"});
  var showCI=$("#ci").checked,max=Math.max.apply(null,ds.map(function(d){return showCI?d.hi:d.rate}))*1.15,sc=(W-L-52)/max;
  for(var t=0;t<=Math.floor(max);t+=2){svg.appendChild(el("line",{x1:L+sc*t,x2:L+sc*t,y1:4,y2:H-24,"class":"ax"}));svg.appendChild(el("text",{x:L+sc*t-8,y:H-6},t+"%"))}
  arr.forEach(function(d,i){var y=6+i*rowH,g=el("g",{"class":"b",tabindex:0,role:"button","aria-label":d.name+" 篩檢陽性率 "+d.rate.toFixed(2)+"%，納入 "+d.months+" 個月"});
   g.appendChild(el("text",{x:2,y:y+rowH/2+3},d.name+(d.months<12?"（"+d.months+"個月）":"")));
   g.appendChild(el("rect",{x:L,y:y,width:Math.max(1,sc*d.rate),height:rowH-8,rx:3,"class":"bar"+(d.name===cur?" sel":"")}));
   if(showCI)g.appendChild(el("line",{x1:L+sc*d.lo,x2:L+sc*d.hi,y1:y+(rowH-8)/2,y2:y+(rowH-8)/2,"class":"err"}));
   g.appendChild(el("text",{x:L+6+sc*(showCI?d.hi:d.rate),y:y+rowH/2+3},d.rate.toFixed(2)+"%"));
   var html="<b>"+d.name+"</b><br>篩檢人數 "+fmt(d.s)+"<br>陽性數 "+fmt(d.p)+"<br>篩檢陽性率 "+d.rate.toFixed(2)+"%<br>95% 信賴區間 "+d.lo.toFixed(2)+"–"+d.hi.toFixed(2)+"%<br>納入月數 "+d.months;
   g.addEventListener("mousemove",function(e){showTip(html,e.clientX,e.clientY)});
   g.addEventListener("mouseleave",hideTip);
   g.addEventListener("focus",function(){var r=g.getBoundingClientRect();showTip(html,r.left+20,r.top)});
   g.addEventListener("blur",function(){if(!rebuilding)hideTip()});
   g.addEventListener("click",function(e){pick(d.name,e.clientX,e.clientY,html)});
   g.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();var r=g.getBoundingClientRect();pick(d.name,r.left+20,r.top,html);var n=document.querySelectorAll("#bars g.b");for(var k=0;k<n.length;k++){if(n[k].getAttribute("aria-label").indexOf(d.name)===0){n[k].focus();break}}}});
   svg.appendChild(g)});
  $("#bars").innerHTML="";$("#bars").appendChild(svg)}
 function line(){
  var d=by[cur],W=cw("#line"),H=260,L=44,B=28,svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,role:"img","aria-label":cur+" 每月篩檢陽性率折線圖"});
  var months=[];for(var m=1;m<=12;m++)months.push("2025-"+(m<10?"0":"")+m);
  var pts=months.map(function(k){var v=d.m[k];if(!v)return null;var w=wilson(v.p,v.s);return {k:k,s:v.s,p:v.p,rate:v.p/v.s*100,lo:w[0],hi:w[1]}});
  var showCI=$("#ci").checked,step=YMAX>10?4:2;
  var X=function(i){return L+i*(W-L-16)/11},Y=function(v){return 10+(H-B-10)*(1-v/YMAX)};
  for(var v=0;v<=YMAX;v+=step){svg.appendChild(el("line",{x1:L,x2:W-6,y1:Y(v),y2:Y(v),"class":"ax"}));svg.appendChild(el("text",{x:2,y:Y(v)+4},v+"%"))}
  var seg=[];pts.forEach(function(p,i){if(p){seg.push(X(i)+","+Y(p.rate))}else{if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));seg=[]}});
  if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));
  var small=W<520;
  pts.forEach(function(p,i){if(!small||i%2===0)svg.appendChild(el("text",{x:X(i)-9,y:H-8},(i+1)+"月"));
   if(!p){svg.appendChild(el("text",{x:X(i)-5,y:Y(0)-8,style:"font-weight:700"},"×"));return}
   if(showCI)svg.appendChild(el("line",{x1:X(i),x2:X(i),y1:Y(p.lo),y2:Y(Math.min(p.hi,YMAX)),"class":"err"}));
   svg.appendChild(el("circle",{cx:X(i),cy:Y(p.rate),r:5,"class":"dot"}));
   var html="<b>"+cur+"　"+p.k+"</b><br>篩檢人數 "+fmt(p.s)+"<br>陽性數 "+fmt(p.p)+"<br>篩檢陽性率 "+p.rate.toFixed(2)+"%<br>95% 信賴區間 "+p.lo.toFixed(2)+"–"+p.hi.toFixed(2)+"%";
   var c=el("circle",{cx:X(i),cy:Y(p.rate),r:15,"class":"hit",tabindex:0,role:"img","aria-label":cur+" "+p.k+" 篩檢陽性率 "+p.rate.toFixed(2)+"%"});
   c.addEventListener("mousemove",function(e){showTip(html,e.clientX,e.clientY)});c.addEventListener("mouseleave",hideTip);
   c.addEventListener("click",function(e){showTip(html,e.clientX,e.clientY)});
   c.addEventListener("focus",function(){var r=c.getBoundingClientRect();showTip(html,r.left+10,r.top)});c.addEventListener("blur",hideTip);
   svg.appendChild(c)});
  $("#line").innerHTML="";$("#line").appendChild(svg);
  $("#meta").textContent=cur+"：納入 "+d.months+" 個月，合計篩檢 "+fmt(d.s)+" 人、陽性 "+fmt(d.p)+" 人（"+d.rate.toFixed(2)+"%）"}
 sel.addEventListener("change",function(){cur=sel.value;bars();line()});
 $("#ci").addEventListener("change",function(){bars();line()});
 $("#ord").addEventListener("change",bars);
 document.addEventListener("click",function(e){if(!e.target.closest||!e.target.closest("g.b,circle"))hideTip()});
 var rt;window.addEventListener("resize",function(){clearTimeout(rt);rt=setTimeout(function(){bars();line()},120)});
 bars();line();
})();
</script>
</body>
</html>
"""
# 所有區、所有月份的 Wilson 95% 信賴區間上界，決定固定縱軸上限（所有區一致）
def _wilson_hi(x, n, z=1.96):
    import math
    p = x / n; d = 1 + z * z / n
    return ((p + z * z / (2 * n)) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d * 100
import math
ymax = int(math.ceil(max(_wilson_hi(r[3], r[2]) for r in rows) / 2.0) * 2)
out = HTML.replace("__YMAX__", str(ymax)).replace("__DATA__", json.dumps(rows, ensure_ascii=False))
open("docs/prebuilt/demo_fictional_interactive_dashboard.html", "w", encoding="utf-8").write(out)
print("ymax", ymax, "rows", len(rows), "bytes", len(out))
