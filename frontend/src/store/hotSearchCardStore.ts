import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
export const DEFAULT_HOT_SUBSCRIPTIONS = ['baidu', 'weibo', 'zhihu', 'juejin', 'readhub'];
export const useHotSearchCardStore = create<{
  subscriptions: Record<string, string[]>;
  save: (scope: string, ids: string[]) => void;
}>()(
  persist(
    (set) => ({
      subscriptions: {},
      save: (scope, ids) =>
        set((state) => ({ subscriptions: { ...state.subscriptions, [scope]: [...new Set(ids)] } })),
    }),
    {
      name: 'aihot-home-hot-card',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ subscriptions: state.subscriptions }),
    },
  ),
);
