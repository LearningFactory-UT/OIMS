import { apiBaseUrl } from "../runtimeConfig";
import { getCurrentRouteDeviceToken } from "./deviceAuth";

export class ApiError extends Error {
  constructor(message, status, body = null) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch(path, options = {}) {
  const { allowStatuses = [], ...requestOptions } = options;
  const deviceToken = getCurrentRouteDeviceToken();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(deviceToken ? { "X-OIMS-Device-Token": deviceToken } : {}),
      ...(requestOptions.headers || {}),
    },
    credentials: "include",
    cache: "no-store",
    ...requestOptions,
  });

  if (allowStatuses.includes(response.status)) {
    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || `Request failed with status ${response.status}`, response.status);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
