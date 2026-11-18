import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { jukeboxes } from "../lib/endpoints";
import { Empty } from "../components/ui";

export function JukeboxesHome() {
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const data = await jukeboxes.list();
      if (cancelled) return;
      if (data.length > 0) {
        navigate(`/jukeboxes/${data[0].id}`, { replace: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return <Empty>conectando a la transmisión…</Empty>;
}
