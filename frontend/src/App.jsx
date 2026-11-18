import React, { useState } from 'react';
import PlanPage from './pages/PlanPage';
import MeetingPage from './pages/MeetingPage';
import InboxPage from './pages/InboxPage';
import DashboardPage from './pages/DashboardPage';
import CalendarPage from './pages/CalendarPage';

export default function App() {
  const [currentView, setCurrentView] = useState('planner');

  const navItems = [
    { key: 'dashboard', label: '대시보드', ico: '▦' },
    { key: 'calendar', label: '캘린더', ico: '▣' },
    { key: 'planner', label: 'AI 계획 세분화', ico: '✧', tag: 'AI' },
    { key: 'meetings', label: '회의록 분석', ico: '◉', tag: 'AI' },
    { key: 'inbox', label: '채팅 일정 추출', ico: '▤', count: '3' },
  ];

  const viewNames = {
    dashboard: '대시보드',
    calendar: '캘린더',
    planner: 'AI 계획 세분화',
    meetings: '회의록 분석',
    inbox: '채팅 일정 추출'
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">✦</div>
          <div>
            <strong>flowday</strong>
            <span>TEAM WORKSPACE</span>
          </div>
        </div>

        <div className="workspace-picker">
          <div className="workspace-avatar">N</div>
          <div>
            <strong>넥스트 프로젝트</strong>
            <small>Team workspace</small>
          </div>
          <span className="chevron">⌄</span>
        </div>

        <div className="nav-heading">WORKSPACE</div>
        <nav className="nav">
          {navItems.map(item => (
            <button
              key={item.key}
              className={`nav-link ${currentView === item.key ? 'active' : ''}`}
              onClick={() => setCurrentView(item.key)}
            >
              <span className="nav-ico">{item.ico}</span> {item.label}
              {item.tag && <span className="tag-new">{item.tag}</span>}
              {item.count && <span className="nav-count">{item.count}</span>}
            </button>
          ))}
        </nav>

        <div className="nav-heading teams-heading">MY PROJECTS</div>
        <div className="project-links">
          <button className="project-link">
            <span className="project-dot violet"></span> 오픈소스 SW 팀 프로젝트
          </button>
          <button className="project-link">
            <span className="project-dot mint"></span> 학기 학습 계획
          </button>
        </div>

        <div className="sidebar-bottom">
          <div className="plan-card">
            <span className="sparkle">✦</span>
            <strong>흩어진 약속을 한곳에</strong>
            <p>계획, 회의, 채팅의 일정을 하나의 캘린더로.</p>
            <button onClick={() => setCurrentView('planner')}>
              AI 계획 만들기 <span>↗</span>
            </button>
          </div>
          <div className="profile">
            <div className="profile-icon">박</div>
            <div>
              <strong>박수현</strong>
              <small>프론트엔드 개발자</small>
            </div>
            <span>•••</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>{viewNames[currentView]}</strong>
          </div>
          <div className="top-actions">
            <span className="demo-pill">
              <span className="live-dot"></span> 인터랙티브 데모 (박수현 브랜치)
            </span>
            <div className="mini-avatar">박</div>
          </div>
        </header>

        {currentView === 'dashboard' && <DashboardPage />}
        {currentView === 'calendar' && <CalendarPage />}
        {currentView === 'planner' && <PlanPage onNavigate={setCurrentView} />}
        {currentView === 'meetings' && <MeetingPage onNavigate={setCurrentView} />}
        {currentView === 'inbox' && <InboxPage />}
      </main>
    </div>
  );
}