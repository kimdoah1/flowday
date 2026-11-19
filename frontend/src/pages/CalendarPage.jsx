import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { listEvents, createEvent, updateEvent, deleteEvent } from '../api/client';
import EventModal from '../components/EventModal';
import { dateKey, eventsForDay, monthCells, SOURCE_LABEL } from '../utils/calendar';

const WEEK = ['일','월','화','수','목','금','토'];
const monthTitle = (year, month) => `${year}년 ${month + 1}월`;
export default function CalendarPage() {
  const today = useMemo(() => dateKey(new Date()), []);
  const [view, setView] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selected, setSelected] = useState(today);
  const [events, setEvents] = useState([]);
  const [active, setActive] = useState(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true);setError('');
    try { const result = await listEvents(); setEvents(result.events ?? []); }
    catch(e) { setError(e.message ?? '일정 조회에 실패했습니다.'); }
    finally { setLoading(false); }
  },[]);
  useEffect(()=>{refresh();},[refresh]);
  useEffect(()=>{const onFocus=()=>refresh();window.addEventListener('focus',onFocus);return()=>window.removeEventListener('focus',onFocus);},[refresh]);
  const cells = useMemo(() => monthCells(view.getFullYear(), view.getMonth()),[view]);
  const chosen = eventsForDay(events, selected).sort((a,b)=>a.start_at.localeCompare(b.start_at));
  const shift = n => setView(v=>new Date(v.getFullYear(),v.getMonth()+n,1));
  async function save(payload) {
    if(active) await updateEvent(active.event_id,payload); else await createEvent(payload);
    setActive(undefined);await refresh();
  }
  async function remove(id) {try{await deleteEvent(id);setActive(undefined);await refresh();}catch(e){setError(e.message);}}
  async function toggle(event) {try{await updateEvent(event.event_id,{done:!event.done});await refresh();}catch(e){setError(e.message);}}
  return <div className="content">
    <div className="page-heading"><div><p className="eyebrow">TEAM SCHEDULE</p><h1>▣ 캘린더</h1><p className="subtitle">AI 계획 · 회의 · Discord에서 등록한 일정을 한곳에서 확인하세요.</p></div><button className="btn primary" onClick={()=>setActive(null)}>+ 일정 추가</button></div>
    <div className="calendar-layout">
      <section className="panel calendar-panel">
        <div className="panel-head"><div><h2 className="panel-title calendar-month">{monthTitle(view.getFullYear(),view.getMonth())}</h2><p className="panel-sub">{events.filter(e=>e.start_at?.slice(0,7)===dateKey(view).slice(0,7)).length}개 일정</p></div><div className="calendar-toolbar"><button className="btn small" onClick={()=>{const now=new Date();setView(new Date(now.getFullYear(),now.getMonth(),1));setSelected(dateKey(now));}}>오늘</button><button aria-label="이전 달" className="btn small" onClick={()=>shift(-1)}>‹</button><button aria-label="다음 달" className="btn small" onClick={()=>shift(1)}>›</button></div></div>
        <div className="calendar-grid calendar-weekdays">{WEEK.map(day=><div key={day}>{day}</div>)}</div>
        <div className="calendar-grid calendar-days">{cells.map((day,index)=> <button key={day??`empty-${index}`} disabled={!day} onClick={()=>setSelected(day)} className={`calendar-day ${day===today?'today':''} ${day===selected?'selected':''} ${!day?'outside':''}`}>
          {day&&<><span className="day-number">{Number(day.slice(-2))}</span><div className="calendar-chip-list">{eventsForDay(events,day).slice(0,3).map(ev=><span key={ev.event_id} className={`calendar-chip source-${ev.source} ${ev.done?'is-done':''}`}>{ev.title}</span>)}{eventsForDay(events,day).length>3&&<span className="calendar-more">+{eventsForDay(events,day).length-3}개</span>}</div></>}
        </button>)}</div>
      </section>
      <aside className="panel calendar-side"><div className="panel-head"><div><h3 className="panel-title">{selected} 일정</h3><p className="panel-sub">{chosen.length}개 일정</p></div><button className="btn small" onClick={()=>setActive(null)}>+ 추가</button></div>
        {loading&&<p className="helper">일정 불러오는 중...</p>}{error&&<p className="event-error" role="alert">{error} <button className="btn small" onClick={refresh}>다시 시도</button></p>}
        {chosen.length===0?<div className="empty-note">이 날에 등록된 일정이 없습니다.</div>:chosen.map(ev=><div key={ev.event_id} className="day-event"><div className="day-event-main"><span className={`event-dot source-${ev.source}`}/><div><button className="event-edit" onClick={()=>setActive(ev)}>{ev.title}</button><p className="helper">{ev.start_at.slice(11,16)}–{ev.end_at.slice(11,16)} · {SOURCE_LABEL[ev.source]??ev.source}</p>{ev.memo&&<p className="helper">{ev.memo}</p>}</div></div><label className="event-done"><input type="checkbox" checked={Boolean(ev.done)} onChange={()=>toggle(ev)} /> 완료</label></div>)}
      </aside>
    </div>
    {active!==undefined&&<EventModal initial={active} selectedDate={selected} onClose={()=>setActive(undefined)} onSave={save} onDelete={remove}/>}
  </div>;
}
