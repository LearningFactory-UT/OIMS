import { io } from "socket.io-client";

import { socketBaseUrl } from "../runtimeConfig";

let socket;

export function getSocket() {
  if (!socket) {
    socket = io(socketBaseUrl, {
      transports: ["polling"],
      upgrade: false,
    });
  }
  return socket;
}
