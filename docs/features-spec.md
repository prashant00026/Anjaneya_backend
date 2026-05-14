# Features Spec — Step 6

Companion to [`frontend-audit.md`](./frontend-audit.md), [`backend-plan.md`](./backend-plan.md), [`search-spec.md`](./search-spec.md).
Source of truth for what step 6 will (and will not) build.

## 1. Phase A — what the live frontend actually implies

I re-checked `scripts/crawl_out/bundle.txt` against each of the six
feature buckets in the step 6 brief.

| Brief feature | Frontend surface today | Already built? |
| --- | --- | --- |
| **Contact / inquiry form** | ✅ Two forms: the sticky sidebar on the project detail (`name / mobile / email / message`) and the (404-but-bundled) `/contact` page using the same shape. The home page has a `Connect with us` CTA that links to the contact page. | **Yes** — `apps/enquiries.Enquiry` (single model, nullable `project` FK, `source` distinguishes `contact_page` vs `project_sidebar`), `POST /api/v1/enquiries/`, throttle 60/hour, honeypot, IP + UA capture, admin with status workflow. Step 2. |
| **Featured / Trending** | ✅ Home "Featured Properties" row (3 hard-coded cards). **No "Trending" anywhere.** | **Featured: yes** — `Project.is_featured` + `featured_order`, `GET /api/v1/projects/featured/`. Step 2. Trending: skip — no UI. |
| **View counter** | ❌ Zero "X views" badges, no "Most viewed" sort dropdown, no view affordance anywhere. Bundle grep for `views?`, `view_count`, `Most viewed`, `eye-icon` returns 0 hits. | Skip. |
| **Similar properties** | ❌ Project detail page has Gallery / Amenities / Highlights / Developer / Location only. In-page anchors: `overview`, `amenities`, `highlights`, `developers`, `location`. No "Similar properties" / "You may also like" / "More in this locality" carousel. | Skip. |
| **Share tracking** | ⚠ One floating WhatsApp button on every page (`wa.me/917311103111?text=...`) — a single-channel deep-link with no backend involvement. No multi-channel share menu, no copy-link, no Facebook/Twitter/Email. | Skip — backend has no role in the current share flow. |
| **Recently viewed** | ❌ No carousel. Bundle has no `localStorage` calls and no UI surface. | Skip — would be frontend-driven anyway. |

The brief's other speculative inquiry-shape items (Schedule Visit,
Get Callback, Loan Assistance) also have **zero UI** today —
the sidebar form is a single free-text textarea labeled
"Any specific requirements?".

## 2. Existing inquiry pipeline (step 2 recap)

We already have a unified `Enquiry` model that handles both UI forms
via a `source` choice plus a nullable `project` FK:

```python
class Enquiry(models.Model):
    project = FK("projects.Project", null=True, on_delete=SET_NULL)
    full_name = CharField(120)
    mobile = CharField(20)
    email = EmailField(blank=True)
    message = TextField(blank=True)
    source = CharField(choices=("contact_page", "project_sidebar"))
    status = CharField(choices=("new", "contacted", "qualified", "closed"))
    ip_address = GenericIPAddressField(null=True)
    user_agent = CharField(255, blank=True)
    created_at, updated_at
```

`POST /api/v1/enquiries/` accepts both shapes (project is optional).
Throttle: 60/hour per IP. Honeypot field. Admin has status workflow,
date hierarchy, search, autocomplete on `project`.

The step 6 brief proposes splitting this into two separate models
(`ContactRequest` + `PropertyInquiry`) with a `is_read` boolean, an
`inquiry_type` choice, optional visit date/time fields, etc. Doing
that here would be a **regression**:

- We'd duplicate fields across two tables for no schema gain (the UI
  forms share the same fields).
- `is_read` is a subset of the existing `status="new"` — adding it
  would create two parallel sources of truth.
- `inquiry_type` choices like `site_visit` / `callback` /
  `price_negotiation` / `loan_assistance` have **no UI selector** —
  every row would be `general`.
- `preferred_visit_date` / `preferred_visit_time` would be NULL on
  100% of rows because there's no date picker.

## 3. Recommended scope for step 6

Three things to add. Everything else gets deferred and documented.

### 3.1 Email notification on inquiry submission (✅ implied)

Without this, admins only learn about new inquiries by manually
visiting `/admin/enquiries/enquiry/`. That's not visible in the UI
but it's the obvious admin workflow.

- Send on `Enquiry` create via a `post_save` signal.
- Template: `templates/emails/inquiry_notification.html` (rendered via
  Django templates — HTML version) + plain-text auto-stripped fallback.
- Recipients from `INQUIRY_NOTIFICATION_EMAILS` env var (CSV, empty list
  = no notifications). Defaults to empty so dev runs don't blast email.
- Subject: `New inquiry: <project title>` when `project` is set, else
  `New site enquiry from <full_name>`.
- Synchronous, `fail_silently=True` — broken SMTP doesn't break the
  API response. Celery comes in step 7 per the brief.
- Dev: `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`
  in `development.py`. Production: keep `smtp.EmailBackend` as the
  Django default; env-configured.

### 3.2 Tighter throttling on the enquiry POST (✅ implied)

