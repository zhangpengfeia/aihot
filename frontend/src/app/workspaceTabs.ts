import type { ViewKey } from './navigation';
export interface WorkspaceTabs {
  active: ViewKey;
  opened: ViewKey[];
}
export const initialTabs: WorkspaceTabs = { active: 'summary', opened: ['summary'] };
export function openTab(state: WorkspaceTabs, view: ViewKey): WorkspaceTabs {
  return {
    active: view,
    opened: state.opened.includes(view) ? state.opened : [...state.opened, view],
  };
}
export function closeTab(state: WorkspaceTabs, view: ViewKey): WorkspaceTabs {
  if (view === 'summary' || !state.opened.includes(view)) return state;
  const index = state.opened.indexOf(view);
  const opened = state.opened.filter((key) => key !== view);
  return { opened, active: state.active === view ? opened[Math.max(0, index - 1)] : state.active };
}
