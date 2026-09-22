import "./setup.js";
import assert from "node:assert/strict";
import { test } from "node:test";

import { buildServer } from "../src/server.js";

// `.inject()` de Fastify -- contrato HTTP real (rutas, hooks, serializacion)
// sin abrir un socket TCP real y SIN tocar whatsapp_gateway/src/whatsapp/socket.ts
// mas alla de leer su estado inicial (nunca se llama /session/start en estos
// tests -- cero conexion real a Baileys, a proposito, ver AUDITORIA/
// WHATSAPP_BAILEYS_ARCHITECTURE.md sobre el incidente de conexion real de la
// Fase 7-8).

test("GET /health responde 200 sin token (Fase 21: healthcheck de Docker sin credenciales)", async () => {
  const app = await buildServer();
  const res = await app.inject({ method: "GET", url: "/health" });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.json(), { status: "ok", service: "whatsapp_gateway", provider: "baileys" });
  await app.close();
});

test("GET /status sin token responde 401", async () => {
  const app = await buildServer();
  const res = await app.inject({ method: "GET", url: "/status" });
  assert.equal(res.statusCode, 401);
  await app.close();
});

test("GET /status con token invalido responde 401", async () => {
  const app = await buildServer();
  const res = await app.inject({ method: "GET", url: "/status", headers: { "x-gateway-token": "wrong" } });
  assert.equal(res.statusCode, 401);
  await app.close();
});

test("GET /status con token correcto responde 200 con el contrato real, sin sesion", async () => {
  const app = await buildServer();
  const res = await app.inject({
    method: "GET",
    url: "/status",
    headers: { "x-gateway-token": process.env.WA_GATEWAY_INTERNAL_TOKEN! },
  });
  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.equal(body.provider, "baileys");
  assert.equal(body.status, "DISCONNECTED");
  assert.equal(body.qr_available, false);
  await app.close();
});

test("POST /messages/send sin recipient/text responde 400", async () => {
  const app = await buildServer();
  const res = await app.inject({
    method: "POST",
    url: "/messages/send",
    headers: { "x-gateway-token": process.env.WA_GATEWAY_INTERNAL_TOKEN!, "content-type": "application/json" },
    payload: {},
  });
  assert.equal(res.statusCode, 400);
  await app.close();
});

test("POST /messages/send sin socket conectado responde FAILED, nunca lanza sin control", async () => {
  const app = await buildServer();
  const res = await app.inject({
    method: "POST",
    url: "/messages/send",
    headers: { "x-gateway-token": process.env.WA_GATEWAY_INTERNAL_TOKEN!, "content-type": "application/json" },
    payload: { recipient: "573000000000", text: "hola" },
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.json().accepted, false);
  await app.close();
});

test("POST /messages/send aplica rate limit real (Fase 20): la 21a peticion en 1 minuto responde 429", async () => {
  const app = await buildServer();
  const headers = { "x-gateway-token": process.env.WA_GATEWAY_INTERNAL_TOKEN!, "content-type": "application/json" };
  const payload = { recipient: "573000000000", text: "hola" };

  let lastStatus = 0;
  for (let i = 0; i < 21; i++) {
    // remoteAddress fijo: el keyGenerator por defecto del plugin agrupa por
    // IP -- sin esto, .inject() puede no dar una IP estable entre llamadas
    // y cada peticion se contaria como un cliente distinto (bucket nunca
    // se llena). En produccion real el caller es siempre Django, misma
    // maquina/red -- fijar la IP aqui refleja ese caso real, no lo fuerza.
    const res = await app.inject({ method: "POST", url: "/messages/send", headers, payload, remoteAddress: "10.0.0.5" });
    lastStatus = res.statusCode;
  }
  assert.equal(lastStatus, 429, "la peticion numero 21 debe ser rechazada por el rate limit (max 20/min)");
  await app.close();
});
