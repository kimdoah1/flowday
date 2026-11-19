import React, { useState } from 'react';
import { aiPlan, createEvent } from '../api/client';

export default function PlanPage({ onNavigate }) {
  const [goal, setGoal] = useState('오픈소스 SW 팀 프로젝트 완성');
  const [description, setDescription] = useState('React, FastAPI, PostgreSQL, Docker Compose 연동');
  const [deadline, setDeadline] = useState('2026-11-20');
  const [intensity, setIntensity] = useState('balanced');
  const [mode, setMode] = useState('');
  const [tasks, setTasks] = useState([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await aiPlan({
        goal,
        description,
        start_date: new Date().toISOString().split('T')[0],
        deadline,
        intensity
      });
      setMode(res.mode || '');
      setTasks((res.tasks || []).map(t => ({ ...t, selected: true })));
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToCalendar = async () => {
    if (!tasks.length || saving) return;
    setSaving(true);
    try {
      for (const t of tasks.filter(task => task.selected && !task.saved)) {
        await createEvent({
          title: t.title,
          start_at: `${t.date}T09:00:00+09:00`,
          end_at: `${t.date}T10:00:00+09:00`,
          source: 'ai_plan',
          memo: `목표: ${goal}`,
          done: false
        });
        t.saved = true;
        setTasks(current => current.map(item => item === t ? { ...item, saved: true } : item));
      }
      alert('선택한 일정이 캘린더에 저장되었습니다.');
      if (onNavigate) onNavigate('calendar');
    } catch (err) {
      alert('일정 저장 중 오류가 발생했습니다. 이미 저장한 항목은 재시도에서 제외됩니다.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SMART PROJECT PLANNER</p>
          <h1>✦ AI 계획 세분화</h1>
          <p className="subtitle">큰 목표와 마감일을 입력하면 주차별·단계별 실행 계획을 제안합니다.</p>
        </div>
      </div>

      <div className="two-column">
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">새로운 목표 설정</h3>
          </div>
          <form onSubmit={handleGenerate}>
            <div className="field">
              <label>목표명</label>
              <input value={goal} onChange={(e) => setGoal(e.target.value)} required />
            </div>
            <div className="field">
              <label>목표 상세 설명</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="form-inline">
              <div className="field">
                <label>마감일</label>
                <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} required />
              </div>
              <div className="field">
                <label>작업 강도</label>
                <select value={intensity} onChange={(e) => setIntensity(e.target.value)}>
                  <option value="balanced">균형 있게</option>
                  <option value="light">여유 있게</option>
                  <option value="intense">집중적으로</option>
                </select>
              </div>
            </div>
            <button className="btn primary" type="submit" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'AI 계획 생성 중...' : '✦ 단계별 계획 생성하기'}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">생성된 실행 계획</h3>
          </div>
          {mode === 'rule' && <p role="status">규칙 기반 초안입니다. 실제 AI 호출 결과가 아닙니다.</p>}
          {tasks.length === 0 ? (
            <div className="result-empty">
              <div className="empty-icon">✧</div>
              <strong>새 계획을 만들어 보세요</strong>
            </div>
          ) : (
            <div>
              {tasks.map((task, idx) => (
                <div key={idx} className="step-row">
                  <input type="checkbox" aria-label={`${task.title} 선택`} checked={task.selected} disabled={task.saved} onChange={e => setTasks(current => current.map((t, i) => i === idx ? { ...t, selected: e.target.checked } : t))} />
                  <div className="step-number">{idx + 1}</div>
                  <div className="step-body">
                    <strong>{task.title}</strong>
                    <small>{task.date} 예정</small>
                  </div>
                </div>
              ))}
              <div className="result-action">
                <button className="btn primary" disabled={saving || !tasks.some(t => t.selected && !t.saved)} onClick={handleSaveToCalendar}>
                  ▣ 선택 일정 캘린더 등록
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
