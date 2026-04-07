import { io } from "socket.io-client";

import { socketBaseUrl } from "../runtimeConfig";

let socket;

export function getSocket() {
  if (!socket) {
    socket = io(socketBaseUrl, {
      transports: ["polling"],
      upgrade: false,
      autoConnect: false,
      withCredentials: true,
      closeOnBeforeunload: true,
    });
  }
  return socket;
}

export function disconnectSocket() {
  if (!socket) {
    return;
  }
  socket.disconnect();
  socket = undefined;
}
