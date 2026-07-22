/**
 * Offline Testing Helper - Copy & Paste in Browser Console
 * 
 * Quick tests for useEnums fallback catalog
 * Usage: Paste entire file into browser DevTools console and run individual tests
 */

// ============================================================================
// TEST 1: Verify fallback catalog exists and is complete
// ============================================================================
async function testFallbackCompleteness() {
  console.log('%c[Test 1] Fallback Catalog Completeness', 'color: blue; font-weight: bold');
  
  const expectedCatalogs = [
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
    'contractor-types'
  ];
  
  // Check each catalog
  for (const catalog of expectedCatalogs) {
    const item = localStorage.getItem(`enum_cache_${catalog}`);
    const status = item ? '✅' : '❌';
    console.log(`  ${status} ${catalog}: ${item ? 'cached' : 'not found'}`);
  }
  
  console.log('%cExpected: All catalogs should be cached or fallback available', 'color: gray');
}

// ============================================================================
// TEST 2: Simulate offline by blocking API calls
// ============================================================================
async function testOfflineSimulation() {
  console.log('%c[Test 2] Offline Simulation - Clear Cache & Block API', 'color: blue; font-weight: bold');
  
  // Step 1: Clear caches
  console.log('1️⃣  Clearing localStorage...');
  localStorage.clear();
  
  console.log('2️⃣  Clearing sessionStorage...');
  sessionStorage.clear();
  
  // Step 2: Instructions
  console.log('%c3️⃣  MANUAL STEP: Go to DevTools → Network tab', 'color: red; font-weight: bold');
  console.log('%c   Right-click any request → Throttling → Offline', 'color: red');
  
  console.log('%c4️⃣  MANUAL STEP: Reload page (F5)', 'color: red; font-weight: bold');
  
  console.log('%cThen run: testPageOffline()', 'color: green; font-weight: bold; font-size: 14px');
}

// Run after reload with offline mode
async function testPageOffline() {
  console.log('%c[Test 2 Continuation] Page Offline Verification', 'color: blue; font-weight: bold');
  
  // Check if page loaded without errors
  const hasErrors = document.body.innerHTML.includes('500') || 
                    document.body.innerHTML.includes('error');
  
  console.log(`Page loaded without errors: ${hasErrors ? '❌' : '✅'}`);
  
  // Check localStorage is still empty (offline, so no cache fetch)
  const cacheCount = Object.keys(localStorage)
    .filter(k => k.startsWith('enum_cache_')).length;
  console.log(`Cache items (should be 0): ${cacheCount}`);
  
  // Check if enum labels are visible (using fallback)
  const labels = document.querySelectorAll('[class*="bg-success"], [class*="bg-warning"], [class*="bg-danger"]');
  console.log(`Visible enum labels: ${labels.length}`);
  
  console.log('%cExpected: Page loads, no cache, labels visible (from fallback)', 'color: gray');
}

// ============================================================================
// TEST 3: Cache access performance
// ============================================================================
function testCachePerformance() {
  console.log('%c[Test 3] Cache Access Performance', 'color: blue; font-weight: bold');
  
  // Test 1: localStorage access
  console.time('localStorage 1000 accesses');
  for (let i = 0; i < 1000; i++) {
    localStorage.getItem('enum_cache_order-statuses');
  }
  console.timeEnd('localStorage 1000 accesses');
  
  // Test 2: JSON parse
  const cached = localStorage.getItem('enum_cache_order-statuses');
  if (cached) {
    console.time('Parse 1000 times');
    for (let i = 0; i < 1000; i++) {
      JSON.parse(cached);
    }
    console.timeEnd('Parse 1000 times');
  } else {
    console.log('⚠️  No cached data to test parsing');
  }
  
  console.log('%cExpected: Both operations < 50ms total', 'color: gray');
}

// ============================================================================
// TEST 4: Corrupted localStorage recovery
// ============================================================================
async function testCorruptedCache() {
  console.log('%c[Test 4] Corrupted Cache Recovery', 'color: blue; font-weight: bold');
  
  // Corrupt the cache
  console.log('1️⃣  Corrupting localStorage...');
  localStorage.setItem('enum_cache_order-statuses', 'INVALID_JSON_{]');
  
  console.log('%c2️⃣  MANUAL STEP: Reload page (F5)', 'color: red; font-weight: bold');
  
  console.log('%cThen run: testCorruptedRecovery()', 'color: green; font-weight: bold; font-size: 14px');
}

// Run after reload with corrupted cache
async function testCorruptedRecovery() {
  console.log('%c[Test 4 Continuation] Corrupted Cache Recovery Check', 'color: blue; font-weight: bold');
  
  // Check if page loaded without crash
  const hasCrash = document.body.innerHTML.includes('Uncaught') ||
                   document.body.innerHTML.includes('Cannot');
  console.log(`No crash on corrupted cache: ${hasCrash ? '❌' : '✅'}`);
  
  // Check if labels are visible
  const labels = document.querySelectorAll('[class*="bg-"]');
  console.log(`Enum labels visible: ${labels.length > 0 ? '✅' : '❌'}`);
  
  // Check cache was rebuilt
  const newCache = localStorage.getItem('enum_cache_order-statuses');
  try {
    if (newCache) {
      JSON.parse(newCache);
      console.log('Valid cache after recovery: ✅');
    }
  } catch {
    console.log('Cache still corrupted: ❌');
  }
  
  console.log('%cExpected: Page loads, no crash, cache is valid JSON', 'color: gray');
}

