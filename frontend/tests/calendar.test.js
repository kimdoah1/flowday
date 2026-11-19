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
