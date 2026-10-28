/**
 * Parts of the app that can be switched off while they aren't ready. Their
 * code stays; the entry points show "Unavailable" while the flag is off.
 *
 * Catches (community pins): on. A catch that names a fish needs a photo the
 * server's photo check agrees with (backend services/fish_id.py).
 */
export const CATCHES_AVAILABLE = true;

export const CATCHES_SOON = "Catches are coming soon";
