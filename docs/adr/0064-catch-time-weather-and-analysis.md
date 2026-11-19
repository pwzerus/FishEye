# 0064. Catch time, weather, and "My catch analysis"

Date: 2026-11-19. Status: accepted.

## Context

The business plan (2026-11-14) names three Plus features; one is the fishing
log's analysis: "哪种饵、哪个时段、什么天气最灵" (which bait, which time of
day, what weather). Its row said what was missing: catches recorded bait and
gear (ADR 0056), but not the time of day or the weather. On 2026-11-19 the
owner asked for "我的渔获分析". Until FishEye Plus opens, everything is free
and what will be Plus says "free in beta" (the plan's 测试期).

Weather for a past moment needs a source with reports for that hour, legal
for a commercial product, and free:

- The National Weather Service's API (public domain, "open data, free to use
  for any purpose") has every airport station's hourly reports, but "only 7
  days of observations are retained" (weather.gov/documentation/services-web-api,
  checked 2026-11-19: reports 6 days back came back, 8 days back none).
- NOAA's Integrated Surface Database through NCEI's data service returned
  nothing for any 2026 date. Its successor GHCNh is updated daily, but as one
  file per station per year (32 MB for Austin Camp Mabry): not for a lookup
  per catch.
- Open-Meteo: "You may only use the free API services for non-commercial
  purposes." (open-meteo.com/en/terms).

The one promise FishEye makes is about spots (ADR 0057). Asking the weather
service for "the weather at this point" would send it the spot.

## Decision

**A catch has a time.** `catch_pins.caught_time` is the time on the angler's
clock ("06:40"), and `caught_utc_offset` that clock's offset from UTC in
minutes, which the browser sends with the time (`-getTimezoneOffset()` for
that day and time). The form fills the time from the photo's EXIF time when
its day is the catch's day, as it already filled the day. A time without an
offset is kept but placed against nothing.

**The weather is looked up, from the nearest airport station, never from the
spot.** `app/data/nws_stations.json` holds the weather service's 2,694 airport
stations (ICAO ids: K… in the lower 48, PA/PF/PO/PP… in Alaska, PH… in Hawaii;
`tools/weather/nws_stations.py`). The server finds the three nearest within
80 km itself and asks the weather service only for a station's reports in a
time window (`services/catch_weather.py`). The report nearest the catch
within 75 minutes stands for it: sky (clear, partly cloudy, cloudy, rain,
snow; from what is falling, then the most cloud reported), air temperature,
wind, pressure, and the pressure's change over the three hours before
(rising or falling by 1 hPa or more, else steady). It runs after the answer
(a background task), so saving a catch never waits on the weather service.

Only catches made in the last 6.5 days can be looked up. For anything older,
or without a time, the form asks for the sky instead (five chips, optional);
the angler's pick is stored the same way with `source = "angler"`. A station
that answered without a report for that hour leaves an empty row, so it isn't
asked again; a failed request leaves none, and opening the analysis tries
again for recent catches. A new time or spot drops a looked-up report (it
was for another moment); an angler's own pick stays.

`catch_weather` is a table of its own, one row per catch. The catch's page
shows the weather to whoever can see the catch, as it shows gear, with
"National Weather Service" beside a looked-up one.

**Time of day goes by that day's sun.** Dawn is from an hour before sunrise
to two hours after, dusk from two hours before sunset to an hour after,
midday an hour and a half either side of solar noon, morning and afternoon
in between, night outside (`services/catch_analysis.py`, NOAA's solar
formulas, within a couple of minutes of the almanac). So 8:20 is dawn in
December and morning in June. Where the sun doesn't rise or set (northern
Alaska), the clock decides.

**The analysis counts, it doesn't rate.** `GET /api/pins/analysis` (signed in)
counts the angler's own catches, public and private, whatever their gear
switch says (ADR 0056: paid features can't depend on consent), leaving out
any a moderator removed: fish; lures and baits (the /gear list's `lures` and
`bait`, not rods or bobbers); time of day; sky, pressure trend, temperature
(under 50, 50-64, 65-79, 80 °F and up) and wind (under 5, 5-14, 15 mph and
up); months; waters. One fish at a time with `?species=`. Every count says
how many catches it is out of, and the page says it counts catches, not bite
rates: a log has no record of hours fished without a bite.

**The page** is `/account/analysis`, linked from the account menu and from
"My catches" on the account page, with the "free in beta" tag. Headline tiles
(top fish, bait, time, weather) show only once at least three catches record
that thing. Every chart is one series in one green, its counts printed beside
the bars; hover and keyboard focus add the share. How it is counted sits in a
fold at the bottom.

## Consequences

- The privacy policy says catches record the date and time and the weather
  then, and names the National Weather Service among those who receive data:
  the nearest station and the time, never the spot. Its `UPDATED` date moves
  to the day this goes live.
- Weather reaches only catches logged within about a week of being made,
  unless the angler picks the sky. If the owner wants weather for older
  catches, GHCNh by station and year is the free source to build on.
- A time typed on a device in another time zone than the water's is placed by
  that device's clock. The station lookup and the sun use the offset sent
  with the time, so the catch is placed right as long as the angler types the
  time the clock at the water showed.
- `CATCH_WEATHER=off` keeps the test suite and CI off the network; the tests
  feed made-up station reports.
- When Plus opens, this page is one of its three core features; nothing in
  it is free-tier today that Plus would take away.
