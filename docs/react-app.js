import React, { useCallback, useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);
const app = window.LastEatApp;

const BATCH_SIZE = 12;
const DISTRICT_HIDE_ZOOM = 14;
const LEAFLET_CSS_INTEGRITY = "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
const LEAFLET_JS_INTEGRITY = "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";
const MC_JS_INTEGRITY = "sha256-Hk4dIpcqOSb0hZjgyvFOP+cEmDXUKKNE/tT542ZbNQg=";
const MC_CSS_INTEGRITY = "sha256-YSWCMtmNZNwqex4CEw1nQhvFub2lmU7vcCKP+XVwwXA=";
const MC_CSS_BASE_INTEGRITY = "sha256-YU3qCpj/P06tdPBJGPax0bm6Q1wltfwjsho5TR4+TYc=";
const LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
const MC_BASE_URL = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3";

const PRICE_RANGES = [
  { value: "0-30", label: "<=30 EUR" },
  { value: "31-50", label: "31-50 EUR" },
  { value: "51-80", label: "51-80 EUR" },
  { value: "80-999", label: "80+ EUR" },
];

const SORT_OPTIONS_BASE = [
  { value: "rating", label: "Ranking" },
  { value: "name", label: "A-Z" },
  { value: "price", label: "Precio" },
];

let leafletLoadPromise = null;

function appendStylesheetOnce(id, href, integrity) {
  if (document.getElementById(id)) return;
  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.href = href;
  if (integrity) link.integrity = integrity;
  link.crossOrigin = "anonymous";
  document.head.appendChild(link);
}

function appendScriptOnce(id, src, integrity) {
  return new Promise(function loadScript(resolve, reject) {
    const existing = document.getElementById(id);
    if (existing) {
      if (existing.dataset.loaded === "1") {
        resolve();
      } else {
        existing.addEventListener("load", function onLoad() {
          resolve();
        }, { once: true });
        existing.addEventListener("error", function onError() {
          reject(new Error("Failed to load " + src));
        }, { once: true });
      }
      return;
    }

    const script = document.createElement("script");
    script.id = id;
    script.src = src;
    if (integrity) script.integrity = integrity;
    script.crossOrigin = "anonymous";
    script.onload = function onLoad() {
      script.dataset.loaded = "1";
      resolve();
    };
    script.onerror = function onError() {
      reject(new Error("Failed to load " + src));
    };
    document.head.appendChild(script);
  });
}

function loadLeafletStack() {
  if (window.L && window.L.markerClusterGroup) return Promise.resolve();
  if (leafletLoadPromise) return leafletLoadPromise;

  leafletLoadPromise = (async function loadAll() {
    appendStylesheetOnce("leaflet-css", LEAFLET_CSS_URL, LEAFLET_CSS_INTEGRITY);
    await appendScriptOnce("leaflet-js", LEAFLET_JS_URL, LEAFLET_JS_INTEGRITY);
    appendStylesheetOnce("markercluster-css-base", MC_BASE_URL + "/MarkerCluster.css", MC_CSS_BASE_INTEGRITY);
    appendStylesheetOnce("markercluster-css-default", MC_BASE_URL + "/MarkerCluster.Default.css", MC_CSS_INTEGRITY);
    await appendScriptOnce("markercluster-js", MC_BASE_URL + "/leaflet.markercluster.js", MC_JS_INTEGRITY);
  })();

  return leafletLoadPromise;
}

function safeGetStorage(key, fallbackValue) {
  try {
    const value = localStorage.getItem(key);
    return value == null ? fallbackValue : value;
  } catch (_error) {
    return fallbackValue;
  }
}

function safeSetStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (_error) {
    // Ignore storage errors.
  }
}

function safeParseArray(value) {
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function splitCuisine(raw) {
  if (!raw) return [];
  return String(raw)
    .split(/[\u2022,]/)
    .map(function trimToken(token) {
      return token.trim();
    })
    .filter(Boolean);
}

function sanitizeExternalUrl(url) {
  if (!url) return "";
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.href;
    }
  } catch (_error) {
    return "";
  }
  return "";
}

function getRestaurantId(restaurant) {
  return restaurant.s || restaurant.n || "";
}

function parseUrlState(searchText) {
  const params = new URLSearchParams(searchText);

  let cuisine = params.getAll("c");
  if (cuisine.length === 1 && cuisine[0].includes(",")) cuisine = cuisine[0].split(",");

  let district = params.getAll("d");
  if (district.length === 1 && district[0].includes(",")) district = district[0].split(",");

  const view = params.get("v") === "map" ? "map" : "grid";

  return {
    query: params.get("q") || "",
    cuisine: cuisine.filter(Boolean),
    district: district.filter(Boolean),
    price: params.getAll("p").filter(Boolean),
    sort: params.get("s") || "rating",
    favsOnly: params.get("f") === "1",
    view,
  };
}

