import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { listEvents, createEvent, updateEvent, deleteEvent } from '../api/client';
import EventModal from '../components/EventModal';
import { dateKey, dateInMonth, eventsForDay, groupEventsByDay, monthCells, SOURCE_LABEL } from '../utils/calendar';

const WEEK = ['일', '월', '화', '수', '목', '금', '토'];

export default function CalendarPage() {
  const today = dateKey(new Date());
  const [view, setView] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selected, setSelected] = useState(today);
  const [mode, setMode] = useState('month');
  const [events, setEvents] = useState([]);
  const [active, setActive] = useState(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await listEvents();
      setEvents(result.events ?? []);
    } catch (e) {
      setError(e.message ?? '일정 조회에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    window.addEventListener('focus', refresh);
    return () => window.removeEventListener('focus', refresh);
  }, [refresh]);

  const cells = useMemo(() => monthCells(view.getFullYear(), view.getMonth()), [view]);
  const eventsByDay = useMemo(() => new Map(groupEventsByDay(events)), [events]);
  const groups = useMemo(() => groupEventsByDay(events), [events]);
  const chosen = eventsForDay(events, selected).sort((a, b) => new Date(a.start_at) - new Date(b.start_at));
  const currentYear = new Date().getFullYear();
  const years = [...new Set([
    ...Array.from({ length: 21 }, (_, i) => currentYear - 10 + i),
    view.getFullYear(),
    ...events.map(event => Number(event.start_at.slice(0, 4))),
  ])].sort((a, b) => a - b);

  function changeMonth(year, month) {
    setView(new Date(year, month, 1));
    setSelected(dateInMonth(selected, year, month));
  }
  function showDay(day) {
    const [year, month] = day.split('-').map(Number);
    setView(new Date(year, month - 1, 1));
    setSelected(day);
    setMode('month');
  }
  async function save(payload) {
    if (active) await updateEvent(active.event_id, payload);
    else await createEvent(payload);
    const day = payload.start_at.slice(0, 10);
    const [year, month] = day.split('-').map(Number);
    setView(new Date(year, month - 1, 1));
    setSelected(day);
    setActive(undefined);
    await refresh();
  }
  async function remove(id) {
    try { await deleteEvent(id); setActive(undefined); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function toggle(event) {
    try { await updateEvent(event.event_id, { done: !event.done }); await refresh(); }
    catch (e) { setError(e.message); }
  }
  function eventRow(event) {
    return <div key={event.event_id} className="day-event">
      <div className="day-event-main">
        <span className={`event-dot source-${event.source}`} />
        <div>
          <button className="event-edit" onClick={() => setActive(event)}>{event.title}</button>
          <p className="helper">{event.start_at.slice(11, 16)}–{event.end_at.slice(11, 16)} · {SOURCE_LABEL[event.source] ?? event.source}</p>
          {event.memo && <p className="helper">{event.memo}</p>}
        </div>
      </div>
      <label className="event-done">
        <input type="checkbox" aria-label={`${event.title} 완료`} checked={Boolean(event.done)} onChange={() => toggle(event)} /> 완료
      </label>
    </div>;
  }

  return <div className="content">
    <div className="page-heading">
      <div><p className="eyebrow">TEAM SCHEDULE</p><h1>▣ 캘린더</h1><p className="subtitle">AI 계획 · 회의 · Discord에서 등록한 일정을 한곳에서 확인하세요.</p></div>
      <button className="btn primary" onClick={() => setActive(null)}>+ 일정 추가</button>
    </div>
    <div className="calendar-view-controls">
      <div className="calendar-view-switch" role="group" aria-label="일정 보기 방식">
        <button className={`btn ${mode === 'year' ? 'primary' : ''}`} aria-pressed={mode === 'year'} onClick={() => setMode('year')}>연간 보기</button>
        <button className={`btn ${mode === 'month' ? 'primary' : ''}`} aria-pressed={mode === 'month'} onClick={() => setMode('month')}>월간 달력</button>
        <button className={`btn ${mode === 'all' ? 'primary' : ''}`} aria-pressed={mode === 'all'} onClick={() => setMode('all')}>전체 일정 ({events.length})</button>
      </div>
      <button className="btn" onClick={refresh} disabled={loading}>새로고침</button>
    </div>
    {loading && <p className="helper" role="status">일정 불러오는 중...</p>}
    {error && <p className="event-error" role="alert">{error} <button className="btn small" onClick={refresh}>다시 시도</button></p>}

    {mode === 'year' ? <section aria-label="연간 달력">
      <div className="panel-head calendar-heading">
        <div><h2 className="panel-title">{view.getFullYear()}년 한눈에 보기</h2><p className="panel-sub">날짜를 누르면 해당 일정을 확인할 수 있어요. 색 점은 일정이 있는 날입니다.</p></div>
        <div className="calendar-toolbar">
          <button className="btn small" aria-label="이전 연도" onClick={() => changeMonth(view.getFullYear() - 1, view.getMonth())}>‹</button>
          <select aria-label="연도 선택" value={view.getFullYear()} onChange={e => changeMonth(Number(e.target.value), view.getMonth())}>
            {years.map(year => <option key={year} value={year}>{year}년</option>)}
          </select>
          <button className="btn small" aria-label="다음 연도" onClick={() => changeMonth(view.getFullYear() + 1, view.getMonth())}>›</button>
          <button className="btn small" onClick={() => changeMonth(currentYear, new Date().getMonth())}>올해</button>
        </div>
      </div>
      <div className="calendar-year-grid">{Array.from({ length: 12 }, (_, month) => {
        const firstDay = dateKey(new Date(view.getFullYear(), month, 1));
        return <section className="panel calendar-mini" key={month} aria-label={`${view.getFullYear()}년 ${month + 1}월 작은 달력`}>
          <h3><button className="event-edit" aria-label={`${view.getFullYear()}년 ${month + 1}월 크게 보기`} onClick={() => showDay(firstDay)}>{month + 1}월 <span aria-hidden="true">›</span></button></h3>
          <div className="calendar-grid mini-weekdays">{WEEK.map(day => <span key={day}>{day}</span>)}</div>
          <div className="calendar-grid">{monthCells(view.getFullYear(), month).map((day, index) => {
            if (!day) return <span key={`empty-${index}`} />;
            const items = eventsByDay.get(day) ?? [];
            const sources = [...new Set(items.map(event => event.source))].slice(0, 3);
            return <button key={day} className={`mini-day ${day === today ? 'today' : ''} ${day === selected ? 'selected' : ''}`} aria-label={`${day}, 일정 ${items.length}개, 달력에서 보기`} aria-current={day === today ? 'date' : undefined} title={`${day} · 일정 ${items.length}개`} onClick={() => showDay(day)}>
              <span>{Number(day.slice(-2))}</span>
              <span className="mini-dots" aria-hidden="true">{sources.map(source => <span key={source} className={`event-dot source-${source}`} />)}</span>
            </button>;
          })}</div>
        </section>;
      })}</div>
    </section> : mode === 'month' ? <div className="calendar-layout">
      <section className="panel calendar-panel">
        <div className="panel-head calendar-heading">
          <div>
            <h2 className="panel-title calendar-month">{view.getFullYear()}년 {view.getMonth() + 1}월</h2>
            <p className="panel-sub">이 달 {events.filter(e => e.start_at.slice(0, 7) === dateKey(view).slice(0, 7)).length}개 · 전체 {events.length}개 일정</p>
          </div>
          <div className="calendar-toolbar">
            <select aria-label="연도 선택" value={view.getFullYear()} onChange={e => changeMonth(Number(e.target.value), view.getMonth())}>
              {years.map(year => <option key={year} value={year}>{year}년</option>)}
            </select>
            <select aria-label="월 선택" value={view.getMonth()} onChange={e => changeMonth(view.getFullYear(), Number(e.target.value))}>
              {Array.from({ length: 12 }, (_, month) => <option key={month} value={month}>{month + 1}월</option>)}
            </select>
            <button className="btn small" onClick={() => showDay(dateKey(new Date()))}>오늘</button>
            <button aria-label="이전 달" className="btn small" onClick={() => changeMonth(view.getFullYear(), view.getMonth() - 1)}>‹</button>
            <button aria-label="다음 달" className="btn small" onClick={() => changeMonth(view.getFullYear(), view.getMonth() + 1)}>›</button>
          </div>
        </div>
        <div className="calendar-grid calendar-weekdays">{WEEK.map(day => <div key={day}>{day}</div>)}</div>
        <div className="calendar-grid calendar-days">{cells.map((day, index) => <button key={day ?? `empty-${index}`} disabled={!day} aria-label={day ? `${day} 일정 보기` : undefined} onClick={() => setSelected(day)} className={`calendar-day ${day === today ? 'today' : ''} ${day === selected ? 'selected' : ''} ${!day ? 'outside' : ''}`}>
          {day && <><span className="day-number">{Number(day.slice(-2))}</span><div className="calendar-chip-list">
            {eventsForDay(events, day).slice(0, 3).map(event => <span key={event.event_id} className={`calendar-chip source-${event.source} ${event.done ? 'is-done' : ''}`}>{event.title}</span>)}
            {eventsForDay(events, day).length > 3 && <span className="calendar-more">+{eventsForDay(events, day).length - 3}개</span>}
          </div></>}
        </button>)}</div>
      </section>
      <aside className="panel calendar-side">
        <div className="panel-head"><div><h3 className="panel-title">{selected} 일정</h3><p className="panel-sub">{chosen.length}개 일정</p></div><button className="btn small" onClick={() => setActive(null)}>+ 추가</button></div>
        {chosen.length === 0 ? !loading && !error && <div className="empty-note">이 날에 등록된 일정이 없습니다.</div> : chosen.map(eventRow)}
      </aside>
    </div> : <section className="panel calendar-all">
      <h2 className="panel-title">전체 일정</h2>
      <p className="panel-sub">월과 관계없이 저장된 일정 {events.length}개를 날짜순으로 표시합니다. 완료된 일정도 포함합니다.</p>
      {groups.length === 0 && !loading && !error && <div className="empty-note">등록된 일정이 없습니다.</div>}
      {groups.map(([day, items]) => <section key={day} className="calendar-date-group" aria-label={`${day} 일정 목록`}>
        <div className="panel-head"><h3 className="panel-title">{day} · {items.length}개</h3><button className="btn small" aria-label={`${day} 달력에서 보기`} onClick={() => showDay(day)}>달력에서 보기</button></div>
        {items.map(eventRow)}
      </section>)}
    </section>}
    {active !== undefined && <EventModal initial={active} selectedDate={selected} onClose={() => setActive(undefined)} onSave={save} onDelete={remove} />}
  </div>;
}
