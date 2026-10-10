// HomeFix Thợ — service worker (SPEC 13). Nhận push, mở URL khi chạm thông báo.
// Chỉ cache tệp tĩnh tối thiểu; KHÔNG cache trang hay dữ liệu khách hàng.
const BO_NHO = "homefix-tinh-v1";
const TEP_TINH = {{ tep_tinh|safe }};

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(BO_NHO).then((c) => c.addAll(TEP_TINH)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ds) => Promise.all(ds.filter((k) => k !== BO_NHO).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin || !url.pathname.startsWith("/static/")) {
    return; // trang, API, ảnh hiện trường: luôn đi mạng
  }
  e.respondWith(caches.match(e.request).then((co) => co || fetch(e.request)));
});

self.addEventListener("push", (e) => {
  let du_lieu = { tieu_de: "HomeFix", noi_dung: "", duong_dan: "/tho/" };
  try { du_lieu = Object.assign(du_lieu, e.data.json()); } catch (_) {}
  e.waitUntil(
    self.registration.showNotification(du_lieu.tieu_de, {
      body: du_lieu.noi_dung,
      data: { url: du_lieu.duong_dan },
      lang: "vi",
      requireInteraction: true,
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/tho/";
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ds) => {
      for (const c of ds) {
        if ("focus" in c) { c.navigate(url); return c.focus(); }
      }
      return self.clients.openWindow(url);
    })
  );
});