function formatUpdatedDate(meta) {
  if (!meta || !meta.updated) return "";
  try {
    const date = new Date(meta.updated);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("es-ES", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(date);
  } catch (_error) {
    return "";
  }
}

function makeCountMap(list, extractor) {
  const result = Object.create(null);
  list.forEach(function each(item) {
    extractor(item).forEach(function countValue(value) {
      if (!value) return;
      result[value] = (result[value] || 0) + 1;
    });
  });
  return result;
}

function sortedOptions(counts) {
  return Object.keys(counts)
    .sort(function sortNames(left, right) {
      return left.localeCompare(right, "es");
    })
    .map(function makeOption(name) {
      return { value: name, label: name, count: counts[name] || 0 };
    });
}

function topValues(counts, limit) {
  return Object.keys(counts)
    .sort(function sortTop(left, right) {
      const diff = (counts[right] || 0) - (counts[left] || 0);
      return diff !== 0 ? diff : left.localeCompare(right, "es");
    })
    .slice(0, limit);
}

function getTileUrl(theme) {
  return theme === "dark"
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
}

function markerIcon(Lib) {
  const width = 14;
  const height = 19;
  const cx = width / 2;
  const cr = width / 2 - 1;

  const svg =
    "<svg width='" + width + "' height='" + height + "' viewBox='0 0 " + width + " " + height + "' xmlns='http://www.w3.org/2000/svg'>" +
    "<path d='M" + cx + " " + height +
    " C" + (cx - cr * 0.7) + " " + (height * 0.62) +
    " 1 " + (cr + 2) +
    " 1 " + (cr + 1) +
    " A" + cr + " " + cr + " 0 1 1 " + (width - 1) + " " + (cr + 1) +
    " C" + (width - 1) + " " + (cr + 2) +
    " " + (cx + cr * 0.7) + " " + (height * 0.62) +
    " " + cx + " " + height + "Z'" +
    " fill='currentColor' stroke='#fff' stroke-width='1.2'/>" +
    "<circle cx='" + cx + "' cy='" + (cr + 1) + "' r='" + (cr * 0.38) + "' fill='#fff' opacity='0.9'/>" +
    "</svg>";

  return Lib.divIcon({
    html: "<div class='map-marker' style='color:var(--accent)'>" + svg + "</div>",
    className: "",
    iconSize: [width, height],
    iconAnchor: [width / 2, height],
    popupAnchor: [0, -height + 4],
  });
}

function districtStyle(selected) {
  const styles = getComputedStyle(document.documentElement);
  const accent = styles.getPropertyValue("--accent").trim() || "#2e6058";
  const border = styles.getPropertyValue("--line").trim() || "#dde0d6";

  if (selected) {
    return {
      fillColor: accent,
      fillOpacity: 0.25,
      color: accent,
      weight: 2.5,
      opacity: 1,
    };
  }

  return {
    fillColor: accent,
    fillOpacity: 0.06,
    color: border,
    weight: 1,
    opacity: 0.6,
  };
}

function buildPopupHtml(restaurant, esc) {
  const tags = splitCuisine(restaurant.c);
  const parts = [];

  parts.push("<div class='map-popup'>");
  parts.push("<div class='map-popup-name'>" + esc(restaurant.n || "") + "</div>");

  if (restaurant.r && restaurant.r !== "-") {
    parts.push("<span class='map-popup-rating'>" + esc(restaurant.r) + "</span>");
  }

  const meta = [];
  if (restaurant.d) meta.push(esc(restaurant.d));
  if (restaurant.p) meta.push(esc(restaurant.p) + " EUR");
  parts.push("<div class='map-popup-meta'>" + meta.join(" · ") + "</div>");

  if (tags.length) {
    parts.push("<div class='map-popup-tags'>" + esc(tags.slice(0, 3).join(", ")) + "</div>");
  }

  if (restaurant.s) {
    parts.push("<a class='map-popup-link' href='/r/" + encodeURIComponent(restaurant.s) + ".html'>Ver mas →</a>");
  }

  parts.push("</div>");
  return parts.join("");
}

function FilterBox(props) {
  const {
    title,
    options,
    selected,
    top,
    onToggle,
    onClear,
  } = props;

  return html`
    <details className="filter-box">
      <summary>${title}${selected.length ? ` (${selected.length})` : ""}</summary>
      <div className="filter-body">
        <div className="top-tags">
          ${top.map(function renderTop(value) {
            return html`
              <button
                key=${value}
                type="button"
                className=${`top-tag ${selected.includes(value) ? "active" : ""}`}
                onClick=${function clickTop() {
                  onToggle(value);
                }}
              >
                ${value}
              </button>
            `;
          })}
        </div>

        <div className="option-list" role="listbox" aria-label=${title}>
          ${options.map(function renderOption(option) {
            return html`
              <label key=${option.value} className="option-line">
                <input
                  type="checkbox"
                  checked=${selected.includes(option.value)}
                  onChange=${function toggleOption() {
                    onToggle(option.value);
                  }}
                />
                <span>${option.label}</span>
                <em>${option.count}</em>
              </label>
            `;
          })}
        </div>

        ${selected.length
          ? html`
              <button type="button" className="option-clear" onClick=${onClear}>
                Limpiar ${title.toLowerCase()}
              </button>
            `
          : null}
      </div>
    </details>
  `;
}

function RestaurantCard(props) {
  const {
    restaurant,
    expanded,
    isFav,
    onToggleExpand,
    onToggleFav,
  } = props;

  const id = getRestaurantId(restaurant);
  const ratingText = restaurant.r && restaurant.r !== "-" ? restaurant.r : "-";
  const ratingClassName = ratingText === "-" ? "rating empty" : "rating";
  const cuisines = splitCuisine(restaurant.c);
  const tagsText = cuisines.join(", ");
  const priceText = restaurant.p ? `${restaurant.p} EUR` : "";
  const districtText = restaurant.d || "Sin zona";
  const detailUrl = restaurant.s ? `/r/${encodeURIComponent(restaurant.s)}.html` : "#";
  const mapsUrl =
    "https://www.google.com/maps/search/?api=1&query=" +
    encodeURIComponent(`${restaurant.n || ""}, ${restaurant.a || ""}`);
  const websiteUrl = sanitizeExternalUrl(restaurant.w);
  const sourceUrl = sanitizeExternalUrl(restaurant.u);

  const hasDetail = Boolean(
    restaurant.rf ||
    restaurant.rd ||
    restaurant.rs ||
    restaurant.a ||
    restaurant.ph ||
    websiteUrl ||
    sourceUrl,
  );

  function onCardClick(event) {
    const interactive = event.target.closest("a,button,input,label");
    if (interactive) return;
    onToggleExpand(id);
  }

  function onCardKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onToggleExpand(id);
    }
  }

  return html`
    <article
      className="card"
      data-rid=${id}
      tabIndex="0"
      role="article"
      aria-label=${restaurant.n || "Restaurante"}
      onClick=${onCardClick}
      onKeyDown=${onCardKeyDown}
    >
      <div className="card-head">
        <h3 className="card-name"><a href=${detailUrl}>${restaurant.n || "Sin nombre"}</a></h3>

        <button
          type="button"
          className=${`fav ${isFav ? "active" : ""}`}
          aria-label=${isFav ? "Quitar de favoritos" : "Agregar a favoritos"}
          aria-pressed=${isFav ? "true" : "false"}
          onClick=${function clickFav(event) {
            event.stopPropagation();
            onToggleFav(id);
          }}
        >
          ${isFav ? "&#9829;" : "&#9825;"}
        </button>

        <div className=${ratingClassName}>${ratingText}</div>
      </div>

      <div className="card-meta">
        ${districtText}${priceText ? ` · ${priceText}` : ""}${restaurant._dist != null ? ` · ${app.formatDist(restaurant._dist)}` : ""}
      </div>

      ${tagsText ? html`<div className="card-tags">${tagsText}</div>` : null}

      <div className="card-actions">
        <a href=${mapsUrl} target="_blank" rel="noopener noreferrer" onClick=${function stopClick(event) {
            event.stopPropagation();
          }}>
          Ver en Maps
        </a>

        ${websiteUrl
          ? html`
              <a href=${websiteUrl} target="_blank" rel="noopener noreferrer" onClick=${function stopClick(event) {
                  event.stopPropagation();
                }}>
                Web
              </a>
            `
          : null}

        ${sourceUrl
          ? html`
              <a href=${sourceUrl} target="_blank" rel="noopener noreferrer" onClick=${function stopClick(event) {
                  event.stopPropagation();
                }}>
                Fuente
              </a>
            `
          : null}

        ${hasDetail
          ? html`
              <button
                type="button"
                onClick=${function clickExpand(event) {
                  event.stopPropagation();
                  onToggleExpand(id);
                }}
              >
                ${expanded ? "Ocultar" : "Detalle"}
              </button>
            `
          : null}
      </div>

      ${expanded && hasDetail
        ? html`
            <div className="expand">
              ${restaurant.rf || restaurant.rd || restaurant.rs
                ? html`
                    <div>
                      ${restaurant.rf ? `Comida ${restaurant.rf}` : ""}
                      ${restaurant.rd ? ` · Decor ${restaurant.rd}` : ""}
                      ${restaurant.rs ? ` · Servicio ${restaurant.rs}` : ""}
                    </div>
                  `
                : null}

              ${restaurant.a ? html`<div>${restaurant.a}</div>` : null}

              ${restaurant.ph
                ? html`
                    <div>
                      <a
                        href=${`tel:${String(restaurant.ph).replace(/\s+/g, "")}`}
                        onClick=${function stopClick(event) {
                          event.stopPropagation();
                        }}
                      >
                        ${restaurant.ph}
                      </a>
                    </div>
                  `
                : null}
            </div>
          `
        : null}
    </article>
  `;
}

