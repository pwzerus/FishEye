import type { Locale } from "./config";

/** NWS short forecasts ("Mostly Clear") in the site's other languages; the
 * common ones, the same as the backend's (knowledge/plan_text.py
 * FORECASTS). Any other stays in English, as NWS wrote it. Korean uses the
 * Korea Meteorological Administration's sky words (맑음, 구름많음, 흐림). */
const FORECASTS: Record<Exclude<Locale, "en">, Record<string, string>> = {
  zh: {
    sunny: "晴", "mostly sunny": "大部晴", "partly sunny": "晴间多云", clear: "晴朗", "mostly clear": "大部晴朗",
    "partly cloudy": "局部多云", "mostly cloudy": "大部多云", cloudy: "多云", overcast: "阴",
    "patchy fog": "局部有雾", "areas of fog": "部分地区有雾", fog: "雾", haze: "霾",
    "slight chance rain showers": "小概率阵雨", "chance rain showers": "可能有阵雨", "rain showers likely": "很可能有阵雨",
    "rain showers": "阵雨", "light rain": "小雨", rain: "雨", "heavy rain": "大雨", drizzle: "毛毛雨",
    "slight chance showers and thunderstorms": "小概率雷阵雨", "chance showers and thunderstorms": "可能有雷阵雨",
    "showers and thunderstorms likely": "很可能有雷阵雨", "showers and thunderstorms": "雷阵雨",
    "chance thunderstorms": "可能有雷暴", thunderstorms: "雷暴", snow: "雪", "chance snow showers": "可能有阵雪",
  },
  es: {
    sunny: "Soleado", "mostly sunny": "Mayormente soleado", "partly sunny": "Parcialmente soleado",
    clear: "Despejado", "mostly clear": "Mayormente despejado", "partly cloudy": "Parcialmente nublado",
    "mostly cloudy": "Mayormente nublado", cloudy: "Nublado", overcast: "Cubierto",
    "patchy fog": "Niebla en partes", "areas of fog": "Zonas de niebla", fog: "Niebla", haze: "Bruma",
    "slight chance rain showers": "Ligera posibilidad de chubascos", "chance rain showers": "Posibles chubascos",
    "rain showers likely": "Probables chubascos", "rain showers": "Chubascos", "light rain": "Lluvia ligera",
    rain: "Lluvia", "heavy rain": "Lluvia fuerte", drizzle: "Llovizna",
    "slight chance showers and thunderstorms": "Ligera posibilidad de chubascos y tormentas",
    "chance showers and thunderstorms": "Posibles chubascos y tormentas",
    "showers and thunderstorms likely": "Probables chubascos y tormentas",
    "showers and thunderstorms": "Chubascos y tormentas", "chance thunderstorms": "Posibles tormentas",
    thunderstorms: "Tormentas", snow: "Nieve", "chance snow showers": "Posibles nevadas",
  },
  ko: {
    sunny: "맑음", "mostly sunny": "대체로 맑음", "partly sunny": "구름조금", clear: "맑음", "mostly clear": "대체로 맑음",
    "partly cloudy": "구름조금", "mostly cloudy": "구름많음", cloudy: "흐림", overcast: "흐림",
    "patchy fog": "곳에 따라 안개", "areas of fog": "곳에 따라 안개", fog: "안개", haze: "연무",
    "slight chance rain showers": "소나기 가능성 낮음", "chance rain showers": "소나기 가능성", "rain showers likely": "소나기 예상",
    "rain showers": "소나기", "light rain": "약한 비", rain: "비", "heavy rain": "강한 비", drizzle: "이슬비",
    "slight chance showers and thunderstorms": "소나기·뇌우 가능성 낮음", "chance showers and thunderstorms": "소나기·뇌우 가능성",
    "showers and thunderstorms likely": "소나기·뇌우 예상", "showers and thunderstorms": "소나기·뇌우",
    "chance thunderstorms": "뇌우 가능성", thunderstorms: "뇌우", snow: "눈", "chance snow showers": "눈 소나기 가능성",
  },
  ja: {
    sunny: "晴れ", "mostly sunny": "おおむね晴れ", "partly sunny": "晴れ時々曇り", clear: "晴れ", "mostly clear": "おおむね晴れ",
    "partly cloudy": "晴れ時々曇り", "mostly cloudy": "曇りがち", cloudy: "曇り", overcast: "曇り",
    "patchy fog": "所により霧", "areas of fog": "所により霧", fog: "霧", haze: "もや",
    "slight chance rain showers": "にわか雨の可能性は低い", "chance rain showers": "にわか雨の可能性", "rain showers likely": "にわか雨の見込み",
    "rain showers": "にわか雨", "light rain": "小雨", rain: "雨", "heavy rain": "大雨", drizzle: "霧雨",
    "slight chance showers and thunderstorms": "にわか雨や雷雨の可能性は低い", "chance showers and thunderstorms": "にわか雨や雷雨の可能性",
    "showers and thunderstorms likely": "にわか雨や雷雨の見込み", "showers and thunderstorms": "にわか雨と雷雨",
    "chance thunderstorms": "雷雨の可能性", thunderstorms: "雷雨", snow: "雪", "chance snow showers": "にわか雪の可能性",
  },
};

