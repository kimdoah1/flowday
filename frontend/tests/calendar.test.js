import test from 'node:test';
import assert from 'node:assert/strict';
import {dateKey, monthCells, eventsForDay, countDone} from '../src/utils/calendar.js';
test('local dates remain on the selected day', ()=> assert.equal(dateKey(new Date(2026,10,13)), '2026-11-13'));
test('month aligns weekdays and keeps 7 columns', ()=> {
  const cells=monthCells(2026,10);
  assert.equal(cells.length%7,0);
  assert.equal(cells[0], '2026-11-01');
  assert.equal(cells.filter(Boolean).length,30);
});
test('date filtering and done state',()=>{
  const events=[{start_at:'2026-11-13T09:00:00+09:00',done:true},{start_at:'2026-11-14T09:00:00+09:00',done:false}];
  assert.equal(eventsForDay(events,'2026-11-13').length,1);
  assert.equal(countDone(events),1);
});
test('leap year and December rollover', () => {
  assert.equal(monthCells(2028, 1).filter(Boolean).length, 29);
  assert.equal(dateKey(new Date(2026, 12, 1)), '2027-01-01');
});

test('changing month clamps the selected day, including leap years and year rollover', async () => {
  const { dateInMonth } = await import('../src/utils/calendar.js');
  assert.equal(dateInMonth('2026-01-31', 2026, 1), '2026-02-28');
  assert.equal(dateInMonth('2028-01-31', 2028, 1), '2028-02-29');
  assert.equal(dateInMonth('2026-12-19', 2026, 12), '2027-01-19');
  assert.equal(dateInMonth('2026-01-19', 2026, -1), '2025-12-19');
});

test('all events includes other months, other years and completed events without mutating input', async () => {
  const { groupEventsByDay } = await import('../src/utils/calendar.js');
  const events = [
    { event_id: 1, start_at: '2027-01-03T10:00:00+09:00', done: true },
    { event_id: 2, start_at: '2026-11-19T11:00:00+09:00' },
    { event_id: 3, start_at: '2026-11-19T09:00:00+09:00' },
  ];
  const groups = groupEventsByDay(events);
  assert.deepEqual(groups.map(([day]) => day), ['2026-11-19', '2027-01-03']);
  assert.deepEqual(groups[0][1].map(e => e.event_id), [3, 2]);
  assert.equal(groups[1][1][0].done, true);
  assert.deepEqual(events.map(e => e.event_id), [1, 2, 3]);
});
