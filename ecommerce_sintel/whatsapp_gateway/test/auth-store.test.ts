import "./setup.js";
import assert from "node:assert/strict";
import { rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { test } from "node:test";

import { FileAuthStateStore } from "../src/auth/fileAuthStateStore.js";

const TEST_DIR = path.resolve("test/.tmp/auth-store-unit");

async function freshStore(): Promise<FileAuthStateStore> {
  await rm(TEST_DIR, { recursive: true, force: true });
  return new FileAuthStateStore(TEST_DIR);
}

test("exists() es false antes de guardar nada", async () => {
  const store = await freshStore();
  assert.equal(await store.exists(), false);
});

test("getCreds() sin datos previos inicializa credenciales reales (initAuthCreds)", async () => {
  const store = await freshStore();
  const creds = await store.getCreds();
  assert.ok(creds.noiseKey, "initAuthCreds() debe producir un noiseKey real");
});

test("saveCreds() + exists() -- persistencia real en disco", async () => {
  const store = await freshStore();
  const creds = await store.getCreds();
  await store.saveCreds(creds);
  assert.equal(await store.exists(), true);
});

test("setKeys()/getKeys() -- round-trip preserva Buffer real, no solo el shape JSON", async () => {
  const store = await freshStore();
  await store.setKeys({
    "pre-key": { "1": { public: Buffer.from([1, 2, 3]), private: Buffer.from([4, 5, 6]) } as any },
  });
  const got = await store.getKeys("pre-key", ["1"]);
  assert.ok(Buffer.isBuffer((got["1"] as any).public), "el valor recuperado debe seguir siendo un Buffer real, no un objeto {type:'Buffer',data:[...]}");
  assert.deepEqual(Array.from((got["1"] as any).public as Buffer), [1, 2, 3]);
});

test("removeKeys() borra la clave -- getKeys() posterior no la devuelve", async () => {
  const store = await freshStore();
  await store.setKeys({ "pre-key": { "1": { v: 1 } as any } });
  await store.removeKeys("pre-key", ["1"]);
  const got = await store.getKeys("pre-key", ["1"]);
  assert.equal(Object.keys(got).length, 0);
});

test("acquireLock() dos veces desde el MISMO proceso no lanza (mismo PID)", async () => {
  const store = await freshStore();
  await store.acquireLock();
  await assert.doesNotReject(() => store.acquireLock());
});

test("acquireLock() con un lock huerfano (PID que ya no existe) se recupera, no lanza", async () => {
  const store = await freshStore();
  await store.acquireLock();
  await store.releaseLock();
  // PID improbable de existir realmente -- simula un crash previo sin cleanup.
  await writeFile(path.join(TEST_DIR, ".lock"), JSON.stringify({ pid: 999999, startedAt: new Date().toISOString() }));
  await assert.doesNotReject(() => store.acquireLock());
});

test("clear() borra creds + keys + lock -- exists() vuelve a false", async () => {
  const store = await freshStore();
  const creds = await store.getCreds();
  await store.saveCreds(creds);
  await store.setKeys({ "pre-key": { "1": { v: 1 } as any } });
  await store.acquireLock();
  await store.clear();
  assert.equal(await store.exists(), false);
  const got = await store.getKeys("pre-key", ["1"]);
  assert.equal(Object.keys(got).length, 0);
});

test.after(async () => {
  await rm(TEST_DIR, { recursive: true, force: true });
});
