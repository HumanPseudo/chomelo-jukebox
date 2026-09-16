import { useEffect, useRef, useState } from "react";
import { music } from "../../lib/endpoints";
import type { PlayerStateOut, QueueItemOut } from "../../lib/types";

const DRIFT_TOLERANCE_MS = 2000;

/**
 * Conecta el elemento <audio> real con el track_id resuelto por el worker
 * (stream efímero) y lo mantiene sincronizado con la posición autoritativa
 * del servidor. Los navegadores bloquean el autoplay con sonido sin un
 * gesto del usuario, así que expone `locked`/`unlock` para pedirlo.
 */
export function useAudioSync(item: QueueItemOut | undefined, player: PlayerStateOut) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [locked, setLocked] = useState(false);
  const loadedTrackId = useRef<string | null>(null);

  function attemptPlay() {
    const audio = audioRef.current;
    if (!audio) return;
    audio
      .play()
      .then(() => setLocked(false))
      .catch(() => setLocked(true));
  }

  useEffect(() => {
    if (!item) {
      loadedTrackId.current = null;
      const audio = audioRef.current;
      audio?.pause();
      audio?.removeAttribute("src");
      return;
    }
    if (loadedTrackId.current === item.track_id) return;
    const trackId = item.track_id;
    loadedTrackId.current = trackId;
    music
      .resolveStream(trackId)
      .then((resolved) => {
        const audio = audioRef.current;
        // Ignorar si mientras tanto se pidió otro track (cubre tanto el
        // doble efecto de desarrollo de StrictMode como un cambio real
        // de canción antes de que resolviera el stream anterior).
        if (!audio || loadedTrackId.current !== trackId) return;
        audio.src = resolved.stream_url;
        audio.currentTime = player.position_ms / 1000;
        if (player.is_playing) attemptPlay();
      })
      .catch(() => {
        // stream no disponible (worker caído, video retirado, etc.):
        // el readout sigue mostrando el estado, sin audio.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.track_id]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !item || !audio.src) return;
    if (player.is_playing) {
      if (Math.abs(audio.currentTime * 1000 - player.position_ms) > DRIFT_TOLERANCE_MS) {
        audio.currentTime = player.position_ms / 1000;
      }
      attemptPlay();
    } else {
      audio.pause();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [player.is_playing, player.position_ms, item?.id]);

  return { audioRef, locked, unlock: attemptPlay };
}
