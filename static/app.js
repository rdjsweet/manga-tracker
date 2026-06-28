/* =======================================================
   Helpers
======================================================= */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* Deterministic gradient for cover placeholders, derived from the title. */
function hashHue(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 360;
  return h;
}

function colouriseCover(cover) {
  const h = hashHue(cover.dataset.title || '');
  cover.style.background =
    `linear-gradient(135deg, hsl(${h} 62% 55%), hsl(${(h + 40) % 360} 58% 45%))`;
}

function colouriseAll() {
  document.querySelectorAll('.cover').forEach(colouriseCover);
}

/* =======================================================
   Theme toggle
======================================================= */
(function initTheme() {
  const root = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;
  const sync = () => {
    toggle.textContent = root.getAttribute('data-theme') === 'dark' ? '🌙' : '☀️';
  };
  sync();
  toggle.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    sync();
  });
})();

/* =======================================================
   Toast notifications (top-centre)
======================================================= */
function ensureToastContainer() {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    document.body.appendChild(c);
  }
  return c;
}

function showFlash(message, category) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${category}`;
  toast.setAttribute('role', 'status');
  toast.textContent = message;
  ensureToastContainer().appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('toast-show'));
  setTimeout(() => {
    toast.classList.remove('toast-show');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
  }, 4000);
}

/* =======================================================
   Card rendering
======================================================= */
function renderMangaCard(manga) {
  const id = Number(manga.id);
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.mangaId = id;

  const badge = manga.unread_count > 0
    ? `<span class="badge">${manga.unread_count} new</span>` : '';
  const coverImg = manga.has_cover
    ? `<img src="/api/manga/${id}/cover" alt="${escapeHtml(manga.title)} cover" loading="lazy" onerror="this.remove()">`
    : '';

  const progress = manga.continue_url
    ? `<span class="unread">● ${manga.unread_count} unread</span>`
    : `Caught up · ${escapeHtml(manga.latest_chapter_title || 'N/A')}`;

  const action = manga.continue_url
    ? `<button class="btn-continue" type="button" data-url="${escapeHtml(manga.continue_url)}"
         title="Next: ${escapeHtml(manga.continue_title || '')}" onclick="continueReading(this)">Continue ▸</button>`
    : `<span class="btn-continue caught-up">Caught up</span>`;

  const options = manga.chapters
    .map((ch) => `<option value="${escapeHtml(ch.url)}">${escapeHtml(ch.chapter_title)}</option>`)
    .join('');

  card.innerHTML = `
    <div class="cover" data-title="${escapeHtml(manga.title)}">
      <span class="cover-fallback">${escapeHtml(manga.title)}</span>
      ${coverImg}
      ${badge}
      <button class="delete-x" type="button" aria-label="Remove ${escapeHtml(manga.title)}"
        data-manga-id="${id}" data-manga-title="${escapeHtml(manga.title)}"
        onclick="confirmDelete(this.dataset.mangaId, this.dataset.mangaTitle)">✕</button>
    </div>
    <div class="card-body">
      <p class="card-title">${escapeHtml(manga.title)}</p>
      <p class="progress">${progress}</p>
      <div class="card-actions">
        ${action}
        <select class="menu" aria-label="Jump to a chapter of ${escapeHtml(manga.title)}"
          onchange="jumpToChapter(this)">
          <option value="" disabled selected>⋯</option>
          ${options}
        </select>
      </div>
    </div>`;

  colouriseCover(card.querySelector('.cover'));
  return card;
}

function setLibraryCount() {
  const n = document.querySelectorAll('#grid .card').length;
  document.getElementById('library-count').textContent = `${n} series`;
}

function renderGrid(mangaArray) {
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  if (!mangaArray.length) {
    grid.innerHTML =
      '<div class="empty-state">No manga tracked yet.<br>Paste a chapter-list URL above to start.</div>';
    setLibraryCount();
    return;
  }
  mangaArray.forEach((m) => grid.appendChild(renderMangaCard(m)));
  setLibraryCount();
}

function renderActivity(logs) {
  const ul = document.getElementById('activity');
  ul.innerHTML = '';
  if (!logs.length) {
    ul.innerHTML = '<li class="empty-state">No activity yet.</li>';
    return;
  }
  logs.forEach((log) => {
    const li = document.createElement('li');
    li.innerHTML =
      `<span class="activity-date">${escapeHtml(log.date_added)}</span><strong>${escapeHtml(log.manga_title)}</strong>` +
      (log.chapters_added > 0 ? ` · ${log.chapters_added} new chapter(s)` : '');
    ul.appendChild(li);
  });
}

function replaceCard(manga) {
  const existing = document.querySelector(`.card[data-manga-id="${manga.id}"]`);
  if (existing) existing.replaceWith(renderMangaCard(manga));
}

/* =======================================================
   Reading + progress
======================================================= */
async function markRead(mangaId, chapterUrl) {
  try {
    const resp = await fetch(`/api/manga/${mangaId}/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: chapterUrl }),
    });
    if (!resp.ok) {
      console.warn('mark_read failed:', resp.status);
      return;
    }
    const data = await resp.json();
    if (data.manga) replaceCard(data.manga);
  } catch (err) {
    console.error('mark_read error:', err);
  }
}

function continueReading(btn) {
  const url = btn.dataset.url;
  if (url) window.open(url, '_blank', 'noopener');
  const card = btn.closest('.card');
  if (card) markRead(card.dataset.mangaId, url);
}

