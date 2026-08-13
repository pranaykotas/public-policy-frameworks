/**
 * Ask Our Views — calls the /ask backend and renders author-grouped excerpts.
 * Loaded by ask.qmd via <script src="scripts/ask.js">.
 * Expects these DOM ids: ask-input, ask-btn, ask-results
 */
(function () {
  var API_BASE = 'https://ask-our-views-api.onrender.com';

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

  function renderGroup(group) {
    var html = '<div class="ask-group">';
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
    return html;
  }

  function render(data) {
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
    container.innerHTML = data.groups.map(renderGroup).join('');
  }

  function doAsk() {
    var inputEl = document.getElementById('ask-input');
    var container = document.getElementById('ask-results');
    if (!inputEl || !container) return;

    var question = inputEl.value.trim();
    if (!question) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = '<p class="finder-no-results">Searching five years of newsletter archives…</p>';

    fetch(API_BASE + '/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question }),
    })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {
        container.innerHTML = '<p class="finder-error">This is taking longer than usual — try again in a moment.</p>';
      });
  }

  function init() {
    var btn = document.getElementById('ask-btn');
    var input = document.getElementById('ask-input');
    if (!btn || !input) return;
    btn.addEventListener('click', doAsk);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') doAsk(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
