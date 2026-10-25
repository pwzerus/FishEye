export function ActionIcon({ name }: { name: "map" | "fish" | "ask" | "arrow" | "pin" }) {
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {name === "map" && <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/></>}
    {name === "fish" && <><path d="M3 12c3-5 9-6 13-3l5-3v12l-5-3c-4 3-10 2-13-3Z"/><circle cx="8" cy="11" r=".7" fill="currentColor"/></>}
    {name === "ask" && <><path d="M4 4h16v12H9l-5 4Z"/><path d="M9.5 8.5a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 3"/><path d="M12 14h.01"/></>}
    {name === "arrow" && <><path d="M5 12h14m-6-6 6 6-6 6"/></>}
    {name === "pin" && <><path d="M18 10c0 5-6 11-6 11S6 15 6 10a6 6 0 0 1 12 0Z"/><circle cx="12" cy="10" r="2"/></>}
  </svg>;
}
