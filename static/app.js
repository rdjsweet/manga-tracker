/* -------------------------------------------------------
   Inline flash messages
------------------------------------------------------- */
function showFlash(message, category) {
  let container = document.querySelector('.flashes');
  if (!container) {
    container = document.createElement('div');
    container.className = 'flashes';
    document.querySelector('.content').appendChild(container);
  }
  const alert = document.createElement('div');
  alert.className = `alert alert-${category} flash-message`;
  alert.textContent = message;
  container.appendChild(alert);
  setTimeout(() => alert.remove(), 4000);
}

/* -------------------------------------------------------
   Chapter link sync
------------------------------------------------------- */
function updateChapterLink(mangaId) {
  const select = document.getElementById(`chapter_select_${mangaId}`);
  const link = document.getElementById(`read_link_${mangaId}`);
  if (select && link) link.href = select.value;
}

/* -------------------------------------------------------
   Render a single manga card <li>
------------------------------------------------------- */
function renderMangaCard(manga) {
  const li = document.createElement('li');
  li.dataset.mangaId = manga.id;
  if (manga.new_chapters_count > 0) li.classList.add('updated-chapters');

  const firstUrl = manga.chapters.length > 0 ? manga.chapters[0].url : '#';
  const chapterOptions = manga.chapters
    .map((ch, i) => `<option value="${ch.url}"${i === 0 ? ' selected' : ''}>${ch.chapter_title}</option>`)
    .join('');

  const newBadge = manga.new_chapters_count > 0
    ? `<span class="new-chapters"># ${manga.new_chapters_count} new chapter(s)!</span><br>`
    : '';

  li.innerHTML = `
    <strong>${manga.title}</strong><br>
    Latest Chapter: ${manga.latest_chapter_title || 'N/A'}<br>
    <label for="chapter_select_${manga.id}">Read Chapter:</label>
    <select id="chapter_select_${manga.id}" name="chapter"
      onchange="updateChapterLink(${manga.id})">
      ${chapterOptions}
    </select><br>
    ${newBadge}
    <div class="manga-links">
      <a id="read_link_${manga.id}" href="${firstUrl}" target="_blank">Read on MangaPill</a>
      <a href="#" data-manga-id="${manga.id}" data-manga-title="${manga.title}"
         onclick="confirmDelete(this.dataset.mangaId, this.dataset.mangaTitle)">Delete</a>
    </div>
  `;
  return li;
}

/* -------------------------------------------------------
   Re-render the full manga list
------------------------------------------------------- */
function renderMangaList(mangaArray) {
  const ul = document.querySelector('.scroll-box-manga ul');
  ul.innerHTML = '';
  mangaArray.forEach(manga => ul.appendChild(renderMangaCard(manga)));
}

/* -------------------------------------------------------
   Re-render the activity log
------------------------------------------------------- */
function renderLogs(logs) {
  const ul = document.querySelector('.scroll-box-logs ul');
  ul.innerHTML = '';
  logs.forEach(log => {
    const li = document.createElement('li');
    li.innerHTML = `${log.date_added}<br><strong>${log.manga_title}</strong>${log.chapters_added > 0 ? `: ${log.chapters_added} new chapter(s) added!` : ''}`;
    ul.appendChild(li);
  });
}

/* -------------------------------------------------------
   Check for updates
------------------------------------------------------- */
document.querySelector('form[action*="check_updates"]').addEventListener('submit', async (e) => {
  e.preventDefault();
  const overlay = document.getElementById('spinner-overlay');
  overlay.style.display = 'flex';

  try {
    const resp = await fetch('/api/check_updates', { method: 'POST' });
    if (!resp.ok) throw new Error('Server error');
    const data = await resp.json();
    renderMangaList(data.manga);
    renderLogs(data.logs);
    document.getElementById('last-checked').textContent = `Last Checked: ${data.last_checked}`;
    showFlash(`Update check complete! ${data.total_new} update(s) found.`, 'info');
  } catch {
    showFlash('Error checking for updates. Please try again.', 'error');
  } finally {
    overlay.style.display = 'none';
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
      document.querySelector('.scroll-box-manga ul').prepend(renderMangaCard(data.manga));
      urlInput.value = '';
      showFlash('Manga added successfully!', 'success');
    }
  } catch {
    showFlash('Error: Could not add manga. Please try again.', 'error');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

/* -------------------------------------------------------
   Delete modal
------------------------------------------------------- */
function confirmDelete(mangaId, mangaTitle) {
  document.getElementById('deleteModal').style.display = 'block';
  document.getElementById('modal-text').innerText = `Are you sure you want to delete "${mangaTitle}"?`;

  document.getElementById('confirmDeleteBtn').onclick = async function () {
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
          setTimeout(() => li.remove(), 400);
        }
        showFlash('Manga deleted successfully.', 'info');
      } else {
        showFlash(data.error || 'Error deleting manga.', 'error');
      }
    } catch {
      showFlash('Error: Could not delete manga. Please try again.', 'error');
    }
  };
}

function closeModal() {
  document.getElementById('deleteModal').style.display = 'none';
}

window.onclick = function (event) {
  const modal = document.getElementById('deleteModal');
  if (event.target === modal) closeModal();
};
