"""The 50 states and DC: postal code, name, Geofabrik extract name and the
state fish and wildlife agency's home page (State.official_source_url).

The national map lights a state once it has lakes (api/states.py); every
state has a row from the start, so that question is one query."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.waterbody import State


@dataclass(frozen=True)
class UsState:
    code: str
    name: str
    geofabrik: str
    agency_url: str


STATES: tuple[UsState, ...] = (
    UsState("AL", "Alabama", "alabama", "https://www.outdooralabama.com"),
    UsState("AK", "Alaska", "alaska", "https://www.adfg.alaska.gov"),
    UsState("AZ", "Arizona", "arizona", "https://www.azgfd.com"),
    UsState("AR", "Arkansas", "arkansas", "https://www.agfc.com"),
    UsState("CA", "California", "california", "https://wildlife.ca.gov"),
    UsState("CO", "Colorado", "colorado", "https://cpw.state.co.us"),
    UsState("CT", "Connecticut", "connecticut", "https://portal.ct.gov/deep"),
    UsState("DE", "Delaware", "delaware", "https://dnrec.delaware.gov/fish-wildlife/"),
    UsState("DC", "District of Columbia", "district-of-columbia", "https://doee.dc.gov"),
    UsState("FL", "Florida", "florida", "https://myfwc.com"),
    UsState("GA", "Georgia", "georgia", "https://georgiawildlife.com"),
    UsState("HI", "Hawaii", "hawaii", "https://dlnr.hawaii.gov/dar/"),
    UsState("ID", "Idaho", "idaho", "https://idfg.idaho.gov"),
    UsState("IL", "Illinois", "illinois", "https://dnr.illinois.gov"),
    UsState("IN", "Indiana", "indiana", "https://www.in.gov/dnr/"),
    UsState("IA", "Iowa", "iowa", "https://www.iowadnr.gov"),
    UsState("KS", "Kansas", "kansas", "https://ksoutdoors.com"),
    UsState("KY", "Kentucky", "kentucky", "https://fw.ky.gov"),
    UsState("LA", "Louisiana", "louisiana", "https://www.wlf.louisiana.gov"),
    UsState("ME", "Maine", "maine", "https://www.maine.gov/ifw/"),
    UsState("MD", "Maryland", "maryland", "https://dnr.maryland.gov"),
    UsState("MA", "Massachusetts", "massachusetts", "https://www.mass.gov/orgs/division-of-fisheries-and-wildlife"),
    UsState("MI", "Michigan", "michigan", "https://www.michigan.gov/dnr"),
    UsState("MN", "Minnesota", "minnesota", "https://www.dnr.state.mn.us"),
    UsState("MS", "Mississippi", "mississippi", "https://www.mdwfp.com"),
    UsState("MO", "Missouri", "missouri", "https://mdc.mo.gov"),
    UsState("MT", "Montana", "montana", "https://fwp.mt.gov"),
    UsState("NE", "Nebraska", "nebraska", "https://outdoornebraska.gov"),
    UsState("NV", "Nevada", "nevada", "https://www.ndow.org"),
    UsState("NH", "New Hampshire", "new-hampshire", "https://www.wildlife.nh.gov"),
    UsState("NJ", "New Jersey", "new-jersey", "https://dep.nj.gov/njfw/"),
    UsState("NM", "New Mexico", "new-mexico", "https://wildlife.dgf.nm.gov"),
    UsState("NY", "New York", "new-york", "https://dec.ny.gov"),
    UsState("NC", "North Carolina", "north-carolina", "https://www.ncwildlife.org"),
    UsState("ND", "North Dakota", "north-dakota", "https://gf.nd.gov"),
    UsState("OH", "Ohio", "ohio", "https://ohiodnr.gov"),
    UsState("OK", "Oklahoma", "oklahoma", "https://www.wildlifedepartment.com"),
    UsState("OR", "Oregon", "oregon", "https://myodfw.com"),
    UsState("PA", "Pennsylvania", "pennsylvania", "https://www.fishandboat.com"),
    UsState("RI", "Rhode Island", "rhode-island", "https://dem.ri.gov"),
    UsState("SC", "South Carolina", "south-carolina", "https://www.dnr.sc.gov"),
    UsState("SD", "South Dakota", "south-dakota", "https://gfp.sd.gov"),
    UsState("TN", "Tennessee", "tennessee", "https://www.tn.gov/twra"),
    UsState("TX", "Texas", "texas", "https://tpwd.texas.gov"),
    UsState("UT", "Utah", "utah", "https://wildlife.utah.gov"),
    UsState("VT", "Vermont", "vermont", "https://vtfishandwildlife.com"),
    UsState("VA", "Virginia", "virginia", "https://dwr.virginia.gov"),
    UsState("WA", "Washington", "washington", "https://wdfw.wa.gov"),
    UsState("WV", "West Virginia", "west-virginia", "https://wvdnr.gov"),
    UsState("WI", "Wisconsin", "wisconsin", "https://dnr.wisconsin.gov"),
    UsState("WY", "Wyoming", "wyoming", "https://wgfd.wyo.gov"),
)
BY_CODE: dict[str, UsState] = {s.code: s for s in STATES}


def ensure_states(db: Session) -> int:
    """A State row for every state and DC; existing rows are left as they
    are (Texas keeps its TPWD lakes page as its source). Returns rows added."""
    have = set(db.scalars(select(State.code)))
    added = 0
    for s in STATES:
        if s.code not in have:
            db.add(State(code=s.code, name=s.name, official_source_url=s.agency_url))
            added += 1
    db.flush()
    return added
