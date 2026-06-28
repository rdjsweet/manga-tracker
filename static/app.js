/* -------------------------------------------------------
   Helpers
------------------------------------------------------- */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* -------------------------------------------------------
   Toast notifications (replaces inline flashes)
------------------------------------------------------- */
function ensureToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  return container;
}

function showFlash(message, category) {
  const container = ensureToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${category}`;
  toast.setAttribute('role', 'status');
  toast.textContent = message;
  container.appendChild(toast);

  // Animate in on the next frame so the transition fires.
  requestAnimationFrame(() => toast.classList.add('toast-show'));

  setTimeout(() => {
    toast.classList.remove('toast-show');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
  }, 4000);
}

/* Convert any server-rendered flashes into toasts on load. */
document.addEventListener('DOMContentLoaded', () => {
  const inline = document.querySelector('.flashes');
  if (!inline) return;
  inline.querySelectorAll('.alert').forEach((el) => {
    const match = el.className.match(/alert-(\w+)/);
    showFlash(el.textContent.trim(), match ? match[1] : 'info');
  });
  inline.remove();
});

/* -------------------------------------------------------
   Open a chosen chapter in a new tab
------------------------------------------------------- */
function jumpToChapter(select) {
  if (select.value) {
    window.open(select.value, '_blank', 'noopener');
  }
  select.selectedIndex = 0; // reset back to the placeholder
}

/* -------------------------------------------------------
   Render a single manga card <li>
------------------------------------------------------- */
function renderMangaCard(manga) {
  const li = document.createElement('li');
  li.className = 'manga-card' + (manga.new_chapters_count > 0 ? ' updated' : '');
  li.dataset.mangaId = manga.id;

  const latestUrl = manga.chapters.length ? manga.chapters[0].url : '#';
  const options = manga.chapters
    .map((ch) => `<option value="${escapeHtml(ch.url)}">${escapeHtml(ch.chapter_title)}</option>`)
    .join('');
  const badge = manga.new_chapters_count > 0
    ? `<span class="badge-new">${manga.new_chapters_count} new</span>`
    : '';

  li.innerHTML = `
    <div class="manga-card-top">
      <strong class="manga-title">${escapeHtml(manga.title)}</strong>
      ${badge}
    </div>
    <p class="manga-latest">Latest: ${escapeHtml(manga.latest_chapter_title || 'N/A')}</p>
    <div class="manga-actions">
      <a class="btn-read" href="${escapeHtml(latestUrl)}" target="_blank" rel="noopener noreferrer">Read latest</a>
      <select class="chapter-jump" aria-label="Jump to a chapter for ${escapeHtml(manga.title)}"
        onchange="jumpToChapter(this)">
        <option value="" disabled selected>Jump to chapter…</option>
        ${options}
      </select>
    </div>
    <button type="button" class="btn-delete"
      data-manga-id="${manga.id}" data-manga-title="${escapeHtml(manga.title)}"
      onclick="confirmDelete(this.dataset.mangaId, this.dataset.mangaTitle)">Delete</button>
  `;
  return li;
}

/* -------------------------------------------------------
   Re-render the full manga list
------------------------------------------------------- */
function renderMangaList(mangaArray) {
  const ul = document.querySelector('.scroll-box-manga ul');
  ul.innerHTML = '';
  if (!mangaArray.length) {
    const li = document.createElement('li');
    li.className = 'empty-state';
    li.innerHTML = 'No manga tracked yet.<br>Paste a chapter-list URL above to start.';
    ul.appendChild(li);
    return;
  }
  mangaArray.forEach((manga) => ul.appendChild(renderMangaCard(manga)));
}

/* -------------------------------------------------------
   Re-render the activity log
------------------------------------------------------- */
function renderLogs(logs) {
  const ul = document.querySelector('.scroll-box-logs ul');
  ul.innerHTML = '';
  if (!logs.length) {
    const li = document.createElement('li');
    li.className = 'empty-state';
    li.textContent = 'No activity yet.';
    ul.appendChild(li);
    return;
  }
  logs.forEach((log) => {
    const li = document.createElement('li');
    li.innerHTML = `${escapeHtml(log.date_added)}<br><strong>${escapeHtml(log.manga_title)}</strong>${log.chapters_added > 0 ? `: ${log.chapters_added} new chapter(s) added!` : ''}`;
    ul.appendChild(li);
  });
}

/* -------------------------------------------------------
   Check for updates
------------------------------------------------------- */
const checkForm = document.querySelector('form[action*="check_updates"]');
checkForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const overlay = document.getElementById('spinner-overlay');
  const btn = checkForm.querySelector('button');
  const listBox = document.querySelector('.scroll-box-manga');

  overlay.style.display = 'flex';
  btn.disabled = true;
  listBox.classList.add('is-loading');

  try {
    const resp = await fetch('/api/check_updates', { method: 'POST' });
    if (!resp.ok) throw new Error('Server error');
    const data = await resp.json();
    renderMangaList(data.manga);
    renderLogs(data.logs);
    document.getElementById('last-checked').textContent = `Last Checked: ${data.last_checked}`;
    showFlash(`Update check complete! ${data.total_new} update(s) found.`, 'info');
  } catch (err) {
    console.error('check_updates error:', err);
    showFlash('Error checking for updates. Please try again.', 'error');
  } finally {
    overlay.style.display = 'none';
    btn.disabled = false;
    listBox.classList.remove('is-loading');
  }
});

/* -------------------------------------------------------
   Add manga
------------------------------------------------------- */
document.querySelector('.form-inline').addEventListener('submit', async (e) => {
  e.preventDefault();
  const urlInput = document.getElementById('url');
  const btn = e.target.querySelector('button');
  const originalText = btn.textContent;
  btn.textContent = 'Adding...';
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
      const ul = document.querySelector('.scroll-box-manga ul');
      const emptyState = ul.querySelector('.empty-state');
      if (emptyState) emptyState.remove();
      ul.prepend(renderMangaCard(data.manga));
      urlInput.value = '';
      showFlash('Manga added successfully!', 'success');
    }
  } catch (err) {
    console.error('api_add error:', err);
    showFlash('Error: Could not add manga. Please try again.', 'error');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

/* -------------------------------------------------------
   Delete modal (with focus management + keyboard support)
------------------------------------------------------- */
let lastFocusedTrigger = null;

function confirmDelete(mangaId, mangaTitle) {
  const modal = document.getElementById('deleteModal');
  lastFocusedTrigger = document.activeElement;

  document.getElementById('modal-text').textContent = `Are you sure you want to delete "${mangaTitle}"?`;
  modal.style.display = 'flex';

  const confirmBtn = document.getElementById('confirmDeleteBtn');
  confirmBtn.onclick = async function () {
    closeModal();
    try {
      const resp = await fetch(`/api/manga/${mangaId}`, { method: 'DELETE' });
      const data = await resp.json();
      if (data.ok) {
        const li = document.querySelector(`[data-manga-id="${mangaId}"]`);
        if (li) {
          li.style.transition = 'opacity 0.3s, max-height 0.4s';
          li.style.overflow = 'hidden';
          li.style.opacity = '0';
          li.style.maxHeight = '0';
          setTimeout(() => {
            li.remove();
            const ul = document.querySelector('.scroll-box-manga ul');
            if (ul && !ul.children.length) renderMangaList([]);
          }, 400);
        }
        showFlash('Manga deleted successfully.', 'info');
      } else {
        showFlash(data.error || 'Error deleting manga.', 'error');
      }
    } catch (err) {
      console.error('api_delete error:', err);
      showFlash('Error: Could not delete manga. Please try again.', 'error');
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

/* Backdrop click closes the modal. */
window.addEventListener('click', (event) => {
  const modal = document.getElementById('deleteModal');
  if (event.target === modal) closeModal();
});

/* Escape closes; Tab is trapped inside the dialog. */
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
