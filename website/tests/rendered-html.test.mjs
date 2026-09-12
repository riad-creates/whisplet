import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
test('static export directs users to this fork and describes the actual installation route', async () => {
  const html = await readFile(new URL('../out/index.html', import.meta.url), 'utf8');
  assert.match(html, /Whisplet — Your voice, right on your Mac/);
  assert.match(html, /github.com\/riad-creates\/whisplet\/blob\/main\/docs\/INSTALL.md/);
  assert.match(html, /github.com\/riad-creates\/whisplet\/blob\/main\/AGENTS.md/);
  assert.match(html, /Source-build preview/);
  assert.match(html, /No paid Apple Developer membership/);
  assert.match(html, /off by default/);
  assert.doesNotMatch(html, /Phonon\.dmg|brew install --cask|phonon\.sh|fonts\.googleapis/);
});
