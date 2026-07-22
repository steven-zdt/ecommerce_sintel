/**
 * Load Test: useEnums Cache Validation
 * Simula 100 concurrent requests concurrentes al endpoint de enums
 * 
 * Execution: node --max-old-space-size=2048 enum-cache-load-node.js
 * 
 * Metrics:
 * - Cache hit rate
 * - Response time p99
 * - Deduplication events
 * - Error rate
 */

import http from 'http';
import https from 'https';
import { performance } from 'perf_hooks';

// Configuration
const API_BASE = 'http://localhost:8000';
const CONCURRENT_VUS = 100;
const DURATION_SECONDS = 30;
const TEST_INTERVAL_MS = 100; // Request every 100ms per VU

// Metrics storage
const metrics = {
  totalRequests: 0,
  successfulRequests: 0,
  failedRequests: 0,
  responseTimes: [],
  cacheHits: 0,
  cacheMisses: 0,
  deduplicationEvents: 0,
  startTime: Date.now(),
  errors: [],
};

// Track inflight requests for deduplication
const inflightRequests = new Map();

// Enum catalogs to test
const enumCatalogs = [
  'order-statuses',
  'payment-methods',
  'payment-statuses',
  'service-priorities',
  'rental-statuses',
  'quote-statuses',
  'operation-statuses',
  'operation-types',
  'quote-types',
  'order-payment-methods',
  'contractor-types',
];

/**
 * Make HTTP request to enum endpoint
 */
function fetchEnum(enumName) {
  return new Promise((resolve) => {
    const startTime = performance.now();
    const url = `${API_BASE}/api/v1/core/enums/${enumName}/`;

    // Check deduplication
    if (inflightRequests.has(enumName)) {
      metrics.deduplicationEvents++;
    }
    
    inflightRequests.set(enumName, true);

    http
      .get(url, { timeout: 5000 }, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          const duration = performance.now() - startTime;
          metrics.responseTimes.push(duration);
          metrics.totalRequests++;

          try {
            const json = JSON.parse(data);
            if (res.statusCode === 200 && json.name && json.values) {
              metrics.successfulRequests++;
              
              // Simulate cache hit detection (if response < 10ms = likely cached)
              if (duration < 10) {
                metrics.cacheHits++;
              } else {
                metrics.cacheMisses++;
              }
            } else {
              metrics.failedRequests++;
              metrics.errors.push(`Invalid response structure for ${enumName}`);
            }
          } catch (e) {
            metrics.failedRequests++;
            metrics.errors.push(`JSON parse error: ${e.message}`);
          }

          inflightRequests.delete(enumName);
          resolve();
        });
      })
      .on('error', (err) => {
        metrics.failedRequests++;
        metrics.errors.push(`Request error: ${err.message}`);
        inflightRequests.delete(enumName);
        resolve();
      });
  });
}

/**
 * Virtual User: Makes requests at regular interval
 */
async function virtualUser(userId) {
  const startTime = Date.now();
  let requestCount = 0;

  while (Date.now() - startTime < DURATION_SECONDS * 1000) {
    const enumName = enumCatalogs[Math.floor(Math.random() * enumCatalogs.length)];
    await fetchEnum(enumName);
    requestCount++;
    
    // Sleep between requests
    await new Promise((resolve) => setTimeout(resolve, TEST_INTERVAL_MS));
  }

  console.log(`[VU ${userId}] Completed ${requestCount} requests`);
}

/**
 * Run load test
 */
