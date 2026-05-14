# Backend Plan — Anjaneya Real Estate

**Status:** Phase B (proposal). **No code will be written until this is approved.**
Companion to [`frontend-audit.md`](./frontend-audit.md).

## 1. Guiding principles

- **Model only what the live frontend renders today** (plus the obvious
  data behind links that are 404 on the server but built in the SPA
  bundle: `/projects`, `/projects/:id`, `/about`, `/team`, `/contact`).
  Anything purely speculative (favorites, end-user signup, blog,
  search filters beyond category/text) is **out of scope** for now.
- One Django app per bounded concern. No mega-apps.
- Public reads are open; all writes (admin + content) are
  authenticated. Enquiry submission is the only public write endpoint
  and is rate-limited.
- API surface: `GET` everywhere for the frontend, plus `POST /enquiries/`.

## 2. App breakdown

**Decision (post-review):** No `accounts` app, no custom `User`. This
is a listing-only site with no end-user signup; Django's built-in
`auth.User` handles `/admin/` login for staff and nothing else.

| App             | Responsibility                                                                 |
| --------------- | ------------------------------------------------------------------------------ |
| `catalog`       | Reference data: `City`, `Developer`, `Amenity`, `Category`.                    |
| `projects`      | The main `Project` entity + child tables (`ProjectImage`, `ProjectHighlight`, `ProjectStat`). Featured / published flags. |
| `enquiries`     | Contact-form & project-sidebar lead submissions. One model, optional `project` FK. |
| `team`          | `TeamMember` (founders / leadership grid).                                     |
| `testimonials`  | `Testimonial` (homepage carousel).                                             |
| `site_settings` | Singleton `SiteSettings` (phone, email, address, social links, hero stats, copyright year) + simple `CmsPage` for About / Privacy / Terms / Disclaimer. |

> `site_settings` is **not** named `site` because Python ships a stdlib
> module called `site` and our `apps/` directory is on `sys.path`,
> which would shadow it.

> Apps **deliberately not** created in this step: `accounts` (no
> signup), `favorites`, `reviews`, `agents`, `blog`, generic `media`.
> The frontend has no surface for any of them.

> `media` as a top-level upload manager is not needed yet — project
> images, team photos, and CMS hero images each live as `ImageField`
> on their owning model with structured `upload_to` paths.

## 3. ER diagram

