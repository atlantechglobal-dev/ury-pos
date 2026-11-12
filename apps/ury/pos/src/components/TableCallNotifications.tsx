import { useEffect, useRef, useState } from 'react';
import { Bell, Phone, GlassWater, Receipt, XCircle } from 'lucide-react';
import { Button } from './ui';
import { showToast } from './ui/toast';
import { getSocket } from '../lib/realtime';
import { getOpenCallRequests, resolveCallRequest, TableCallRequest } from '../lib/table-call-api';
import { t } from '../i18n';

const REQUEST_ICONS: Record<TableCallRequest['request_type'], typeof Phone> = {
  'Call Waiter': Phone,
  Water: GlassWater,
  Bill: Receipt,
  Cancel: XCircle,
};

function playBeep() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.25);
  } catch {
    // Audio not available — ignore, the visual badge/toast still shows.
  }
}

function formatElapsed(requestedOn: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(requestedOn.replace(' ', 'T')).getTime()) / 1000));
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return minutes > 0 ? `${minutes}m ${secs}s` : `${secs}s`;
}

export default function TableCallNotifications() {
  const [requests, setRequests] = useState<TableCallRequest[]>([]);
  const [popupQueue, setPopupQueue] = useState<TableCallRequest[]>([]);
  const [showPanel, setShowPanel] = useState(false);
  const [now, setNow] = useState(Date.now());
  const panelRef = useRef<HTMLDivElement>(null);
  const [resolvingName, setResolvingName] = useState<string | null>(null);

  useEffect(() => {
    getOpenCallRequests().then(setRequests).catch(() => {});
  }, []);

  useEffect(() => {
    let socketInstance: Awaited<ReturnType<typeof getSocket>> | null = null;
    let cancelled = false;

    getSocket().then((socket) => {
      if (cancelled) return;
      socketInstance = socket;

      const onRequest = (data: TableCallRequest) => {
        setRequests((prev) => (prev.some((r) => r.name === data.name) ? prev : [...prev, data]));
        // Alongside the bell badge/toast, queue a prominent popup that stays
        // on screen until the staff member acts on it — a toast alone is too
        // easy to miss for a time-sensitive customer request.
        setPopupQueue((prev) => (prev.some((r) => r.name === data.name) ? prev : [...prev, data]));
        playBeep();
        showToast.info(t('table_calls.new_request_toast', { table: data.table, type: data.request_type }));
      };
      const onResolved = (data: { name: string }) => {
        setRequests((prev) => prev.filter((r) => r.name !== data.name));
        setPopupQueue((prev) => prev.filter((r) => r.name !== data.name));
      };

      socket.on('ury_table_call_request', onRequest);
      socket.on('ury_table_call_resolved', onResolved);
    });

    return () => {
      cancelled = true;
      if (socketInstance) {
        socketInstance.off('ury_table_call_request');
        socketInstance.off('ury_table_call_resolved');
      }
    };
  }, []);

  useEffect(() => {
    if (!showPanel && popupQueue.length === 0) return;
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [showPanel, popupQueue.length]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setShowPanel(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  async function handleResolve(name: string) {
    setResolvingName(name);
    try {
      await resolveCallRequest(name);
      setRequests((prev) => prev.filter((r) => r.name !== name));
      setPopupQueue((prev) => prev.filter((r) => r.name !== name));
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : t('table_calls.resolve_failed'));
    } finally {
      setResolvingName(null);
    }
  }

  function handleDismissPopup(name: string) {
    // Only dismisses the popup — the request stays open in the bell panel.
    setPopupQueue((prev) => prev.filter((r) => r.name !== name));
  }

  const activePopup = popupQueue[0];

  return (
    <div className="relative" ref={panelRef}>
      <Button
        onClick={() => setShowPanel((v) => !v)}
        variant="ghost"
        size="icon"
        className="relative text-gray-600 hover:text-gray-900"
        aria-label={t('table_calls.title')}
      >
        <Bell className="w-5 h-5" />
        {requests.length > 0 && (
          <span className="absolute -top-1 -end-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold">
            {requests.length}
          </span>
        )}
      </Button>

      {showPanel && (
        <div className="absolute end-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto">
          <div className="p-3 border-b border-gray-200 font-semibold text-gray-900">
            {t('table_calls.title')}
          </div>
          {requests.length === 0 ? (
            <div className="p-4 text-sm text-gray-500 text-center">{t('table_calls.no_requests')}</div>
          ) : (
            requests.map((req) => {
              const Icon = REQUEST_ICONS[req.request_type] || Bell;
              return (
                <div key={req.name} className="flex items-center gap-3 p-3 border-b border-gray-100 last:border-b-0">
                  <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-red-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {t('table_calls.table_label')} {req.table} — {t(`table_calls.types.${req.request_type.toLowerCase().replace(' ', '_')}`)}
                    </p>
                    <p className="text-xs text-gray-500">{formatElapsed(req.requested_on, now)} {t('table_calls.ago')}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={resolvingName === req.name}
                    onClick={() => handleResolve(req.name)}
                  >
                    {t('table_calls.resolve')}
                  </Button>
                </div>
              );
            })
          )}
        </div>
      )}

      {activePopup && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4 p-6 text-center animate-in fade-in zoom-in duration-200">
            <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
              {(() => {
                const Icon = REQUEST_ICONS[activePopup.request_type] || Bell;
                return <Icon className="w-8 h-8 text-red-500" />;
              })()}
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">
              {t('table_calls.table_label')} {activePopup.table}
            </h3>
            <p className="text-gray-600 mb-1">
              {t(`table_calls.types.${activePopup.request_type.toLowerCase().replace(' ', '_')}`)}
            </p>
            <p className="text-xs text-gray-400 mb-6">
              {formatElapsed(activePopup.requested_on, now)} {t('table_calls.ago')}
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => handleDismissPopup(activePopup.name)}
              >
                {t('table_calls.dismiss')}
              </Button>
              <Button
                className="flex-1"
                disabled={resolvingName === activePopup.name}
                onClick={() => handleResolve(activePopup.name)}
              >
                {t('table_calls.resolve')}
              </Button>
            </div>
            {popupQueue.length > 1 && (
              <p className="text-xs text-gray-400 mt-4">
                +{popupQueue.length - 1} more
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
