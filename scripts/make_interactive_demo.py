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
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#5b6675;--line:#e3e7ed;--brand:#0f766e;--hi:#b91c1c;--warnbg:#fef3c7;--warn:#92400e}
@media (prefers-color-scheme:dark){:root{--bg:#10151b;--card:#18202a;--ink:#e8edf3;--mute:#9aa6b5;--line:#2a3441;--brand:#2dd4bf;--hi:#f87171;--warnbg:#3a2e10;--warn:#fcd34d}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,"Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif;overflow-wrap:anywhere}
main{max-width:980px;margin:auto;padding:16px}
h1{font-size:clamp(20px,4vw,28px);margin:8px 0 4px}
.sub{color:var(--mute);margin:0 0 14px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.big b{display:block;font-size:28px;color:var(--brand);line-height:1.2}
.big span{color:var(--mute);font-size:13px}
.row{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin:0 0 10px;font-size:14px}
select{font:inherit;padding:4px 8px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
svg{display:block;width:100%;height:auto}
svg text{fill:var(--ink);font-size:12px;font-family:inherit}
.ax{stroke:var(--line)}
.bar{fill:var(--brand);cursor:pointer}.bar.top{fill:var(--hi)}
.bar.sel{stroke:var(--ink);stroke-width:2}
g.b:focus{outline:none}g.b:focus .bar{stroke:var(--ink);stroke-width:2}
.ln{fill:none;stroke:var(--brand);stroke-width:2.5}.dot{fill:var(--brand)}
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
<p class="sub">虛構資料・2025 年・分析用 91 列（已排除缺值與待查列）。滑鼠移到長條上（手機點一下）看細節；點長條或用下拉選單看該區每月趨勢。</p>
<div class="cards">
<div class="card big"><b id="c1">–</b><span>總篩檢人數</span></div>
<div class="card big"><b id="c2">–</b><span>總陽性數</span></div>
<div class="card big"><b id="c3">–</b><span>整體篩檢陽性率</span></div>
</div>
<div class="card">
<div class="row"><b>各區篩檢陽性率（由高到低）</b>
<label><input type="checkbox" id="ci" checked> 顯示 95% 信賴區間</label></div>
<div id="bars"></div>
</div>
<div class="card" style="margin-top:12px">
<div class="row"><b>每月趨勢</b>
<label>行政區 <select id="sel"></select></label>
<span id="meta" class="note" style="margin:0"></span></div>
<div id="line"></div>
<p class="note">折線中斷的月份，是因為該月資料缺值或待查而被排除，並未補值。單月人數較少，波動可能很大，不宜過度解讀。</p>
</div>
<div class="warn"><b>資料限制</b>
<ul>
<li>篩檢對象非隨機抽樣；篩檢陽性率不等於區內盛行率。</li>
<li>陽性為初篩結果，未含確診。</li>
<li>未做年齡標準化；各區納入月數不同。</li>
<li>本頁為電腦隨機產生的虛構資料（A–H 區為代號），不代表任何真實地區或個案。</li>
</ul></div>
</main>
<div id="tip" role="status"></div>
<script>
var DATA=__DATA__; /* [月份, 行政區, 篩檢人數, 陽性數] */
(function(){
 var $=function(s){return document.querySelector(s)},NS="http://www.w3.org/2000/svg";
 function el(n,a,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;return e}
 function wilson(x,n){var z=1.96,p=x/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [(c-h)*100,(c+h)*100]}
 var fmt=function(v){return v.toLocaleString()};
 /* 由資料計算 */
 var by={},tot={s:0,p:0};
 DATA.forEach(function(r){var d=by[r[1]]||(by[r[1]]={name:r[1],s:0,p:0,m:{}});d.s+=r[2];d.p+=r[3];d.m[r[0]]={s:r[2],p:r[3]};tot.s+=r[2];tot.p+=r[3]});
 var ds=Object.keys(by).map(function(k){var d=by[k];d.rate=d.p/d.s*100;var w=wilson(d.p,d.s);d.lo=w[0];d.hi=w[1];d.months=Object.keys(d.m).length;return d}).sort(function(a,b){return b.rate-a.rate});
 $("#c1").textContent=fmt(tot.s);$("#c2").textContent=fmt(tot.p);$("#c3").textContent=(tot.p/tot.s*100).toFixed(2)+"%";
 var tip=$("#tip");
 function showTip(html,x,y){tip.innerHTML=html;tip.style.display="block";var w=tip.offsetWidth;tip.style.left=Math.max(8,Math.min(innerWidth-w-8,x+12))+"px";tip.style.top=(y+14)+"px"}
 function hideTip(){tip.style.display="none"}
 var sel=$("#sel");ds.forEach(function(d){var o=document.createElement("option");o.value=d.name;o.textContent=d.name;sel.appendChild(o)});
 var cur=ds[0].name;
 function bars(){
  var W=640,H=ds.length*34+30,svg=el("svg",{viewBox:"0 0 "+W+" "+H,role:"img","aria-label":"各行政區篩檢陽性率長條圖"});
  var showCI=$("#ci").checked,max=Math.max.apply(null,ds.map(function(d){return showCI?d.hi:d.rate}))*1.12,sc=(W-130)/max;
  for(var t=0;t<=Math.floor(max);t+=2){svg.appendChild(el("line",{x1:50+sc*t,x2:50+sc*t,y1:6,y2:H-22,class:"ax"}));svg.appendChild(el("text",{x:50+sc*t-6,y:H-6},t+"%"))}
  ds.forEach(function(d,i){var y=8+i*34,g=el("g",{"class":"b",tabindex:0,role:"button","aria-label":d.name+" 篩檢陽性率 "+d.rate.toFixed(2)+"%"});
   g.appendChild(el("text",{x:4,y:y+19},d.name));
   g.appendChild(el("rect",{x:50,y:y,width:Math.max(1,sc*d.rate),height:26,rx:3,"class":"bar"+(i<2?" top":"")+(d.name===cur?" sel":"")}));
   if(showCI)g.appendChild(el("line",{x1:50+sc*d.lo,x2:50+sc*d.hi,y1:y+13,y2:y+13,"class":"err"}));
   g.appendChild(el("text",{x:56+sc*(showCI?d.hi:d.rate),y:y+19},d.rate.toFixed(2)+"%"));
   var html="<b>"+d.name+"</b><br>篩檢人數 "+fmt(d.s)+"<br>陽性數 "+fmt(d.p)+"<br>篩檢陽性率 "+d.rate.toFixed(2)+"%<br>95% 信賴區間 "+d.lo.toFixed(2)+"–"+d.hi.toFixed(2)+"%<br>納入月數 "+d.months;
   g.addEventListener("mousemove",function(e){showTip(html,e.clientX,e.clientY)});
   g.addEventListener("mouseleave",hideTip);
   g.addEventListener("focus",function(){var r=g.getBoundingClientRect();showTip(html,r.left+20,r.top)});
   g.addEventListener("blur",hideTip);
   g.addEventListener("click",function(e){cur=d.name;sel.value=cur;showTip(html,e.clientX,e.clientY);bars();line()});
   g.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();cur=d.name;sel.value=cur;bars();line();var n=document.querySelectorAll("#bars g.b")[i];if(n)n.focus()}});
   svg.appendChild(g)});
  $("#bars").innerHTML="";$("#bars").appendChild(svg)}
 function line(){
  var d=by[cur],W=640,H=250,L=44,B=28,svg=el("svg",{viewBox:"0 0 "+W+" "+H,role:"img","aria-label":cur+" 每月篩檢陽性率折線圖"});
  var months=[];for(var m=1;m<=12;m++)months.push("2025-"+(m<10?"0":"")+m);
  var pts=months.map(function(k){var v=d.m[k];if(!v)return null;var w=wilson(v.p,v.s);return {k:k,s:v.s,p:v.p,rate:v.p/v.s*100,lo:w[0],hi:w[1]}});
  var vals=pts.filter(Boolean),showCI=$("#ci").checked;
  var lo=Math.floor(Math.min.apply(null,vals.map(function(x){return showCI?x.lo:x.rate}))-.3),hi=Math.ceil(Math.max.apply(null,vals.map(function(x){return showCI?x.hi:x.rate}))+.3);
  var X=function(i){return L+i*(W-L-14)/11},Y=function(v){return 10+(H-B-10)*(1-(v-lo)/(hi-lo))};
  for(var v=lo;v<=hi;v++){svg.appendChild(el("line",{x1:L,x2:W-6,y1:Y(v),y2:Y(v),"class":"ax"}));svg.appendChild(el("text",{x:2,y:Y(v)+4},v+"%"))}
  var seg=[];pts.forEach(function(p,i){if(p){seg.push(X(i)+","+Y(p.rate))}else{if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));seg=[]}});
  if(seg.length>1)svg.appendChild(el("polyline",{points:seg.join(" "),"class":"ln"}));
  pts.forEach(function(p,i){svg.appendChild(el("text",{x:X(i)-9,y:H-8},(i+1)+"月"));
   if(!p){svg.appendChild(el("text",{x:X(i)-4,y:H-B-6,style:"opacity:.55"},"×"));return}
   if(showCI)svg.appendChild(el("line",{x1:X(i),x2:X(i),y1:Y(p.lo),y2:Y(p.hi),"class":"err"}));
   var c=el("circle",{cx:X(i),cy:Y(p.rate),r:5,"class":"dot",tabindex:0});
   var html="<b>"+cur+"　"+p.k+"</b><br>篩檢人數 "+fmt(p.s)+"<br>陽性數 "+fmt(p.p)+"<br>篩檢陽性率 "+p.rate.toFixed(2)+"%<br>95% 信賴區間 "+p.lo.toFixed(2)+"–"+p.hi.toFixed(2)+"%";
   c.addEventListener("mousemove",function(e){showTip(html,e.clientX,e.clientY)});c.addEventListener("mouseleave",hideTip);
   c.addEventListener("click",function(e){showTip(html,e.clientX,e.clientY)});
   svg.appendChild(c)});
  $("#line").innerHTML="";$("#line").appendChild(svg);
  $("#meta").textContent=cur+"：納入 "+d.months+" 個月，合計篩檢 "+fmt(d.s)+" 人、陽性 "+fmt(d.p)+" 人（"+d.rate.toFixed(2)+"%）"}
 sel.addEventListener("change",function(){cur=sel.value;bars();line()});
 $("#ci").addEventListener("change",function(){bars();line()});
 document.addEventListener("click",function(e){if(!e.target.closest||!e.target.closest("g.b,circle"))hideTip()});
 bars();line();
})();
</script>
</body>
</html>
"""
out = HTML.replace("__DATA__", json.dumps(rows, ensure_ascii=False))
open("docs/prebuilt/demo_fictional_interactive_dashboard.html", "w", encoding="utf-8").write(out)
print("rows", len(rows), "bytes", len(out))
