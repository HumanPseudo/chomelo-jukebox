import { useEffect, useRef, useState } from "react";
import { music } from "../../lib/endpoints";
import type { PlayerStateOut, QueueItemOut } from "../../lib/types";

const DRIFT_TOLERANCE_MS = 2000;

/**
 * Conecta el elemento <audio> real con el track_id resuelto por el worker
 * (stream efímero) y lo mantiene sincronizado con la posición autoritativa
 * del servidor. Es un jukebox físico: solo el dispositivo del admin (el
 * que está conectado a las bocinas) reproduce audio de verdad — por eso
 * `enabled` viene en false para los oyentes, que solo ven el estado.
 * Los navegadores bloquean el autoplay con sonido sin un gesto del
 * usuario, así que expone `locked`/`unlock` para pedirlo.
 */
export function useAudioSync(item: QueueItemOut | undefined, player: PlayerStateOut, enabled: boolean) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [locked, setLocked] = useState(false);
  const loadedTrackId = useRef<string | null>(null);

  // Resolver el stream real tarda varios segundos (yt-dlp + red); si el
  // usuario pausa mientras tanto, el callback async no debe usar el
  // `player` capturado al iniciar la resolución (quedaría obsoleto) sino
  // el estado más reciente — de ahí esta ref en vez de leer `player`
  // directamente dentro del `.then()`.
  const playerRef = useRef(player);
  useEffect(() => {
    playerRef.current = player;
  }, [player]);

  function attemptPlay() {
    const audio = audioRef.current;
    if (!audio) return;
    audio
      .play()
      .then(() => setLocked(false))
      .catch(() => setLocked(true));
  }

  // Además de la promesa de cada intento puntual, se escucha el propio
  // elemento <audio>: si queda en pausa mientras el servidor dice que
  // debería estar sonando (p.ej. el navegador lo pausó solo al volver de
  // segundo plano), el botón "activar sonido" tiene que reaparecer sin
  // depender de un intento explícito que lo capte.
  useEffect(() => {
    if (!enabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    const onPause = () => setLocked(player.is_playing);
    const onPlay = () => setLocked(false);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("play", onPlay);
    return () => {
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("play", onPlay);
    };
  }, [enabled, player.is_playing]);

  useEffect(() => {
    if (!enabled) return;
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
        // Usar el estado más reciente (playerRef), no el `player` de
        // cuando arrancó esta resolución: pudo haberse pausado mientras
        // tanto.
        audio.currentTime = playerRef.current.position_ms / 1000;
        if (playerRef.current.is_playing) attemptPlay();
      })
      .catch(() => {
        // stream no disponible (worker caído, video retirado, etc.):
        // el readout sigue mostrando el estado, sin audio.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, item?.track_id]);

  useEffect(() => {
    if (!enabled) return;
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
  }, [enabled, player.is_playing, player.position_ms, item?.id]);

  return { audioRef, locked, unlock: attemptPlay };
}
