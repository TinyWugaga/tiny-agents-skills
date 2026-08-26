import { useEffect, useState } from "react";
import { legacyFetch } from "../api/client";

export function useCart(userId: string) {
  const [items, setItems] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    setLoading(true);
    legacyFetch(`/api/cart/${userId}`).then((d) => {
      setItems(d.items);
      setLoading(false);
    });
  }, [userId]);
  return { items, loading };
}
