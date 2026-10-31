import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { get, write } from '../api/http';

export const CARD_LABELS = {
  overview: '项目 · 批次概览',
  new_entries: '项目 · 新上榜',
  risers: '项目 · 排名上升',
  growth: '项目 · Star 增长',
  knowledge: '知识库 · 最新选题',
  hotlists: '全网热搜',
  favorites: '我的收藏',
} as const;
export type CardId = keyof typeof CARD_LABELS;
export const DEFAULT_CARDS: CardId[] = [
  'overview',
  'new_entries',
  'risers',
  'growth',
  'knowledge',
  'hotlists',
];
export type CardWidth = 'full' | 'half';
export const DEFAULT_WIDTHS: Record<CardId, CardWidth> = {
  overview: 'full',
  new_entries: 'half',
  risers: 'half',
  growth: 'full',
  knowledge: 'full',
  hotlists: 'full',
  favorites: 'full',
};
export function normalizeWidths(value: unknown): Record<CardId, CardWidth> {
  const widths = { ...DEFAULT_WIDTHS };
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    for (const id of Object.keys(CARD_LABELS) as CardId[]) {
      const width = (value as Record<string, unknown>)[id];
      if (width === 'full' || width === 'half') widths[id] = width;
    }
  }
  return widths;
}
interface Layout {
  cards: CardId[];
  widths: Record<CardId, CardWidth>;
  revision: number;
  dirty: boolean;
}
export const DEFAULT_LAYOUT: Layout = {
  cards: DEFAULT_CARDS,
  widths: DEFAULT_WIDTHS,
  revision: 0,
  dirty: false,
};
export const dashboardScope = (userId?: number) =>
  userId === undefined ? 'guest' : `user:${userId}`;
export function normalizeCards(value: unknown): CardId[] {
  if (!Array.isArray(value)) return [...DEFAULT_CARDS];
  const expanded = value.flatMap((id) => (id === 'projects' ? DEFAULT_CARDS.slice(0, 4) : [id]));
  return [
    ...new Set(
      expanded.filter(
        (id): id is CardId =>
          typeof id === 'string' && Object.prototype.hasOwnProperty.call(CARD_LABELS, id),
      ),
    ),
  ];
}
interface DashboardState {
  layouts: Record<string, Layout>;
  activeScope: string;
  syncing: Record<string, boolean>;
  errors: Record<string, string>;
  activate: (scope: string) => void;
  setCards: (scope: string, cards: CardId[]) => void;
  setWidth: (scope: string, card: CardId, width: CardWidth) => void;
  load: (scope: string) => Promise<void>;
  sync: (scope: string) => Promise<void>;
}
const requests = new Map<string, Promise<void>>();
export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, state) => ({
      layouts: {},
      activeScope: 'guest',
      syncing: {},
      errors: {},
      activate: (scope) => {
        let initial = DEFAULT_LAYOUT;
        if (scope === 'guest') {
          try {
            const old = localStorage.getItem('aihot-dashboard-guest');
            if (old) initial = { ...DEFAULT_LAYOUT, cards: normalizeCards(JSON.parse(old)) };
          } catch {
            /* 使用默认配置。 */
          }
        }
        set((current) => ({
          activeScope: scope,
          layouts: current.layouts[scope]
            ? current.layouts
            : { ...current.layouts, [scope]: initial },
        }));
      },
      setCards: (scope, cards) => {
        set((current) => ({
          layouts: {
            ...current.layouts,
            [scope]: {
              cards: normalizeCards(cards).filter((id) => scope !== 'guest' || id !== 'favorites'),
              widths: current.layouts[scope]?.widths ?? { ...DEFAULT_WIDTHS },
              revision: (current.layouts[scope]?.revision ?? 0) + 1,
              dirty: scope !== 'guest',
            },
          },
          errors: { ...current.errors, [scope]: '' },
        }));
        if (scope !== 'guest') void state().sync(scope);
      },
      setWidth: (scope, card, width) => {
        set((current) => {
          const layout = current.layouts[scope] ?? DEFAULT_LAYOUT;
          return {
            layouts: {
              ...current.layouts,
              [scope]: {
                ...layout,
                widths: { ...layout.widths, [card]: width },
                revision: layout.revision + 1,
                dirty: scope !== 'guest',
              },
            },
            errors: { ...current.errors, [scope]: '' },
          };
        });
        if (scope !== 'guest') void state().sync(scope);
      },
      load: async (scope) => {
        if (scope === 'guest') return;
        if (state().layouts[scope]?.dirty) {
          await state().sync(scope);
          return;
        }
        const revision = state().layouts[scope]?.revision ?? 0;
        try {
          const result = await get<{ cards: string[]; widths?: Record<string, unknown> }>(
            '/workspace/dashboard-preferences',
          );
          set((current) => {
            const layout = current.layouts[scope];
            // 慢速读取不得覆盖用户刚刚拖动后的本地配置。
            if (current.activeScope !== scope || layout?.dirty || layout?.revision !== revision)
              return current;
            return {
              layouts: {
                ...current.layouts,
                [scope]: {
                  cards: normalizeCards(result.cards),
                  widths: normalizeWidths(result.widths),
                  revision,
                  dirty: false,
                },
              },
              errors: { ...current.errors, [scope]: '' },
            };
          });
        } catch (e) {
          if (state().activeScope === scope)
            set((current) => ({ errors: { ...current.errors, [scope]: (e as Error).message } }));
        }
      },
      sync: (scope) => {
        if (scope === 'guest' || state().activeScope !== scope) return Promise.resolve();
        const running = requests.get(scope);
        if (running) return running;
        const request = (async () => {
          set((current) => ({ syncing: { ...current.syncing, [scope]: true } }));
          try {
            // 每个账号只允许一个写入请求；拖动期间产生的更新合并到下一轮。
            while (state().activeScope === scope && state().layouts[scope]?.dirty) {
              const layout = state().layouts[scope];
              await write('/workspace/dashboard-preferences', 'PUT', {
                cards: layout.cards,
                widths: layout.widths,
              });
              set((current) =>
                current.layouts[scope]?.revision !== layout.revision
                  ? current
                  : {
                      layouts: { ...current.layouts, [scope]: { ...layout, dirty: false } },
                      errors: { ...current.errors, [scope]: '' },
                    },
              );
            }
          } catch (e) {
            set((current) => ({ errors: { ...current.errors, [scope]: (e as Error).message } }));
          } finally {
            set((current) => ({ syncing: { ...current.syncing, [scope]: false } }));
          }
        })().finally(() => {
          requests.delete(scope);
        });
        requests.set(scope, request);
        return request;
      },
    }),
    {
      name: 'aihot-dashboard-layouts',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ layouts: state.layouts }),
      merge: (persisted, current) => {
        const entries =
          (persisted as { layouts?: Record<string, Layout> } | undefined)?.layouts ?? {};
        const layouts: Record<string, Layout> = {};
        for (const [scope, layout] of Object.entries(entries)) {
          if (
            (scope !== 'guest' && !/^user:\d+$/.test(scope)) ||
            !layout ||
            typeof layout !== 'object'
          )
            continue;
          layouts[scope] = {
            cards: normalizeCards(layout.cards).filter(
              (id) => scope !== 'guest' || id !== 'favorites',
            ),
            widths: normalizeWidths(layout.widths),
            revision: Number.isSafeInteger(layout.revision) ? layout.revision : 0,
            dirty: scope !== 'guest' && layout.dirty === true,
          };
        }
        return { ...current, layouts };
      },
    },
  ),
);
