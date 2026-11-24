import React from 'react';
import {AbsoluteFill,interpolate,useCurrentFrame} from 'remotion';

export const warmTheme={background:'#F7F2E8',ink:'#17383A',accent:'#BE6654',board:'#F3D9C2',paper:'#FFFDF7',mint:'#E8EFE8',soft:'#785C5D'};
export type WarmItem={title:string; detail:string; icon:'gear'|'file'|'work'|'calendar'|'search'|'shield'};
export type WarmSlide={eyebrow:string;title:string;subtitle:string;items:WarmItem[];footer?:string};
const enter=(f:number,n:number)=>interpolate(f,[n*8+4,n*8+24],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
function Icon({kind}:{kind:WarmItem['icon']}){const paths={gear:<><circle cx="50" cy="50" r="17"/><path d="M50 9v15m0 52v15M9 50h15m52 0h15M21 21l11 11m36 36 11 11M79 21 68 32M32 68 21 79"/></>,file:<><path d="M23 10h38l17 18v60H23zM61 10v19h17M34 46h32M34 59h32M34 72h22"/></>,work:<><rect x="12" y="32" width="76" height="53" rx="10"/><path d="M34 32V20h32v12M12 55c22 19 54 19 76 0"/></>,calendar:<><rect x="15" y="22" width="70" height="65" rx="9"/><path d="M15 42h70M33 12v20M67 12v20M33 58h10M56 58h10M33 73h10"/></>,search:<><circle cx="44" cy="43" r="25"/><path d="m63 63 24 24"/></>,shield:<><path d="M50 10 81 23v24c0 21-12 34-31 44-19-10-31-23-31-44V23z"/><path d="m36 50 10 10 20-23"/></>};return <svg width="92" height="92" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">{paths[kind]}</svg>}

/** Warm illustrated explainer: 3–6 semantic items, each with a real icon and label. 1920×1080. */
export function WarmIllustrated({slide}:{slide:WarmSlide}){
 const f=useCurrentFrame(),t=warmTheme,items=slide.items.slice(0,6);
 return <AbsoluteFill style={{background:t.background,color:t.ink,fontFamily:'EngineeringNoto, sans-serif'}}>
   <div style={{position:'absolute',left:88,top:50,fontSize:18,letterSpacing:3,color:t.soft}}>{slide.eyebrow}</div><div style={{position:'absolute',right:88,top:50,fontSize:18,color:t.soft}}>02 / WARM ILLUSTRATED</div>
   <div style={{position:'absolute',left:88,top:125,fontSize:48,fontWeight:700}}>{slide.title}</div><div style={{position:'absolute',left:90,top:192,fontSize:23,color:t.soft}}>{slide.subtitle}</div>
   <div style={{position:'absolute',left:90,top:275,width:1720,height:600,borderRadius:40,background:t.board,transform:'rotate(-1deg)'}}/>
   {items.map((item,i)=>{const col=i%3,row=Math.floor(i/3),x=125+col*575,y=310+row*260,p=enter(f,i);return <div key={i} style={{position:'absolute',left:x,top:y,width:500,height:205,borderRadius:30,boxSizing:'border-box',padding:28,background:i%2?t.paper:t.mint,boxShadow:'0 13px 0 #8D5B5B24',display:'flex',alignItems:'center',gap:26,opacity:p,transform:`translateY(${(1-p)*30}px)`}}><div style={{color:i%2?t.accent:'#32776D'}}><Icon kind={item.icon}/></div><div><div style={{fontSize:34,fontWeight:700}}>{item.title}</div><div style={{fontSize:22,marginTop:12,color:t.soft}}>{item.detail}</div></div></div>})}
   <div style={{position:'absolute',left:90,bottom:162,fontSize:21,color:t.soft}}>{slide.footer||'理解组成，才能用好工具'}</div><div style={{position:'absolute',left:0,bottom:0,width:'100%',height:6,background:t.accent}}/>
 </AbsoluteFill>
}
