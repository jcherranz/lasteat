import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);

function safeExternalUrl(value) {
  if (!value || typeof value !== "string") return "";
  try {
    const url = new URL(value, window.location.origin);
    if (url.protocol === "http:" || url.protocol === "https:") return url.href;
  } catch (_error) {
    return "";
  }
  return "";
}

function splitCuisine(raw) {
  if (!raw) return [];
  return String(raw)
    .replace(/,/g, "•")
    .split(/\u2022/)
    .map(function trim(token) {
      return token.trim();
    })
    .filter(Boolean);
}

function getMapsUrl(data) {
  const query = `${data.name || ""}, ${data.address || ""}`;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function parseRestaurantData() {
  const el = document.getElementById("restaurant-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch (_error) {
    return null;
  }
}

function App(props) {
  const { restaurant } = props;

  const [theme, setTheme] = useState(function getInitialTheme() {
    try {
      const saved = localStorage.getItem("mf-theme");
      if (saved === "dark" || saved === "light") return saved;
    } catch (_error) {
      // Ignore localStorage errors.
    }

    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  });

  useEffect(
    function syncTheme() {
      document.documentElement.setAttribute("data-theme", theme);
      try {
        localStorage.setItem("mf-theme", theme);
      } catch (_error) {
        // Ignore localStorage errors.
      }
    },
    [theme],
  );

  const cuisines = useMemo(
    function computeCuisines() {
      return splitCuisine(restaurant.cuisine);
    },
    [restaurant.cuisine],
  );

  const website = safeExternalUrl(restaurant.website);
  const source = safeExternalUrl(restaurant.macarfi_url);
  const mapsUrl = getMapsUrl(restaurant);
  const hasCoords = Boolean(restaurant.latitude && restaurant.longitude);

  const rating = restaurant.rating && restaurant.rating !== "-" ? restaurant.rating : "—";
  const meta = [restaurant.district, restaurant.price_eur ? `${restaurant.price_eur} €` : ""].filter(Boolean);
  const ratingParts = [
    restaurant.rating_food ? `Comida ${restaurant.rating_food}` : "",
    restaurant.rating_decor ? `Decor ${restaurant.rating_decor}` : "",
    restaurant.rating_service ? `Servicio ${restaurant.rating_service}` : "",
  ].filter(Boolean);

  return html`
    <>
      <a href="#main" className="skip-link">Saltar al contenido</a>
      <button
        type="button"
        className="theme-btn"
        onClick=${function toggleTheme() {
          setTheme(function next(current) {
            return current === "dark" ? "light" : "dark";
          });
        }}
      >
        ${theme === "dark" ? "Modo claro" : "Modo oscuro"}
      </button>

      <main className="container" id="main">
        <a href="/" className="back">← Last Eat</a>
        <h1>${restaurant.name || "Restaurante"}</h1>

        ${meta.length
          ? html`
              <div className="meta">
                ${meta.map(function renderMeta(item) {
                  return html`<span key=${item}>${item}</span>`;
                })}
              </div>
            `
          : null}

        ${cuisines.length ? html`<div className="tags">${cuisines.join(", ")}</div>` : null}

        <div className="score">${rating}</div>

        ${ratingParts.length ? html`<div className="ratings">${ratingParts.join(" · ")}</div>` : null}

        <div className="card">
          <div className="card-label">Dirección</div>
          <div className="card-value">${restaurant.address || "—"}</div>
        </div>

        ${restaurant.phone || website || source
          ? html`
              <div className="contact">
                ${restaurant.phone
                  ? html`
                      <a href=${`tel:${String(restaurant.phone).replace(/\s+/g, "")}`}>${restaurant.phone}</a>
                    `
                  : null}
                ${restaurant.phone && (website || source) ? " · " : null}
                ${website ? html`<a href=${website} target="_blank" rel="noopener noreferrer">Web</a>` : null}
                ${website && source ? " · " : null}
                ${source ? html`<a href=${source} target="_blank" rel="noopener noreferrer">Fuente</a>` : null}
              </div>
            `
          : null}

        ${hasCoords
          ? html`
              <a href=${mapsUrl} className="maps-btn" target="_blank" rel="noopener noreferrer">
                Ver en Google Maps
              </a>
            `
          : null}
      </main>

      <footer>
        <a href="/">Last Eat</a> · Restaurantes en Madrid
      </footer>
    </>
  `;
}

const restaurant = parseRestaurantData();
const rootEl = document.getElementById("restaurant-root");

if (!rootEl || !restaurant) {
  console.error("Restaurant detail bootstrap failed");
} else {
  createRoot(rootEl).render(html`<${App} restaurant=${restaurant} />`);
}