```mermaid
erDiagram
    User ||--o{ Enquiry : "claimed_by (optional)"
    City ||--o{ Project : "located in"
    Developer ||--o{ Project : "built by"
    Category ||--o{ Project : "classified as"
    Project ||--o{ ProjectImage : "has gallery"
    Project ||--o{ ProjectHighlight : "has highlights"
    Project ||--o{ ProjectStat : "has stats"
    Project }o--o{ Amenity : "offers"
    Project ||--o{ Enquiry : "enquired about (optional)"

    User {
        bigint id PK
        string username
        string email
        string phone
        string role "admin|staff|agent"
        bool is_staff
        bool is_active
        datetime date_joined
    }

    City {
        bigint id PK
        string name "Noida, Greater Noida, Gurugram, ..."
        string slug UK
        int display_order
        bool is_active
    }

    Developer {
        bigint id PK
        string name "CRC Group, Godrej, ..."
        string slug UK
        text description
        image logo
        url website
    }

    Category {
        bigint id PK
        string name "Residential | Commercial | Luxury"
        string slug UK
        text description
        int display_order
        bool is_active
    }

    Amenity {
        bigint id PK
        string name "Ample Parking, Hi-Tech Security, ..."
        string slug UK
        image icon
        int display_order
        bool is_active
    }

    Project {
        bigint id PK
        string title
        string slug UK
        FK category_id
        FK city_id
        string locality "Sector-140A"
        FK developer_id "nullable"
        string status "under_construction|ready|new_launch|sold_out"
        string property_type "free-text: Retail/Office Space, 3BHK Apartment, ..."
        string tagline
        text description
        decimal price_starting_lacs "nullable; UI shows '80 Lacs*'"
        string price_display "free-text override, e.g. '80 Lacs*'"
        string size_display "e.g. '360 Sq.Ft. onwards'"
        string rera_number "nullable"
        url map_embed_url "Google Maps iframe src"
        image cover_image
        bool is_featured
        int featured_order
        bool is_published
        datetime published_at
        datetime created_at
        datetime updated_at
    }

    ProjectImage {
        bigint id PK
        FK project_id
        image image "projects/<project_id>/gallery/<filename>"
        string caption
        int display_order
    }

    ProjectHighlight {
        bigint id PK
        FK project_id
        string text "Prime Corner Plot in Sec 140A"
        int display_order
    }

    ProjectStat {
        bigint id PK
        FK project_id
        string label "Property status / Price Starts from / Sizes / ..."
        string value "Under Construction / 80 Lacs*"
        string icon_key "string identifier, admin-chosen"
        int display_order
    }

    Enquiry {
        bigint id PK
        FK project_id "nullable"
        string full_name
        string mobile
        string email
        text message
        string source "contact_page|project_sidebar"
        string status "new|contacted|qualified|closed"
        FK claimed_by_id "User, nullable"
        string ip_address
        string user_agent
        datetime created_at
        datetime updated_at
    }

    TeamMember {
        bigint id PK
        string name
        string designation "Founder & CEO, ..."
        text bio "stored as text; rendered as paragraphs by splitting on blank lines on the frontend, OR stored as JSON list"
        image photo
        url linkedin_url
        int display_order
        bool is_active
    }

    Testimonial {
        bigint id PK
        string name
        string role "Business Owner, IT Professional, ..."
        text content
        image photo "nullable; UI currently uses a shared avatar"
        int display_order
        bool is_active
    }

    SiteSettings {
        bigint id PK
        string phone
        string email
        string address
        url whatsapp_url
        url instagram_url
        url linkedin_url
        url facebook_url
        url youtube_url
        string hero_stat_clients "98+"
        string hero_stat_clients_label "Happy clients, countless smiles delivered"
        string hero_stat_value "100Cr+"
        string hero_stat_value_label "Property value managed with excellence"
        int copyright_year
    }

    CmsPage {
        bigint id PK
        string slug UK "about|privacy|terms|disclaimer"
        string title
        text body "markdown or HTML"
        image hero_image
        bool is_published
        datetime updated_at
    }
```

> Note: ASCII fields inside Mermaid `erDiagram` boxes can't carry full
> type signatures the way SQL does; the column lines are descriptive
> rather than strictly typed. The Model Spec tables in section 4 are the
> source of truth for types/constraints.

## 4. Model spec per app

Field type abbreviations: `CF` = `CharField`, `TF` = `TextField`,
`IF` = `ImageField`, `URL` = `URLField`, `FK` = `ForeignKey`,
`M2M` = `ManyToManyField`, `DT` = `DateTimeField`, `D` = `DecimalField`,
`B` = `BooleanField`, `I` = `IntegerField`, `S` = `SlugField`.

### 4.1 `accounts`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `User(AbstractUser)` | `phone` | `CF(15, blank=True)` | E.164-ish, no validator yet |
|                      | `role` | `CF(20, choices=ROLE_CHOICES, default="admin")` | `admin / staff / agent` |
|                      | inherits: `username, email, first_name, last_name, password, is_staff, is_active, date_joined`|||

`Meta`: default ordering by `id`. `__str__`: `f"{self.username} ({self.role})"`.

### 4.2 `catalog`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `City` | `name` | `CF(80, unique=True)` | |
|        | `slug` | `S(unique=True)` | auto-populated from name |
|        | `display_order` | `I(default=0)` | for "Find Property in" |
|        | `is_active` | `B(default=True)` | |
| `Developer` | `name` | `CF(120, unique=True)` | |
|             | `slug` | `S(unique=True)` | |
|             | `description` | `TF(blank=True)` | |
|             | `logo` | `IF(upload_to="developers/", blank=True)` | |
|             | `website` | `URL(blank=True)` | |
| `Category` | `name` | `CF(60, unique=True)` | `Residential / Commercial / Luxury` |
|            | `slug` | `S(unique=True)` | |
|            | `description` | `TF(blank=True)` | |
|            | `display_order` | `I(default=0)` | |
|            | `is_active` | `B(default=True)` | |
| `Amenity` | `name` | `CF(80, unique=True)` | |
|           | `slug` | `S(unique=True)` | |
|           | `icon` | `IF(upload_to="amenities/", blank=True)` | |
|           | `display_order` | `I(default=0)` | |
|           | `is_active` | `B(default=True)` | |

