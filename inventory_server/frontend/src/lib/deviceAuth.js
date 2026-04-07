function storageKeyForRole(role) {
  return `oims_device_token_${role}`;
}

export function storeDeviceToken(role, token) {
  if (!role || !token) {
    return;
  }
  window.localStorage.setItem(storageKeyForRole(role), token);
}

export function getStoredDeviceToken(role) {
  if (!role) {
    return "";
  }
  return window.localStorage.getItem(storageKeyForRole(role)) || "";
}

export function getCurrentRouteDeviceToken() {
  const pathname = window.location.pathname || "";
  if (pathname.startsWith("/inventory")) {
    return getStoredDeviceToken("inventory");
  }
  if (pathname.startsWith("/tablet")) {
    return getStoredDeviceToken("tablet");
  }
  return "";
}
