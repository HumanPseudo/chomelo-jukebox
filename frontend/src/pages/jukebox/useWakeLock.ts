import { useEffect, useRef } from "react";

/**
 * Pide un wake lock de pantalla mientras `active` es true, para que el
 * dispositivo del admin (conectado a las bocinas) no apague la pantalla
 * y corte el audio de fondo. El wake lock se libera solo cuando la
 * pestaña deja de ser visible (por spec), así que hay que re-pedirlo al
 * volver — de ahí el listener de "visibilitychange".
 */
export function useWakeLock(active: boolean) {
  const sentinelRef = useRef<WakeLockSentinel | null>(null);

  useEffect(() => {
    if (!active || !("wakeLock" in navigator)) return;

    let cancelled = false;

    async function acquire() {
      try {
        const sentinel = await navigator.wakeLock.request("screen");
        if (cancelled) {
          await sentinel.release();
          return;
        }
        sentinelRef.current = sentinel;
      } catch {
        // el navegador puede rechazarlo (pestaña no visible, sin permiso,
        // etc.); no es crítico, el audio sigue intentando sonar igual.
      }
    }

    acquire();

    function onVisibilityChange() {
      if (document.visibilityState === "visible" && sentinelRef.current === null) {
        acquire();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibilityChange);
      sentinelRef.current?.release().catch(() => {});
      sentinelRef.current = null;
    };
  }, [active]);
}