`Meta`/ordering: each model ordered by `(display_order, name)`.
`__str__`: name.
**Indexes:** `slug` is unique-indexed automatically.

### 4.3 `projects`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `Project` | `title` | `CF(160)` | |
|           | `slug` | `S(160, unique=True)` | auto from title; frontend can keep `/projects/<id>` for now |
|           | `category` | `FK("catalog.Category", on_delete=PROTECT, related_name="projects")` | |
|           | `city` | `FK("catalog.City", on_delete=PROTECT, related_name="projects")` | |
|           | `locality` | `CF(120, blank=True)` | "Sector-140A" |
|           | `developer` | `FK("catalog.Developer", null=True, blank=True, on_delete=SET_NULL, related_name="projects")` | |
|           | `status` | `CF(24, choices=STATUS_CHOICES, default="under_construction")` | `new_launch / under_construction / ready_to_move / sold_out` |
|           | `property_type` | `CF(120, blank=True)` | free-text, mirrors UI |
|           | `tagline` | `CF(240, blank=True)` | card sub-line |
|           | `description` | `TF(blank=True)` | About section, paragraphs separated by blank lines |
|           | `price_starting_lacs` | `D(max_digits=10, decimal_places=2, null=True, blank=True)` | machine-sortable price in lakhs; nullable |
|           | `price_display` | `CF(60, blank=True)` | UI string override, e.g. "80 Lacs*" |
|           | `size_display` | `CF(80, blank=True)` | "360 Sq.Ft. onwards" |
|           | `rera_number` | `CF(60, blank=True)` | |
|           | `map_embed_url` | `URL(blank=True)` | Google Maps `iframe` src |
|           | `cover_image` | `IF(upload_to=_project_upload_path)` | `projects/<id>/cover/<filename>` |
|           | `is_featured` | `B(default=False)` | |
|           | `featured_order` | `I(default=0)` | |
|           | `is_published` | `B(default=False)` | |
|           | `published_at` | `DT(null=True, blank=True)` | "Posted X days ago" — auto-set on first publish |
|           | `amenities` | `M2M("catalog.Amenity", blank=True, related_name="projects")` | |
|           | `created_at` | `DT(auto_now_add=True)` | |
|           | `updated_at` | `DT(auto_now=True)` | |
| `ProjectImage` | `project` | `FK(Project, on_delete=CASCADE, related_name="images")` | |
|                | `image` | `IF(upload_to=_project_image_path)` | `projects/<project_id>/gallery/<filename>` |
|                | `caption` | `CF(200, blank=True)` | |
|                | `display_order` | `I(default=0)` | |
| `ProjectHighlight` | `project` | `FK(Project, on_delete=CASCADE, related_name="highlights")` | |
|                    | `text` | `CF(200)` | |
|                    | `display_order` | `I(default=0)` | |
| `ProjectStat` | `project` | `FK(Project, on_delete=CASCADE, related_name="stats")` | |
|               | `label` | `CF(60)` | "Property status", "Price Starts from", "Sizes", "Developer", "Property Type" |
|               | `value` | `CF(120)` | |
|               | `icon_key` | `CF(40, blank=True)` | string identifier, admin-chosen from a known set |
|               | `display_order` | `I(default=0)` | |

`Meta`:
- `Project.ordering = ("-published_at", "-id")`
- `ProjectImage.ordering = ProjectHighlight.ordering = ProjectStat.ordering = ("display_order", "id")`
- Indexes on `Project`: `(is_published, is_featured)`, `(city, category)`, `slug`.

`__str__`: `Project.title`, child rows show `f"{project.title} · {label/text/caption}"`.

