/**
 * test/setup.ts
 *
 * Fase 23 del plan de migracion Baileys. Variables de entorno minimas para
 * que src/config.ts (fail-closed sin WA_GATEWAY_INTERNAL_TOKEN) no aborte
 * al importarse desde los tests. Debe ser el PRIMER import de cada archivo
 * de test (el orden de evaluacion de modulos ES sigue el orden de los
 * imports -- esto corre antes de que cualquier modulo de src/ se evalue).
 */
process.env.WA_GATEWAY_INTERNAL_TOKEN ||= "test-suite-token";
process.env.WA_SESSION_STORAGE ||= "file";
process.env.WA_AUTH_STORAGE_DIR ||= "test/.tmp/auth-store";
process.env.WA_LOG_LEVEL ||= "silent";
process.env.WA_RECONNECT_ENABLED ||= "false";
