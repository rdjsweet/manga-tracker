# AJAX & UX Improvements — Design Spec

**Date:** 2026-06-28
**Project:** manga-tracker

---

## Overview

Replace full-page-refresh form submits with AJAX calls for Check Updates, Add Manga, and Delete Manga. Sort updated manga to the top of the list. Fix several UI/UX issues and make the backend DRY.

---

## Section 1: API Layer (Backend)

### New JSON Endpoints

Three new endpoints added to `views/manga.py`:

| Method | Route | Returns |
|--------|-------|---------|
| `POST` | `/api/check_updates` | `{ total_new: N, manga: [...], logs: [...], last_checked: "..." }` |
| `POST` | `/api/add` | `{ manga: {...} }` or `{ error: "..." }` |
| `DELETE` | `/api/manga/<id>` | `{ ok: true }` or `{ error: "..." }` |

The `manga` array in `/api/check_updates` and `/api/add` responses includes all fields the template needs: `id`, `title`, `latest_chapter_title`, `chapters` (list of `{chapter_title, url}`), `new_chapters_count`.

The `manga` array is sorted: updated items (`new_chapters_count > 0`) first, then alphabetically by title.

Existing form-based routes (`/check_updates`, `/add`, `/delete/<id>`) are kept for graceful degradation.

### `db_cursor()` Context Manager

Add to `utils/db.py`:

```python
from contextlib import contextmanager

@contextmanager
def db_cursor():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
```

All routes — old and new, including `load_user` in `app.py` and `views/auth.py` — move to `with db_cursor() as cursor:`.

### Scraper Bug Fix

`scraper.py` error branches return 5 values; callers unpack 4. Normalise all return paths to 4 values: `(title, chapter_titles, chapter_urls, chapter_count)`. Update the `__main__` block to match.

### N+1 Query Fix

The `index` route (and the `/api/check_updates` response builder) currently runs one `SELECT` per manga to fetch chapters. Replace with a single query joining manga and chapters, then group chapters by manga ID in Python.

### Dead Code Removal

Remove the `select_chapter` route in `views/manga.py` — it references a non-existent `chapter_dropdown.html` template and is not called anywhere.

---

## Section 2: AJAX & Frontend JS

### Extract `static/app.js`

Move the inline `<script>` block from `index.html` into `static/app.js`. Link it with `<script src="{{ url_for('static', filename='app.js') }}" defer></script>`.

### Check Updates

1. Intercept the form submit.
2. Disable the button, show a full-page semi-transparent spinner overlay with "Checking for updates..." text.
3. `POST /api/check_updates`.
4. On success: re-render the manga list in place (sorted updated-first), update the "Last Checked" text, refresh the activity log, remove the spinner, show an inline flash message.
5. On error: remove spinner, show error flash.

### Add Manga

1. Intercept the form submit.
2. Show a loading state on the Add button ("Adding...").
3. `POST /api/add` with `{ url }` as JSON.
4. On success: prepend the new manga card to the list, clear the URL input, show success flash.
5. On error: restore button, show error flash.

### Delete Manga

1. Confirm modal "yes" button fires `DELETE /api/manga/<id>` instead of `window.location.href`.
2. On success: animate the card out (fade + collapse), remove from DOM, close modal.
3. On error: close modal, show error flash.

### Inline Flash Messages

Since AJAX removes redirects, Flask's session-based flash system is bypassed. Add a `showFlash(message, category)` JS function that injects `.alert.alert-<category>` markup into `.flashes` (already styled in `styles.css`) and auto-dismisses after 4 seconds.

---

## Section 3: Sorting

**Initial page load (`index` route):** sorted alphabetically by title — there is no stored "has updates" flag in the DB, so updated-first is not meaningful here.

**After `POST /api/check_updates`:** the server sorts the returned manga list in Python after computing `new_chapters_count`: updated items first, then alphabetically. The JS replaces the list with this pre-sorted result.

**JS (client):** the re-render function always uses the server-returned order, so no client-side sort logic is needed.

---

## Section 4: UX Fixes

| Issue | Fix |
|-------|-----|
| Chapter dropdown too narrow (`width: 10vw`) | Change to `width: auto; min-width: 8rem; max-width: 100%` |
| "Read on MangaPill" initialises as `href="#"` | Write the first chapter URL directly into `href` in the Jinja template, removing the DOMContentLoaded initialisation loop |
| `<footer>` and `<script>` tags are outside `</body>` | Move footer and scripts inside `<body>` before `</body>` |
| Delete modal cancel button inherits red colour | Add explicit `background-color: #888` rule for the cancel button |

---

## Section 5: Code Quality / DRY

- `to_est` timezone helper moved from `views/manga.py` to `utils/formatting.py` and imported where needed.
- `load_user` in `app.py` updated to use `db_cursor()`.
- `views/auth.py` updated to use `db_cursor()`.
- All `views/manga.py` routes updated to use `db_cursor()`.

---

## Out of Scope

- "Mark as read" chapter tracking
- Per-manga individual update checks
- Authentication changes
- Halloween page changes
