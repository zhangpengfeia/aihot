import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = ts.transpileModule(readFileSync(new URL('../src/app/workspaceTabs.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const { openTab, closeTab, initialTabs } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

test('returning to an opened page retains its tab identity without duplicates', () => {
  let state = openTab(initialTabs, 'knowledge');
  state = openTab(state, 'today');
  const pages = state.opened;
  state = openTab(state, 'knowledge');
  assert.equal(state.active, 'knowledge');
  assert.equal(state.opened, pages);
  assert.deepEqual(state.opened, ['summary', 'knowledge', 'today']);
});
test('closing active page selects its neighbour; closing background page preserves active page', () => {
  let state = openTab(openTab(initialTabs, 'knowledge'), 'today');
  state = closeTab(state, 'today');
  assert.deepEqual(state, { active: 'knowledge', opened: ['summary', 'knowledge'] });
  state = openTab(state, 'history');
  state = closeTab(state, 'knowledge');
  assert.equal(state.active, 'history');
  assert.deepEqual(closeTab(state, 'history'), initialTabs);
});
test('home cannot close; reopening a closed page creates a fresh entry', () => {
  assert.equal(closeTab(initialTabs, 'summary'), initialTabs);
  const state = closeTab(openTab(initialTabs, 'today'), 'today');
  assert.deepEqual(openTab(state, 'today').opened, ['summary', 'today']);
  assert.deepEqual(initialTabs, { active: 'summary', opened: ['summary'] });
});
