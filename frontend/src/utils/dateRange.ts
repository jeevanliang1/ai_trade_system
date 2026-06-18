export function defaultTwoYearDateRange(today = new Date()): { start_date: string; end_date: string } {
  const end = dateKey(today);
  const startDate = new Date(today);
  startDate.setFullYear(today.getFullYear() - 2);
  return { start_date: dateKey(startDate), end_date: end };
}

function dateKey(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}${month}${day}`;
}
