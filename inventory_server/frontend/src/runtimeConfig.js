const runtimeConfig = window.__OIMS_CONFIG__ || {};

const fallbackBaseUrl =
  window.location.port === "3000"
    ? `http://${window.location.hostname || "localhost"}:3010`
    : "";

const stripTrailingSlash = (value) => value.replace(/\/+$/, "");

export const apiBaseUrl = stripTrailingSlash(
  runtimeConfig.apiBaseUrl || process.env.REACT_APP_API_BASE_URL || fallbackBaseUrl
);

export const socketBaseUrl = stripTrailingSlash(
  runtimeConfig.socketBaseUrl || process.env.REACT_APP_SOCKET_BASE_URL || apiBaseUrl
);
