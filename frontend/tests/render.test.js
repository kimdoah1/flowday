import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import React from 'react';
import { renderToString } from 'react-dom/server';

test('calendar, dashboard and event modal render', async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    for (const [file, label, props] of [
      ['pages/CalendarPage.jsx', '캘린더', {}],
      ['pages/DashboardPage.jsx', '대시보드', {}],
      ['components/EventModal.jsx', '새 일정 추가', { selectedDate: '2026-11-20', onClose() {} }],
    ]) {
      const { default: Component } = await vite.ssrLoadModule(`/src/${file}`);
      const html = renderToString(React.createElement(Component, props));
      assert.ok(html.includes(label));
      assert.ok(!html.includes('undefined'));
    }
  } finally { await vite.close(); }
});
