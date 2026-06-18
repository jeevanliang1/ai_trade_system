import { defaultTwoYearDateRange } from "./dateRange";

test("defaultTwoYearDateRange returns current day and same day two years earlier", () => {
  expect(defaultTwoYearDateRange(new Date("2026-06-18T08:00:00+08:00"))).toEqual({
    start_date: "20240618",
    end_date: "20260618"
  });
});