### 4.4 `enquiries`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `Enquiry` | `project` | `FK("projects.Project", null=True, blank=True, on_delete=SET_NULL, related_name="enquiries")` | nullable for site-wide contact |
|           | `full_name` | `CF(120)` | |
|           | `mobile` | `CF(20)` | |
|           | `email` | `EmailField(blank=True)` | UI doesn't mark required — keep optional |
|           | `message` | `TF(blank=True)` | "Any specific requirements?" — sometimes empty |
|           | `source` | `CF(24, choices=SOURCE_CHOICES, default="contact_page")` | `contact_page / project_sidebar` |
|           | `status` | `CF(24, choices=STATUS_CHOICES, default="new")` | `new / contacted / qualified / closed` — admin tracks via /admin/ |
|           | `ip_address` | `GenericIPAddressField(null=True, blank=True)` | server-side stamp |
|           | `user_agent` | `CF(255, blank=True)` | server-side stamp |
|           | `created_at` | `DT(auto_now_add=True)` | |
|           | `updated_at` | `DT(auto_now=True)` | |

`Meta`: `ordering = ("-created_at",)`. Index on `(status, created_at)`.
`__str__`: `f"{full_name} ({mobile}) — {project or 'site'}"`.

### 4.5 `team`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `TeamMember` | `name` | `CF(120)` | |
|              | `slug` | `S(unique=True)` | for future `/team/<slug>` |
|              | `designation` | `CF(120)` | "Founder & CEO" |
|              | `bio` | `TF(blank=True)` | paragraphs separated by blank lines |
|              | `photo` | `IF(upload_to="team/")` | |
|              | `linkedin_url` | `URL(blank=True)` | |
|              | `display_order` | `I(default=0)` | |
|              | `is_active` | `B(default=True)` | |

`Meta`: `ordering = ("display_order", "id")`.

### 4.6 `testimonials`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `Testimonial` | `name` | `CF(120)` | |
|               | `role` | `CF(120, blank=True)` | "Business Owner" |
|               | `content` | `TF` | |
|               | `photo` | `IF(upload_to="testimonials/", blank=True)` | |
|               | `display_order` | `I(default=0)` | |
|               | `is_active` | `B(default=True)` | |

`Meta`: `ordering = ("display_order", "id")`.

### 4.7 `site`

| Model | Field | Type | Notes |
| ----- | ----- | ---- | ----- |
| `SiteSettings` (singleton) | `phone` | `CF(30)` | |
|                            | `email` | `EmailField` | |
|                            | `address` | `TF` | |
|                            | `whatsapp_url` | `URL(blank=True)` | |
|                            | `instagram_url` | `URL(blank=True)` | |
|                            | `linkedin_url` | `URL(blank=True)` | |
|                            | `facebook_url` | `URL(blank=True)` | |
|                            | `youtube_url` | `URL(blank=True)` | |
|                            | `hero_stat_clients` | `CF(20, default="98+")` | |
|                            | `hero_stat_clients_label` | `CF(120, default="Happy clients, countless smiles delivered")` | |
|                            | `hero_stat_value` | `CF(20, default="100Cr+")` | |
|                            | `hero_stat_value_label` | `CF(120, default="Property value managed with excellence")` | |
|                            | `copyright_year` | `I(default=2026)` | |
| `CmsPage`                  | `slug` | `S(unique=True)` | `about / privacy / terms / disclaimer` |
|                            | `title` | `CF(160)` | |
|                            | `body` | `TF(blank=True)` | rendered as HTML/markdown |
|                            | `hero_image` | `IF(upload_to="cms/", blank=True)` | |
|                            | `is_published` | `B(default=True)` | |
|                            | `updated_at` | `DT(auto_now=True)` | |

`SiteSettings.save()` enforces a single row (`pk=1`). Helper classmethod `SiteSettings.load()`.

## 5. API surface

All endpoints mounted at `/api/v1/<app>/...`. **The API is read-only
for the frontend, with one exception: `POST /enquiries/`.** All staff
writes (creating projects, editing settings, moderating enquiries)
happen via Django admin at `/admin/`. There is no API-side admin CRUD
and no public JWT token endpoint, because there are no end-users to
log in.

Pagination: PageNumberPagination, `page_size=20`. All list views support
`?page=N` and `?page_size=…` (within limits).

