import { io, Socket } from 'socket.io-client';
import { call } from './frappe-sdk';

let socket: Socket | null = null;
let connecting: Promise<Socket> | null = null;

// Mirrors Frappe's own desk socketio client connection recipe: connect to
// the current origin under the site's namespace, using session cookies for
// auth (the realtime server authenticates via the `sid` cookie — see
// apps/frappe/realtime/middlewares/authenticate.js). No manual room-joining
// is needed for per-user events: the server auto-joins every socket to
// `user:{email}` on connect (see apps/frappe/realtime/handlers/frappe_handlers.js).
//
// The namespace must be the site's actual name (e.g. "arabian.local"), not
// necessarily the hostname the browser used — nginx pins
// `X-Frappe-Site-Name` to the real site name regardless of access IP/host,
// so we fetch it once from the server rather than guessing client-side.
export async function getSocket(): Promise<Socket> {
  if (socket) return socket;
  if (connecting) return connecting;

  connecting = call
    .get<{ message: string }>('ury.ury.api.table_call.get_site_name')
    .then((res) => {
      const siteName = res.message;
      socket = io(`${window.location.origin}/${siteName}`, {
        withCredentials: true,
        reconnectionAttempts: 5,
      });
      return socket;
    });

  return connecting;
}
