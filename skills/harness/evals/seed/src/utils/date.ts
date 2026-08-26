export function formatDate(date: Date, tz = "UTC"): string {
  const t = new Intl.DateTimeFormat("sv-SE", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
  return t.replace("T", " ");
}
