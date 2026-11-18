// Fetch one file through a real browser and save it: node fetch.mjs <page url> <file url> <dest>
// Used by scripts/gs_photo.py when a site refuses scripted downloads (upload.wikimedia.org answered 429 to every
// scripted request for over 1.5 hours during b02, 2026-11-17). The page is opened first so the file request comes
// from that site's own page.
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [pageUrl, fileUrl, dest] = process.argv.slice(2);
const browser = await chromium.launch();
try {
  const page = await (await browser.newContext()).newPage();
  await page.goto(pageUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const res = await page.context().request.get(fileUrl, { headers: { referer: pageUrl }, timeout: 120000 });
  if (!res.ok()) throw new Error(`HTTP ${res.status()}`);
  const body = await res.body();
  writeFileSync(dest, body);
  console.log(`OK ${body.length}`);
} catch (e) {
  console.log(`FAILED ${e.message}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
