/**
 * Load Test: GET payment/payments/feature-flags/ (ADR-001 Fase 9)
 *
 * De todos los endpoints nuevos del proyecto de migracion a integracion API
 * propia con Wompi, este es el UNICO candidato razonable para una prueba de
 * carga: es publico (AllowAny, sin JWT que gestionar por VU), sin estado
 * (lee un singleton, PaymentFeatureFlags.get_active()), y se llama en CADA
 * carga de /checkout (CheckoutView.vue::fetchFeatureFlags()) -- si este
 * endpoint se degrada, se degrada el checkout completo, no solo el flujo de
 * tarjeta. El resto de endpoints nuevos de este proyecto (initialize/,
 * resync/, events/) requieren JWT + datos de orden/transaccion reales por
 * request, y varios de ellos (initialize/ con card_token) llamarian a la API
 * real de Wompi bajo carga -- fuera de alcance sin autorizacion explicita,
 * ver payment/.AGENT/docs/FASE2_ADAPTADOR_WOMPI.md.
 *
 * Execution: node --max-old-space-size=2048 payment-feature-flags-load-node.js
 */

import http from 'http';
import { performance } from 'perf_hooks';

const API_HOST = 'localhost';
const API_PORT = 8000;
const API_PATH = '/api/v1/payment/payments/feature-flags/';
const CONCURRENT_VUS = 50;
const DURATION_SECONDS = 15;
const REQUEST_INTERVAL_MS = 100;

const metrics = {
  totalRequests: 0,
  successfulRequests: 0,
  failedRequests: 0,
  responseTimes: [],
  errors: [],
};

function fetchFeatureFlags() {
  return new Promise((resolve) => {
    const startTime = performance.now();
    const req = http.request(
      { host: API_HOST, port: API_PORT, path: API_PATH, method: 'GET', timeout: 5000 },
      (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          const duration = performance.now() - startTime;
          metrics.responseTimes.push(duration);
          metrics.totalRequests++;
          try {
            const json = JSON.parse(data);
            if (res.statusCode === 200 && typeof json.card_api_flow_enabled === 'boolean') {
              metrics.successfulRequests++;
            } else {
              metrics.failedRequests++;
              metrics.errors.push(`Respuesta inesperada (status ${res.statusCode}): ${data.slice(0, 100)}`);
            }
          } catch (e) {
            metrics.failedRequests++;
            metrics.errors.push(`Error parseando JSON: ${e.message}`);
          }
          resolve();
        });
      },
    );
    req.on('timeout', () => { req.destroy(); metrics.failedRequests++; metrics.totalRequests++; metrics.errors.push('Timeout'); resolve(); });
    req.on('error', (err) => {
      metrics.failedRequests++;
      metrics.totalRequests++;
      metrics.errors.push(`Error de conexion: ${err.message}`);
      resolve();
    });
    req.end();
  });
}

async function virtualUser(userId) {
  const startTime = Date.now();
  let requestCount = 0;
  while (Date.now() - startTime < DURATION_SECONDS * 1000) {
    await fetchFeatureFlags();
    requestCount++;
    await new Promise((resolve) => setTimeout(resolve, REQUEST_INTERVAL_MS));
  }
  return requestCount;
}

async function runLoadTest() {
  console.log('='.repeat(80));
  console.log('PAYMENT FEATURE FLAGS LOAD TEST — ADR-001 FASE 9');
  console.log('='.repeat(80));
  console.log(`Endpoint: http://${API_HOST}:${API_PORT}${API_PATH}`);
  console.log(`VUs concurrentes: ${CONCURRENT_VUS} | Duracion: ${DURATION_SECONDS}s`);
  console.log('');

  const startTime = Date.now();
  await Promise.all(Array.from({ length: CONCURRENT_VUS }, (_, i) => virtualUser(i)));
  const duration = (Date.now() - startTime) / 1000;

  const times = metrics.responseTimes.sort((a, b) => a - b);
  const p50 = times[Math.floor(times.length * 0.5)] ?? 0;
  const p95 = times[Math.floor(times.length * 0.95)] ?? 0;
  const p99 = times[Math.floor(times.length * 0.99)] ?? 0;
  const avg = times.length ? times.reduce((a, b) => a + b, 0) / times.length : 0;
  const successRate = metrics.totalRequests ? ((metrics.successfulRequests / metrics.totalRequests) * 100).toFixed(2) : '0';
  const throughput = (metrics.totalRequests / duration).toFixed(2);

  console.log('RESULTADOS');
  console.log('='.repeat(80));
  console.log(`Duracion real: ${duration.toFixed(2)}s`);
  console.log(`Total requests: ${metrics.totalRequests}`);
  console.log(`Exitosos: ${metrics.successfulRequests} | Fallidos: ${metrics.failedRequests}`);
  console.log(`Tasa de exito: ${successRate}%`);
  console.log('');
  console.log('Tiempo de respuesta (ms):');
  console.log(`  p50: ${p50.toFixed(2)}ms  p95: ${p95.toFixed(2)}ms  p99: ${p99.toFixed(2)}ms  avg: ${avg.toFixed(2)}ms`);
  console.log('');
  console.log(`Throughput: ${throughput} req/s`);
  console.log('');

  const checks = [
    { name: 'p99 response time < 200ms', passed: p99 < 200, actual: `${p99.toFixed(2)}ms` },
    { name: 'Tasa de exito >= 99%', passed: parseFloat(successRate) >= 99, actual: `${successRate}%` },
    { name: 'Throughput >= 20 req/s', passed: parseFloat(throughput) >= 20, actual: `${throughput} req/s` },
  ];
  console.log('CHECKLIST DE VALIDACION');
  console.log('='.repeat(80));
  checks.forEach((c) => console.log(`${c.passed ? '✓' : '✗'} ${c.name.padEnd(30)} ${c.actual.padStart(12)}`));
  const allPassed = checks.every((c) => c.passed);
  console.log('');
  console.log(allPassed ? '✓ TODOS LOS CHECKS PASARON' : '✗ ALGUNOS CHECKS FALLARON');
  console.log('='.repeat(80));

  if (metrics.errors.length > 0) {
    console.log('\nErrores (unicos):');
    [...new Set(metrics.errors)].forEach((e) => console.log(`  - ${e}`));
  }

  process.exit(allPassed ? 0 : 1);
}

runLoadTest().catch((err) => {
  console.error('Load test fallo:', err);
  process.exit(1);
});
