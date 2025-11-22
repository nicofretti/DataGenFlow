// format elapsed time from start date
export function getElapsedTime(startTime: string): string {
  const start = new Date(startTime);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);

  if (seconds < 60) return `${seconds}s`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;

  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

// truncate text for display
export function truncateText(text: any, maxLength: number = 100): string {
  const str = typeof text === "string" ? text : JSON.stringify(text);
  return str.length > maxLength ? str.substring(0, maxLength) + "..." : str;
}

export function getElapsedTimeBetween(
  endTime: number | string,
  startTime: number | string
): string {
  const start = new Date(startTime);
  const end = new Date(endTime);
  const seconds = Math.floor((end.getTime() - start.getTime()) / 1000);

  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}
