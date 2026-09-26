"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useToast } from "@/components/ui/Toast";
import { useAuth } from "./AuthProvider";

/** "Angler Amy" -> "AA"; words that don't start with a letter or digit
 * ("(admin)", emoji) are skipped. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter((w) => /^[\p{L}\p{N}]/u.test(w));
  if (words.length === 0) return "?";
  const first = Array.from(words[0])[0];
  const last = words.length > 1 ? Array.from(words[words.length - 1])[0] : "";
  return (first + last).toUpperCase();
}

/** The header's right edge: "Sign in", or an avatar with the account menu. */
export function AccountMenu() {
  const { user, loading, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname() ?? "/";
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Close on navigation (adjusting state during render, not in an effect).
  const [menuPath, setMenuPath] = useState(pathname);
  if (menuPath !== pathname) {
    setMenuPath(pathname);
    setOpen(false);
  }

  if (loading) return <span className="avatar-btn avatar-skeleton" aria-hidden="true" />;
  if (!user) {
    const next = pathname.startsWith("/login") ? "/" : pathname;
    return (
      <Link href={`/login?next=${encodeURIComponent(next)}`} className="btn btn-primary btn-sm signin-btn">
        Sign in
      </Link>
    );
  }

  return (
    <div className="account-menu" ref={ref}>
      <button
        type="button"
        className="avatar-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account menu for ${user.display_name}`}
        onClick={() => setOpen((v) => !v)}
      >
        {initials(user.display_name)}
      </button>
      {open && (
        <div className="menu-pop" role="menu">
          <div className="menu-who">
            <strong>{user.display_name}</strong>
            <span>{user.email}</span>
            {user.role === "admin" && <span className="tag tag-admin">Admin</span>}
          </div>
          <Link role="menuitem" href="/account" className="menu-item">
            Account
          </Link>
          <Link role="menuitem" href="/account#pins" className="menu-item">
            My pins
          </Link>
          <Link role="menuitem" href="/map?addPin=1" className="menu-item">
            Add a pin
          </Link>
          {user.role === "admin" && (
            <Link role="menuitem" href="/admin" className="menu-item">
              Admin
            </Link>
          )}
          <button
            role="menuitem"
            type="button"
            className="menu-item menu-danger"
            onClick={async () => {
              setOpen(false);
              await signOut();
              toast("Signed out", "info");
              if (pathname.startsWith("/account") || pathname.startsWith("/admin")) router.push("/");
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
