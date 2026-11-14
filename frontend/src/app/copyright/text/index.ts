import type { Locale } from "@/i18n/config";
import type { LegalText } from "@/lib/legal";

import { en } from "./en";
import { es } from "./es";
import { ja } from "./ja";
import { ko } from "./ko";
import { zh } from "./zh";
import { zht } from "./zht";

/** The copyright page in each language. en.tsx is the one that applies;
 * zht.tsx is made from zh.tsx by scripts/zh_hant.py. */
export const COPYRIGHT: Record<Locale, LegalText> = { en, zh, zht, es, ja, ko };