/* The chapter menu is pure navigation: it opens any chapter without touching
   read progress, so jumping back to re-read an old chapter never rewinds your
   position and re-flags newer chapters as unread. "Continue" is what advances
   progress. */
function jumpToChapter(select) {
  const url = select.value;
  if (url) window.open(url, '_blank', 'noopener');
  select.selectedIndex = 0;
}

/* =======================================================
   Summary banner
======================================================= */
function showSummary(totalNew, seriesCount) {
  const banner = document.getElementById('summary-banner');
  const text = document.getElementById('summary-text');
  if (totalNew > 0) {
    text.innerHTML =
      `<strong>${totalNew} new chapter${totalNew !== 1 ? 's' : ''}</strong> across ${seriesCount} series since your last check.`;
  } else {
    text.textContent = 'No new chapters found.';
  }
  banner.hidden = false;
}

document.getElementById('summary-close').addEventListener('click', () => {
  document.getElementById('summary-banner').hidden = true;
});

/* =======================================================
   Check for updates
======================================================= */
const checkForm = document.querySelector('form[action*="check_updates"]');
checkForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const overlay = document.getElementById('spinner-overlay');
  const btn = checkForm.querySelector('button');
  overlay.style.display = 'flex';
  btn.disabled = true;

  try {
    const resp = await fetch('/api/check_updates', { method: 'POST' });
    if (!resp.ok) throw new Error('Server error');
    const data = await resp.json();
    renderGrid(data.manga);
    renderActivity(data.logs);
    document.getElementById('last-checked').textContent = `Last checked: ${data.last_checked}`;
    showSummary(data.total_new, data.new_series_count);
  } catch (err) {
    console.error('check_updates error:', err);
    showFlash('Error checking for updates. Please try again.', 'error');
  } finally {
    overlay.style.display = 'none';
    btn.disabled = false;
  }
});

/* =======================================================
   Add series
======================================================= */
document.querySelector('.add-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const urlInput = document.getElementById('url');
  const btn = e.target.querySelector('button');
  const originalText = btn.textContent;
  btn.textContent = 'Adding…';
  btn.disabled = true;

  try {
    const resp = await fetch('/api/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlInput.value.trim() }),
    });
    const data = await resp.json();
    if (data.error) {
      showFlash(data.error, 'error');
    } else {
      const grid = document.getElementById('grid');
      const empty = grid.querySelector('.empty-state');
      if (empty) empty.remove();
      grid.prepend(renderMangaCard(data.manga));
      setLibraryCount();
      urlInput.value = '';
      showFlash('Series added.', 'success');
    }
  } catch (err) {
    console.error('api_add error:', err);
    showFlash('Could not add the series. Please try again.', 'error');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

/* =======================================================
   Delete modal (focus-managed + keyboard accessible)
======================================================= */
let lastFocusedTrigger = null;

function confirmDelete(mangaId, mangaTitle) {
  const modal = document.getElementById('deleteModal');
  lastFocusedTrigger = document.activeElement;
  document.getElementById('modal-text').textContent =
    `Are you sure you want to remove "${mangaTitle}"?`;
  modal.style.display = 'flex';

  const confirmBtn = document.getElementById('confirmDeleteBtn');
  confirmBtn.onclick = async function () {
    closeModal();
    try {
      const resp = await fetch(`/api/manga/${mangaId}`, { method: 'DELETE' });
      const data = await resp.json();
      if (data.ok) {
        const card = document.querySelector(`.card[data-manga-id="${mangaId}"]`);
        if (card) {
          card.style.transition = 'opacity .3s, transform .3s';
          card.style.opacity = '0';
          card.style.transform = 'scale(.95)';
          setTimeout(() => {
            card.remove();
            const grid = document.getElementById('grid');
            if (!grid.querySelector('.card')) renderGrid([]);
            else setLibraryCount();
          }, 300);
        }
        showFlash('Series removed.', 'info');
      } else {
        showFlash(data.error || 'Error removing series.', 'error');
      }
    } catch (err) {
      console.error('api_delete error:', err);
      showFlash('Could not remove the series. Please try again.', 'error');
    }
  };

  confirmBtn.focus();
}

function closeModal() {
  document.getElementById('deleteModal').style.display = 'none';
  if (lastFocusedTrigger && typeof lastFocusedTrigger.focus === 'function') {
    lastFocusedTrigger.focus();
  }
  lastFocusedTrigger = null;
}

window.addEventListener('click', (event) => {
  const modal = document.getElementById('deleteModal');
  if (event.target === modal) closeModal();
});

document.addEventListener('keydown', (e) => {
  const modal = document.getElementById('deleteModal');
  if (modal.style.display !== 'flex') return;
  if (e.key === 'Escape') {
    closeModal();
    return;
  }
  if (e.key === 'Tab') {
    const focusables = modal.querySelectorAll('button, [tabindex="0"]');
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
});

/* =======================================================
   On load: colourise covers, convert server flashes to toasts
======================================================= */
document.addEventListener('DOMContentLoaded', () => {
  colouriseAll();
  const inline = document.querySelector('.flashes');
  if (inline) {
    inline.querySelectorAll('.alert').forEach((el) => {
      const m = el.className.match(/alert-(\w+)/);
      showFlash(el.textContent.trim(), m ? m[1] : 'info');
    });
    inline.remove();
  }
});