function App() {
  const restaurants = Array.isArray(window.RESTAURANTS) ? window.RESTAURANTS : [];
  const meta = window.META && typeof window.META === "object" ? window.META : { count: restaurants.length };

  const urlState = useMemo(function initUrlState() {
    return parseUrlState(window.location.search || "");
  }, []);

  const slugSet = useMemo(function buildSlugSet() {
    return new Set(
      restaurants
        .map(function getSlug(item) {
          return item && item.s ? item.s : "";
        })
        .filter(Boolean),
    );
  }, [restaurants]);

  const nameToSlug = useMemo(function buildNameToSlug() {
    const map = Object.create(null);
    restaurants.forEach(function each(item) {
      if (!item || !item.n || !item.s) return;
      if (!map[item.n]) map[item.n] = item.s;
    });
    return map;
  }, [restaurants]);

  const [theme, setTheme] = useState(function getInitialTheme() {
    const stored = safeGetStorage("mf-theme", "");
    if (stored === "dark" || stored === "light") return stored;
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  });

  const [query, setQuery] = useState(urlState.query);
  const [selectedPrices, setSelectedPrices] = useState(urlState.price);
  const [selectedCuisine, setSelectedCuisine] = useState(urlState.cuisine);
  const [selectedDistrict, setSelectedDistrict] = useState(urlState.district);
  const [sort, setSort] = useState(urlState.sort || "rating");
  const [favsOnly, setFavsOnly] = useState(urlState.favsOnly);
  const [view, setView] = useState(urlState.view);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const [favs, setFavs] = useState(function initFavs() {
    const raw = safeParseArray(safeGetStorage("mf-fav", "[]"));
    const normalized = raw
      .map(function normalize(value) {
        if (typeof value !== "string" || !value) return "";
        if (slugSet.has(value)) return value;
        return nameToSlug[value] || "";
      })
      .filter(Boolean);
    return Array.from(new Set(normalized));
  });

  const [expandedIds, setExpandedIds] = useState([]);
  const [visibleCount, setVisibleCount] = useState(BATCH_SIZE);

  const [userPos, setUserPos] = useState(null);
  const [geoPending, setGeoPending] = useState(false);
  const [geoError, setGeoError] = useState("");

  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState("");
  const [mapVisibleItems, setMapVisibleItems] = useState([]);
  const [mapVisibleCount, setMapVisibleCount] = useState(0);
  const [activePanelId, setActivePanelId] = useState("");

  const mapNodeRef = useRef(null);
  const mapRef = useRef(null);
  const tileLayerRef = useRef(null);
  const clusterRef = useRef(null);
  const markerIndexRef = useRef([]);
  const markerByIdRef = useRef(new Map());
  const mapFitDoneRef = useRef(false);
  const userMarkerRef = useRef(null);
  const mapZoomHookBoundRef = useRef(false);

  const districtGeoDataRef = useRef(null);
  const districtLayerRef = useRef(null);
  const districtLayersByNameRef = useRef(Object.create(null));
  const selectedDistrictRef = useRef(new Set());
  const districtCountsRef = useRef(Object.create(null));

  useEffect(function updateSelectedDistrictRef() {
    selectedDistrictRef.current = new Set(selectedDistrict);
  }, [selectedDistrict]);

  useEffect(function syncTheme() {
    document.documentElement.setAttribute("data-theme", theme);
    safeSetStorage("mf-theme", theme);
  }, [theme]);

  useEffect(function persistFavs() {
    safeSetStorage("mf-fav", JSON.stringify(favs));
  }, [favs]);

  useEffect(function registerSw() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(function ignore() {
        // Ignore SW registration errors.
      });
    }
  }, []);

  const restaurantsForFilter = useMemo(function withDistance() {
    if (!userPos) return restaurants;
    return restaurants.map(function mapDistance(item) {
      if (!item.lat || !item.lng) return { ...item, _dist: 99999 };
      return {
        ...item,
        _dist: app.haversine(userPos.lat, userPos.lng, parseFloat(item.lat), parseFloat(item.lng)),
      };
    });
  }, [restaurants, userPos]);

  useEffect(function normalizeSortWithGeo() {
    if (sort === "distance" && !userPos) {
      setSort("rating");
    }
  }, [sort, userPos]);

  const favSet = useMemo(function buildFavSet() {
    return new Set(favs);
  }, [favs]);

  const baseCuisineCounts = useMemo(function countBaseCuisine() {
    return makeCountMap(restaurants, function fromItem(item) {
      return splitCuisine(item.c);
    });
  }, [restaurants]);

  const baseDistrictCounts = useMemo(function countBaseDistrict() {
    return makeCountMap(restaurants, function fromItem(item) {
      return item.d ? [item.d] : [];
    });
  }, [restaurants]);

  const topCuisineValues = useMemo(function computeTopCuisine() {
    return topValues(baseCuisineCounts, 6);
  }, [baseCuisineCounts]);

  const topDistrictValues = useMemo(function computeTopDistrict() {
    return topValues(baseDistrictCounts, 6);
  }, [baseDistrictCounts]);

  const effectiveSort = sort === "distance" && !userPos ? "rating" : sort;

  const filtered = useMemo(
    function computeFiltered() {
      return app.getFiltered(restaurantsForFilter, {
        query,
        selCuisine: new Set(selectedCuisine),
        selDistrict: new Set(selectedDistrict),
        priceValue: selectedPrices,
        favsOnly,
        favs: favSet,
        sort: effectiveSort,
        getFavKey: getRestaurantId,
        fuzzy: true,
      });
    },
    [restaurantsForFilter, query, selectedCuisine, selectedDistrict, selectedPrices, favsOnly, favSet, effectiveSort],
  );

  const dynamicCounts = useMemo(
    function computeDynamicCounts() {
      const forCuisine = app.getFiltered(restaurantsForFilter, {
        query,
        priceValue: selectedPrices,
        selCuisine: new Set(),
        selDistrict: new Set(selectedDistrict),
        favsOnly,
        favs: favSet,
        sort: "rating",
        getFavKey: getRestaurantId,
        fuzzy: true,
      });

      const forDistrict = app.getFiltered(restaurantsForFilter, {
        query,
        priceValue: selectedPrices,
        selCuisine: new Set(selectedCuisine),
        selDistrict: new Set(),
        favsOnly,
        favs: favSet,
        sort: "rating",
        getFavKey: getRestaurantId,
        fuzzy: true,
      });

      const cuisine = Object.create(null);
      forCuisine.forEach(function countCuisine(item) {
        splitCuisine(item.c).forEach(function addCuisine(name) {
          cuisine[name] = (cuisine[name] || 0) + 1;
        });
      });

      const district = Object.create(null);
      forDistrict.forEach(function countDistrict(item) {
        if (!item.d) return;
        district[item.d] = (district[item.d] || 0) + 1;
      });

      return { cuisine, district };
    },
    [restaurantsForFilter, query, selectedPrices, selectedCuisine, selectedDistrict, favsOnly, favSet],
  );

  useEffect(function updateDistrictCountRef() {
    districtCountsRef.current = dynamicCounts.district;
  }, [dynamicCounts]);

  const cuisineOptions = useMemo(function buildCuisineOptions() {
    return sortedOptions(baseCuisineCounts).map(function attachCounts(option) {
      return { ...option, count: dynamicCounts.cuisine[option.value] || 0 };
    });
  }, [baseCuisineCounts, dynamicCounts]);

  const districtOptions = useMemo(function buildDistrictOptions() {
    return sortedOptions(baseDistrictCounts).map(function attachCounts(option) {
      return { ...option, count: dynamicCounts.district[option.value] || 0 };
    });
  }, [baseDistrictCounts, dynamicCounts]);

  const sortOptions = useMemo(function buildSortOptions() {
    const options = SORT_OPTIONS_BASE.slice();
    if (userPos) options.push({ value: "distance", label: "Distancia" });
    return options;
  }, [userPos]);

  const activeTags = useMemo(
    function buildActiveTags() {
      const tags = [];
      if (query.trim()) {
        tags.push({
          key: `q-${query}`,
          label: `Busqueda: ${query.trim()}`,
          onRemove: function removeQuery() {
            setQuery("");
          },
        });
      }

      selectedPrices.forEach(function eachPrice(value) {
        const found = PRICE_RANGES.find(function findPrice(item) {
          return item.value === value;
        });
        tags.push({
          key: `p-${value}`,
          label: `Precio: ${found ? found.label : value}`,
          onRemove: function removePrice() {
            setSelectedPrices(function removeValue(previous) {
              return previous.filter(function keep(item) {
                return item !== value;
              });
            });
          },
        });
      });

      selectedCuisine.forEach(function eachCuisine(value) {
        tags.push({
          key: `c-${value}`,
          label: `Cocina: ${value}`,
          onRemove: function removeCuisine() {
            setSelectedCuisine(function removeValue(previous) {
              return previous.filter(function keep(item) {
                return item !== value;
              });
            });
          },
        });
      });

      selectedDistrict.forEach(function eachDistrict(value) {
        tags.push({
          key: `d-${value}`,
          label: `Zona: ${value}`,
          onRemove: function removeDistrict() {
            setSelectedDistrict(function removeValue(previous) {
              return previous.filter(function keep(item) {
                return item !== value;
              });
            });
          },
        });
      });

      if (favsOnly) {
        tags.push({
          key: "fav-only",
          label: "Solo favoritos",
          onRemove: function removeFavOnly() {
            setFavsOnly(false);
          },
        });
      }

      return tags;
    },
    [query, selectedPrices, selectedCuisine, selectedDistrict, favsOnly],
  );

  useEffect(
    function resetPagination() {
      setVisibleCount(BATCH_SIZE);
      setExpandedIds([]);
      setActivePanelId("");
    },
    [query, selectedPrices, selectedCuisine, selectedDistrict, effectiveSort, favsOnly],
  );

  const visibleRestaurants = useMemo(function getVisibleRestaurants() {
    return filtered.slice(0, visibleCount);
  }, [filtered, visibleCount]);

  useEffect(
    function syncUrl() {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      selectedCuisine.forEach(function eachCuisine(value) {
        params.append("c", value);
      });
      selectedDistrict.forEach(function eachDistrict(value) {
        params.append("d", value);
      });
      selectedPrices.forEach(function eachPrice(value) {
        params.append("p", value);
      });
      if (effectiveSort !== "rating") params.set("s", effectiveSort);
      if (favsOnly) params.set("f", "1");
      if (view === "map") params.set("v", "map");

      const next = params.toString();
      history.replaceState(null, "", next ? `?${next}` : location.pathname);
    },
    [query, selectedCuisine, selectedDistrict, selectedPrices, effectiveSort, favsOnly, view],
  );

  useEffect(function closeFilterOverlayOnGrid() {
    if (view !== "map") {
      setFiltersOpen(false);
    }
  }, [view]);

  function toggleSelection(setter, value) {
    setter(function toggle(previous) {
      if (previous.includes(value)) {
        return previous.filter(function keep(item) {
          return item !== value;
        });
      }
      return previous.concat(value);
    });
  }

  function toggleFavorite(id) {
    if (!id) return;
    setFavs(function toggleFav(previous) {
      if (previous.includes(id)) {
        return previous.filter(function keep(item) {
          return item !== id;
        });
      }
      return previous.concat(id);
    });
  }

  function toggleExpanded(id) {
    if (!id) return;
    setExpandedIds(function toggleExpand(previous) {
      if (previous.includes(id)) {
        return previous.filter(function keep(item) {
          return item !== id;
        });
      }
      return previous.concat(id);
    });
  }

  function clearAllFilters() {
    setQuery("");
    setSelectedPrices([]);
    setSelectedCuisine([]);
    setSelectedDistrict([]);
    setFavsOnly(false);
  }

  function runSurprise() {
    if (!filtered.length) return;
    if (view !== "grid") setView("grid");

    const index = Math.floor(Math.random() * filtered.length);
    const picked = filtered[index];
    const id = getRestaurantId(picked);

    const requiredVisible = Math.ceil((index + 1) / BATCH_SIZE) * BATCH_SIZE;
    if (requiredVisible > visibleCount) {
      setVisibleCount(requiredVisible);
    }

    setExpandedIds(function ensureExpanded(previous) {
      if (previous.includes(id)) return previous;
      return previous.concat(id);
    });

    setTimeout(function focusChosenCard() {
      const cards = document.querySelectorAll("[data-rid]");
      for (const card of cards) {
        if (card.getAttribute("data-rid") === id) {
          card.scrollIntoView({ behavior: "smooth", block: "center" });
          card.focus({ preventScroll: true });
          break;
        }
      }
    }, 80);
  }

  function toggleGeo() {
    if (userPos) {
      setUserPos(null);
      setGeoError("");
      if (sort === "distance") setSort("rating");
      return;
    }

    if (!navigator.geolocation) {
      setGeoError("Tu navegador no soporta geolocalizacion.");
      return;
    }

    setGeoPending(true);
    setGeoError("");

    navigator.geolocation.getCurrentPosition(
      function onSuccess(position) {
        setUserPos({ lat: position.coords.latitude, lng: position.coords.longitude });
        setGeoPending(false);
      },
      function onError() {
        setGeoPending(false);
        setGeoError("No se pudo obtener tu ubicacion.");
      },
      {
        enableHighAccuracy: false,
        timeout: 15000,
        maximumAge: 300000,
      },
    );
  }

  const syncMapPanel = useCallback(function syncMapPanel() {
    const map = mapRef.current;
    if (!map) return;

    const bounds = map.getBounds();
    const visible = [];

    markerIndexRef.current.forEach(function each(item) {
      if (bounds.contains(item.marker.getLatLng())) {
        visible.push(item.data);
      }
    });

    setMapVisibleItems(visible);
    setMapVisibleCount(visible.length);
  }, []);

  const syncDistrictLayerVisibility = useCallback(function syncDistrictVisibility() {
    const map = mapRef.current;
    const districtLayer = districtLayerRef.current;
    if (!map || !districtLayer) return;

    const selectedCount = selectedDistrictRef.current.size;

    if (map.getZoom() >= DISTRICT_HIDE_ZOOM && selectedCount === 0) {
      if (map.hasLayer(districtLayer)) map.removeLayer(districtLayer);
    } else if (!map.hasLayer(districtLayer)) {
      map.addLayer(districtLayer);
    }
  }, []);

  const applyDistrictStyles = useCallback(
    function applyStyles() {
      const layersByName = districtLayersByNameRef.current;
      Object.keys(layersByName).forEach(function eachDistrict(name) {
        const layer = layersByName[name];
        const selected = selectedDistrictRef.current.has(name);
        layer.setStyle(districtStyle(selected));

        const count = districtCountsRef.current[name] || 0;
        if (layer.getTooltip()) {
          layer.setTooltipContent(name + " (" + count + ")");
        }
      });

      syncDistrictLayerVisibility();
    },
    [syncDistrictLayerVisibility],
  );

  const ensureDistrictGeo = useCallback(async function ensureDistrictGeo() {
    if (districtGeoDataRef.current) return;
    const response = await fetch("districts.geojson");
    if (!response.ok) throw new Error("No se pudo cargar districts.geojson");
    districtGeoDataRef.current = await response.json();
  }, []);

  const addDistrictLayer = useCallback(
    function addDistrictLayer() {
      const map = mapRef.current;
      const geo = districtGeoDataRef.current;
      const Lib = window.L;
      if (!map || !geo || !Lib) return;

      if (districtLayerRef.current) {
        map.removeLayer(districtLayerRef.current);
        districtLayerRef.current = null;
      }

      districtLayersByNameRef.current = Object.create(null);

      if (!map.getPane("districts")) {
        map.createPane("districts");
        map.getPane("districts").style.zIndex = 250;
      }

      const geoLayer = Lib.geoJSON(geo, {
        pane: "districts",
        style: function styleFeature(feature) {
          const name = feature.properties.name;
          return districtStyle(selectedDistrictRef.current.has(name));
        },
        onEachFeature: function eachFeature(feature, layer) {
          const name = feature.properties.name;
          districtLayersByNameRef.current[name] = layer;

          const count = districtCountsRef.current[name] || 0;
          layer.bindTooltip(name + " (" + count + ")", {
            sticky: true,
            direction: "top",
            className: "map-tooltip",
          });

          layer.on("mouseover", function hoverIn() {
            if (!selectedDistrictRef.current.has(name)) {
              layer.setStyle({ fillOpacity: 0.18, weight: 1.5 });
            }
          });

          layer.on("mouseout", function hoverOut() {
            layer.setStyle(districtStyle(selectedDistrictRef.current.has(name)));
          });

          layer.on("click", function clickDistrict(event) {
            Lib.DomEvent.stopPropagation(event);
            setSelectedDistrict(function toggle(previous) {
              if (previous.includes(name)) {
                return previous.filter(function keep(item) {
                  return item !== name;
                });
              }
              return previous.concat(name);
            });
          });
        },
      });

      geoLayer.addTo(map);
      districtLayerRef.current = geoLayer;

      if (!mapZoomHookBoundRef.current) {
        map.on("zoomend", syncDistrictLayerVisibility);
        mapZoomHookBoundRef.current = true;
      }

      applyDistrictStyles();
    },
    [applyDistrictStyles, syncDistrictLayerVisibility],
  );

  const updateMapMarkers = useCallback(
    function updateMarkers() {
      const map = mapRef.current;
      const Lib = window.L;
      if (!map || !Lib || !Lib.markerClusterGroup) return;

      if (clusterRef.current) {
        map.removeLayer(clusterRef.current);
        clusterRef.current = null;
      }

      const cluster = Lib.markerClusterGroup({
        maxClusterRadius: function byZoom(zoom) {
          if (zoom >= 16) return 10;
          if (zoom >= 14) return 20;
          if (zoom >= 12) return 30;
          return 40;
        },
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        disableClusteringAtZoom: 17,
        animateAddingMarkers: true,
      });

      const markerIndex = [];
      const markerById = new Map();

      filtered.forEach(function eachRestaurant(restaurant) {
        if (!restaurant.lat || !restaurant.lng) return;

        const markerId = getRestaurantId(restaurant);
        const latlng = Lib.latLng(parseFloat(restaurant.lat), parseFloat(restaurant.lng));
        const marker = Lib.marker(latlng, { icon: markerIcon(Lib) });

        marker.bindPopup(buildPopupHtml(restaurant, app.esc), {
          maxWidth: 260,
          minWidth: 180,
        });

        marker.on("popupopen", function popupOpen() {
          setActivePanelId(markerId);
        });

        marker.on("popupclose", function popupClose() {
          syncMapPanel();
        });

        cluster.addLayer(marker);
        markerIndex.push({ marker, data: restaurant });
        if (markerId) markerById.set(markerId, marker);
      });

      map.addLayer(cluster);
      clusterRef.current = cluster;
      markerIndexRef.current = markerIndex;
      markerByIdRef.current = markerById;

      if (userMarkerRef.current) {
        userMarkerRef.current.remove();
        userMarkerRef.current = null;
      }

      if (userPos) {
        const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#2e6058";
        userMarkerRef.current = Lib.circleMarker([userPos.lat, userPos.lng], {
          radius: 8,
          fillColor: accent,
          fillOpacity: 1,
          color: "#fff",
          weight: 2.5,
        })
          .bindPopup("Tu ubicacion")
          .addTo(map);
      }

      if (!mapFitDoneRef.current) {
        const allMarkers = markerIndex.map(function each(item) {
          return item.marker;
        });
        if (userMarkerRef.current) allMarkers.push(userMarkerRef.current);

        if (allMarkers.length) {
          const group = Lib.featureGroup(allMarkers);
          map.fitBounds(group.getBounds().pad(0.1));
        }

        mapFitDoneRef.current = true;
      }

      syncMapPanel();
      applyDistrictStyles();
    },
    [filtered, userPos, syncMapPanel, applyDistrictStyles],
  );

  useEffect(
    function mountMapOnView() {
      if (view !== "map") return;

      let cancelled = false;

      loadLeafletStack()
        .then(async function onLoaded() {
          if (cancelled) return;

          const Lib = window.L;
          if (!Lib) throw new Error("Leaflet no disponible");

          setMapReady(true);
          setMapError("");

          if (!mapRef.current) {
            const map = Lib.map(mapNodeRef.current).setView([40.42, -3.7], 13);
            map.attributionControl.setPrefix("");
            mapRef.current = map;

            tileLayerRef.current = Lib.tileLayer(getTileUrl(theme), {
              attribution:
                "&copy; <a href='https://www.openstreetmap.org/copyright'>OSM</a> &copy; <a href='https://carto.com/attributions'>CARTO</a>",
            }).addTo(map);

            map.on("moveend", syncMapPanel);
          }

          if (!districtGeoDataRef.current) {
            try {
              await ensureDistrictGeo();
            } catch (_error) {
              // District layer is optional; map still works without it.
            }
          }

          if (districtGeoDataRef.current && !districtLayerRef.current) {
            addDistrictLayer();
          }

          updateMapMarkers();

          setTimeout(function invalidateMap() {
            if (mapRef.current) mapRef.current.invalidateSize();
          }, 50);
        })
        .catch(function onMapError(error) {
          setMapError(error && error.message ? error.message : "Error cargando el mapa");
        });

      return function cleanup() {
        cancelled = true;
      };
    },
    [view, theme, syncMapPanel, ensureDistrictGeo, addDistrictLayer, updateMapMarkers],
  );

  useEffect(
    function updateMapWhenFiltersChange() {
      if (view !== "map") return;
      if (!mapRef.current) return;
      updateMapMarkers();
    },
    [view, updateMapMarkers],
  );

  useEffect(
    function updateMapThemeAndDistricts() {
      if (!mapRef.current) return;
      if (tileLayerRef.current) {
        tileLayerRef.current.setUrl(getTileUrl(theme));
      }
      applyDistrictStyles();
    },
    [theme, applyDistrictStyles],
  );

  useEffect(
    function updateDistrictStylesOnSelection() {
      applyDistrictStyles();
    },
    [selectedDistrict, dynamicCounts, applyDistrictStyles],
  );

  useEffect(
    function addMapClassToBody() {
      document.body.classList.toggle("map-mode", view === "map");
      return function cleanup() {
        document.body.classList.remove("map-mode");
      };
    },
    [view],
  );

  function focusMapItem(item) {
    const markerId = getRestaurantId(item);
    const map = mapRef.current;
    const cluster = clusterRef.current;
    const marker = markerByIdRef.current.get(markerId);
    if (!map || !cluster || !marker) return;

    setActivePanelId(markerId);
    map.flyTo(marker.getLatLng(), 16, { duration: 0.6 });
    cluster.zoomToShowLayer(marker, function showMarker() {
      marker.openPopup();
    });
  }

  const footerUpdated = formatUpdatedDate(meta);
  const showFiltersPanel = view !== "map" || filtersOpen;
  const filterCount = selectedCuisine.length + selectedDistrict.length + selectedPrices.length;

  if (!app || typeof app.getFiltered !== "function") {
    return html`
      <div className="shell">
        <section className="empty">Error: no se pudo cargar app.js.</section>
      </div>
    `;
  }

  return html`
    <div className="shell">
      <a href="#results" className="skip-link">Saltar al listado</a>

      <header className="hero">
        <p className="kicker">Madrid Restaurant Atlas</p>
        <h1 className="brand">Last Eat</h1>
        <p className="lead">
          Explorador de restaurantes en React. Busca, filtra, guarda favoritos y alterna entre listado y mapa.
        </p>

        <button
          type="button"
          className="theme-btn"
          onClick=${function toggleTheme() {
            setTheme(function switchTheme(current) {
              return current === "dark" ? "light" : "dark";
            });
          }}
        >
          ${theme === "dark" ? "Modo claro" : "Modo oscuro"}
        </button>
      </header>

      <section className="panel">
        <div className="row view-row">
          <div className="view-toggle">
            <button
              type="button"
              className=${`chip ${view === "grid" ? "active" : ""}`}
              onClick=${function toGrid() {
                setView("grid");
              }}
            >
              Lista
            </button>
            <button
              type="button"
              className=${`chip ${view === "map" ? "active" : ""}`}
              onClick=${function toMap() {
                setView("map");
              }}
            >
              Mapa
            </button>
          </div>

          ${view === "map"
            ? html`
                <button
                  type="button"
                  className=${`chip ${filtersOpen ? "active" : ""}`}
                  onClick=${function toggleFilters() {
                    setFiltersOpen(function toggle(current) {
                      return !current;
                    });
                  }}
                >
                  Filtros${filterCount ? ` (${filterCount})` : ""}
                </button>
              `
            : null}

          <button
            type="button"
            className=${`chip ${favsOnly ? "active" : ""}`}
            aria-pressed=${favsOnly ? "true" : "false"}
            onClick=${function toggleFavOnly() {
              setFavsOnly(function toggle(current) {
                return !current;
              });
            }}
          >
            Favoritos${favs.length ? ` (${favs.length})` : ""}
          </button>

          <button type="button" className="chip" onClick=${runSurprise}>Sorprendeme</button>

          <button
            type="button"
            className=${`chip ${userPos ? "active" : ""}`}
            onClick=${toggleGeo}
            disabled=${geoPending}
          >
            ${geoPending ? "Localizando..." : userPos ? "Quitar ubicacion" : "Cerca de mi"}
          </button>
        </div>

        ${geoError ? html`<div className="error-msg">${geoError}</div>` : null}

        ${showFiltersPanel
          ? html`
              <div className="row" style=${{ marginTop: "0.55rem" }}>
                <label className="sr-only" htmlFor="search-box">Buscar restaurante</label>
                <input
                  id="search-box"
                  className="search"
                  type="text"
                  placeholder="Buscar restaurante, cocina, zona..."
                  value=${query}
                  onInput=${function onInput(event) {
                    setQuery(event.target.value);
                  }}
                />

                ${query
                  ? html`
                      <button
                        type="button"
                        className="clear-btn"
                        onClick=${function clearSearch() {
                          setQuery("");
                        }}
                      >
                        Limpiar
                      </button>
                    `
                  : null}
              </div>

              <div className="row" style=${{ marginTop: "0.55rem" }}>
                ${PRICE_RANGES.map(function renderPrice(range) {
                  return html`
                    <button
                      key=${range.value}
                      type="button"
                      className=${`chip ${selectedPrices.includes(range.value) ? "active" : ""}`}
                      onClick=${function togglePrice() {
                        toggleSelection(setSelectedPrices, range.value);
                      }}
                    >
                      ${range.label}
                    </button>
                  `;
                })}
              </div>

              <div className="filter-grid">
                <${FilterBox}
                  title="Cocina"
                  options=${cuisineOptions}
                  selected=${selectedCuisine}
                  top=${topCuisineValues}
                  onToggle=${function onToggleCuisine(value) {
                    toggleSelection(setSelectedCuisine, value);
                  }}
                  onClear=${function clearCuisine() {
                    setSelectedCuisine([]);
                  }}
                />

                <${FilterBox}
                  title="Zona"
                  options=${districtOptions}
                  selected=${selectedDistrict}
                  top=${topDistrictValues}
                  onToggle=${function onToggleDistrict(value) {
                    toggleSelection(setSelectedDistrict, value);
                  }}
                  onClear=${function clearDistrict() {
                    setSelectedDistrict([]);
                  }}
                />
              </div>

              <div className="row sort-row">
                <span className="sort-title">Ordenar</span>
                ${sortOptions.map(function renderSort(option) {
                  return html`
                    <button
                      key=${option.value}
                      type="button"
                      className=${`sort-btn ${effectiveSort === option.value ? "active" : ""}`}
                      onClick=${function setSortValue() {
                        setSort(option.value);
                      }}
                    >
                      ${option.label}
                    </button>
                  `;
                })}
              </div>
            `
          : null}

        ${activeTags.length
          ? html`
              <div className="tags">
                ${activeTags.map(function renderTag(tag) {
                  return html`
                    <span className="tag" key=${tag.key}>
                      ${tag.label}
                      <button type="button" onClick=${tag.onRemove} aria-label="Quitar filtro">&#10005;</button>
                    </span>
                  `;
                })}

                <button type="button" className="clear-btn" onClick=${clearAllFilters}>
                  Limpiar filtros
                </button>
              </div>
            `
          : null}
      </section>

      <main id="results">
        ${view === "grid"
          ? html`
              <div className="results-head">
                <strong>${filtered.length}</strong> de ${meta.count || restaurants.length} restaurantes
              </div>

              <div className="cards">
                ${visibleRestaurants.length
                  ? visibleRestaurants.map(function renderRestaurant(restaurant, index) {
                      const id = getRestaurantId(restaurant);
                      return html`
                        <${RestaurantCard}
                          key=${id || `${restaurant.n || "restaurant"}-${index}`}
                          restaurant=${restaurant}
                          expanded=${expandedIds.includes(id)}
                          isFav=${favSet.has(id)}
                          onToggleExpand=${toggleExpanded}
                          onToggleFav=${toggleFavorite}
                        />
                      `;
                    })
                  : html`
                      <section className="empty">
                        <p>No encontramos restaurantes con estos filtros.</p>
                        <button type="button" className="clear-btn" onClick=${clearAllFilters}>
                          Limpiar filtros
                        </button>
                      </section>
                    `}
              </div>

              ${filtered.length > visibleCount
                ? html`
                    <div className="load-wrap">
                      <button
                        type="button"
                        className="load-more"
                        onClick=${function loadMore() {
                          setVisibleCount(function next(previous) {
                            return previous + BATCH_SIZE;
                          });
                        }}
                      >
                        Mostrar mas (${Math.min(BATCH_SIZE, filtered.length - visibleCount)} restantes)
                      </button>
                    </div>
                  `
                : null}
            `
          : html`
              <section className="map-shell ${mapReady ? "" : "loading"}">
                <aside className="map-side" aria-label="Restaurantes visibles en mapa">
                  <div className="map-topline">
                    <span>Explora Madrid</span>
                    <span>${mapVisibleCount} visibles</span>
                  </div>

                  ${mapVisibleItems.length
                    ? html`
                        <ul className="map-list">
                          ${mapVisibleItems.map(function renderMapItem(item) {
                            const id = getRestaurantId(item);
                            return html`
                              <li key=${id}>
                                <button
                                  type="button"
                                  className=${`map-list-item ${activePanelId === id ? "active" : ""}`}
                                  onClick=${function focusItem() {
                                    focusMapItem(item);
                                  }}
                                >
                                  <span className="map-item-name">${item.n}</span>
                                  <span className="map-item-meta">
                                    ${item.r && item.r !== "-" ? `${item.r} · ` : ""}${item.d || "Sin zona"}${item.p ? ` · ${item.p} EUR` : ""}
                                  </span>
                                </button>
                              </li>
                            `;
                          })}
                        </ul>
                      `
                    : html`<div className="map-empty">Mueve el mapa para ver restaurantes en esta zona.</div>`}
                </aside>

                <div className="map-main">
                  <div ref=${mapNodeRef} className="map-canvas" id="map-view-react"></div>
                  <div className="map-count-badge">${mapVisibleCount} restaurantes visibles</div>
                  ${mapError ? html`<div className="error-msg map-error">${mapError}</div>` : null}
                </div>
              </section>
            `}
      </main>

      <footer className="footer">
        <span>Last Eat · React</span>
        <span>${footerUpdated ? `Actualizado ${footerUpdated}` : ""}</span>
      </footer>
    </div>
  `;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
