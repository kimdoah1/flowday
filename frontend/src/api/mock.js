let dummyEvents = [
  {
    event_id: 1,
    title: "프로젝트 요구사항 정리",
    start_at: "2026-11-10T09:00:00+09:00",
    end_at: "2026-11-10T10:00:00+09:00",
    source: "ai_plan",
    memo: "초기 기획",
    done: true
  },
  {
    event_id: 2,
    title: "팀 주간 회의",
    start_at: "2026-11-12T14:00:00+09:00",
    end_at: "2026-11-12T15:00:00+09:00",
    source: "meeting",
    memo: "진행 상황 공유",
    done: false
  }
];

let dummyProposals = [
  {
    proposal_id: 1,
    title: "프론트엔드 1차 시안 리뷰",
    start_at: "2026-11-15T15:00:00+09:00",
    end_at: "2026-11-15T16:00:00+09:00",
    source: "discord",
    origin_message_id: "discord-msg-101",
    original_text: "@팀원 이번 주 일요일까지 프론트 시안 확인 부탁해요.",
    status: "pending"
  }
];

export const mockListEvents = async () => ({ events: dummyEvents });
export const mockCreateEvent = async (payload) => {
  const newEv = { event_id: Date.now(), done: false, memo: "", ...payload };
  dummyEvents.push(newEv);
  return newEv;
};
export const mockUpdateEvent = async (id, payload) => {
  dummyEvents = dummyEvents.map(e => e.event_id === id ? { ...e, ...payload } : e);
  return dummyEvents.find(e => e.event_id === id);
};
export const mockDeleteEvent = async (id) => {
  dummyEvents = dummyEvents.filter(e => e.event_id !== id);
  return null;
};
export const mockAiPlan = async (payload) => ({
  tasks: [
    { title: `${payload.goal} - 요구사항 확정`, date: "2026-11-11" },
    { title: `${payload.goal} - 핵심 기능 구현`, date: "2026-11-13" },
    { title: `${payload.goal} - 통합 테스트 및 배포`, date: payload.deadline || "2026-11-15" }
  ]
});
export const mockExtractSchedule = async ({ text }) => ({
  events: [
    { title: "추출된 팀 일정", start_at: "2026-11-14T14:00:00+09:00", end_at: "2026-11-14T15:00:00+09:00" }
  ]
});
export const mockUploadMeeting = async () => ({ meeting_id: 10, status: "waiting" });
export const mockGetMeeting = async (id) => ({
  meeting_id: id,
  status: "done",
  summary: "주간 프론트엔드 및 API 연동 일정을 확정함.",
  transcript: "회의 요약 텍스트 및 일정 논의 내용...",
  events: [
    { title: "API 명세 최종 완료", start_at: "2026-11-13T16:00:00+09:00", end_at: "2026-11-13T17:00:00+09:00" }
  ],
  error: null
});
export const mockListProposals = async () => ({ proposals: dummyProposals.filter(p => p.status === 'pending') });
export const mockCreateProposal = async (payload) => {
  const newProp = { proposal_id: Date.now(), status: "pending", ...payload };
  dummyProposals.push(newProp);
  return newProp;
};
export const mockApproveProposal = async (id) => {
  const p = dummyProposals.find(item => item.proposal_id === id);
  if (p) {
    p.status = "approved";
    const newEv = {
      event_id: Date.now(),
      title: p.title,
      start_at: p.start_at,
      end_at: p.end_at,
      source: "discord",
      memo: p.original_text,
      done: false
    };
    dummyEvents.push(newEv);
    return { event: newEv, status: "approved" };
  }
};
export const mockRejectProposal = async (id) => {
  dummyProposals = dummyProposals.map(p => p.proposal_id === id ? { ...p, status: "rejected" } : p);
  return { proposal_id: id, status: "rejected" };
};