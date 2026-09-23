# Weather scoring — what the sources actually say

Every threshold in `app/services/scoring.py`'s weather factor traces back
to this document. It exists because the first version of that code had
numbers I picked by intuition, which is exactly the failure mode this
project is otherwise built to avoid: fluent, confident output with nothing
behind it.

## The honest summary first

**There is no authoritative quantitative rubric for "weather → fishing
quality."** State agencies and university extensions publish water-quality
and regulation data, not scoring models. The usable knowledge lives in
angling publications and professional anglers' experience — consistent and
mechanistically plausible, but *experiential consensus, not measured data*.

So the thresholds below are heuristics calibrated to expressed expert
consensus. They are not fitted to catch data, and this project has no catch
data to fit them to. Where a number is a judgment call, it says so.

## Factor-by-factor

### Wind speed — strongest support, and non-monotonic

The consensus is unusually clear: **a light chop beats dead calm**, and the
mechanism is described the same way across sources.

- Wind-driven current concentrates plankton on downwind shores, which draws
  baitfish, which draws bass. Bassresource quantifies the current itself:
  surface current runs roughly 1–2% of wind speed, so a 15 mph wind moves
  water about 0.1 mph, a 30 mph wind about 0.5 mph.
  ([Bassresource](https://www.bassresource.com/fishing/wind_fish.html))
- Surface chop reduces light penetration, which makes fish "less spooky,
  especially in clear water" (same source). Two independent mechanisms
  pointing the same way.
- The upper bound is about the angler, not the fish: strong wind on open
  water is a boat-control and safety problem.

**Encoded as:** calm (<4 mph) scores below a light chop; 4–15 mph is the
favorable band; 15–22 mph is workable but degraded; above 22 mph is scored
low and flagged as a safety concern rather than merely poor fishing.

*Judgment call:* the exact mph breakpoints. Sources describe the shape of
the curve and the mechanism, not cutoffs. The band edges are mine.

### Wind direction — only useful for naming the shore

Sources support using direction to locate fish (the downwind/windblown bank
holds the food chain), **not** as a quality signal in itself. The old saying
"wind from the west, fish bite the best" has no mechanistic support and is
not encoded.

Note the unit trap this project already hit once: NWS reports the compass
point wind blows **from**, so an SE wind stacks bait on the **NW** shore.
Naming the wrong bank sends an angler to the dead side of the lake.

### Water temperature — best-supported factor, and we cannot measure it

This is the factor with real numbers behind it, because it's ordinary
cold-blooded physiology rather than folklore. For largemouth bass
([Today's Bite Report](https://www.todaysbitereport.com/blog/water-temperature-bass-feeding-chart)):

| Water temp | Behavior |
|---|---|
| 38–45°F | near dormant, may go days between meals |
| 45–55°F | slow, building; activity picks up above 48°F |
| 55–65°F | aggressive pre-spawn feeding |
| **65–75°F** | **peak metabolic window — highest strike rate** |
| 75–85°F | active but shifts to dawn/dusk/night; deep at midday |
| 85°F+ | heat stress, increasingly lethargic |

**The problem: NWS gives air temperature, not water temperature.** They are
not interchangeable — water lags air by days to weeks and stratifies with
depth. Substituting air temp here would be the single most misleading thing
this scoring engine could do, because it would look authoritative and be
wrong in spring and fall precisely when it matters most.

**Encoded as:** an explicitly unavailable sub-signal. It costs confidence
and is named in the output, the same treatment habitat gets. The table above
is kept here ready for the day a water-temperature source is wired in (USGS
gauges cover some reservoirs; TPWD publishes some survey temps).

### Barometric pressure — deliberately NOT a scoring factor

This is the one that changed my mind mid-research.

Belief in falling pressure as a bite trigger is close to universal among
professional anglers — Wired2Fish quotes pros saying the bite "usually
improves as the barometer drops, in pre-frontal conditions."
([Wired2Fish](https://www.wired2fish.com/fish-biology/understanding-barometric-pressure-in-fishing))
Commercial fishing apps sell forecasts built on it.

But the same article concedes there are "no significant scientific studies
that correlate fish behavior with barometric changes," and the physics
argument against it is hard to dismiss
([The Fisherman](https://www.thefisherman.com/article/the-truth-about-barometric-pressure/)):
water is ~800× denser than air, so **a fish moving three feet vertically
experiences a larger pressure change than the passage of a major
hurricane** — and it experiences it in seconds rather than over a day. A
fish that cared about barometric pressure could not hold depth.

The conclusion that survives: *"It is not the barometric pressure that is
influencing the fish or fishing."* Falling pressure **correlates** with
things that do matter — wind shift, cloud cover, temperature change,
turbidity — and anglers reading the barometer are really reading an
approaching front.

**Encoded as:** nothing. Pressure gets no weight of its own. Giving it one
would double-count the wind, cloud and precipitation signals it proxies for,
and would require an extra API call (pressure isn't in the NWS hourly
forecast; it needs the observation-station endpoint) to buy a number whose
causal claim doesn't survive scrutiny. What pressure was *proxying for* is
captured directly instead — see below.

### Frontal passage — capture the thing pressure was a proxy for

The pre-front / post-front pattern is the most consistently reported effect
in the angling literature:

- **Pre-frontal** (front approaching): feeding window, often the best bite.
- **Post-frontal** ("bluebird sky"): the notoriously tough bite. Berkley
  describes the mechanism — surface water cools, bass "become lethargic and
  their metabolism slows," and they drop to deeper, more stable water and
  bury in tight cover.
  ([Berkley](https://www.berkley-fishing.com/pages/berkley-ae-fishing-after-cold-fronts))

**Encoded as:** a front signal derived from the *forecast temperature
trend*, which NWS does give us hourly. A sharp drop ahead means a front is
arriving, so the hours before it are scored as a feeding window.

**Known gap:** the NWS hourly forecast only looks forward, so this detects
an *approaching* front but not one that has *just passed* — and post-frontal
is the condition anglers most want warned about. Closing it needs recent
observations (`/stations/{id}/observations`), which is a real API addition,
not a tweak. Documented rather than faked.

### Cloud cover and low light

Supported, with a weaker evidentiary base than wind. Overcast keeps bass
shallower and more active/roaming, while bright sun pushes them tight to
shade and cover
([Smartbaits](https://www.smartbaits.com/blogs/news/best-overcast-fishing-tips-for-bass-anglers)).
Above 75°F, feeding shifts to early morning, late evening and night (temp
table above) — which is the same dawn/dusk preference, arriving through
temperature rather than light.

**Encoded as:** a modest low-light bonus in the time-window search only, not
in the spot score. It affects *when* to go, not *where*, and the effect size
claimed in the sources doesn't justify more.

## What would make this better than heuristics

Log predicted score against actual reported catch (the PRD's community pins
are the obvious source), then fit the weights. Until then these are
defensible priors, labeled as priors — which is the honest state for a
system with no outcome data yet, and is why the API returns per-factor
reasons rather than just a number.