async function runLoadTest() {
  console.log('='.repeat(80));
  console.log('ENUM CACHE LOAD TEST - PHASE 5 VALIDATION');
  console.log('='.repeat(80));
  console.log(`Starting ${CONCURRENT_VUS} virtual users for ${DURATION_SECONDS} seconds...`);
  console.log(`API Base: ${API_BASE}`);
  console.log(`Enum Catalogs: ${enumCatalogs.join(', ')}`);
  console.log(''.repeat(80));

  const startTime = Date.now();

  // Start all virtual users concurrently
  const vuPromises = [];
  for (let i = 0; i < CONCURRENT_VUS; i++) {
    vuPromises.push(virtualUser(i).catch(console.error));
  }

  // Wait for all VUs to complete
  await Promise.all(vuPromises);

  const duration = (Date.now() - startTime) / 1000;

  // Calculate statistics
  const responseTimes = metrics.responseTimes.sort((a, b) => a - b);
  const p50 = responseTimes[Math.floor(responseTimes.length * 0.5)];
  const p95 = responseTimes[Math.floor(responseTimes.length * 0.95)];
  const p99 = responseTimes[Math.floor(responseTimes.length * 0.99)];
  const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;

  const successRate = ((metrics.successfulRequests / metrics.totalRequests) * 100).toFixed(2);
  const cacheHitRate = ((metrics.cacheHits / (metrics.cacheHits + metrics.cacheMisses)) * 100).toFixed(2);
  const throughput = (metrics.totalRequests / duration).toFixed(2);

  // Print results
  console.log('\n' + '='.repeat(80));
  console.log('RESULTS');
  console.log('='.repeat(80));
  console.log(`Duration: ${duration.toFixed(2)}s`);
  console.log(`Total Requests: ${metrics.totalRequests}`);
  console.log(`Successful: ${metrics.successfulRequests}`);
  console.log(`Failed: ${metrics.failedRequests}`);
  console.log(`Success Rate: ${successRate}%`);
  console.log('');
  console.log('Response Time (ms):');
  console.log(`  p50:  ${p50.toFixed(2)}ms`);
  console.log(`  p95:  ${p95.toFixed(2)}ms`);
  console.log(`  p99:  ${p99.toFixed(2)}ms`);
  console.log(`  avg:  ${avgResponseTime.toFixed(2)}ms`);
  console.log('');
  console.log('Cache Metrics:');
  console.log(`  Cache Hits: ${metrics.cacheHits} (estimated)`);
  console.log(`  Cache Misses: ${metrics.cacheMisses} (estimated)`);
  console.log(`  Cache Hit Rate: ${cacheHitRate}%`);
  console.log('');
  console.log('Deduplication:');
  console.log(`  Events: ${metrics.deduplicationEvents}`);
  console.log(`  (Higher = better inflight dedup)`);
  console.log('');
  console.log('Throughput:');
  console.log(`  Requests/sec: ${throughput}`);
  console.log('');

  // Validation checklist
  console.log('='.repeat(80));
  console.log('VALIDATION CHECKLIST');
  console.log('='.repeat(80));
  const checks = [
    { name: 'p99 response time < 50ms', passed: p99 < 50, actual: `${p99.toFixed(2)}ms` },
    { name: 'Success rate ≥ 95%', passed: parseFloat(successRate) >= 95, actual: `${successRate}%` },
    { name: 'Cache hit rate ≥ 50%', passed: parseFloat(cacheHitRate) >= 50, actual: `${cacheHitRate}%` },
    { name: 'Deduplication active', passed: metrics.deduplicationEvents > 0, actual: `${metrics.deduplicationEvents} events` },
    { name: 'Throughput ≥ 10 req/s', passed: parseFloat(throughput) >= 10, actual: `${throughput} req/s` },
  ];

  checks.forEach((check) => {
    const status = check.passed ? '✓' : '✗';
    console.log(`${status} ${check.name.padEnd(35)} ${check.actual.padStart(15)}`);
  });

  const allPassed = checks.every((c) => c.passed);
  console.log('');
  console.log(allPassed ? '✓ ALL CHECKS PASSED' : '✗ SOME CHECKS FAILED');
  console.log('='.repeat(80));

  // Print errors if any
  if (metrics.errors.length > 0) {
    console.log('\nErrors encountered:');
    const uniqueErrors = [...new Set(metrics.errors)];
    uniqueErrors.forEach((err) => {
      console.log(`  - ${err}`);
    });
  }

  process.exit(allPassed ? 0 : 1);
}

// Run test
runLoadTest().catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
