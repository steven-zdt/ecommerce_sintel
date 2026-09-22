import "./setup.js";
import assert from "node:assert/strict";
import { test } from "node:test";

import { ConnectionState, ConnectionStateMachine, InvalidStateTransitionError } from "../src/state.js";

test("estado inicial es DISCONNECTED", () => {
  const machine = new ConnectionStateMachine();
  assert.equal(machine.state, ConnectionState.DISCONNECTED);
});

test("camino feliz completo: DISCONNECTED -> STARTING -> QR_REQUIRED -> PAIRING -> CONNECTED", () => {
  const machine = new ConnectionStateMachine();
  machine.transition(ConnectionState.STARTING);
  machine.transition(ConnectionState.QR_REQUIRED);
  machine.transition(ConnectionState.PAIRING);
  machine.transition(ConnectionState.CONNECTED);
  assert.equal(machine.state, ConnectionState.CONNECTED);
  assert.ok(machine.lastConnectedAt !== null, "lastConnectedAt debe registrarse al llegar a CONNECTED");
});

test("desconexion temporal: CONNECTED -> RECONNECTING -> CONNECTED", () => {
  const machine = new ConnectionStateMachine();
  machine.transition(ConnectionState.STARTING);
  machine.transition(ConnectionState.QR_REQUIRED);
  machine.transition(ConnectionState.PAIRING);
  machine.transition(ConnectionState.CONNECTED);
  machine.transition(ConnectionState.RECONNECTING);
  assert.ok(machine.lastDisconnectAt !== null);
  machine.transition(ConnectionState.CONNECTED);
  assert.equal(machine.state, ConnectionState.CONNECTED);
});

test("logout: CONNECTED -> LOGGED_OUT -> QR_REQUIRED", () => {
  const machine = new ConnectionStateMachine();
  machine.transition(ConnectionState.STARTING);
  machine.transition(ConnectionState.QR_REQUIRED);
  machine.transition(ConnectionState.PAIRING);
  machine.transition(ConnectionState.CONNECTED);
  machine.transition(ConnectionState.LOGGED_OUT);
  machine.transition(ConnectionState.QR_REQUIRED);
  assert.equal(machine.state, ConnectionState.QR_REQUIRED);
});

test("ANY -> ERROR siempre permitido, incluso desde DISCONNECTED", () => {
  const machine = new ConnectionStateMachine();
  machine.transition(ConnectionState.ERROR);
  assert.equal(machine.state, ConnectionState.ERROR);
});

test("transicion invalida (saltar pasos) lanza InvalidStateTransitionError", () => {
  const machine = new ConnectionStateMachine();
  assert.throws(
    () => machine.transition(ConnectionState.CONNECTED),
    InvalidStateTransitionError,
    "DISCONNECTED -> CONNECTED directo no es un salto valido del diagrama de la Fase 2",
  );
});

test("forceTransition nunca lanza, sin importar el estado de partida", () => {
  const machine = new ConnectionStateMachine();
  assert.doesNotThrow(() => machine.forceTransition(ConnectionState.CONNECTED));
  assert.equal(machine.state, ConnectionState.CONNECTED);
  assert.doesNotThrow(() => machine.forceTransition(ConnectionState.QR_REQUIRED));
  assert.equal(machine.state, ConnectionState.QR_REQUIRED);
});

test("transition a si mismo es un no-op valido (no lanza)", () => {
  const machine = new ConnectionStateMachine();
  assert.doesNotThrow(() => machine.transition(ConnectionState.DISCONNECTED));
});