Current setup: `anon=60/hour` blanket. That's correct for cheap reads
but loose for a public write endpoint (a 60/hour throttle gives spam
bots 1,440 free posts per day).

- Add a named `enquiry` scope at **10/hour per IP**.
- Apply via `throttle_classes = (EnquiryThrottle,)` on the create view
  only (so list/detail endpoints in other apps keep the looser
  anon rate).
- The brief's "contact" vs "inquiry" split makes sense only if we
  split the models. With a unified model, one scope is right.
- 429 responses already include `Retry-After` (DRF default behaviour).

### 3.3 Admin polish (✅ obvious admin need)

- "Mark as contacted" admin action (bulk). The existing `status` field
  already supports this — just expose it as a one-click action so
  admins don't have to open each row.
- "Export to CSV" admin action.
- Auto-bump `status` from `new` → `contacted` when an admin opens the
  detail view (override `change_view`). This is the brief's `is_read`
  auto-flip semantics applied to our existing status field.
- Read-only `ip_address` + `user_agent` already shown in step 2; keep.

### 3.4 Documentation

This file becomes the final contract.

## 4. Explicitly skipped — and why

These are the brief's items that have no live UI consumer. Each gets
catalogued here so the next step has a paper trail when the frontend
grows.

| Skipped | Why | When to revisit |
| --- | --- | --- |
| Split `Enquiry` into `ContactRequest` + `PropertyInquiry` | Regression vs unified model; same fields, same UI shape | Only if the two forms diverge in shape |
| `inquiry_type` choice field | No UI selector; all rows would be `general` | When the form gets a "What can we help with?" dropdown |
| `preferred_visit_date` / `_time` | No date picker UI | When a "Schedule visit" form appears |
| `view_count` + `last_viewed_at` + `POST /track-view/` | No view affordance; "Most viewed" sort not in UI | When the listings page adds a view counter or sort dropdown |
| `share_count` + `POST /track-share/` + `ShareEvent` | Single-channel WhatsApp deep-link doesn't touch the backend; no multi-channel share menu | When a multi-channel share component appears |
| `GET /properties/<id>/similar/` + scoring algorithm | No "Similar properties" / "You may also like" section on detail page | When the detail page adds a related-properties carousel |
| `GET /properties/trending/` | No "Trending in your city" UI; would need view tracking first | After view tracking is built |
| `GET /properties/by-ids/?ids=...` (recently viewed) | No "Recently viewed" UI; would be frontend-driven anyway | When a Recently Viewed component appears |
| `featured_until` auto-expiry on featured | The 3 featured projects are curated manually; admin can flip `is_featured` directly. Adding `featured_until` plus a manager method is over-engineering for 3 rows. | When marketing wants timed promotions |
| Similar-properties scoring fields (`bhk`, `listing_type`, `carpet_area_sqft`, `furnishing`) | The schema additions were deferred in step 5 (Path A). The algorithm depends on fields we don't have. | When step 5's deferred fields land |

## 5. Locked scope (Path A + recently-viewed by-ids)

User decision: Path A baseline + one B-subset item — the `by-ids`
endpoint. Everything else from §4 stays skipped.

1. **Email notification** — `apps/enquiries/notifications.py` with a
   `send_inquiry_email(enquiry)` helper. Connected via `post_save` on
   `Enquiry` in `apps/enquiries/apps.py ready()`. HTML template at
   `templates/emails/inquiry_notification.html`.
2. **Settings** — `INQUIRY_NOTIFICATION_EMAILS` from env (Csv,
   default empty). `EMAIL_BACKEND = console` in `development.py`,
   `DEFAULT_FROM_EMAIL` from env.
3. **Throttle scope** — `apps/common/throttles.py` adds
   `EnquiryThrottle(scope="enquiry")`. Apply on `EnquiryCreateView`.
   Add `"enquiry": "10/hour"` to `DEFAULT_THROTTLE_RATES` in base.
4. **Admin actions** — `mark_as_contacted`, `export_csv` actions on
   `EnquiryAdmin`; `change_view` override flips `status` from `new` to
   `contacted` on open.
5. **`GET /api/v1/projects/by-ids/?ids=12,45,7`** —
   order-preserving (`WHERE id IN (...)` doesn't preserve insertion
   order, so reorder in Python), capped at 20 IDs, uses
   `ProjectListSerializer`, cached 5 minutes per unique sorted ID
   tuple. Cache via Django's default `LocMemCache` (Redis was
   deferred in step 5).
6. **Tests** — email outbox assertion, throttle 429 after 10/hour,
   admin action smoke test, status auto-flip on detail open,
   by-ids preserves order + clamps at 20 + invalid IDs.

## 6. Final endpoint contract

| Method | Path | Auth | Throttle | Cache | Notes |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/enquiries/` | none | **10/hour per IP** (was 60/hour) | none | Honeypot, IP+UA captured server-side, triggers email notification |
| GET | `/api/v1/projects/featured/` | none | anon | n/a | Already shipped |
| **GET** | **`/api/v1/projects/by-ids/?ids=12,45,7`** | **none** | **anon** | **5 min** | **New. Returns those projects in the input order. Max 20 IDs. Unknown IDs silently dropped. Only published projects.** |
| All other read endpoints | none | anon=60/hour | n/a | n/a | Unchanged |
