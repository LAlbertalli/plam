const fs = require('fs');
const path = require('path');

// Default threshold for all metrics (statements, branches, functions, lines)
const DEFAULT_THRESHOLD = 70.0;

// Specific file thresholds (if any need to be higher, e.g. critical modules)
const SPECIFIC_THRESHOLDS = {
  // e.g. 'src/app/page.tsx': 80.0
};

// Exemptions / Allowed lower thresholds
const EXEMPTIONS = {
  // No files currently need exemptions below 70% as all exceed it!
};

function main() {
  const summaryFile = path.resolve(__dirname, '..', 'coverage', 'coverage-summary.json');
  if (!fs.existsSync(summaryFile)) {
    console.error(`Error: Coverage summary JSON file not found at ${summaryFile}`);
    console.error('Please run npm run test:coverage first.');
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(summaryFile, 'utf8'));
  let failed = false;
  let checkedCount = 0;

  console.log('Checking frontend per-file code coverage...');
  console.log('='.repeat(60));

  const frontendDir = path.resolve(__dirname, '..');

  for (const [absPath, fileInfo] of Object.entries(data)) {
    if (absPath === 'total') continue;

    // Convert absolute path to project-relative path (e.g. src/components/Sidebar.tsx)
    const relPath = path.relative(frontendDir, absPath);

    // Only check files in the src/ directory
    if (!relPath.startsWith('src/')) {
      continue;
    }

    const { lines, statements, functions, branches } = fileInfo;

    // Determine expected threshold
    let expected = DEFAULT_THRESHOLD;
    let desc = '';
    if (relPath in SPECIFIC_THRESHOLDS) {
      expected = SPECIFIC_THRESHOLDS[relPath];
      desc = ' (Custom minimum)';
    } else if (relPath in EXEMPTIONS) {
      expected = EXEMPTIONS[relPath];
      desc = ' (Exemption)';
    }

    const linePct = lines.pct;
    const stmtPct = statements.pct;
    const funcPct = functions.pct;
    const branchPct = branches.pct;

    checkedCount++;

    if (linePct < expected || stmtPct < expected || funcPct < expected || branchPct < expected) {
      console.error(`FAIL: ${relPath}`);
      console.error(`      Lines: ${linePct.toFixed(2)}%, Statements: ${stmtPct.toFixed(2)}%, Functions: ${funcPct.toFixed(2)}%, Branches: ${branchPct.toFixed(2)}%`);
      console.error(`      Expected: >= ${expected.toFixed(2)}%${desc}`);
      failed = true;
    } else {
      console.log(`PASS: ${relPath}`);
      console.log(`      (Lines: ${linePct.toFixed(2)}%, Branches: ${branchPct.toFixed(2)}% >= ${expected.toFixed(2)}%${desc})`);
    }
  }

  console.log('='.repeat(60));
  if (failed) {
    console.error('Coverage check FAILED! Some files do not meet their coverage threshold.');
    process.exit(1);
  } else {
    console.log(`Coverage check PASSED! All ${checkedCount} checked files met their thresholds.`);
    process.exit(0);
  }
}

main();
