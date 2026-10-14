#!/usr/bin/env node
// umlview SVG driver for tests: run the template's own draw() under a DOM
// shim, then dump one JSON object: the text elements of every class box.
//
// The umlview page builds its SVG at runtime with dagre and innerHTML, so a
// test that asserts on the SVG must execute the template. This driver is the
// smallest harness that lets the real template run: a singleton canvas, a
// chainable jQuery stub, and the vendored dagre already embedded in the page.
//
// Usage: node umlview_svg_driver.js PAGE.html
// Output: {"classes":[{"id":"...","texts":[{x,y,anchor,font,text},...]},...]}

"use strict";

const fs = require("fs");

const page = fs.existsSync(process.argv[2])
  ? fs.readFileSync(process.argv[2], "utf8")
  : fs.readFileSync(process.argv[2] + ".html", "utf8");
const blocks = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
if (blocks.length < 4) {
  throw new Error("expected 4 inline scripts, found " + blocks.length);
}
const dagreSrc = blocks[2];
const mainSrc = blocks[3];

function element() {
  return {
    innerHTML: "",
    dataset: {},
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    style: {},
    setAttribute() {},
    getAttribute() { return null; },
    getBoundingClientRect: () => ({ width: 1200, height: 800, left: 0, top: 0 }),
    setPointerCapture() {},
    releasePointerCapture() {},
    textContent: "",
    tagName: "DIV",
  };
}

function collection(el) {
  const self = { 0: el, length: 1, outerWidth: 100, outerHeight: 100 };
  const noop = () => self;
  for (const name of [
    "text", "html", "attr", "addClass", "removeClass", "toggleClass",
    "find", "closest", "css", "next", "append", "remove", "on", "off",
    "val", "prop", "empty", "show", "hide",
  ]) {
    self[name] = noop;
  }
  self.each = () => self;
  self.hasClass = () => false;
  self.get = () => el;
  return self;
}

const canvas = collection(element());
const $ = () => canvas;

global.$ = global.jQuery = $;
global.window = { parent: null, matchMedia: () => ({ matches: false }) };
global.window.parent = global.window;
global.window.addEventListener = function () {};
global.document = {
  documentElement: {
    className: "",
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  },
  getElementById: () => element(),
  querySelector: () => element(),
  addEventListener() {},
  createElement: () => element(),
};
global.localStorage = { getItem: () => null, setItem() {} };
global.matchMedia = () => ({ matches: false });
global.setTimeout = (fn) => { try { fn(); } catch (e) {} };

const dagreModule = { exports: {} };
new Function("module", "exports", dagreSrc)(dagreModule, dagreModule.exports);
global.dagre = dagreModule.exports;

const runSource = mainSrc + "\n;return;";
new Function("$", "document", "window", "localStorage", "matchMedia",
  "setTimeout", "dagre", runSource)(
    $, global.document, global.window, global.localStorage, global.matchMedia,
    global.setTimeout, global.dagre);

const svg = canvas[0].innerHTML;
const decode = (text) => text
  .replace(/&amp;/g, "&")
  .replace(/&lt;/g, "<")
  .replace(/&gt;/g, ">")
  .replace(/&quot;/g, '"');

const classes = [];
for (const group of svg.matchAll(/<g class="cls" data-id="([^"]+)">([\s\S]*?)<\/g>/g)) {
  const texts = [];
  for (const text of group[2].matchAll(
    /<text class="([^"]*)" x="([\d.]+)" y="([\d.]+)"([^>]*)>([\s\S]*?)<\/text>/g,
  )) {
    const attrs = text[4];
    const anchor = /text-anchor="(middle|end)"/.exec(attrs);
    const size = /text-\[([\d.]+)px\]/.exec(text[1]);
    texts.push({
      x: parseFloat(text[2]),
      y: parseFloat(text[3]),
      anchor: anchor ? anchor[1] : "start",
      font: size ? parseFloat(size[1]) : 12,
      text: decode(text[5]),
    });
  }
  classes.push({ id: group[1], texts });
}
process.stdout.write(JSON.stringify({ classes }));