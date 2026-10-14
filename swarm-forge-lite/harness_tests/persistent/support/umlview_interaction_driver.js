#!/usr/bin/env node
// umlview interaction driver for tests: run the template's own script under a
// recording DOM shim, then drive the four selection paths and dump the state
// after each. The template builds its SVG at runtime, so a test of the
// selection must execute the template.
//
// The shim keeps one element per selector, records every `on` handler (with its
// delegate selector), and parses the emitted SVG into class/edge elements with a
// dataset and a class set. The driver then calls window.umlview and fires the
// recorded handlers, the way a click would.
//
// Usage: node umlview_interaction_driver.js PAGE.html CANVAS_ID ROW_ID
// Output: {"rect":...,"api":[...],"classes":[{id,cx,cy,w,h}],
//          "steps":[{"label","panel","transform","view","lit","dimmed","tipHidden"}]}

"use strict";

const fs = require("fs");

const pagePath = process.argv[2];
const page = fs.readFileSync(pagePath, "utf8");
const canvasPick = process.argv[3];
const rowPick = process.argv[4];
const noOpPick = process.argv[5];

const blocks = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
if (blocks.length < 4) {
  throw new Error("expected 4 inline scripts, found " + blocks.length);
}

// --- recording DOM shim ---------------------------------------------------- //
const elements = new Map();

function element(key) {
  const el = {
    key,
    innerHTML: "",
    innerText: "",
    dataset: {},
    attrs: {},
    handlers: [],
    closestMap: {},
    classSet: new Set(),
  };
  el.classList = {
    add: (...names) => names.forEach((n) => el.classSet.add(n)),
    remove: (...names) => names.forEach((n) => el.classSet.delete(n)),
    toggle: (name, force) => {
      const on = force === undefined ? !el.classSet.has(name) : force;
      if (on) {
        el.classSet.add(name);
      } else {
        el.classSet.delete(name);
      }
      return on;
    },
    contains: (name) => el.classSet.has(name),
  };
  el.setAttribute = (name, value) => { el.attrs[name] = value; };
  el.getAttribute = (name) => (name in el.attrs ? el.attrs[name] : null);
  el.getBoundingClientRect = () => ({ width: 1200, height: 800, left: 0, top: 0 });
  el.setPointerCapture = () => {};
  el.releasePointerCapture = () => {};
  el.querySelector = () => element("query");
  el.tagName = "DIV";
  return el;
}

function getEl(selector) {
  if (!elements.has(selector)) {
    elements.set(selector, element(selector));
  }
  return elements.get(selector);
}

function applyClasses(list, names, add) {
  for (const item of list) {
    if (!item) {
      continue;
    }
    for (const name of names.split(/\s+/).filter(Boolean)) {
      if (add) {
        item.classList.add(name);
      } else {
        item.classList.remove(name);
      }
    }
  }
}

function collection(items) {
  const list = items.filter(Boolean);
  const self = { length: list.length, outerWidth: () => 100, outerHeight: () => 100 };
  list.forEach((item, index) => { self[index] = item; });
  const each = () => self;
  for (const name of ["on", "off", "css", "attr", "val", "prop", "append", "remove",
    "empty", "show", "hide", "next", "first"]) {
    self[name] = () => self;
  }
  self.text = (value) => {
    if (value === undefined) {
      return list.length ? list[0].innerText : "";
    }
    list.forEach((item) => { item.innerText = value; });
    return self;
  };
  self.html = (value) => {
    if (value === undefined) {
      return list.length ? list[0].innerHTML : "";
    }
    list.forEach((item) => { item.innerHTML = value; });
    return self;
  };
  self.addClass = (...names) => { applyClasses(list, names.join(" "), true); return self; };
  self.removeClass = (...names) => { applyClasses(list, names.join(" "), false); return self; };
  self.toggleClass = (name, force) => {
    list.forEach((item) => item.classList.toggle(name, force));
    return self;
  };
  self.hasClass = (name) => list.length > 0 && list[0].classList.contains(name);
  self.find = () => collection(allElements());
  self.closest = (selector) => collection([list[0] && list[0].closestMap[selector]]);
  self.each = function (fn) {
    list.forEach((item) => fn.call(item));
    return self;
  };
  self.on = function (type, delegate, handler) {
    if (typeof delegate === "function") {
      handler = delegate;
      delegate = null;
    }
    list.forEach((item) => {
      if (!item.handlers) {
        item.handlers = [];
      }
      item.handlers.push({ type, delegate, handler });
    });
    return self;
  };
  return self;
}

function $(arg) {
  if (typeof arg === "string") {
    return collection([getEl(arg)]);
  }
  if (arg === undefined || arg === null) {
    return collection([]);
  }
  return collection([arg]);
}

