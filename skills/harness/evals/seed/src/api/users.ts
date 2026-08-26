import { legacyFetch } from "./client";

export async function getusers() {
  return legacyFetch("/api/users");          // TODO: 換成 httpClient
}
