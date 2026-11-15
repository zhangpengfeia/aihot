import { useSyncExternalStore } from 'react';

const mobileLayout = window.matchMedia(
  '(max-width: 767px), (max-width: 950px) and (hover: none) and (pointer: coarse)',
);

function subscribe(onChange: () => void) {
  mobileLayout.addEventListener('change', onChange);
  return () => mobileLayout.removeEventListener('change', onChange);
}

export function useMobileLayout() {
  return useSyncExternalStore(subscribe, () => mobileLayout.matches);
}
