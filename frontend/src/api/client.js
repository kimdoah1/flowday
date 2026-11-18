import * as mock from './mock';

const USE_MOCK = true;
const BASE_URL = '/api';

const request = async (url, options = {}) => {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: '요청 처리 실패' }));
    throw new Error(errorData.detail || '서버 오류');
  }
  return res.status === 204 ? null : res.json();
};

export const listEvents = async (start, end) => {
  if (USE_MOCK) return mock.mockListEvents();
  const query = start && end ? `?start=${start}&end=${end}` : '';
  return request(`/events${query}`);
};

export const createEvent = async (payload) => {
  if (USE_MOCK) return mock.mockCreateEvent(payload);
  return request('/events', { method: 'POST', body: JSON.stringify(payload) });
};

export const updateEvent = async (eventId, payload) => {
  if (USE_MOCK) return mock.mockUpdateEvent(eventId, payload);
  return request(`/events/${eventId}`, { method: 'PATCH', body: JSON.stringify(payload) });
};

export const deleteEvent = async (eventId) => {
  if (USE_MOCK) return mock.mockDeleteEvent(eventId);
  return request(`/events/${eventId}`, { method: 'DELETE' });
};

export const aiPlan = async (payload) => {
  if (USE_MOCK) return mock.mockAiPlan(payload);
  return request('/ai/plan', { method: 'POST', body: JSON.stringify(payload) });
};

export const extractSchedule = async (payload) => {
  if (USE_MOCK) return mock.mockExtractSchedule(payload);
  return request('/ai/extract', { method: 'POST', body: JSON.stringify(payload) });
};

export const uploadMeeting = async (file, name) => {
  if (USE_MOCK) return mock.mockUploadMeeting();
  const formData = new FormData();
  if (file) formData.append('file', file);
  if (name) formData.append('name', name);
  const res = await fetch(`${BASE_URL}/meetings`, { method: 'POST', body: formData });
  return res.json();
};

export const getMeeting = async (meetingId) => {
  if (USE_MOCK) return mock.mockGetMeeting(meetingId);
  return request(`/meetings/${meetingId}`);
};

export const listProposals = async () => {
  if (USE_MOCK) return mock.mockListProposals();
  return request('/proposals');
};

export const createProposal = async (payload) => {
  if (USE_MOCK) return mock.mockCreateProposal(payload);
  return request('/proposals', { method: 'POST', body: JSON.stringify(payload) });
};

export const approveProposal = async (id) => {
  if (USE_MOCK) return mock.mockApproveProposal(id);
  return request(`/proposals/${id}/approve`, { method: 'POST' });
};

export const rejectProposal = async (id) => {
  if (USE_MOCK) return mock.mockRejectProposal(id);
  return request(`/proposals/${id}/reject`, { method: 'POST' });
};