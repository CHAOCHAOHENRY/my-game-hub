// 回归验证脚本 v6
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, 'index.html');
const html = fs.readFileSync(htmlPath, 'utf-8');
let errors = [];
function ok(m){ console.log('OK', m); }
function fail(m){ console.error('FAIL', m); errors.push(m); }
function assertRe(name, pat, text){
  if (pat.test(text)) ok(name);
  else fail(name + ': pattern ' + pat.source + ' not found');
}

// A. 源码级断言
assertRe('A1 feed scrollTop', /f\.scrollTop\s*=\s*f\.scrollHeight/, html);
assertRe('A2 analyze pair s field', /type:'pair',\s*key:RANK_VAL\[d\[0\]\.r\],\s*r:d\[0\]\.r,\s*s:d\[0\]\.s/, html);
assertRe('A3 canBeat pair compare', /p\.type==='single'\s*\|\|\s*p\.type==='pair'/, html);

// B. 逻辑单元测试：提取关键函数运行
// 从 html 中提取 <script> 内容
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) { fail('No script tag found'); process.exit(1); }
const script = scriptMatch[1];

// 提供最小浏览器环境 mock
const mockWindow = {
  location: { protocol: 'file:' },
  addEventListener: function(){},
  innerWidth: 1366,
  innerHeight: 768
};
const mockDocument = {
  createElement: function(tag){ return { style: {}, classList: { add: function(){}, remove: function(){} }, appendChild: function(){}, setAttribute: function(){}, textContent: '' }; },
  getElementById: function(id){ return { classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } }, style: {}, innerHTML: '', appendChild: function(){}, removeChild: function(){}, children: [], scrollTop: 0, scrollHeight: 0, onclick: null, value: '' }; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; },
  body: { appendChild: function(){} }
};
const mockConsole = console;

const fn = new Function('window', 'document', 'console', script + `
  return { analyze: analyze, canBeat: canBeat, mk: mk, desc: desc, strength: strength, RANK_VAL: RANK_VAL, SUIT_VAL: SUIT_VAL };
`);

let api;
try {
  api = fn(mockWindow, mockDocument, mockConsole);
} catch(e) {
  // 如果全局代码报错（如 EventSource 等），尝试用正则只提取需要的函数定义
  const extract = (name) => {
    const m = script.match(new RegExp('function ' + name + '\\(.*?\\}\\n'));
    return m ? m[0] : '';
  };
  const mkFn = new Function('SUIT_ORDER', 'RANK_ORDER', 'RANK_VAL', 'SUIT_VAL',
    html.match(/function mk\(s,r\)\{.*?\}/s)?.[0] || ''
  );
  fail('Script execution failed: ' + e.message + '. Fallback not implemented, but source asserts passed.');
  if (errors.length) {
    console.error('\n验证失败：');
    errors.forEach(e => console.error(' -', e));
    process.exit(1);
  }
  console.log('\n===== ALL PASSED (source asserts only) =====');
  process.exit(0);
}

// B1: pair 花色比较测试
// 方块7 + 黑桃7  vs  红桃7 + 梅花7
const p1 = api.analyze([api.mk('d','7'), api.mk('s','7')]);
const p2 = api.analyze([api.mk('h','7'), api.mk('c','7')]);
if (p1 && p2 && api.canBeat(p1, p2)) ok('B1 pair 方块7+黑桃7 打过 红桃7+梅花7');
else fail('B1 pair 方块7+黑桃7 应该打过 红桃7+梅花7');

// B2: 同花色 pair 应该不能互打（相等）
const p3 = api.analyze([api.mk('d','7'), api.mk('s','7')]);
const p4 = api.analyze([api.mk('d','7'), api.mk('s','7')]);
if (p3 && p4 && !api.canBeat(p3, p4)) ok('B2 相同 pair 不能互打');
else fail('B2 相同 pair 应该不能互打');

// B3: 较小花色 pair 不能打过较大花色 pair
const p5 = api.analyze([api.mk('h','7'), api.mk('c','7')]);
const p6 = api.analyze([api.mk('d','7'), api.mk('s','7')]);
if (p5 && p6 && !api.canBeat(p5, p6)) ok('B3 较小花色 pair 不能打过较大花色 pair');
else fail('B3 较小花色 pair 不应打过较大花色 pair');

// B4: 点数不同的 pair 仍然按点数比较（忽略花色）
const p7 = api.analyze([api.mk('c','8'), api.mk('h','8')]);
const p8 = api.analyze([api.mk('d','7'), api.mk('s','7')]);
if (p7 && p8 && api.canBeat(p7, p8)) ok('B4 点数大的 pair 打过点数小的 pair');
else fail('B4 点数大的 pair 应该打过点数小的 pair');

if (errors.length) {
  console.error('\n验证失败：');
  errors.forEach(e => console.error(' -', e));
  process.exit(1);
}
console.log('\n===== ALL PASSED =====');
