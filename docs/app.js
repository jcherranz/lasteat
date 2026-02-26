(function(root) {
  'use strict';

  function esc(value) {
    var s = value == null ? '' : String(value);
    return s
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function haversine(lat1, lng1, lat2, lng2) {
    var R = 6371;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLng = (lng2 - lng1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function formatDist(km) {
    if (km >= 99999) return '';
    if (km < 1) return Math.round(km * 1000) + ' m';
    return km.toFixed(1) + ' km';
  }

  function sortList(list, key) {
    return list.slice().sort(function(a, b) {
      if (key === 'rating') return (parseFloat(b.r) || 0) - (parseFloat(a.r) || 0);
      if (key === 'name') return a.n.localeCompare(b.n, 'es');
      if (key === 'price') return (parseInt(a.p, 10) || 9999) - (parseInt(b.p, 10) || 9999);
      if (key === 'distance') return (a._dist || 99999) - (b._dist || 99999);
      return 0;
    });
  }

  function toSet(setLike) {
    if (setLike instanceof Set) return setLike;
    if (!setLike) return new Set();
    return new Set(setLike);
  }

  function splitCuisine(raw) {
    if (!raw) return [];
    return String(raw)
      .split(/[\u2022,]/)
      .map(function(t) { return t.trim(); })
      .filter(Boolean);
  }

  function defaultFavKey(r) {
    return (r && r.s) ? r.s : (r && r.n ? r.n : '');
  }

  function getFiltered(restaurants, options) {
    var opts = options || {};
    var q = (opts.query || '').toLowerCase().trim();
    var selCuisine = toSet(opts.selCuisine);
    var selDistrict = toSet(opts.selDistrict);
    var priceValue = opts.priceValue || '';
    var favsOnly = Boolean(opts.favsOnly);
    var favs = toSet(opts.favs);
    var sortKey = opts.sort || 'rating';
    var getFavKey = opts.getFavKey || defaultFavKey;

    var list = restaurants.filter(function(r) {
      if (q) {
        var haystack = (r.n + ' ' + (r.c || '') + ' ' + (r.d || '') + ' ' + (r.a || '')).toLowerCase();
        if (haystack.indexOf(q) === -1) return false;
      }

      if (selCuisine.size) {
        var tags = splitCuisine(r.c);
        if (!tags.some(function(t) { return selCuisine.has(t); })) return false;
      }

      if (selDistrict.size && !selDistrict.has(r.d)) return false;

      if (priceValue) {
        var parts = priceValue.split('-').map(Number);
        var min = parts[0];
        var max = parts[1];
        var price = parseInt(r.p, 10) || 0;
        if (!r.p || price < min || price > max) return false;
      }

      if (favsOnly && !favs.has(getFavKey(r))) return false;

      return true;
    });

    return sortList(list, sortKey);
  }

  var api = {
    esc: esc,
    haversine: haversine,
    formatDist: formatDist,
    sortList: sortList,
    getFiltered: getFiltered,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }

  root.LastEatApp = api;
})(typeof window !== 'undefined' ? window : globalThis);
