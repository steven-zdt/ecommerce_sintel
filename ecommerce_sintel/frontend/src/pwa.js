/**
 * PWA Registration and Utilities
 * Registra Service Worker y maneja notificaciones push
 */

export function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
        .then(registration => {
          console.log('Service Worker registered:', registration);
          checkForUpdates(registration);
        })
        .catch(error => {
          console.error('Service Worker registration failed:', error);
        });
    });
  }
}

function checkForUpdates(registration) {
  setInterval(() => {
    registration.update();
  }, 60000); // Check every minute
}

export function requestNotificationPermission() {
  if ('Notification' in window && 'serviceWorker' in navigator) {
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }
}

export function subscribeToPushNotifications() {
  if ('serviceWorker' in navigator && 'PushManager' in window) {
    navigator.serviceWorker.ready.then(registration => {
      registration.pushManager.getSubscription().then(subscription => {
        if (!subscription) {
          registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(process.env.VITE_VAPID_PUBLIC_KEY),
          }).then(subscription => {
            console.log('Push subscription successful:', subscription);
            // Send subscription to backend
            sendSubscriptionToBackend(subscription);
          });
        }
      });
    });
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(base64);
  return new Uint8Array([...rawData].map(char => char.charCodeAt(0)));
}

async function sendSubscriptionToBackend(subscription) {
  try {
    await fetch('/api/push-subscriptions/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription),
    });
  } catch (error) {
    console.error('Failed to send subscription:', error);
  }
}

export function isAppInstallable() {
  return 'BeforeInstallPromptEvent' in window;
}

export function listenForInstallPrompt(onPrompt) {
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    onPrompt(event);
  });
}
