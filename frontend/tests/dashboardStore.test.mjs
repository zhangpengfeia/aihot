import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';

const cache = new Map();
globalThis.localStorage = {
  getItem:key => cache.get(key) ?? null,
  setItem:(key,value) => cache.set(key,value),
  removeItem:key => cache.delete(key),
};
const response = value => new Response(JSON.stringify(value), {status:200, headers:{'Content-Type':'application/json'}});
const deferred = () => {let resolve; const promise = new Promise(r => {resolve=r;}); return {promise,resolve};};
const moduleUrl = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const compile = source => ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
let sequence = 0;
async function freshStore() {
  const httpUrl = moduleUrl(compile(readFileSync(new URL('../src/api/http.ts', import.meta.url),'utf8')));
  const source = compile(readFileSync(new URL('../src/store/dashboardStore.ts', import.meta.url),'utf8'))
    .replace("from 'zustand'",`from '${import.meta.resolve('zustand')}'`)
    .replace("from 'zustand/middleware'",`from '${import.meta.resolve('zustand/middleware')}'`)
    .replace("from '../api/http'",`from '${httpUrl}'`);
  return import(`${moduleUrl(source)}#${sequence++}`);
}

test('guest persistence, legacy expansion, empty selection and account isolation',async () => {
  cache.clear();
  cache.set('aihot-dashboard-guest',JSON.stringify(['hotlists','projects']));
  let requests = 0;
  globalThis.fetch = async () => {requests++; return response({cards:[]});};
  const {useDashboardStore:store,normalizeCards} = await freshStore();
  store.getState().activate('guest');
  assert.deepEqual(store.getState().layouts.guest.cards,['hotlists','overview','new_entries','risers','growth']);
  store.getState().setCards('guest',[]);
  store.getState().activate('user:10');
  assert.ok(store.getState().layouts['user:10'].cards.length);
  const reloaded = (await freshStore()).useDashboardStore;
  reloaded.getState().activate('guest');
  assert.deepEqual(reloaded.getState().layouts.guest.cards,[]);
  assert.equal(requests,0);
  assert.deepEqual(normalizeCards(['growth','unknown','growth','favorites']),['growth','favorites']);
});

test('serial writes coalesce rapid reorders and persist the latest order',async () => {
  cache.clear();
  const first = deferred();
  const writes = [];
  globalThis.fetch = async (_,options) => {
    writes.push(JSON.parse(options.body).cards);
    return writes.length === 1 ? first.promise : response({cards:writes.at(-1)});
  };
  const store = (await freshStore()).useDashboardStore;
  store.getState().activate('user:1');
  store.getState().setCards('user:1',['growth','knowledge']);
  store.getState().setCards('user:1',['knowledge','growth']);
  store.getState().setCards('user:1',['hotlists','growth']);
  assert.equal(writes.length,1);
  first.resolve(response({cards:['growth','knowledge']}));
  await store.getState().sync('user:1');
  assert.deepEqual(writes,[['growth','knowledge'],['hotlists','growth']]);
  assert.equal(store.getState().layouts['user:1'].dirty,false);
  assert.deepEqual(JSON.parse(cache.get('aihot-dashboard-layouts')).state.layouts['user:1'].cards,['hotlists','growth']);
});

test('slow initial read cannot overwrite a newer drag order',async () => {
  cache.clear();
  const read = deferred();
  globalThis.fetch = async (_,options) => options?.method === 'PUT' ? response({}) : read.promise;
  const store = (await freshStore()).useDashboardStore;
  store.getState().activate('user:2');
  const loading = store.getState().load('user:2');
  store.getState().setCards('user:2',['favorites','growth']);
  await store.getState().sync('user:2');
  read.resolve(response({cards:['projects']}));
  await loading;
  assert.deepEqual(store.getState().layouts['user:2'].cards,['favorites','growth']);
});

test('offline changes survive reload and retry, including all-hidden layout',async () => {
  cache.clear();
  globalThis.fetch = async () => {throw new Error('offline');};
  let store = (await freshStore()).useDashboardStore;
  store.getState().activate('user:3');
  store.getState().setCards('user:3',[]);
  await store.getState().sync('user:3');
  assert.equal(store.getState().layouts['user:3'].dirty,true);
  assert.equal(store.getState().errors['user:3'],'offline');
  store = (await freshStore()).useDashboardStore;
  store.getState().activate('user:3');
  let sent;
  globalThis.fetch = async (_,options) => {sent=JSON.parse(options.body); return response(sent);};
  await store.getState().load('user:3');
  assert.deepEqual(sent,{cards:[]});
  assert.equal(store.getState().layouts['user:3'].dirty,false);
});

test('account switch prevents queued old-account writes',async () => {
  cache.clear();
  const first = deferred();
  let writes = 0;
  globalThis.fetch = async () => {writes++;return first.promise;};
  const store = (await freshStore()).useDashboardStore;
  store.getState().activate('user:4');
  store.getState().setCards('user:4',['growth']);
  store.getState().setCards('user:4',['knowledge']);
  store.getState().activate('user:5');
  first.resolve(response({}));
  await store.getState().sync('user:4');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(writes,1);
  assert.equal(store.getState().layouts['user:4'].dirty,true);
  assert.notDeepEqual(store.getState().layouts['user:5'].cards,['knowledge']);
});
