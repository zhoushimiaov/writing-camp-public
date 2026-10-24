/* 写作小能手训练营 · 离线缓存（网络优先，断网时用缓存） */
'use strict';
const CACHE = 'writing-camp-v11';
const CORE = [
  './',
  './index.html',
  './style.css',
  './manifest.json',
  './js/data.js',
  './js/app.js',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
  './fonts/LXGWWenKai-Regular.woff2',
  './fonts/LXGWWenKai-Medium.woff2'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = e.request.url;
  /* 分享链接（?w=…）不进缓存，避免每个链接都占一份缓存（审查 N7 修复） */
  if (url.includes('?w=')) {
    e.respondWith(fetch(e.request).catch(() => caches.match('./index.html')));
    return;
  }
  e.respondWith(
    fetch(e.request)
      .then(resp => {
        /* 5xx 等坏响应不写缓存，走缓存回退（审查 N7 修复） */
        if (!resp || !resp.ok || resp.type === 'opaque') throw new Error('bad response');
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return resp;
      })
      .catch(() =>
        caches.match(e.request, { ignoreSearch: true })
          .then(r => r || caches.match('./index.html'))
      )
  );
});
