// Authored trusted integration fixture. Not claimed to be a native Agent result.
import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, interpolate, spring, useVideoConfig} from 'remotion';
import type {VideoProps, Scene} from './contracts';
const blue='#315ff3',ink='#182b49';
function Visual({scene,index}:{scene:Scene;index:number}){
 const f=useCurrentFrame(),{fps}=useVideoConfig();
 const enter=spring({frame:f,fps,config:{damping:18}});
 const progress=interpolate(f,[0,scene.frames-1],[0,1],{extrapolateRight:'clamp'});
 return <AbsoluteFill style={{padding:'72px 100px 150px',color:ink,background:'linear-gradient(140deg,#f8fbff,#edf3fb)'}}>
   <div style={{fontSize:19,letterSpacing:4,color:blue}}>ENGINEERING VIDEO AGENT / {String(index+1).padStart(2,'0')}</div>
   <h1 style={{fontSize:66,margin:'35px 0 22px',lineHeight:1.3,opacity:enter,transform:`translateY(${(1-enter)*20}px)`}}>{scene.title}</h1>
   {index===0 ? <div style={{display:'flex',alignItems:'center',height:500,gap:80}}>
      <div style={{position:'relative',width:470,height:410,display:'grid',placeItems:'center'}}>
        <div style={{position:'absolute',width:330,height:330,border:`3px dashed ${blue}55`,borderRadius:'50%',transform:`rotate(${f*.5}deg)`}}/>
        <div style={{width:220,height:220,borderRadius:48,background:blue,color:'white',display:'grid',placeItems:'center',fontSize:42,boxShadow:'0 25px 60px #315ff333'}}>创作引擎</div>
      </div>
      <div><p style={{fontSize:44,fontWeight:700}}>一个想法，一份源码</p><p style={{fontSize:30,color:'#61738e'}}>理解内容 · 编写工程 · 验证结果</p><div style={{height:6,width:600,background:'#d9e3f5',borderRadius:6}}><div style={{height:6,width:`${progress*100}%`,background:blue,borderRadius:6}}/></div></div>
   </div> : index===1 ? <div style={{marginTop:85}}>
     <svg width="1720" height="360"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10" fill={blue}/></marker></defs>
       {[0,1,2].map(i=><path key={i} d={`M${370+i*420},180 L${470+i*420},180`} stroke="#9eb4ee" strokeWidth="4" markerEnd="url(#arrow)"/>)}
       {['理解与策划','分镜与工程','配音与对齐','渲染与验证'].map((label,i)=>{const a=interpolate(f,[i*15,i*15+16],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});return <g key={label} opacity={a}><rect x={70+i*420} y="95" width="300" height="170" rx="24" fill="white" stroke={blue} strokeWidth="2"/><text x={220+i*420} y="155" textAnchor="middle" fill={blue} fontSize="23">STEP {i+1}</text><text x={220+i*420} y="207" textAnchor="middle" fill={ink} fontSize="30" fontWeight="700">{label}</text></g>})}
       <circle cx={220+progress*1260} cy="304" r="9" fill={blue}/><path d="M220,304 L1480,304" stroke={blue} opacity=".2" strokeWidth="3"/>
     </svg><p style={{fontSize:32,color:'#61738e',textAlign:'center'}}>让每一段讲解，都有对应的画面和可验证的工程</p>
   </div> : <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:38,marginTop:100}}>
      {['脚本与分镜','音频与字幕','完整视频工程'].map((label,i)=><div key={label} style={{height:310,borderRadius:28,padding:36,background:'white',border:'2px solid #d9e4f5',transform:`translateY(${(1-enter)*(30+i*10)}px)`}}><div style={{fontSize:70,color:blue,fontWeight:700}}>0{i+1}</div><h2 style={{fontSize:34}}>{label}</h2><p style={{fontSize:24,color:'#6a7c93'}}>可编辑 · 可追溯 · 可继续迭代</p></div>)}
   </div>}
 </AbsoluteFill>;
}
export default function EngineeringVideo(props:VideoProps){return <AbsoluteFill>{props.scenes.map((scene,index)=><Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}><Visual scene={scene} index={index}/></Sequence>)}</AbsoluteFill>}
