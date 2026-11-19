export function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
export function monthCells(year, monthIndex) {
  const start = new Date(year, monthIndex, 1);
  const offset = start.getDay();
  const days = new Date(year, monthIndex + 1, 0).getDate();
  const result = Array(offset).fill(null);
  for (let d = 1; d <= days; d++) result.push(dateKey(new Date(year, monthIndex, d)));
  while (result.length % 7 !== 0) result.push(null);
  return result;
}
export function eventsForDay(events, day) {
  return events.filter(event => event.start_at?.slice(0, 10) === day);
}
export function countDone(events) { return events.filter(event => event.done).length; }
export const SOURCE_LABEL = { manual:'직접 등록', ai_plan:'AI 계획', meeting:'회의', discord:'Discord' };

// Keep the selected day when changing month, clamping to the month's last day.
export function dateInMonth(selected, year, monthIndex) {
  const month = new Date(year, monthIndex, 1);
  const last = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const day = Math.min(Number(selected.slice(8, 10)) || 1, last);
  return dateKey(new Date(month.getFullYear(), month.getMonth(), day));
}

export function groupEventsByDay(events) {
  const groups = new Map();
  for (const event of [...events].sort((a, b) => new Date(a.start_at) - new Date(b.start_at))) {
    const day = event.start_at.slice(0, 10);
    if (!groups.has(day)) groups.set(day, []);
    groups.get(day).push(event);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}
