# FishMate brand assets

| File | Use |
|---|---|
| `fishmate-mark.svg` | The mark on its own: a map pin with a fish and a wave. Headers, splash screens, anywhere 32 px or larger. |
| `fishmate-lockup.svg` | Mark + wordmark, for light backgrounds. |
| `fishmate-lockup-dark.svg` | Mark + wordmark, for dark backgrounds. |
| `fishmate-icon.svg`, `fishmate-icon-256.png` | Rounded-square app icon. Use this below 32 px (browser tabs) and as the future App Store / home-screen icon: the pin's narrow tip leaves too little room for the fish at 16 px. |

The frontend copies these into `public/brand/` and `src/app/` (`icon.svg`,
`favicon.ico`, `apple-icon.png`).

## Colours

| Token | Hex | Where |
|---|---|---|
| Water, light | `#14B8A6` | Top of the gradient |
| Water, deep | `#0B5D7A` | Bottom of the gradient |
| Navy | `#0B3B52` | "Fish" in the wordmark, the fish's eye |
| Teal | `#0E9F9E` | "Mate" in the wordmark |
| Dark-mode text | `#F1F5F9` / `#2DD4BF` | "Fish" / "Mate" on dark backgrounds |

## Type

The wordmark is Poppins Bold, converted to outlines so it renders the same
everywhere without the font installed. Poppins is licensed under the SIL
Open Font License 1.1, which permits this.

## Rules

- Keep clear space around the mark of at least a quarter of its width.
- Don't recolour the fish or put the mark on a busy photo; use the icon
  tile there instead.
- The apple-touch icon is full-bleed on purpose: iOS applies its own
  rounded mask, and transparent corners would show up black.
