// Execute the generated viewer's script against a stub DOM.
// Catches runtime errors (ReferenceError, TypeError) that `node --check` cannot.
// Usage: node tools/umlview/smoke.js path/to/viewer.html

const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync(process.argv[2], 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) {
  console.error('smoke: no script block');
  process.exit(2);
}

function element() {
  const target = {
    dataset: {},
    style: {},
    classList: { add() {}, remove() {}, toggle() {} },
    innerHTML: '',
    textContent: '',
    value: '',
    checked: false,
    clientWidth: 1200,
    clientHeight: 800,
    addEventListener() {},
    removeEventListener() {},
    setAttribute() {},
    appendChild() {},
    querySelector() { return element(); },
    querySelectorAll() { return []; },
  };
  return new Proxy(target, {
    get(object, key) {
      if (key in object) return object[key];
      return () => element();
    },
    set(object, key, value) {
      object[key] = value;
      return true;
    },
  });
}

const document = {
  getElementById() { return element(); },
  createElement() { return element(); },
  createElementNS() { return element(); },
  querySelector() { return element(); },
  querySelectorAll() { return []; },
  body: element(),
};
const window = { addEventListener() {}, removeEventListener() {} };
const context = {
  document,
  window,
  console,
  Math,
  JSON,
  setTimeout,
  clearTimeout,
};

try {
  vm.runInNewContext(match[1], context, { timeout: 5000, filename: 'viewer-script.js' });
  console.log('smoke: viewer script ran without runtime errors');
} catch (error) {
  console.error('smoke: ' + error.message);
  console.error(String(error.stack).split('\n').slice(1, 4).join('\n'));
  process.exit(1);
}
