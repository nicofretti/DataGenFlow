import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const rootDir = path.resolve(__dirname, '../..');
const publicDir = path.resolve(__dirname, '../public');

// copy directory recursively
function copyDir(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

console.log('Copying assets...');

// copy images
const imagesSource = path.join(rootDir, 'images');
const imagesDest = path.join(publicDir, 'images');
if (fs.existsSync(imagesSource)) {
  copyDir(imagesSource, imagesDest);
  console.log('✓ Images copied');
}

// copy docs
const docsSource = path.join(rootDir, 'docs');
const docsDest = path.join(publicDir, 'docs');
if (fs.existsSync(docsSource)) {
  copyDir(docsSource, docsDest);
  console.log('✓ Docs copied');
}

// copy specific markdown files (excluding README.md - website has custom overview.md)
const markdownFiles = ['CONTRIBUTING.md', 'DEVELOPERS.md', 'CHANGELOG.md'];
markdownFiles.forEach(file => {
  const source = path.join(rootDir, file);
  const dest = path.join(publicDir, 'docs', file);
  if (fs.existsSync(source)) {
    fs.copyFileSync(source, dest);
    console.log(`✓ ${file} copied`);
  }
});

console.log('Assets copied successfully!');
