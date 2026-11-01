import { usePageActive } from '../app/pageActivity';
import { useEffect, useState } from 'react';
/** 页面轮询只读接口，真正采集由独立 worker 执行。 */
export function useRefreshTick(interval: number | null = 60_000) {
  const active = usePageActive();
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (interval === null || !active) return;
    const timer = window.setInterval(() => setTick((v) => v + 1), interval);
    return () => window.clearInterval(timer);
  }, [interval, active]);
  return { tick, refresh: () => setTick((v) => v + 1) };
}
