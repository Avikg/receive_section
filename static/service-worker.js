// WBSEDCL Tracking System - Empty Service Worker
// This file exists to prevent 404 errors in the browser console

self.addEventListener('install', function(event) {
  // Service worker installed
  console.log('Service Worker: Installed');
});

self.addEventListener('activate', function(event) {
  // Service worker activated
  console.log('Service Worker: Activated');
});

self.addEventListener('fetch', function(event) {
  // Just pass through - don't cache anything
  event.respondWith(fetch(event.request));
});