// --- the emitted SVG, as elements ------------------------------------------ //
let svgElements = null;
const classElements = new Map();

function allElements() {
  if (svgElements) {
    return svgElements;
  }
  svgElements = [];
  const svg = getEl("#canvas").innerHTML;
  for (const match of svg.matchAll(/<g class="cls" data-id="([^"]+)">([\s\S]*?)<\/g>/g)) {
    const el = getEl(".cls#" + match[1]);
    el.dataset.id = match[1];
    el.closestMap = { ".cls": el };
    const rect = /<rect[^>]* x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/.exec(match[2]);
    if (rect) {
      el.box = { x: parseFloat(rect[1]), y: parseFloat(rect[2]), w: parseFloat(rect[3]), h: parseFloat(rect[4]) };
    }
    classElements.set(match[1], el);
    svgElements.push(el);
  }
  for (const match of svg.matchAll(/<path class="edge[^"]*" data-from="([^"]+)" data-to="([^"]+)"/g)) {
    const el = getEl(".edge#" + match[1] + "->" + match[2]);
    el.dataset.from = match[1];
    el.dataset.to = match[2];
    el.closestMap = { ".edge": el };
    svgElements.push(el);
  }
  return svgElements;
}

// --- environment ----------------------------------------------------------- //
global.$ = global.jQuery = $;
global.window = { parent: null, matchMedia: () => ({ matches: false }) };
global.window.parent = global.window;
global.window.addEventListener = function () {};
global.document = {
  documentElement: {
    className: "",
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains: () => false,
    },
  },
  getElementById: (id) => getEl("#" + id),
  querySelector: () => element("query"),
  addEventListener() {},
  createElement: () => element("created"),
};
global.localStorage = { getItem: () => null, setItem() {} };
global.matchMedia = () => ({ matches: false });
global.setTimeout = (fn) => { try { fn(); } catch (e) {} };

const dagreModule = { exports: {} };
new Function("module", "exports", blocks[2])(dagreModule, dagreModule.exports);
global.dagre = dagreModule.exports;

new Function("$", "document", "window", "localStorage", "matchMedia",
  "setTimeout", "dagre", blocks[3])(
    $, global.document, global.window, global.localStorage, global.matchMedia,
    global.setTimeout, global.dagre);

// --- drive ----------------------------------------------------------------- //
const umlview = global.window.umlview || null;
const steps = [];

function snapshot(label) {
  const state = umlview && umlview.view ? umlview.view : { k: null, x: null, y: null };
  steps.push({
    label,
    api: umlview ? Object.keys(umlview).sort() : [],
    panel: getEl("#detail").innerHTML,
    transform: getEl("#zoom").attrs.transform || "",
    view: { k: state.k, x: state.x, y: state.y },
    lit: [...classElements].filter(([, el]) => el.classList.contains("opacity-100")).map(([id]) => id),
    dimmed: [...classElements].filter(([, el]) => el.classList.contains("opacity-10")).map(([id]) => id),
    tipHidden: getEl("#tip").classList.contains("hidden"),
  });
}

function callApi(name, argument) {
  if (!umlview || typeof umlview[name] !== "function") {
    return;
  }
  umlview[name](argument);
}

function fireOn(selector, type, event) {
  for (const handler of getEl(selector).handlers.filter((h) => h.type === type && !h.delegate)) {
    handler.handler.call(getEl(selector), event);
  }
}

function fireDelegated(selector, type, delegate, thisEl, event) {
  for (const handler of getEl(selector).handlers.filter((h) => h.type === type && h.delegate === delegate)) {
    handler.handler.call(thisEl, event);
  }
}

snapshot("load");

callApi("select", canvasPick);
snapshot("select:api");

callApi("deselect");
snapshot("deselect:api");

fireOn("#canvas", "click", { target: classElements.get(canvasPick) });
snapshot("canvas:cls");

fireOn("#canvas", "click", { target: element("empty") });
snapshot("canvas:empty");

const row = element("row");
row.dataset.id = rowPick;
fireDelegated("#detail", "click", ".entity", row, {});
snapshot("list:row");

fireDelegated("#detail", "click", ".back", getEl("#detail"), { preventDefault() {} });
snapshot("detail:back");

if (noOpPick) {
  callApi("select", noOpPick);
  snapshot("select:noop");
}

const classes = [...classElements].map(([id, el]) => ({
  id,
  cx: el.box ? el.box.x + el.box.w / 2 : 0,
  cy: el.box ? el.box.y + el.box.h / 2 : 0,
  w: el.box ? el.box.w : 0,
  h: el.box ? el.box.h : 0,
}));

process.stdout.write(JSON.stringify({
  rect: getEl("#canvas").getBoundingClientRect(),
  api: umlview ? Object.keys(umlview).sort() : [],
  classes,
  steps,
}));