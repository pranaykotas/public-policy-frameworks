/**
 * Unified Framework Finder + Ask Our Views
 * Single input triggers both: instant framework search (client-side)
 * and newsletter excerpt lookup (API call).
 */
(function () {
  var API_BASE = 'https://ask-our-views-api.onrender.com';
  var frameworks = [];
  var loaded = false;

  var base = document.querySelector('base') ? document.querySelector('base').href : '/';

  fetch(base + 'frameworks.json')
    .then(function (r) { return r.json(); })
    .then(function (data) { frameworks = data; loaded = true; })
    .catch(function () {});

  // ── Framework search (client-side) ──

  var STOP = new Set(['the','and','for','are','but','not','you','all','can','had','her','was',
    'one','our','out','day','get','has','him','his','how','man','new','now','old','see','two',
    'way','who','boy','did','its','let','put','say','she','too','use']);

  function tokenise(text) {
    return text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(function (w) { return w.length > 2 && !STOP.has(w); });
  }

  function score(fw, queryTokens) {
    var s = 0;
    var titleTokens   = tokenise(fw.title);
    var summaryTokens = tokenise(fw.summary);
    var tagTokens     = (fw.tags || []).map(function (t) { return t.toLowerCase(); });
    var useCaseTokens = (fw.use_cases || []).flatMap(function (u) { return tokenise(u); });
    var keywordTokens = (fw.keywords || []).map(function (k) { return k.toLowerCase(); });

    for (var qi = 0; qi < queryTokens.length; qi++) {
      var q = queryTokens[qi];
      if (tagTokens.includes(q))     s += 10;
      if (titleTokens.includes(q))   s += 8;
      if (useCaseTokens.includes(q)) s += 6;
      if (summaryTokens.includes(q)) s += 4;
      if (keywordTokens.includes(q)) s += 3;
      for (var i = 0; i < tagTokens.length; i++)     if (tagTokens[i].includes(q) || q.includes(tagTokens[i])) s += 3;
      for (var j = 0; j < titleTokens.length; j++)   if (titleTokens[j].includes(q) || q.includes(titleTokens[j])) s += 2;
      for (var k = 0; k < useCaseTokens.length; k++) if (useCaseTokens[k].includes(q) || q.includes(useCaseTokens[k])) s += 2;
    }
    return s;
  }

  function explain(fw, queryTokens) {
    var best = null, bestScore = 0;
    var useCases = fw.use_cases || [];
    for (var i = 0; i < useCases.length; i++) {
      var ucTokens = tokenise(useCases[i]);
      var s = 0;
      for (var qi = 0; qi < queryTokens.length; qi++) {
        var q = queryTokens[qi];
        if (ucTokens.includes(q)) s += 2;
        for (var j = 0; j < ucTokens.length; j++) if (ucTokens[j].includes(q) || q.includes(ucTokens[j])) s += 1;
      }
      if (s > bestScore) { bestScore = s; best = useCases[i]; }
    }
    if (best) return best;
    var matchedTags = (fw.tags || []).filter(function (t) {
      return queryTokens.some(function (q) { return t.toLowerCase().includes(q) || q.includes(t.toLowerCase()); });
    });
    if (matchedTags.length) return 'Relevant tags: ' + matchedTags.join(', ');
    return fw.summary.substring(0, 120) + '...';
  }

  function categoryLabel(cat) {
    return cat.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function renderFrameworks(results) {
    var container = document.getElementById('finder-results');
    if (!container) return;
    if (!results.length) {
      container.innerHTML = '<p class="finder-no-results">No frameworks matched this query.</p>';
      return;
    }
    var html = '<p class="finder-count">' + results.length + ' framework' + (results.length > 1 ? 's' : '') + ' found:</p>';
    html += '<div class="finder-result-list">';
    for (var i = 0; i < results.length; i++) {
      var r = results[i];
      html += '<a href="' + r.url + '" class="finder-result-card">'
        + '<div class="finder-result-category">' + categoryLabel(r.category) + '</div>'
        + '<h3 class="finder-result-title">' + r.title + '</h3>'
        + '<p class="finder-result-explain">' + r._explain + '</p>'
        + '</a>';
    }
    html += '</div>';
    container.innerHTML = html;
  }

  function doFrameworkSearch(query) {
    if (!loaded) return;
    var tokens = tokenise(query);
    if (!tokens.length) return;
    var scored = frameworks.map(function (fw) {
      return Object.assign({}, fw, { _score: score(fw, tokens), _explain: explain(fw, tokens) });
    });
    scored.sort(function (a, b) { return b._score - a._score; });
    renderFrameworks(scored.filter(function (x) { return x._score > 0; }).slice(0, 5));
  }

  // ── Ask Our Views (API call) ──

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function truncate(text, maxLen) {
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen).replace(/\s+\S*$/, '') + '…';
  }

  function renderAskResults(data) {
    var container = document.getElementById('ask-results');
    if (!container) return;

    if (data.error) {
      container.innerHTML = '<p class="finder-error">' + escapeHtml(data.message) + '</p>';
      return;
    }
    if (!data.groups || data.groups.length === 0) {
      container.innerHTML = '<p class="finder-no-results">' + escapeHtml(data.message || "We haven't written directly about this yet.") + '</p>';
      return;
    }

    var html = '';
    for (var g = 0; g < data.groups.length; g++) {
      var group = data.groups[g];
      html += '<div class="ask-group">';
      html += '<div class="ask-group-author">' + escapeHtml(group.author) + '</div>';
      if (group.connector_text) {
        html += '<p class="ask-connector">' + escapeHtml(group.connector_text) + '</p>';
      }
      html += '<div class="ask-excerpt-list">';
      for (var i = 0; i < group.excerpts.length; i++) {
        var ex = group.excerpts[i];
        html += '<a href="' + escapeHtml(ex.url) + '" class="ask-excerpt" target="_blank" rel="noopener">';
        html += '<p class="ask-excerpt-text">' + escapeHtml(truncate(ex.text, 400)) + '</p>';
        html += '<div class="ask-excerpt-source">' + escapeHtml(ex.post_title) + ' · ' + escapeHtml(formatDate(ex.date)) + '</div>';
        html += '</a>';
      }
      html += '</div></div>';
    }
    container.innerHTML = html;
  }

  function doAskSearch(question) {
    var container = document.getElementById('ask-results');
    if (!container) return;

    var sectionHeader = document.getElementById('ask-section-header');
    if (sectionHeader) sectionHeader.classList.add('ask-visible');

    container.innerHTML = '<p class="ask-loading">Searching five years of newsletter archives…</p>';

    fetch(API_BASE + '/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question }),
    })
      .then(function (r) { return r.json(); })
      .then(renderAskResults)
      .catch(function () {
        container.innerHTML = '<p class="finder-error">Could not reach the archive search — try again in a moment.</p>';
      });
  }

  // ── Unified search ──

  function doSearch() {
    var inputEl = document.getElementById('finder-input');
    if (!inputEl) return;

    var query = inputEl.value.trim();
    if (!query) {
      var fr = document.getElementById('finder-results');
      var ar = document.getElementById('ask-results');
      var sh = document.getElementById('ask-section-header');
      if (fr) fr.innerHTML = '';
      if (ar) ar.innerHTML = '';
      if (sh) sh.classList.remove('ask-visible');
      return;
    }

    doFrameworkSearch(query);
    doAskSearch(query);
  }

  function init() {
    var btn   = document.getElementById('finder-btn');
    var input = document.getElementById('finder-input');
    if (!btn || !input) return;
    btn.addEventListener('click', doSearch);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') doSearch(); });

    document.querySelectorAll('.example-chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        input.value = chip.dataset.query;
        doSearch();
        input.focus();
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
