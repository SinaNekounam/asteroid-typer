// Copies the root-level web files (the ones GitHub Pages serves) into www/,
// which is the folder Capacitor packages into the iOS/Android native shells.
// Root index.html stays the single source of truth — never edit www/ directly.
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const WWW = path.join(ROOT, 'www');

const FILES_TO_COPY = ['index.html', 'og-image.png', 'manifest.json', 'service-worker.js'];
const DIRS_TO_COPY = ['icons'];

fs.mkdirSync(WWW, { recursive: true });

for (const file of FILES_TO_COPY) {
  fs.copyFileSync(path.join(ROOT, file), path.join(WWW, file));
  console.log('synced', file, '-> www/' + file);
}

for (const dir of DIRS_TO_COPY) {
  fs.cpSync(path.join(ROOT, dir), path.join(WWW, dir), { recursive: true });
  console.log('synced', dir + '/', '-> www/' + dir + '/');
}
