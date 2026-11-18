import React, { useCallback, useEffect, useState } from 'react';
import { listEvents, listProposals } from '../api/client';
import { countDone, dateKey, SOURCE_LABEL } from '../utils/calendar';

export default function DashboardPage({onNavigate}) {
  const [events,setEvents]=useState([]);
  const [proposals,setProposals]=useState([]);
  const [error,setError]=useState('');
  const refresh=useCallback(async()=>{try{const [e,p]=await Promise.all([listEvents(),listProposals()]);setEvents(e.events??[]);setProposals(p.proposals??[]);setError('');}catch(err){setError(err.message);}},[]);
  useEffect(()=>{refresh();const onFocus=()=>refresh();window.addEventListener('focus',onFocus);return()=>window.removeEventListener('focus',onFocus);},[refresh]);
  const now=dateKey(new Date());
  const weekEnd=new Date();weekEnd.setDate(weekEnd.getDate()+7);const weekKey=dateKey(weekEnd);
  const upcoming=events.filter(e=>e.start_at?.slice(0,10)>=now&&!e.done).sort((a,b)=>a.start_at.localeCompare(b.start_at));
  const weekCount=events.filter(e=>e.start_at?.slice(0,10)>=now&&e.start_at.slice(0,10)<weekKey).length;
  const stats=[{label:'전체 일정',value:events.length,icon:'▣'},{label:'완료 일정',value:countDone(events),icon:'✓'},{label:'향후 7일 일정',value:weekCount,icon:'◷'},{label:'검토 대기',value:proposals.length,icon:'▤'}];
  return <div className="content"><div className="page-heading"><div><p className="eyebrow">TEAM OVERVIEW</p><h1>▦ 대시보드</h1><p className="subtitle">팀의 일정과 AI 제안 현황을 확인해 보세요.</p></div><button className="btn" onClick={refresh}>↻ 새로고침</button></div>
    {error&&<p className="event-error" role="alert">데이터를 가져오지 못했습니다: {error}</p>}
    <div className="dashboard-stats">{stats.map(s=><div className="panel stat-card" key={s.label}><span className="stat-icon">{s.icon}</span><p className="stat-label">{s.label}</p><strong className="stat-value">{s.value}</strong></div>)}</div>
    <div className="two-column"><section className="panel"><div className="panel-head"><h3 className="panel-title">예정된 일정</h3><button className="btn small" onClick={()=>onNavigate?.('calendar')}>캘린더 열기</button></div>{upcoming.length?upcoming.slice(0,7).map(e=><div className="upcoming-row" key={e.event_id}><span className={`event-dot source-${e.source}`}/><div><strong>{e.title}</strong><p className="helper">{e.start_at.slice(0,16).replace('T',' ')} · {SOURCE_LABEL[e.source]??e.source}</p></div></div>):<div className="empty-note">예정된 일정이 없습니다.</div>}</section>
    <section className="panel"><h3 className="panel-title">팀 업무 현황</h3><p className="panel-sub">완료된 일정 기준 진행률</p><div className="progress-track" role="progressbar" aria-valuenow={events.length?Math.round(countDone(events)/events.length*100):0} aria-valuemin={0} aria-valuemax={100}><span style={{width:`${events.length?countDone(events)/events.length*100:0}%`}}/></div><p className="progress-caption">{countDone(events)} / {events.length} 일정 완료</p><hr className="divider"/><h3 className="panel-title">승인 대기 일정</h3><p className="subtitle">Discord에서 감지한 후보를 검토 후 등록하세요.</p><button className="btn ghost" onClick={()=>onNavigate?.('inbox')}>검토함 보기 ({proposals.length})</button></section></div>
  </div>;
}
