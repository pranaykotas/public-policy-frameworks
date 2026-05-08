/**
 * Framework Finder — shared search logic used on both the homepage and find-framework page.
 * Loaded by index.qmd and find-framework.qmd via <script src="scripts/finder.js">.
 * Expects frameworks.json at the site root and these DOM ids:
 *   finder-input, finder-btn, finder-results
 */
(function () {
  let frameworks = [];
  let loaded = false;

  // Resolve the base path so this script works from any page depth
  const base = document.querySelector('base') ? document.querySelector('base').href : '/';

  fetch(base + 'frameworks.json')
    .then(r => r.json())
    .then(data => {
      frameworks = data;
      loaded = true;
    })
    .catch(() => {
      const el = document.getElementById('finder-results');
      if (el) el.innerHTML = '<p class="finder-error">Failed to load framework index. Please refresh.</p>';
    });

  function tokenise(text) {
    const STOP = new Set(['the','and','for','are','but','not','you','all','can','had','her','was',
      'one','our','out','day','get','has','him','his','how','man','new','now','old','see','two',
      'way','who','boy','did','its','let','put','say','she','too','use']);
    return text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 2 && !STOP.has(w));
  }

  function score(fw, queryTokens) {
    let s = 0;
    const titleTokens   = tokenise(fw.title);
    const summaryTokens = tokenise(fw.summary);
    const tagTokens     = (fw.tags || []).map(t => t.toLowerCase());
    const useCaseTokens = (fw.use_cases || []).flatMap(u => tokenise(u));
    const keywordTokens = (fw.keywords || []).map(k => k.toLowerCase());

    for (const q of queryTokens) {
      if (tagTokens.includes(q))     s += 10;
      if (titleTokens.includes(q))   s += 8;
      if (useCaseTokens.includes(q)) s += 6;
      if (summaryTokens.includes(q)) s += 4;
      if (keywordTokens.includes(q)) s += 3;
      for (const t of tagTokens)     if (t.includes(q) || q.includes(t)) s += 3;
      for (const t of titleTokens)   if (t.includes(q) || q.includes(t)) s += 2;
      for (const t of useCaseTokens) if (t.includes(q) || q.includes(t)) s += 2;
    }
    return s;
  }

  function explain(fw, queryTokens) {
    let best = null, bestScore = 0;
    for (const uc of (fw.use_cases || [])) {
      const ucTokens = tokenise(uc);
      let s = 0;
      for (const q of queryTokens) {
        if (ucTokens.includes(q)) s += 2;
        for (const t of ucTokens) if (t.includes(q) || q.includes(t)) s += 1;
      }
      if (s > bestScore) { bestScore = s; best = uc; }
    }
    if (best) return best;
    const matchedTags = (fw.tags || []).filter(t =>
      queryTokens.some(q => t.toLowerCase().includes(q) || q.includes(t.toLowerCase()))
    );
    if (matchedTags.length) return 'Relevant tags: ' + matchedTags.join(', ');
    return fw.summary.substring(0, 120) + '...';
  }

  function categoryLabel(cat) {
    return cat.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function render(results) {
    const container = document.getElementById('finder-results');
    if (!container) return;
    if (!results.length) {
      container.innerHTML = '<p class="finder-no-results">No frameworks matched. Try broader terms like "policy failure", "trade", or "institutions".</p>';
      return;
    }
    let html = '<p class="finder-count">Top ' + results.length + ' recommendation' + (results.length > 1 ? 's' : '') + ':</p>';
    html += '<div class="finder-result-list">';
    for (const r of results) {
      html += `
        <a href="${r.url}" class="finder-result-card">
          <div class="finder-result-category">${categoryLabel(r.category)}</div>
          <h3 class="finder-result-title">${r.title}</h3>
          <p class="finder-result-explain">${r._explain}</p>
        </a>`;
    }
    html += '</div>';
    container.innerHTML = html;
  }

  function doSearch() {
    const inputEl = document.getElementById('finder-input');
    if (!inputEl) return;
    if (!loaded) {
      const el = document.getElementById('finder-results');
      if (el) el.innerHTML = '<p class="finder-no-results">Loading framework index…</p>';
      return;
    }
    const raw = inputEl.value.trim();
    if (!raw) { document.getElementById('finder-results').innerHTML = ''; return; }
    const tokens = tokenise(raw);
    if (!tokens.length) {
      document.getElementById('finder-results').innerHTML = '<p class="finder-no-results">Please enter a more specific query.</p>';
      return;
    }
    const scored = frameworks.map(fw => ({ ...fw, _score: score(fw, tokens), _explain: explain(fw, tokens) }));
    scored.sort((a, b) => b._score - a._score);
    render(scored.filter(x => x._score > 0).slice(0, 5));
  }

  function init() {
    const btn   = document.getElementById('finder-btn');
    const input = document.getElementById('finder-input');
    if (!btn || !input) return;
    btn.addEventListener('click', doSearch);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

    // Example chips
    document.querySelectorAll('.example-chip').forEach(chip => {
      chip.addEventListener('click', () => {
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
