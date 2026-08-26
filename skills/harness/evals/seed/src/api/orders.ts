import { legacyFetch } from "./client";

export async function getorders() {
  return legacyFetch("/api/orders");          // TODO: 換成 httpClient
}