### 5.1 `projects`

| Method | Path                              | Auth | Filters / Search / Ordering                                            | Response shape (summary) |
| ------ | --------------------------------- | ---- | ---------------------------------------------------------------------- | ------------------------ |
| `GET`  | `/api/v1/projects/`               | None | `filter`: `category` (slug), `city` (slug), `is_featured`, `status`; `search`: `title`, `locality`; `ordering`: `-published_at`, `featured_order`, `id` | Paginated list of `ProjectListSerializer` (id, slug, title, tagline, category.name, category.slug, city.name, locality, status, cover_image, is_featured) |
| `GET`  | `/api/v1/projects/<id-or-slug>/`  | None | —                                                                      | `ProjectDetailSerializer` (everything above + description, price/size/RERA, map_embed_url, developer (nested), amenities (nested list), highlights (nested), stats (nested), images (nested gallery)) |
| `GET`  | `/api/v1/projects/featured/`      | None | first N by `featured_order`                                            | Same as list, capped at 3 |

Default lookup is `slug`; the same view also resolves by numeric `id`.
Only the published subset (`is_published=True`) is exposed; drafts are
admin-only.

### 5.2 `catalog`

Pure read endpoints used to populate filter dropdowns.

| Method | Path                          | Auth | Notes |
| ------ | ----------------------------- | ---- | ----- |
| `GET`  | `/api/v1/cities/`             | None | Active only, ordered by display_order |
| `GET`  | `/api/v1/developers/`         | None | |
| `GET`  | `/api/v1/categories/`         | None | Active only |
| `GET`  | `/api/v1/amenities/`          | None | Active only |
| Admin via `/admin/` only — no API write endpoints. | | |

### 5.3 `enquiries`

| Method | Path                          | Auth | Notes |
| ------ | ----------------------------- | ---- | ----- |
| `POST` | `/api/v1/enquiries/`          | **None** | Public — accepts `{full_name, mobile, email?, message?, project?, source?}`; server fills `ip_address`, `user_agent`, defaults `source`. Throttled (DRF `AnonRateThrottle`, 10/hour/IP). |

Enquiries are listed, filtered, and updated by staff via Django admin
at `/admin/enquiries/enquiry/` — no API read or write endpoints.

### 5.4 `team`

| Method | Path                          | Auth | Notes |
| ------ | ----------------------------- | ---- | ----- |
| `GET`  | `/api/v1/team/`               | None | Active members only, ordered |
| Admin via `/admin/` only — no API write endpoints. | | | |

### 5.5 `testimonials`

| Method | Path                          | Auth | Notes |
| ------ | ----------------------------- | ---- | ----- |
| `GET`  | `/api/v1/testimonials/`       | None | Active only |
| Admin via `/admin/` only — no API write endpoints. | | | |

### 5.6 `site_settings`

| Method | Path                            | Auth | Notes |
| ------ | ------------------------------- | ---- | ----- |
| `GET`  | `/api/v1/site/settings/`        | None | Singleton; returns the only row |
| `GET`  | `/api/v1/site/pages/<slug>/`    | None | Return `CmsPage` by slug; 404 if unpublished |

Admin edits via `/admin/site_settings/sitesettings/` and `.../cmspage/`.

### 5.7 Auth

No public auth endpoints. SimpleJWT remains installed/configured from
step 1 so it can be enabled later without a migration, but no token
URLs are exposed. Staff sign in to `/admin/` with session auth.

## 6. Serializer conventions

- **List vs detail** split for `Project` only — list keeps the response
  light for the `/projects` grid; detail nests everything the
  `/projects/:id` page renders.
- **Nested read, PK write:** child writes go through nested writable
  serializers on `Project`, so the admin/API can create a project with
  highlights+stats+amenities in one POST.
- Image fields serialize as **absolute URLs** (`use_url=True`).
- `developer`, `category`, `city`, `amenities` are nested objects in
  the detail response but accept PKs (or slugs) on write.

## 7. Permissions, throttling, security

