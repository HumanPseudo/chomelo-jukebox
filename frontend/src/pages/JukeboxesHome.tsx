import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { jukeboxes } from "../lib/endpoints";
import { Empty } from "../components/ui";

export function JukeboxesHome() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("conectando a la transmisión…");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      for (let attempt = 0; attempt < 5 && !cancelled; attempt++) {
        try {
          const data = await jukeboxes.list();
          if (cancelled) return;
          if (data.length > 0) {
            navigate(`/jukeboxes/${data[0].id}`, { replace: true });
            return;
          }
        } catch {
          // reintento
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
      if (!cancelled) setStatus("no se pudo conectar a la transmisión");
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return <Empty>{status}</Empty>;
}
