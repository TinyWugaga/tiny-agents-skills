import { legacyFetch } from "./client";

export async function getproducts() {
  return legacyFetch("/api/products");          // TODO: 換成 httpClient
}
