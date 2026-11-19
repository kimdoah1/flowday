import React from 'react';
import { approveProposal, rejectProposal } from '../api/client';

export default function InboxPage({ proposals = [], error = '', onRefresh = async () => {} }) {
  const handleApprove = async (id) => {
    try {
      await approveProposal(id);
      alert('일정이 승인되어 캘린더에 추가되었습니다.');
      await onRefresh();
    } catch (err) {
      alert('승인 처리 실패');
    }
  };

  const handleReject = async (id) => {
    try {
      await rejectProposal(id);
      alert('후보 일정을 거절(삭제)했습니다.');
      await onRefresh();
    } catch (err) {
      alert('거절 처리 실패');
    }
  };

  return (
    <div className="content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SMART CHAT CAPTURE</p>
          <h1>▤ 채팅 일정 추출 (검토함)</h1>
          <p className="subtitle">대화 속 날짜와 약속을 발견하고, 승인한 일정만 캘린더에 반영합니다.</p>
        </div>
      </div>

      <div className="panel">
        <button className="btn small" onClick={onRefresh}>새로고침</button>
        {error && <p className="event-error" role="alert">{error}</p>}
        <h3 className="panel-title">일정 후보 검토 ({proposals.length}개 대기 중)</h3>
        {proposals.length === 0 ? (
          <div className="empty-note">{error ? '서버 연결을 확인한 뒤 다시 시도해 주세요.' : '검토할 대기 중인 일정이 없습니다.'}</div>
        ) : (
          proposals.map((p) => (
            <div key={p.proposal_id} className="proposal">
              <div className="proposal-body">
                <strong>{p.title}</strong>
                <p>"{p.original_text}"</p>
                <span className="proposal-source">{p.start_at} · 출처: {p.source}</span>
              </div>
              <div className="proposal-actions">
                <button className="btn small primary" onClick={() => handleApprove(p.proposal_id)}>승인</button>
                <button className="btn small" onClick={() => handleReject(p.proposal_id)}>거절</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}