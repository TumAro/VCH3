// Fetch wrapper: JSON in, JSON out; non-2xx responses throw with the server's message.

export async function getJson(url, options) {
  const resp = await fetch(url, options);
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(body.message || resp.status + " " + resp.statusText);
  return body;
}
