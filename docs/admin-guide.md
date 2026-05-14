# Admin Guide — Anjaneya Backend

Onboarding doc for staff who manage listings, enquiries, and content
via the Django admin. Written for non-engineers — bookmark this page.

## 1. Logging in

1. Open `/admin/` on the backend URL.
2. Use the username + password sent to you by IT. (No public signup —
   the only accounts are staff accounts created by the super admin.)
3. First time you log in, you'll land on the **dashboard** — a
   summary of total projects, featured count, today's enquiries, and
   the unread inbox.

If you forget your password, ask the super admin to reset it from
`Users → <your username> → Change password`.

## 2. The sidebar

The sidebar is grouped into four sections:

- **Listings** — `Projects`, `Cities`, `Categories`, `Developers`, `Amenities`
- **Enquiries** — `Enquiries`
- **Content** — `Site settings`, `CMS pages`, `Team`, `Testimonials`
- **System** — `Users`, `Groups`, `Failed notifications`, `Periodic tasks`, `Task results`

You can search across everything via the search bar at the top of the
sidebar.

## 3. Adding a new project

The Project page is the most important screen on this site.

1. **Sidebar → Projects → "Add project"** (top right).
2. Fill in the **Basic info** section:
   - `Title` — full project name (e.g. "Godrej Tropical Isle"). The
     `slug` (URL piece) auto-fills as you type.
   - `Tagline` — one-line card sub-headline (e.g. "Ultra-Luxury
     Apartments with Private Decks").
   - `Cover image` — the headline photo. JPEG / PNG / WEBP, between
     400×300 and 8000×8000 pixels, up to 5 MB.
3. **Classification**:
   - `Category` — Residential, Commercial, or Luxury (start typing).
   - `City` — Noida, Gurugram, etc.
   - `Locality` — free text like "Sector-140A, Noida".
   - `Developer` — optional FK; start typing the name.
   - `Status` — `New Launch` / `Under Construction` / `Ready to Move` / `Sold Out`.
   - `Property type` — free-text label that appears in the stats panel.
4. **Pricing & size**:
   - `Price starting (lacs)` — numeric, in lakhs (₹). e.g. `80` = ₹80 L, `120` = ₹1.2 Cr.
   - `Price display` — optional free-text override shown on the site (e.g. "80 Lacs onwards*").
   - `Size display` — e.g. "360 Sq.Ft. onwards".
5. **Detail content**:
   - `Description` — main paragraphs about the project. Blank lines = paragraph breaks.
   - `Amenities` — pick from the list (use the right-side panel; double-click to add).
   - `RERA number` — optional.
   - `Map embed URL` — full Google Maps `iframe src` URL.
6. **Publishing**:
   - `Is featured` + `Featured order` — controls the home-page "Featured Properties" row.
   - `Is published` — flip ON when you're ready. **Frontend only shows projects with Is published = True.**

Click **"Save"** at the top right (it stays visible as you scroll).

### Inline tabs at the bottom of the page

- **Project stats** — the 5-row stats panel on the detail page (Status / Type / Price / Size / Developer). Each row has a label, a value, and an optional icon key (string the frontend maps to an icon asset).
- **Project highlights** — bulleted list of key selling points.
- **Project images** — gallery shown on the detail page. Drag the `Display order` column to reorder. **Set one row's `Is primary` to True** to mark it as the lead image (gets used as cover on cards).
- **Floor plans** — same as images but accepts PDF too (up to 10 MB).

For bulk-uploading many images at once, click **"Bulk upload images"**
at the top of the project page and select multiple files in one shot.

## 4. Project list view tricks

- **Quick-toggle featured**: tick/untick the `Is featured` checkbox in the list directly.
- **Bulk actions** (action dropdown at top of list):
  - `Publish selected` — flips draft projects live, auto-stamping `published_at`.
  - `Unpublish selected` — pull them back to draft.
  - `Mark as featured` / `Remove from featured`.
  - `Duplicate selected (creates drafts)` — handy when you launch a similar tower / phase. Cover image is reset; everything else carries over.
- **Filter sidebar** on the right — narrow by status, city, category, etc.
- **Search bar** — searches title / slug / locality / developer name.
- **History tab** (top right of any detail page) — every change you've ever made, with the user and timestamp. Great for "who changed the price yesterday?"

## 5. Managing enquiries

1. Sidebar → `Enquiries` lands you on the inbox.
2. Each row has:
   - Caller's name + a **clickable phone link** (`tel:` + WhatsApp) — tap directly to call or message.
   - Linked project name (jumps to the project page).
   - `Source` — Contact page vs Project sidebar.
   - `Status` — New / Contacted / Qualified / Closed. Editable inline.
   - `Contacted` column — "2026-05-14 11:30 by alok" once handled.
3. **Opening an enquiry detail page auto-flips status `New → Contacted`** and stamps your username — even if you only opened it to scan. This is intentional so the inbox actually drains.
4. **Bulk action**: "Mark selected as contacted" — same auto-stamp on multiple rows at once.
5. Use the **Follow-up (admin only)** section to record:
   - `Internal notes` — anything you want — won't be shown to the customer.
   - `Last contacted at` / `Contacted by` are read-only (auto-stamped).
6. Export to CSV / XLSX via the **Export** button at the top right.

## 6. Updating homepage / site content

- **Site settings** (`Content → Site settings`) — phone, email, address, all social URLs, hero stats (`98+` / `100Cr+` and their labels), copyright year. **There's only one row**; the admin opens it directly.
- **CMS pages** — `About`, `Privacy`, `Terms`, `Disclaimer`. Body is **Markdown** — use `#` for headings, `**bold**`, blank line between paragraphs.
- **Team members** — order via `Display order`, deactivate via `Is active`.
- **Testimonials** — same pattern. Up to 3 are typically shown on home.

## 7. Bulk import / export

Every list page has **Import** + **Export** buttons in the top-right.

- **Export**: pick CSV or XLSX, optionally filter rows first via the
  list filters, hit Export.
- **Import**: CSV / XLSX with the columns shown in the import form.
  Foreign keys (city, category, developer) match on `slug` — make sure
  spreadsheets use slugs (`noida`, `commercial`, `crc-group`), not
  display names. Rows with errors are skipped and listed at the end of
  import.

Images are not imported via CSV — too messy. Upload per-project via
the inline tab or the bulk-upload button.

## 8. Common gotchas

- **Slug must be unique.** If "godrej-tropical-isle" already exists, the form will reject the new one. Add a phase number or year ("godrej-tropical-isle-phase-2").
- **Image dimensions** between 400×300 and 8000×8000. The validator rejects out-of-range files with a clear message.
- **MIME spoofing is caught**: renaming `bad.exe` to `bad.jpg` is detected by content sniffing, not just extension.
- **`Is published` must be ON** for projects to show on the public site. Featured doesn't help if unpublished.
- **`Published at` auto-fills** the first time you publish — don't worry about it.
- **History tab** is read-only. Reverting requires manual edit; use the diff as a reference.

## 9. Who to ask

- Password resets / new staff accounts → super admin.
- "Why didn't my email send?" → check `System → Failed notifications`. There's a Retry button.
- Worker / Redis problems → see [docs/notifications-spec.md §6](./notifications-spec.md).
- API contract questions for the frontend team → [docs/search-spec.md](./search-spec.md), [docs/features-spec.md](./features-spec.md).
