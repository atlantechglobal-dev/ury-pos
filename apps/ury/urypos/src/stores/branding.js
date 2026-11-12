import { defineStore } from "pinia";
import frappe from "./frappeSdk.js";

export const useBrandingStore = defineStore("branding", {
  state: () => ({
    logoUrl: null,
    fetched: false,
  }),
  actions: {
    async fetchLogo() {
      if (this.fetched) return;
      this.fetched = true;
      try {
        const result = await frappe.call().get("ury.ury_pos.api.get_branding");
        this.logoUrl = result.message?.logo || null;
      } catch (error) {
        console.error("Failed to fetch branding logo", error);
      }
    },
  },
});
