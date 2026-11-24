import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

export const darkTheme = {background:'#17383A', panel:'#285054', ink:'#FFF8EA', muted:'#B9D7D6', accent:'#E9A56D', mint:'#A9CFC3'};
export type DarkSlide = {eyebrow:string; title:string; highlight:string; description:string; leftLabel:string; rightLabel:string; leftCaption:string; rightCaption:string; footer?:string};
const enter=(frame:number,start:number)=>interpolate(frame,[start,start+22],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
function Symbol({type,color}:{type:'chat'|'work';color:string}){return <svg width="142" height="142" viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round">{type==='chat'?<><rect x="12" y="17" width="76" height="56" rx="16"/><path d="M30 73v15l20-15M29 38h43M29 52h29"/></>:<><rect x="12" y="32" width="76" height="53" rx="10"/><path d="M34 32V20h32v12M12 55c22 19 54 19 76 0M45 61h10"/></>}</svg>}

/** Dark editorial explainer: replace text through slide props, not TSX markup. 1920×1080. */
export function DarkEditorial({slide}:{slide:DarkSlide}){
  const f=useCurrentFrame(), t=darkTheme;
  return <AbsoluteFill style={{background:t.background,color:t.ink,fontFamily:'EngineeringNoto, sans-serif'}}>
    <div style={{position:'absolute',left:88,top:50,fontSize:18,letterSpacing:3,color:t.muted}}>{slide.eyebrow}</div>
    <div style={{position:'absolute',right:88,top:50,fontSize:18,color:t.muted}}>01 / DARK EDITORIAL</div>
    <div style={{position:'absolute',left:88,top:125,fontSize:48,fontWeight:700}}>{slide.title}</div>
    <div style={{position:'absolute',left:90,top:300,width:910,fontSize:83,lineHeight:1.2,fontWeight:700,opacity:enter(f,3)}}>{slide.leftLabel}<br/><span style={{color:t.accent}}>{slide.highlight}</span></div>
    <div style={{position:'absolute',left:95,top:610,width:900,fontSize:29,lineHeight:1.55,color:t.muted,opacity:enter(f,22)}}>{slide.description}</div>
    <div style={{position:'absolute',left:1105,top:256,width:610,height:560,borderRadius:40,background:t.panel,boxShadow:'0 25px 60px #091D28',opacity:enter(f,8)}}>
      <div style={{position:'absolute',left:83,top:72}}><Symbol type="chat" color={t.accent}/></div><div style={{position:'absolute',left:363,top:72}}><Symbol type="work" color={t.mint}/></div>
      <div style={{position:'absolute',left:275,top:125,fontSize:46,color:t.accent}}>→</div>
      <div style={{position:'absolute',left:68,top:290,width:220,textAlign:'center',fontSize:28}}>{slide.leftCaption}</div><div style={{position:'absolute',left:344,top:290,width:220,textAlign:'center',fontSize:28}}>{slide.rightCaption}</div>
      <div style={{position:'absolute',left:82,top:425,width:450,height:7,borderRadius:6,background:t.mint,transform:`scaleX(${enter(f,36)})`,transformOrigin:'left'}}/>
    </div>
    <div style={{position:'absolute',left:90,bottom:162,fontSize:22,color:t.muted}}>{slide.footer||slide.rightLabel}</div>
    <div style={{position:'absolute',left:0,bottom:0,width:'100%',height:6,background:t.accent}}/>
  </AbsoluteFill>
}
