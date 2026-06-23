/**
 * Firebase Cloud Messaging Service Worker
 * Background push notification handler
 */

// Firebase SDK'yı import et
importScripts(
  "https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"
);
importScripts(
  "https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js"
);

// Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyD9QYFaOQVxEvt3ENEfgaqVyweHuRy-MBQ",
  authDomain: "orbis-ffa9e.firebaseapp.com",
  projectId: "orbis-ffa9e",
  storageBucket: "orbis-ffa9e.firebasestorage.app",
  messagingSenderId: "768649602152",
  appId: "1:768649602152:web:d1cd9f7deadcdfef1907dd",
  measurementId: "G-V3FBQWDN61",
};

// Firebase'i başlat
firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Background mesaj handler
messaging.onBackgroundMessage((payload) => {
  console.log("[FCM SW] Background mesaj alındı:", payload);

  const notificationTitle = payload.notification?.title || "ORBIS";
  const notificationOptions = {
    body: payload.notification?.body || "",
    icon: "/static/all-icons/Android/Icon-192.png",
    badge: "/static/all-icons/Android/Icon-72.png",
    tag: payload.data?.tag || "orbis-notification",
    data: payload.data || {},
    vibrate: [200, 100, 200],
    actions: [
      {
        action: "open",
        title: "Aç",
      },
      {
        action: "close",
        title: "Kapat",
      },
    ],
  };

  return self.registration.showNotification(
    notificationTitle,
    notificationOptions
  );
});

// Notification click handler
self.addEventListener("notificationclick", (event) => {
  console.log("[FCM SW] Notification tıklandı:", event);

  event.notification.close();

  const action = event.action;
  const data = event.notification.data || {};

  if (action === "close") {
    return;
  }

  // Uygulamayı aç veya odaklan
  const urlToOpen = data.url || "/";

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        // Açık pencere varsa odaklan
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        // Yoksa yeni pencere aç
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Push event handler (fallback)
self.addEventListener("push", (event) => {
  console.log("[FCM SW] Push event:", event);

  if (event.data) {
    try {
      const payload = event.data.json();

      const title = payload.notification?.title || "ORBIS";
      const options = {
        body: payload.notification?.body || "",
        icon: "/static/all-icons/Android/mipmap-xxxhdpi/ic_launcher.png",
        badge: "/static/all-icons/Android/mipmap-mdpi/ic_launcher.png",
        data: payload.data || {},
      };

      event.waitUntil(self.registration.showNotification(title, options));
    } catch (e) {
      console.error("[FCM SW] Push parse hatası:", e);
    }
  }
});

console.log("[FCM SW] Service Worker yüklendi");
