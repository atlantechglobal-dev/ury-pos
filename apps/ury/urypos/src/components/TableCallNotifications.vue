<template>
  <div class="relative" ref="panelRef">
    <button
      type="button"
      class="relative flex items-center rounded-full bg-gray-100 p-2 text-sm hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-300"
      @click="showPanel = !showPanel"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      <span
        v-if="tableCall.requests.length > 0"
        class="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold"
      >
        {{ tableCall.requests.length }}
      </span>
    </button>

    <div
      v-if="showPanel"
      class="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto"
    >
      <div class="p-3 border-b border-gray-200 font-semibold text-gray-900">
        Table Requests
      </div>
      <div v-if="tableCall.requests.length === 0" class="p-4 text-sm text-gray-500 text-center">
        No open requests
      </div>
      <div
        v-for="req in tableCall.requests"
        :key="req.name"
        class="flex items-center gap-3 p-3 border-b border-gray-100 last:border-b-0"
      >
        <div class="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
          <span class="text-red-500 text-xs font-bold">{{ req.request_type.charAt(0) }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 truncate">
            Table {{ req.table }} — {{ req.request_type }}
          </p>
          <p class="text-xs text-gray-500">{{ formatElapsed(req.requested_on) }} ago</p>
        </div>
        <button
          type="button"
          class="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          :disabled="resolvingName === req.name"
          @click="handleResolve(req.name)"
        >
          Resolve
        </button>
      </div>
    </div>

    <div
      v-if="activePopup"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/40"
    >
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <span class="text-red-500 text-2xl font-bold">{{ activePopup.request_type.charAt(0) }}</span>
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-1">Table {{ activePopup.table }}</h3>
        <p class="text-gray-600 mb-1">{{ activePopup.request_type }}</p>
        <p class="text-xs text-gray-400 mb-6">{{ formatElapsed(activePopup.requested_on) }} ago</p>
        <div class="flex gap-3">
          <button
            type="button"
            class="flex-1 rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
            @click="tableCall.dismissPopup(activePopup.name)"
          >
            Dismiss
          </button>
          <button
            type="button"
            class="flex-1 rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
            :disabled="resolvingName === activePopup.name"
            @click="handleResolve(activePopup.name)"
          >
            Resolve
          </button>
        </div>
        <p v-if="tableCall.popupQueue.length > 1" class="text-xs text-gray-400 mt-4">
          +{{ tableCall.popupQueue.length - 1 }} more
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { useTableCallStore } from "@/stores/tableCall.js";

export default {
  name: "TableCallNotifications",
  setup() {
    const tableCall = useTableCallStore();
    return { tableCall };
  },
  data() {
    return {
      showPanel: false,
      now: Date.now(),
      tickInterval: null,
      resolvingName: null,
    };
  },
  mounted() {
    this.tableCall.fetchOpenRequests();
    this.tableCall.connectSocket();
    document.addEventListener("mousedown", this.handleClickOutside);
  },
  beforeUnmount() {
    document.removeEventListener("mousedown", this.handleClickOutside);
    if (this.tickInterval) clearInterval(this.tickInterval);
  },
  computed: {
    activePopup() {
      return this.tableCall.popupQueue[0] || null;
    },
    shouldTick() {
      return this.showPanel || this.tableCall.popupQueue.length > 0;
    },
  },
  watch: {
    shouldTick(isActive) {
      if (isActive) {
        this.now = Date.now();
        this.tickInterval = setInterval(() => {
          this.now = Date.now();
        }, 1000);
      } else if (this.tickInterval) {
        clearInterval(this.tickInterval);
        this.tickInterval = null;
      }
    },
  },
  methods: {
    handleClickOutside(event) {
      if (this.$refs.panelRef && !this.$refs.panelRef.contains(event.target)) {
        this.showPanel = false;
      }
    },
    formatElapsed(requestedOn) {
      const seconds = Math.max(
        0,
        Math.floor((this.now - new Date(requestedOn.replace(" ", "T")).getTime()) / 1000)
      );
      const minutes = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return minutes > 0 ? `${minutes}m ${secs}s` : `${secs}s`;
    },
    async handleResolve(name) {
      this.resolvingName = name;
      try {
        await this.tableCall.resolveRequest(name);
      } catch (error) {
        console.error("Failed to resolve table call request", error);
      } finally {
        this.resolvingName = null;
      }
    },
  },
};
</script>