// ============================================================================
// TEST 5: Version mismatch detection
// ============================================================================
function testVersionMismatch() {
  console.log('%c[Test 5] Cache Version Mismatch Detection', 'color: blue; font-weight: bold');
  
  // Set old version
  console.log('1️⃣  Setting old cache version (0.9.0)...');
  localStorage.setItem('enum_cache_version', '0.9.0');
  localStorage.setItem('enum_cache_order-statuses', JSON.stringify({
    OLD: { label: 'Old Version' }
  }));
  
  console.log('%c2️⃣  MANUAL STEP: Reload page (F5)', 'color: red; font-weight: bold');
  
  console.log('%cThen run: testVersionRecovery()', 'color: green; font-weight: bold; font-size: 14px');
}

// Run after reload
async function testVersionRecovery() {
  console.log('%c[Test 5 Continuation] Version Recovery Check', 'color: blue; font-weight: bold');
  
  const currentVersion = localStorage.getItem('enum_cache_version');
  console.log(`Current cache version: ${currentVersion}`);
  console.log(`Expected version: 1.0.0`);
  
  if (currentVersion === '1.0.0') {
    console.log('✅ Cache was properly invalidated and updated');
  } else {
    console.log('❌ Cache version not updated');
  }
}

// ============================================================================
// TEST 6: Memory cache performance
// ============================================================================
async function testMemoryCachePerformance() {
  console.log('%c[Test 6] Memory Cache Performance (After API Load)', 'color: blue; font-weight: bold');
  
  // Wait for API calls to complete
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Check cache stats if available
  console.log('Cache contents (localStorage keys starting with enum_cache_):');
  const cacheKeys = Object.keys(localStorage)
    .filter(k => k.startsWith('enum_cache_'));
  
  console.log(`  Total cached: ${cacheKeys.length} items`);
  
  cacheKeys.forEach(key => {
    const size = (localStorage.getItem(key) || '').length;
    console.log(`  - ${key}: ${size} bytes`);
  });
  
  console.log('%cExpected: Multiple enum catalogs cached, sizes < 5KB each', 'color: gray');
}

// ============================================================================
// TEST 7: Fallback comparison (API vs Fallback)
// ============================================================================
function testFallbackComparison() {
  console.log('%c[Test 7] Fallback vs API Comparison', 'color: blue; font-weight: bold');
  
  const fromApi = localStorage.getItem('enum_cache_order-statuses');
  
  if (fromApi) {
    try {
      const apiData = JSON.parse(fromApi);
      console.log('API Response samples:');
      
      // Show first 3 items
      Object.keys(apiData).slice(0, 3).forEach(key => {
        console.log(`  ${key}: ${apiData[key].label}`);
      });
      
      console.log(`Total items: ${Object.keys(apiData).length}`);
    } catch {
      console.log('❌ Could not parse API response');
    }
  } else {
    console.log('ℹ️  No cached data (would use fallback)');
  }
  
  console.log('%cExpected: 15+ statuses, includes PENDING, PAID, COMPLETED, etc.', 'color: gray');
}

// ============================================================================
// QUICK TEST ALL
// ============================================================================
async function runAllOfflineTests() {
  console.log('%c╔════════════════════════════════════════════════╗', 'color: green; font-size: 14px');
  console.log('%c║    OFFLINE TESTING SUITE - ALL TESTS           ║', 'color: green; font-size: 14px');
  console.log('%c╚════════════════════════════════════════════════╝', 'color: green; font-size: 14px');
  
  await testFallbackCompleteness();
  console.log('\n');
  
  await testCachePerformance();
  console.log('\n');
  
  await testMemoryCachePerformance();
  console.log('\n');
  
  await testFallbackComparison();
  console.log('\n');
  
  console.log('%c📋 MANUAL TESTS AVAILABLE:', 'color: orange; font-weight: bold; font-size: 12px');
  console.log('  - testOfflineSimulation()      (clear cache + go offline)');
  console.log('  - testPageOffline()             (run after offline reload)');
  console.log('  - testCorruptedCache()          (corrupt cache)');
  console.log('  - testCorruptedRecovery()       (run after reload)');
  console.log('  - testVersionMismatch()         (set old version)');
  console.log('  - testVersionRecovery()         (run after reload)');
}

// ============================================================================
// PRINT HELPER MENU
// ============================================================================
console.log('%c╔════════════════════════════════════════════════╗', 'color: blue; font-size: 14px; font-weight: bold');
console.log('%c║  OFFLINE TESTING HELPERS - Browser Console     ║', 'color: blue; font-size: 14px; font-weight: bold');
console.log('%c╚════════════════════════════════════════════════╝\n', 'color: blue; font-size: 14px; font-weight: bold');

console.log('%c🎯 Quick Tests (No Reload):', 'color: green; font-weight: bold');
console.log('   runAllOfflineTests()           - Run all automatic tests');
console.log('   testFallbackCompleteness()     - Check if 11 catalogs cached');
console.log('   testCachePerformance()         - Measure cache access speed');
console.log('   testMemoryCachePerformance()   - Show cache stats');
console.log('   testFallbackComparison()       - Compare API vs fallback data\n');

console.log('%c🔄 Manual Tests (With Reload):', 'color: orange; font-weight: bold');
console.log('   testOfflineSimulation()        - 1️⃣  Clear cache & go offline');
console.log('   testPageOffline()              - 2️⃣  Check offline page load\n');

console.log('   testCorruptedCache()           - 1️⃣  Corrupt cache');
console.log('   testCorruptedRecovery()        - 2️⃣  Check recovery\n');

console.log('   testVersionMismatch()          - 1️⃣  Set old version');
console.log('   testVersionRecovery()          - 2️⃣  Check version update\n');

console.log('%c✅ Status: Ready', 'color: green; font-weight: bold; font-size: 14px');