- `DEFAULT_PERMISSION_CLASSES` is currently `IsAuthenticated` (set in
  step 1). I'll override it per-view to `AllowAny` for the public read
  endpoints — that's cleaner than flipping the default and remembering
  to lock everything down.
- `Enquiry` POST: `AllowAny` + `AnonRateThrottle` (10/hour/IP) + simple
  honeypot field on the serializer (`website` — should be empty).
- All write endpoints under admin CRUD require `IsAdminUser`.
- Admin and `/api/docs/` remain authenticated in production (gated by
  Django admin login).

## 8. Seed data plan (step C deliverable)

Three management commands:

- `seed_catalog` — creates cities (Noida, Greater Noida, Gurugram,
  Faridabad, Ghaziabad), categories (Residential, Commercial, Luxury),
  developers (CRC Group, Godrej, Ace, Group 108, Eldeco, etc.), and
  the 10 amenities seen on the CRC detail page.
- `seed_projects` — creates the 8 projects from the bundle, marking the
  3 home-page ones as featured. Each gets a placeholder cover image,
  the stats panel from the detail page where available, and a couple
  of highlights / gallery entries.
- `seed_site` — creates the singleton `SiteSettings`, the four
  `CmsPage` rows (about / privacy / terms / disclaimer with stub
  copy), the 3 testimonials, and the 4 team members from the bundle.

## 9. Open questions / explicit asks before I start

These are the calls I'd make on my own if you said "just decide" —
listing them so you can override before code is written:

1. **`accounts.User`** — I'll create the model with `phone` and `role`
   (choices: `admin / staff / agent`, default `admin`), no public
   signup endpoint, no email-as-username. The role field exists so we
   can later assign enquiries to agents. **Confirm:** OK to omit
   `buyer` / `seller` roles entirely until the frontend has signup?

2. **Project URL** — I'll keep `/projects/<id>` working **and** add
   `/projects/<slug>` working in parallel. Both resolve via the same
   viewset. **Confirm:** OK?

3. **Image handling** — local `FileSystemStorage` in dev (already wired);
   in prod the brief mentioned future S3 via `django-storages`. I won't
   wire S3 yet but I'll keep `upload_to` paths structured so the move
   is a config change.

4. **Pricing** — `price_starting_lacs` (decimal, sortable) plus
   `price_display` (free-text for the UI override like "80 Lacs*").
   This keeps prices both filterable and faithful to the UI. **Confirm.**

5. **Hero stats on `SiteSettings`** — stored as raw strings (`"98+"`,
   `"100Cr+"`) rather than parsed numbers, because the suffix is part
   of the brand voice. **Confirm.**

6. **Testimonial photos** — UI currently reuses one shared avatar
   regardless. I'll model `photo` as nullable so the frontend can fall
   back to a default when absent.

7. **`CmsPage` body format** — store as `TextField` with Markdown; the
   frontend can render with any MD lib. Alternative is raw HTML.
   **Recommendation:** Markdown.

8. **No `Service` model.** Footer service items remain hard-coded in the
   frontend (they go to `/` today anyway). Add later only if a real
   `/services/<slug>` page appears.

9. **Throttling** — DRF anonymous throttle on `POST /enquiries/` at
   **10/hour/IP**. If you want a different rate, say now.

10. **Seed data realism** — the bundle gives me clean record shapes for
    8 projects but **only the CRC project** has a full description,
    stats, amenities, and highlights. For the other 7 I'll seed
    plausible-but-shorter values (real title, real location, real
    category; lorem-ipsum description; empty highlights/stats unless
    you have copy). **Confirm.**

## 10. What will *not* be in step C

Just to be loud about it, none of the following will be scaffolded:

- Favorites / wishlist
- End-user signup / profile pages
- Reviews or ratings (testimonials are admin-curated)
- Schedule-visit / booking
- Price-range / area-range / BHK / amenities filters (filterset stays
  at: `category`, `city`, `is_featured`, `status`, plus search by name/locality)
- Blog
- `Service` model
- Latitude/longitude (we store the embed URL instead)

---

**Awaiting approval.** When you say "proceed" I'll execute Phase C
exactly as scoped above. If you want any item added, removed, or
renamed, edit this doc or tell me inline and I'll regenerate before
writing code.
