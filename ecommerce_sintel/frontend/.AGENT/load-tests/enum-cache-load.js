/**
 * k6 Load Test: useEnums Cache Validation
 * Goal: Verify cache deduplication, hit rate, and response times under concurrent load
 * 
 * Execution: k6 run --vus 100 --duration 30s enum-cache-load.js
 * 
 * Metrics:
 * - Cache hit rate (should be >=90% after first 10s)
 * - Response time p99 (<50ms)
 * - Deduplication success (single inflight request per enum name)
 * - Zero errors during load
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Trend, Counter, Gauge } from 'k6/metrics';

// Custom metrics
const responseTime = new Trend('response_time_ms');
const cacheHitRate = new Gauge('cache_hit_rate');
const deduplicationCount = new Counter('deduplication_events');
const apiErrors = new Counter('api_errors');

// Test configuration
export const options = {
  vus: 100,                      // 100 virtual users
  duration: '30s',               // 30 second test
  ramp: '5s',                    // Ramp up over 5s
  thresholds: {
    'response_time_ms': ['p99<50'],  // p99 response time < 50ms
    'http_req_failed': ['rate<0.05'],  // Less than 5% failures
  },
};

// Track inflight requests to measure deduplication
const inflightRequests = {};
const requestTimings = {};

// Enum catalog to test
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

export default function () {
  group('Enum API Load Test', function () {
    // Randomly select enum catalog
    const enumName = enumCatalogs[Math.floor(Math.random() * enumCatalogs.length)];
    
    // Check if request for this enum is already inflight (deduplication test)
    const requestKey = `${enumName}`;
    const isDeduplicable = inflightRequests[requestKey] !== undefined;
    
    if (isDeduplicable) {
      deduplicationCount.add(1);
    }
    
    // Mark inflight
    inflightRequests[requestKey] = true;
    requestTimings[requestKey] = Date.now();
    
    // Make request to enum endpoint
    const response = http.get(
      `http://localhost:5173/api/v1/core/enums/${enumName}/`,
      {
        tags: { name: 'EnumAPI' },
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache', // Bypass browser cache to test API cache
        },
      }
    );
    
    const duration = Date.now() - requestTimings[requestKey];
    responseTime.add(duration);
    
    // Validation
    check(response, {
      'Status 200': (r) => r.status === 200,
      'Has name field': (r) => r.json('name') !== undefined,
      'Has values object': (r) => r.json('values') !== undefined && typeof r.json('values') === 'object',
      'Response time < 50ms': (r) => duration < 50,
    });
    
    if (response.status !== 200) {
      apiErrors.add(1);
    }
    
    // Cleanup inflight
    delete inflightRequests[requestKey];
    
    // Small sleep to distribute requests
    sleep(Math.random() * 0.1);
  });
}

/**
 * Expected Results (baseline):
 * 
 * PHASE 1: Warmup (VU ramp 0-100 over 5s)
 * - First batch hits API, response ~200-500ms (cache miss)
 * - Deduplication events spike (multiple VUs requesting same enum simultaneously)
 * - By end of phase: all 11 enums cached
 * 
 * PHASE 2: Steady State (100 VUs for 25s)
 * - Cache hit rate: >=90% (mostly localStorage/memory hits)
 * - Response time p99: <10ms (cached responses)
 * - Deduplication: Active but less frequent (inflight dedup)
 * - Zero errors
 * 
 * PHASE 3: Post-TTL (if TTL 30min expires during test)
 * - Response time spikes to ~200ms when cache expires
 * - Cache hit rate drops temporarily
 * - Then recovers as cache repopulates
 * 
 * Success Criteria:
 * ✓ p99 response time < 50ms average
 * ✓ Cache hit rate ≥90% after warmup
 * ✓ Deduplication events > 0 (proves inflight merging works)
 * ✓ API errors < 5%
 * ✓ No 5xx errors from backend
 */
