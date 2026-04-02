export function parseServerDate(value) {
  if (!value) {
    return null;
  }

  // Backend currently emits naive UTC timestamps. Interpret them as UTC
  // instead of browser-local time so countdowns stay correct.
  if (typeof value === "string" && !/[zZ]|[+-]\d{2}:\d{2}$/.test(value)) {
    return new Date(`${value}Z`);
  }

  return new Date(value);
}

export function getTimerSeconds(timer, now = new Date()) {
  if (!timer) {
    return 0;
  }

  if (timer.state === "paused") {
    return timer.paused_seconds || 0;
  }

  if (timer.state !== "running" || !timer.start_time) {
    return timer.remaining_seconds || 0;
  }

  const startedAtDate = parseServerDate(timer.start_time);
  if (!startedAtDate || Number.isNaN(startedAtDate.getTime())) {
    return timer.remaining_seconds || 0;
  }

  const startedAt = startedAtDate.getTime();
  const elapsedSeconds = Math.max(0, Math.floor((now.getTime() - startedAt) / 1000));
  return Math.max(0, (timer.total_seconds || 0) - elapsedSeconds);
}

export function formatTimer(timer, now = new Date()) {
  const seconds = getTimerSeconds(timer, now);
  const minutesPart = String(Math.floor(seconds / 60)).padStart(2, "0");
  const secondsPart = String(seconds % 60).padStart(2, "0");
  return `${minutesPart}:${secondsPart}`;
}
