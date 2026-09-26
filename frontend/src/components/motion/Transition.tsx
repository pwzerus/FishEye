import * as React from "react";
import type { ReactNode, ViewTransitionProps } from "react";

/**
 * React's <ViewTransition> ships in the React build Next.js bundles for the
 * App Router, but not in the stable `react` package that tests run against.
 * Reading it off the namespace (instead of a named import) keeps a missing
 * export from breaking module loading; without it, children render as-is.
 * Browsers without the View Transitions API also just render normally.
 */
const Impl = (React as unknown as { ViewTransition?: React.ComponentType<ViewTransitionProps> })
  .ViewTransition;

export function VT(props: ViewTransitionProps) {
  if (!Impl) return <>{props.children}</>;
  return <Impl {...props} />;
}

/**
 * Wraps a page's content so navigations tagged `nav-forward` / `nav-back`
 * (Link transitionTypes, see SiteHeader and the fish pages) slide in the
 * matching direction. Untyped navigations — the browser's own back button,
 * a refresh — don't slide; the CSS entrance animations cover those.
 * Must wrap each page, not the layout: layouts persist across navigations,
 * so their enter/exit never fire.
 */
export function PageTransition({ children }: { children: ReactNode }) {
  return (
    <VT
      enter={{ "nav-forward": "nav-forward", "nav-back": "nav-back", default: "none" }}
      exit={{ "nav-forward": "nav-forward", "nav-back": "nav-back", default: "none" }}
      default="none"
    >
      {children}
    </VT>
  );
}
