import type { Locale } from "@/i18n/config";

import { en } from "./en";
import { es } from "./es";
import { ja } from "./ja";
import { ko } from "./ko";
import type { TermsText } from "./shared";
import { zh } from "./zh";
import { zht } from "./zht";

/** The terms in each language. en.tsx is the one that applies; zht.tsx is
 * made from zh.tsx by scripts/zh_hant.py. */
export const TERMS: Record<Locale, TermsText> = { en, zh, zht, es, ja, ko };
