import { useEffect } from "react";
import type { PlayerStateOut, QueueItemOut } from "../../lib/types";

interface Actions {
  onPlay: () => void;
  onPause: () => void;
  onNext: () => void;
  onPrevious: () => void;
}

/**
 * Media Session API: metadatos + controles (play/pausa/anterior/
 * siguiente) en la pantalla de bloqueo y notificaciones del sistema del
 * dispositivo del admin. Además de la comodidad, marcar la pestaña como
 * "reproduciendo medios" hace que el navegador la suspenda con menos
 * agresividad al pasar a segundo plano.
 */
export function useMediaSession(
  item: QueueItemOut | undefined,
  player: PlayerStateOut,
  actions: Actions,
) {
  useEffect(() => {
    if (!("mediaSession" in navigator)) return;

    if (!item) {
      navigator.mediaSession.metadata = null;
      navigator.mediaSession.playbackState = "none";
      return;
    }

    navigator.mediaSession.metadata = new MediaMetadata({
      title: item.title,
      artist: item.artist || "desconocido",
      artwork: item.thumbnail_url ? [{ src: item.thumbnail_url }] : [],
    });
    navigator.mediaSession.playbackState = player.is_playing ? "playing" : "paused";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id, item?.title, item?.artist, item?.thumbnail_url, player.is_playing]);

  useEffect(() => {
    if (!("mediaSession" in navigator)) return;
    navigator.mediaSession.setActionHandler("play", actions.onPlay);
    navigator.mediaSession.setActionHandler("pause", actions.onPause);
    navigator.mediaSession.setActionHandler("nexttrack", actions.onNext);
    navigator.mediaSession.setActionHandler("previoustrack", actions.onPrevious);
    return () => {
      navigator.mediaSession.setActionHandler("play", null);
      navigator.mediaSession.setActionHandler("pause", null);
      navigator.mediaSession.setActionHandler("nexttrack", null);
      navigator.mediaSession.setActionHandler("previoustrack", null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actions.onPlay, actions.onPause, actions.onNext, actions.onPrevious]);
}
