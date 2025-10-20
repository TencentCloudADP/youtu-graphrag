"use strict";exports.id=9370,exports.ids=[9370],exports.modules={47410:(e,t,a)=>{function i(e,t){e.accDescr&&t.setAccDescription?.(e.accDescr),e.accTitle&&t.setAccTitle?.(e.accTitle),e.title&&t.setDiagramTitle?.(e.title)}a.d(t,{S:()=>i}),(0,a(77466).K2)(i,"populateCommonDb")},79370:(e,t,a)=>{a.d(t,{diagram:()=>K});var i=a(47410),l=a(21123),r=a(60652),s=a(77466),o=a(15555),n=a(35380),c=s.UI.pie,p={sections:new Map,showData:!1,config:c},d=p.sections,g=p.showData,u=structuredClone(c),m=(0,s.K2)(()=>structuredClone(u),"getConfig"),f=(0,s.K2)(()=>{d=new Map,g=p.showData,(0,s.IU)()},"clear"),x=(0,s.K2)(({label:e,value:t})=>{d.has(e)||(d.set(e,t),s.Rm.debug(`added new section: ${e}, with value: ${t}`))},"addSection"),h=(0,s.K2)(()=>d,"getSections"),S=(0,s.K2)(e=>{g=e},"setShowData"),w=(0,s.K2)(()=>g,"getShowData"),D={getConfig:m,clear:f,setDiagramTitle:s.ke,getDiagramTitle:s.ab,setAccTitle:s.SV,getAccTitle:s.iN,setAccDescription:s.EI,getAccDescription:s.m7,addSection:x,getSections:h,setShowData:S,getShowData:w},T=(0,s.K2)((e,t)=>{(0,i.S)(e,t),t.setShowData(e.showData),e.sections.map(t.addSection)},"populateDb"),$={parse:(0,s.K2)(async e=>{let t=await (0,o.qg)("pie",e);s.Rm.debug(t),T(t,D)},"parse")},y=(0,s.K2)(e=>`
  .pieCircle{
    stroke: ${e.pieStrokeColor};
    stroke-width : ${e.pieStrokeWidth};
    opacity : ${e.pieOpacity};
  }
  .pieOuterCircle{
    stroke: ${e.pieOuterStrokeColor};
    stroke-width: ${e.pieOuterStrokeWidth};
    fill: none;
  }
  .pieTitleText {
    text-anchor: middle;
    font-size: ${e.pieTitleTextSize};
    fill: ${e.pieTitleTextColor};
    font-family: ${e.fontFamily};
  }
  .slice {
    font-family: ${e.fontFamily};
    fill: ${e.pieSectionTextColor};
    font-size:${e.pieSectionTextSize};
    // fill: white;
  }
  .legend text {
    fill: ${e.pieLegendTextColor};
    font-family: ${e.fontFamily};
    font-size: ${e.pieLegendTextSize};
  }
`,"getStyles"),C=(0,s.K2)(e=>{let t=[...e.entries()].map(e=>({label:e[0],value:e[1]})).sort((e,t)=>t.value-e.value);return(0,n.rLf)().value(e=>e.value)(t)},"createPieArcs"),K={parser:$,db:D,renderer:{draw:(0,s.K2)((e,t,a,i)=>{s.Rm.debug("rendering pie chart\n"+e);let o=i.db,c=(0,s.D7)(),p=(0,l.$t)(o.getConfig(),c.pie),d=(0,r.D)(t),g=d.append("g");g.attr("transform","translate(225,225)");let{themeVariables:u}=c,[m]=(0,l.I5)(u.pieOuterStrokeWidth);m??=2;let f=p.textPosition,x=(0,n.JLW)().innerRadius(0).outerRadius(185),h=(0,n.JLW)().innerRadius(185*f).outerRadius(185*f);g.append("circle").attr("cx",0).attr("cy",0).attr("r",185+m/2).attr("class","pieOuterCircle");let S=o.getSections(),w=C(S),D=[u.pie1,u.pie2,u.pie3,u.pie4,u.pie5,u.pie6,u.pie7,u.pie8,u.pie9,u.pie10,u.pie11,u.pie12],T=(0,n.UMr)(D);g.selectAll("mySlices").data(w).enter().append("path").attr("d",x).attr("fill",e=>T(e.data.label)).attr("class","pieCircle");let $=0;S.forEach(e=>{$+=e}),g.selectAll("mySlices").data(w).enter().append("text").text(e=>(e.data.value/$*100).toFixed(0)+"%").attr("transform",e=>"translate("+h.centroid(e)+")").style("text-anchor","middle").attr("class","slice"),g.append("text").text(o.getDiagramTitle()).attr("x",0).attr("y",-200).attr("class","pieTitleText");let y=g.selectAll(".legend").data(T.domain()).enter().append("g").attr("class","legend").attr("transform",(e,t)=>"translate(216,"+(22*t-22*T.domain().length/2)+")");y.append("rect").attr("width",18).attr("height",18).style("fill",T).style("stroke",T),y.data(w).append("text").attr("x",22).attr("y",14).text(e=>{let{label:t,value:a}=e.data;return o.getShowData()?`${t} [${a}]`:t});let K=512+Math.max(...y.selectAll("text").nodes().map(e=>e?.getBoundingClientRect().width??0));d.attr("viewBox",`0 0 ${K} 450`),(0,s.a$)(d,450,K,p.useMaxWidth)},"draw")},styles:y}}};