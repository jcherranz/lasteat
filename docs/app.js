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

  function foldText(value) {
    var s = value == null ? '' : String(value);
    if (typeof s.normalize === 'function') {
      s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }
    return s.toLowerCase();
  }

  function boundedEditDistance(a, b, maxDist) {
    var al = a.length;
    var bl = b.length;
    if (Math.abs(al - bl) > maxDist) return maxDist + 1;

    var prev = new Array(bl + 1);
    var curr = new Array(bl + 1);
    var j;
    for (j = 0; j <= bl; j += 1) prev[j] = j;

    var i;
    for (i = 1; i <= al; i += 1) {
      curr[0] = i;
      var rowMin = curr[0];
      for (j = 1; j <= bl; j += 1) {
        var cost = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
        var val = Math.min(
          prev[j] + 1,
          curr[j - 1] + 1,
          prev[j - 1] + cost
        );
        curr[j] = val;
        if (val < rowMin) rowMin = val;
      }
      if (rowMin > maxDist) return maxDist + 1;
      var tmp = prev;
      prev = curr;
      curr = tmp;
    }
    return prev[bl];
  }

  function fuzzyMatchQuery(query, haystack) {
    var q = foldText(query).trim();
    if (!q) return true;
    var h = foldText(haystack);
    if (h.indexOf(q) !== -1) return true;
    if (q.length < 4) return false;

    var tokens = h.split(/[^a-z0-9]+/).filter(Boolean);
    var maxDist = q.length >= 7 ? 2 : 1;
    var i;
    for (i = 0; i < tokens.length; i += 1) {
      var token = tokens[i];
      if (token.length < 3) continue;
      if (Math.abs(token.length - q.length) > maxDist) continue;
      if (boundedEditDistance(q, token, maxDist) <= maxDist) return true;
    }
    return false;
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
      .split(/\u2022/)
      .map(function(t) { return t.trim(); })
      .filter(Boolean);
  }

  function defaultFavKey(r) {
    return (r && r.s) ? r.s : (r && r.n ? r.n : '');
  }

  function getFiltered(restaurants, options) {
    var opts = options || {};
    var qRaw = opts.query || '';
    var q = foldText(qRaw).trim();
    var selCuisine = toSet(opts.selCuisine);
    var selDistrict = toSet(opts.selDistrict);
    var priceValue = opts.priceValue || '';
    var favsOnly = Boolean(opts.favsOnly);
    var favs = toSet(opts.favs);
    var sortKey = opts.sort || 'rating';
    var getFavKey = opts.getFavKey || defaultFavKey;
    var useFuzzy = opts.fuzzy !== false;

    // Normalize priceValue: accept string (legacy) or array (multi-select)
    var priceRanges = [];
    if (Array.isArray(priceValue)) {
      priceRanges = priceValue;
    } else if (priceValue) {
      priceRanges = [priceValue];
    }

    var list = restaurants.filter(function(r) {
      if (q) {
        var haystack = (r.n + ' ' + (r.c || '') + ' ' + (r.d || '') + ' ' + (r.a || ''));
        var foldedHaystack = foldText(haystack);
        if (foldedHaystack.indexOf(q) === -1) {
          if (!useFuzzy || !fuzzyMatchQuery(qRaw, haystack)) return false;
        }
      }

      if (selCuisine.size) {
        var tags = splitCuisine(r.c);
        if (!tags.some(function(t) { return selCuisine.has(t); })) return false;
      }

      if (selDistrict.size && !selDistrict.has(r.d)) return false;

      if (priceRanges.length) {
        var price = parseInt(r.p, 10) || 0;
        if (!r.p) return false;
        var matched = false;
        for (var pi = 0; pi < priceRanges.length; pi++) {
          var parts = priceRanges[pi].split('-').map(Number);
          if (price >= parts[0] && price <= parts[1]) { matched = true; break; }
        }
        if (!matched) return false;
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
    fuzzyMatchQuery: fuzzyMatchQuery,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }

  root.LastEatApp = api;
})(typeof window !== 'undefined' ? window : globalThis);
