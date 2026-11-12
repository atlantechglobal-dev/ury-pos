import { useEffect, useState } from 'react';
import { call } from './frappe-sdk';

interface Branding {
  logo: string | null;
  app_name: string | null;
}

// Cached so the header and any loading screens sharing this call only ever
// trigger one network request per page load.
let cached: Promise<Branding> | null = null;

export function getBranding(): Promise<Branding> {
  if (!cached) {
    cached = call
      .get<{ message: Branding }>('ury.ury_pos.api.get_branding')
      .then((res) => res.message);
  }
  return cached;
}

// Returns the admin-uploaded logo URL, or null while loading / if none is set
// (callers should fall back to the bundled default logo in that case).
export function useBrandingLogo(): string | null {
  const [logo, setLogo] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    getBranding().then((branding) => {
      if (!cancelled) setLogo(branding.logo);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return logo;
}

// Returns the admin-configured app name, or null while loading / if none is
// set (callers should fall back to the default "URY POS" in that case).
export function useBrandingAppName(): string | null {
  const [appName, setAppName] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    getBranding().then((branding) => {
      if (!cancelled) setAppName(branding.app_name);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return appName;
}
