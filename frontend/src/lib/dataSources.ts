/** The datasets behind the map and the lake pages, for /sources. What each is
 * used for is translated (i18n sourcesPage.dataUse). The full record, with
 * licences and dates, is docs/data-sources.md. */
export const DATA_SOURCES = [
  { id: "osm", label: "© OpenStreetMap contributors", url: "https://www.openstreetmap.org/copyright" },
  { id: "tpwd", label: "Texas Parks and Wildlife Department", url: "https://tpwd.texas.gov/" },
  { id: "georgia", label: "Georgia DNR Wildlife Resources Division", url: "https://georgiawildlife.com/" },
  { id: "cdfw", label: "California Department of Fish and Wildlife (BIOS)", url: "https://wildlife.ca.gov/Data/BIOS" },
  { id: "padus", label: "USGS: PAD-US Public Access", url: "https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004" },
  { id: "nas", label: "USGS: Nonindigenous Aquatic Species", url: "https://nas.er.usgs.gov/" },
  { id: "gbif", label: "GBIF", url: "https://www.gbif.org/" },
  { id: "nws", label: "National Weather Service", url: "https://www.weather.gov/" },
  { id: "census", label: "US Census Bureau: county boundaries", url: "https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html" },
  { id: "bioclip", label: "BioCLIP 2 (Imageomics), with iNaturalist photos through GBIF", url: "https://huggingface.co/imageomics/bioclip-2" },
  { id: "gearcam", label: "Perception Encoder (Meta), with Open Images V7 (Google) and Wikimedia Commons photos", url: "https://huggingface.co/timm/PE-Core-L-14-336" },
] as const;
