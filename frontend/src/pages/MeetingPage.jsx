import React, { useState, useRef, useEffect } from 'react';
import { uploadMeeting, getMeeting, createEvent } from '../api/client';

export default function MeetingPage({ onNavigate }) {
  const [name, setName] = useState('팀 프로젝트 주간 회의');
  const [text, setText] = useState('프론트엔드 시안은 11월 12일까지 완료한다.\nAPI 명세는 11월 15일까지 공유한다.');
  const [file, setFile] = useState(null);
  const generation = useRef(0);
  useEffect(() => () => { generation.current += 1; }, []);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true);
    const current = ++generation.current;
    setResult(null);
    try {
      const input = file || new File([text], 'meeting.txt', { type: 'text/plain' });
      const init = await uploadMeeting(input, name);
      for (let attempt = 0; attempt < 300; attempt++) {
        if (generation.current !== current) return;
        const res = await getMeeting(init.meeting_id);
        if (generation.current !== current) return;
        if (res.status === 'done') { setResult(res); return; }
        if (res.status === 'failed') throw new Error(res.error || '회의 분석 실패');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      throw new Error('분석 대기 시간이 초과되었습니다. Worker 상태를 확인하세요.');
    } catch (err) {
      if (generation.current === current) alert(err.message);
    } finally {
      if (generation.current === current) setLoading(false);
    }
  };

  const handleRegister = async (ev) => {
    try {
      await createEvent({
        title: ev.title,
        start_at: ev.start_at,
        end_at: ev.end_at,
        source: 'meeting',
        memo: `회의 출처: ${name}`,
        done: false
      });
      alert('회의 일정이 캘린더에 등록되었습니다.');
    } catch (err) {
      alert('일정 등록 실패');
    }
  };

  return (
    <div className="content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">MEETING INTELLIGENCE</p>
          <h1>◉ AI 회의록 분석</h1>
          <p className="subtitle">회의 내용을 정리하고, 실제로 실행할 일정만 골라 캘린더에 등록합니다.</p>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <form onSubmit={handleAnalyze}>
            <div className="field">
              <label>회의 이름</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label>회의 내용 텍스트</label>
              <textarea value={text} onChange={(e) => setText(e.target.value)} required={!file} rows={8} />
            </div>
            <div className="field">
              <label>회의 파일 (선택하면 텍스트 대신 분석)</label>
              <input type="file" accept=".txt,.mp3,.m4a,.wav,.webm,.ogg" onChange={e => setFile(e.target.files[0] || null)} />
            </div>
            <button className="btn primary" type="submit" style={{ width: '100%' }} disabled={loading}>
              {loading ? '분석 처리 중...' : '✦ 요약 및 일정 추출'}
            </button>
          </form>
        </div>

        <div className="panel">
          <h3 className="panel-title">회의 분석 결과</h3>
          {!result ? (
            <div className="result-empty">
              <div className="empty-icon">◉</div>
              <strong>아직 분석한 회의가 없어요</strong>
            </div>
          ) : (
            <div>
              <p className="helper"><strong>요약:</strong> {result.summary}</p>
              <hr className="divider" />
              <h4>추출된 일정 후보</h4>
              {result.events.map((ev, i) => (
                <div key={i} className="proposal">
                  <div className="proposal-body">
                    <strong>{ev.title}</strong>
                    <p>{ev.start_at}</p>
                  </div>
                  <button className="btn small primary" onClick={() => handleRegister(ev)}>등록</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}