import React, { useEffect, useState } from 'react';
import { dateKey } from '../utils/calendar';

const fromISO = value => value?.slice(0,16) ?? '';
const toISO = local => local ? `${local}:00+09:00` : null;

export default function EventModal({ initial, selectedDate, onClose, onSave, onDelete }) {
  const [form, setForm] = useState(() => ({
    title: initial?.title ?? '',
    start_at: fromISO(initial?.start_at) || `${selectedDate || dateKey(new Date())}T09:00`,
    end_at: fromISO(initial?.end_at) || `${selectedDate || dateKey(new Date())}T10:00`,
    memo: initial?.memo ?? '',
    source: initial?.source ?? 'manual'
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { const esc = e => { if(e.key==='Escape') onClose(); }; window.addEventListener('keydown',esc); return () => window.removeEventListener('keydown',esc); },[onClose]);
  const field = (key,value) => setForm(f => ({ ...f, [key]:value }));
  async function submit(e) {
    e.preventDefault(); setError('');
    if (!form.title.trim()) return setError('제목을 입력해 주세요.');
    if (form.end_at <= form.start_at) return setError('종료 시간은 시작 시간 이후여야 합니다.');
    setSaving(true);
    try { await onSave({ title:form.title.trim(),start_at:toISO(form.start_at),end_at:toISO(form.end_at),memo:form.memo,source:form.source }); }
    catch(e) { setError(e.message || '저장에 실패했습니다.'); }
    finally { setSaving(false); }
  }
  return <div className="event-modal-backdrop" onMouseDown={e => e.target===e.currentTarget && onClose()}>
    <section className="event-modal panel" role="dialog" aria-modal="true" aria-labelledby="event-dialog-title">
      <div className="panel-head"><h2 id="event-dialog-title" className="panel-title">{initial ? '일정 수정' : '새 일정 추가'}</h2><button className="btn small" type="button" onClick={onClose}>닫기 ✕</button></div>
      <form onSubmit={submit}>
        <div className="field"><label htmlFor="event-title">일정 이름</label><input autoFocus id="event-title" required maxLength={120} value={form.title} onChange={e=>field('title',e.target.value)} /></div>
        <div className="form-inline"><div className="field"><label htmlFor="event-start">시작</label><input id="event-start" type="datetime-local" required value={form.start_at} onChange={e=>field('start_at',e.target.value)} /></div><div className="field"><label htmlFor="event-end">종료</label><input id="event-end" type="datetime-local" required value={form.end_at} onChange={e=>field('end_at',e.target.value)} /></div></div>
        <div className="field"><label htmlFor="event-memo">메모</label><textarea id="event-memo" rows={3} value={form.memo} onChange={e=>field('memo',e.target.value)} /></div>
        {error && <p className="event-error" role="alert">{error}</p>}
        <div className="event-modal-actions">{initial && <button type="button" className="btn event-danger" disabled={saving} onClick={()=>{if(window.confirm('일정을 삭제할까요?'))onDelete(initial.event_id);}}>삭제</button>}<span className="event-spacer"/><button type="button" className="btn" onClick={onClose}>취소</button><button className="btn primary" type="submit" disabled={saving}>{saving?'저장 중...':'저장'}</button></div>
      </form>
    </section>
  </div>;
}
