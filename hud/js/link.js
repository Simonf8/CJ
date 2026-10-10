const token = document.querySelector('meta[name="simon-token"]')?.content ?? "";

export function connect(onEvent, onStatus) {
  let source;
  const open = () => {
    source = new EventSource("events");
    source.onopen = () => onStatus(true);
    source.onerror = () => onStatus(false);
    source.onmessage = msg => {
      try { onEvent(JSON.parse(msg.data)); } catch (err) { console.error(err); }
    };
  };
  open();
  return () => source?.close();
}

export async function call(name, body = {}) {
  try {
    const res = await fetch(`api/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Simon-Token": token },
      body: JSON.stringify(body),
    });
    return res.ok ? (await res.json()).result : null;
  } catch {
    return null;
  }
}