/** 16-point compass words, for "wind from the NE", as each language's
 * weather reports name them (东北偏北, 北北東, 북북동). */
const DIRECTIONS: Record<Exclude<Locale, "en">, Record<string, string>> = {
  zh: {
    N: "北", NNE: "东北偏北", NE: "东北", ENE: "东北偏东", E: "东", ESE: "东南偏东", SE: "东南", SSE: "东南偏南",
    S: "南", SSW: "西南偏南", SW: "西南", WSW: "西南偏西", W: "西", WNW: "西北偏西", NW: "西北", NNW: "西北偏北",
  },
  es: {
    N: "norte", NNE: "nornoreste", NE: "noreste", ENE: "estenoreste", E: "este", ESE: "estesureste", SE: "sureste",
    SSE: "sursureste", S: "sur", SSW: "sursuroeste", SW: "suroeste", WSW: "oestesuroeste", W: "oeste",
    WNW: "oestenoroeste", NW: "noroeste", NNW: "nornoroeste",
  },
  ko: {
    N: "북", NNE: "북북동", NE: "북동", ENE: "동북동", E: "동", ESE: "동남동", SE: "남동", SSE: "남남동",
    S: "남", SSW: "남남서", SW: "남서", WSW: "서남서", W: "서", WNW: "서북서", NW: "북서", NNW: "북북서",
  },
  ja: {
    N: "北", NNE: "北北東", NE: "北東", ENE: "東北東", E: "東", ESE: "東南東", SE: "南東", SSE: "南南東",
    S: "南", SSW: "南南西", SW: "南西", WSW: "西南西", W: "西", WNW: "西北西", NW: "北西", NNW: "北北西",
  },
};

/** "5 to 10 mph" as each language writes a speed: 时速 in Chinese words,
 * 時速 and 시속 before the number in Japanese and Korean. */
const SPEEDS: Record<Exclude<Locale, "en">, (low: string, high: string | null) => string> = {
  zh: (low, high) => `${high ? `${low}–${high}` : low} 英里/小时`,
  es: (low, high) => `${high ? `${low} a ${high}` : low} mph`,
  ko: (low, high) => `시속 ${high ? `${low}~${high}` : low}마일`,
  ja: (low, high) => `時速${high ? `${low}〜${high}` : low}マイル`,
};

export function localForecast(text: string, locale: Locale): string {
  return locale === "en" ? text : (FORECASTS[locale][text.trim().toLowerCase()] ?? text);
}

export function localDirection(code: string | null, locale: Locale): string | null {
  if (!code || locale === "en") return code;
  return DIRECTIONS[locale][code.trim().toUpperCase()] ?? code;
}

/** NWS's wind speed ("10 mph", "5 to 10 mph") in this language; anything
 * else as NWS wrote it. */
export function localWindSpeed(text: string | null, locale: Locale): string | null {
  if (!text || locale === "en") return text;
  const m = /^(\d+)(?: to (\d+))? mph$/i.exec(text.trim());
  return m ? SPEEDS[locale](m[1], m[2] ?? null) : text;
}
