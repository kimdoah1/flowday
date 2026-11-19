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
