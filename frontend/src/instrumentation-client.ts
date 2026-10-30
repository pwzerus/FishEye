// Runs in the browser before the app becomes interactive (Next.js
// instrumentation-client): the guard must be in place before React first
// updates a page someone has translated.
import { guardAgainstPageTranslation } from "@/lib/translateGuard";

guardAgainstPageTranslation();
