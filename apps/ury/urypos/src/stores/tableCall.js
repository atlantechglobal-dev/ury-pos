import { defineStore } from "pinia";
import { io } from "socket.io-client";
import frappe from "./frappeSdk.js";
import { useNotifications } from "./Notification.js";

let socket = null;

export const useTableCallStore = defineStore("tableCall", {
  state: () => ({
    requests: [],
    // Alongside the bell badge/toast, queued requests get a prominent popup
    // that stays on screen until acted upon — a toast alone is too easy to
    // miss for a time-sensitive customer request.
    popupQueue: [],
    notification: useNotifications(),
  }),
  actions: {
    async fetchOpenRequests() {
      try {
        const result = await frappe
          .call()
          .get("ury.ury.api.table_call.get_open_call_requests");
        this.requests = result.message || [];
      } catch (error) {
        console.error("Failed to fetch open table call requests", error);
      }
    },

    // Mirrors Frappe's own desk socketio client connection recipe: connect
    // under the site's actual namespace (nginx pins X-Frappe-Site-Name to
    // the real site name regardless of the hostname/IP used to connect), and
    // rely on session cookies — the server auto-joins every socket to
    // `user:{email}`, so per-user events just work without subscribing to
    // any room.
    async connectSocket() {
      if (socket) return;
      const result = await frappe
        .call()
        .get("ury.ury.api.table_call.get_site_name");
      const siteName = result.message;

      socket = io(`${window.location.origin}/${siteName}`, {
        withCredentials: true,
        reconnectionAttempts: 5,
      });

      socket.on("ury_table_call_request", (data) => {
        if (!this.requests.some((r) => r.name === data.name)) {
          this.requests.push(data);
        }
        if (!this.popupQueue.some((r) => r.name === data.name)) {
          this.popupQueue.push(data);
        }
        this.notification.createNotification(
          `Table ${data.table}: ${data.request_type}`
        );
      });

      socket.on("ury_table_call_resolved", (data) => {
        this.requests = this.requests.filter((r) => r.name !== data.name);
        this.popupQueue = this.popupQueue.filter((r) => r.name !== data.name);
      });
    },

    async resolveRequest(name) {
      await frappe
        .call()
        .post("ury.ury.api.table_call.resolve_call_request", { name });
      this.requests = this.requests.filter((r) => r.name !== name);
      this.popupQueue = this.popupQueue.filter((r) => r.name !== name);
    },

    dismissPopup(name) {
      this.popupQueue = this.popupQueue.filter((r) => r.name !== name);
    },
  },
});
