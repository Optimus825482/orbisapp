/**
 * ORBIS Admin — Vanilla SVG charts
 * Sparkline · Line · Bar
 * Theme-aware (re-renders on 'orbis:themechange' event)
 *
 * API:
 *   OrbisCharts.sparkline(el, values, { color })
 *   OrbisCharts.line(el, series, { xLabels, height })
 *   OrbisCharts.bar(el, bars, { xLabels, height })
 */
(function () {
  'use strict';

  var root = document.documentElement;

  function themeColor(name) {
    return getComputedStyle(root).getPropertyValue('--' + name).trim();
  }

  function fmt(n) {
    if (n === null || n === undefined) return '';
    var abs = Math.abs(n);
    if (abs >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (abs >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(Math.round(n));
  }

  // ─── Sparkline ───────────────────────────────────────
  function sparkline(el, values, opts) {
    if (!el || !values || !values.length) return;
    opts = opts || {};
    var w = el.clientWidth || 200;
    var h = opts.height || 36;
    var stroke = opts.color || themeColor('accent');
    var fill = themeColor('accent-soft') || stroke;

    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var range = max - min || 1;
    var stepX = w / (values.length - 1 || 1);

    var pts = values.map(function (v, i) {
      return [i * stepX, h - ((v - min) / range) * (h - 4) - 2];
    });
    var pathD = pts.map(function (p, i) {
      return (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1);
    }).join(' ');
    var areaD = pathD + ' L' + w + ',' + h + ' L0,' + h + ' Z';
    var last = pts[pts.length - 1];
    var bg = themeColor('surface');

    el.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" width="100%" height="' + h + '" aria-hidden="true">' +
        '<defs>' +
          '<linearGradient id="spark-' + el.id + '" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0%" stop-color="' + stroke + '" stop-opacity="0.30"/>' +
            '<stop offset="100%" stop-color="' + stroke + '" stop-opacity="0"/>' +
          '</linearGradient>' +
          '<linearGradient id="spark-line-' + el.id + '" x1="0" y1="0" x2="1" y2="0">' +
            '<stop offset="0%" stop-color="' + stroke + '" stop-opacity="0.75"/>' +
            '<stop offset="100%" stop-color="' + stroke + '" stop-opacity="1"/>' +
          '</linearGradient>' +
        '</defs>' +
        '<path d="' + areaD + '" fill="url(#spark-' + el.id + ')"/>' +
        '<path d="' + pathD + '" fill="none" stroke="url(#spark-line-' + el.id + ')" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
        '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="3" fill="' + stroke + '" stroke="' + bg + '" stroke-width="2"/>' +
      '</svg>';
  }

  // ─── Line chart ──────────────────────────────────────
  function line(el, series, opts) {
    if (!el) return;
    opts = opts || {};
    var w = el.clientWidth || 600;
    var h = opts.height || 240;
    var pad = { top: 16, right: 16, bottom: 28, left: 48 };
    var xLabels = opts.xLabels || [];
    var axis = themeColor('ink-faint');
    var grid = themeColor('border');
    var surface = themeColor('surface');

    var all = series.reduce(function (acc, s) { return acc.concat(s.values); }, []);
    var minY = Math.min.apply(null, all);
    var maxY = Math.max.apply(null, all);
    if (minY === maxY) { minY -= 1; maxY += 1; }
    var range = maxY - minY;

    function xPos(i) {
      return pad.left + (i / (xLabels.length - 1 || 1)) * (w - pad.left - pad.right);
    }
    function yPos(v) {
      return pad.top + (1 - (v - minY) / range) * (h - pad.top - pad.bottom);
    }

    // 4 grid lines + y labels
    var gridSvg = '';
    for (var t = 0; t < 4; t++) {
      var v = minY + range * (t / 3);
      gridSvg += '<line x1="' + pad.left + '" x2="' + (w - pad.right) + '" y1="' + yPos(v) + '" y2="' + yPos(v) + '" stroke="' + grid + '" stroke-width="1" stroke-dasharray="2 4"/>' +
        '<text x="' + (pad.left - 8) + '" y="' + (yPos(v) + 3) + '" text-anchor="end" fill="' + axis + '" font-size="11" font-family="var(--font-mono)">' + fmt(v) + '</text>';
    }

    // X labels (sparse)
    var xStep = Math.max(1, Math.floor(xLabels.length / 5));
    var xSvg = '';
    for (var i = 0; i < xLabels.length; i++) {
      if (i !== 0 && i !== xLabels.length - 1 && i % xStep !== 0) continue;
      xSvg += '<text x="' + xPos(i) + '" y="' + (h - 8) + '" text-anchor="middle" fill="' + axis + '" font-size="11" font-family="var(--font-mono)">' + xLabels[i] + '</text>';
    }

    // Series paths
    var seriesSvg = '';
    series.forEach(function (s) {
      var c = themeColor(s.color) || themeColor('accent');
      var pts = s.values.map(function (v, i) { return [xPos(i), yPos(v)]; });
      var path = pts.map(function (p, i) { return (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
      var area = path + ' L' + pts[pts.length - 1][0] + ',' + (h - pad.bottom) + ' L' + pts[0][0] + ',' + (h - pad.bottom) + ' Z';
      var last = pts[pts.length - 1];
      seriesSvg += '<path d="' + area + '" fill="' + c + '" fill-opacity="0.08"/>' +
        '<path d="' + path + '" fill="none" stroke="' + c + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
        '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="3.5" fill="' + c + '" stroke="' + surface + '" stroke-width="2"/>';
    });

    el.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="xMidYMid meet" width="100%" height="' + h + '" role="img" aria-label="' + (opts.label || 'Grafik') + '">' +
        gridSvg + seriesSvg + xSvg +
      '</svg>';
  }

  // ─── Bar chart (horizontal) ──────────────────────────
  function bar(el, bars, opts) {
    if (!el) return;
    opts = opts || {};
    var w = el.clientWidth || 600;
    var h = opts.height || 240;
    var pad = { top: 12, right: 16, bottom: 12, left: 140 };
    var axis = themeColor('ink-faint');
    var track = themeColor('surface-2');

    var maxVal = Math.max.apply(null, bars.map(function (b) { return b.value; }).concat([1]));
    var rowH = (h - pad.top - pad.bottom) / (bars.length || 1);

    var labelSvg = '';
    var barSvg = '';
    bars.forEach(function (b, i) {
      var y = pad.top + i * rowH + rowH / 2;
      labelSvg += '<text x="' + (pad.left - 8) + '" y="' + (y + 3) + '" text-anchor="end" fill="' + axis + '" font-size="12" font-family="var(--font-sans)">' + (b.label || '') + '</text>';

      var by = pad.top + i * rowH + rowH * 0.2;
      var bh = rowH * 0.6;
      var bw = (b.value / maxVal) * (w - pad.left - pad.right);
      var c = themeColor(b.color) || themeColor('accent');
      barSvg += '<rect x="' + pad.left + '" y="' + by + '" width="' + Math.max(bw, 1) + '" height="' + bh + '" fill="' + c + '" rx="3"/>' +
        '<text x="' + (pad.left + bw + 6) + '" y="' + (by + bh / 2 + 3) + '" fill="' + axis + '" font-size="12" font-family="var(--font-mono)">' + fmt(b.value) + '</text>';
    });

    el.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="xMidYMid meet" width="100%" height="' + h + '" role="img" aria-label="' + (opts.label || 'Bar grafiği') + '">' +
        labelSvg + barSvg +
      '</svg>';
  }

  // ─── Chart registry: keep last render params for themechange ───
  var registry = new WeakMap();

  function remember(el, fn, args) {
    if (!el) return;
    registry.set(el, function () { fn.apply(null, [el].concat(Array.prototype.slice.call(args))); });
  }

  // Wrap original functions to remember last call
  var _sparkline = sparkline;
  var _line = line;
  var _bar = bar;

  function _wrap(original) {
    return function (el) {
      if (!el) return;
      var args = Array.prototype.slice.call(arguments, 1);
      remember(el, original, args);
      return original.apply(null, [el].concat(args));
    };
  }
  sparkline = _wrap(_sparkline);
  line = _wrap(_line);
  bar = _wrap(_bar);

  // ─── Theme change → re-render all registered charts ───
  document.addEventListener('orbis:themechange', function () {
    // Repaint by walking all elements that have data-chart (re-render from original data)
    var els = document.querySelectorAll('[data-chart]');
    els.forEach(function (el) {
      try {
        var data = JSON.parse(el.getAttribute('data-chart'));
        if (data.type === 'sparkline') _sparkline(el, data.values, data.opts);
        else if (data.type === 'line') _line(el, data.series, data.opts);
        else if (data.type === 'bar') _bar(el, data.bars, data.opts);
      } catch (e) {}
    });
  });

  // ─── Public API ──────────────────────────────────────
  window.OrbisCharts = {
    sparkline: sparkline,
    line: line,
    lineChart: line,
    bar: bar,
    barChart: bar
  };
})();
