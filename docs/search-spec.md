# Search / Filter / Sort Spec — Anjaneya

Phase A audit + the spec we'll implement in Phases B–J.

Sources: [`frontend-audit.md`](./frontend-audit.md), the live SPA bundle at
`scripts/crawl_out/bundle.txt`, the live site at
<https://anjaneya-871i.vercel.app/>.

## 1. What the frontend actually ships today

I greped the bundle for every UI pattern this step's brief assumes —
`slider`, `Range`, `priceMin/Max`, `BHK`, `bedrooms`, `sort`, `Sort by`,
`furnish`, `listing_type`, `verified`, `autocomplete`, `dropdown`,
`Newest`, `Price (asc/desc)`, etc. The matches that aren't React
internals are all marketing copy ("3 & 4 BHK Apartments" inside a
static category description, in-page-nav anchors named `amenities`,
section headings).

**The entire filter/search/sort surface on the live site is three controls:**

| # | Where | Control | Behaviour today |
| - | ----- | ------- | --------------- |
| 1 | `/projects` page | **Category tab pills** | Client-side filter of the bundled array; effectively `?category=<slug>`. Already wired in step 2. |
| 2 | `/projects` page | **Text input** `placeholder="Search by name, location"` (single field, no debounce visible) | Client-side `title`/`location` icontains. Already wired in step 2 via DRF `SearchFilter` over `title, locality, tagline`. |
| 3 | Home hero | **City chips** "Noida / Greater Noida / Gurugram" with `href="#noida"` etc. | In-page anchors that scroll to a section, **not filter URLs**. |

That's it. No sort dropdown. No price slider. No area input. No BHK
filter. No multi-select amenities. No furnishing / sale-vs-rent /
verified / posted-within toggles. No autocomplete. No "View All" arrow
that opens a filter sheet. No hidden hash-state filters.

The Projects list also has prev/next pagination chevrons (client-side
slicing today; our `?page=N` covers it via DRF PageNumberPagination).

## 2. What the step 5 brief assumes

The brief is written for a "typical Indian real estate" listings site
and assumes:

- Price range slider (`price_min`/`price_max`)
- Carpet-area range (`area_min`/`area_max`)
- BHK multi-select (`?bhk=2,3,4`)
- `property_type`, `listing_type`, `status`, `furnishing` filters
- Amenities multi-select with **conjoined (AND)** semantics
- `posted_within_days`, `has_image`, `verified`
- Sort dropdown: price ↑/↓, area ↑/↓, newest, most-viewed, relevance
- Location autocomplete grouped by City / Locality / Project
- Postgres full-text search with `SearchVector` / `SearchRank` / GIN
- Redis caching layer
- 50+ seeded properties for realistic perf testing

**None of these controls exist on the live frontend.** And the model
schema can't honour several of them as-is — see §3.

## 3. Cross-reference: filter ↔ model field ↔ frontend control

| Brief filter | Frontend control? | `Project` field exists? | Implementable today? |
| --- | --- | --- | --- |
| `category` (slug, multi) | ✅ tab pills | ✅ `category` (FK) | ✅ done in step 2 |
| `search=` over title/locality | ✅ text input | ✅ multiple text columns | ✅ done in step 2 (icontains) |
| `city` (slug) | ❌ (chips are in-page anchors only) | ✅ `city` (FK) | filter already exists, no UI; cheap to keep |
| `price_min` / `price_max` | ❌ | partial — `price_starting_lacs` (Decimal) is a *starting* price only | ✅ filter buildable, single-bound (no `price_to`) |
| `area_min` / `area_max` | ❌ | ❌ only `size_display` CharField ("360 Sq.Ft. onwards") — not numerically filterable | ❌ needs schema change (add `carpet_area_sqft` Decimal) |
| `bhk` multi-select | ❌ | ❌ no bedrooms/BHK field | ❌ needs schema change |
| `property_type` multi-select | ❌ | partial — `property_type` is free-text CharField, not a normalized choice | partial — could add IN filter but no canonical list |
| `listing_type` (sale/rent/pg) | ❌ | ❌ no field; site has zero rental content | ❌ needs schema change AND new content |
| `status` (ready / under-construction / new-launch / sold-out) | ❌ | ✅ `status` choices | ✅ filter buildable |
| `furnishing` | ❌ | ❌ | ❌ schema change |
| `amenities` AND-mode multi-select | ❌ | ✅ M2M | ✅ filter buildable |
| `posted_within_days` | ❌ | ✅ `published_at` | ✅ filter buildable |
| `has_image` | ❌ | ✅ via `images` relation | ✅ filter buildable |
| `verified` | ❌ | ❌ | ❌ schema change |
| Sort: `price`/`-price` | ❌ | ✅ `price_starting_lacs` | ✅ buildable (asc-only useful since price is a *starting* price) |
| Sort: `-created_at` (Newest) | ❌ | ✅ `published_at` | ✅ already the default |
| Sort: `view_count` | ❌ | ❌ | ❌ needs `view_count` field + a counter (step 6 territory per brief) |
| Sort: `area` | ❌ | ❌ | ❌ schema change |
| Sort: `relevance` | ❌ | n/a — search backend is plain icontains today | needs Postgres search machinery |
| Location autocomplete | ❌ | n/a | ❌ no consumer |
| Postgres FTS (SearchVector + GIN) | ❌ | n/a — we're on SQLite in dev; no Postgres anywhere | works as **infrastructure** but adds zero value until we move to Postgres |
| Redis cache | n/a | n/a | works as **infrastructure**; no current load (7 projects) |

## 4. Sort options the frontend offers

**Zero.** There is no `<select>` or pill row for sort anywhere in the
bundle. The list is displayed in whatever order the bundled array has
(featured first via the demo data ordering).

## 5. Recommended scope (and what I'd skip)

There are two clean ways to read this brief. I'd rather get a steer
than build either silently.

### Path A — Match the frontend (lean)

Ship only what the live UI actually exercises, plus the
infrastructure that's cheap and useful regardless:

- **Filters (kept / polished)**: `category`, `city`, `status`, `is_featured`, `developer`, `posted_within_days`, `has_image`, `search=`.
- **Sort**: keep default `-published_at, -id`. Allow opt-in `?ordering=price_starting_lacs` and `-price_starting_lacs`. Document them; UI can adopt later.
- **Pagination polish**: `page_size` query param (max 60), include `total_pages` in the envelope.
- **Indexes**: add `published_at`, `price_starting_lacs`, plus the existing composites are fine.
- **List performance**: `.only()` on list serializer columns, `Prefetch` the primary image only for list view, confirm ≤ 5 queries on list / ≤ 8 on detail with `assertNumQueries`.
- **django-debug-toolbar**: install in dev only.
- **Tests**: filter coverage + query-count tests + pagination.
- **Skip**: BHK/area/furnishing/listing_type/verified schema additions, Postgres FTS machinery, autocomplete endpoint, Redis cache, view_count counter, 50-property seed expansion. Document them in `search-spec.md` as "open for next time."

### Path B — Match the step 5 brief (forward-looking)

Build the whole apparatus even though nothing consumes it yet. This
means:

- **Schema changes** on `Project`: add `bedrooms` (smallint, nullable), `carpet_area_sqft` (decimal, nullable), `super_built_up_sqft`, `listing_type` (choices: sale/rent/pg/lease — defaults to `sale`), `furnishing` (choices), `is_verified` (bool), `view_count` (int, default 0). Migration + seed updates.
- **Filters**: every entry in §3 marked ❌ becomes ✅ via filterset, with brief-compatible param names. Amenities AND-mode.
- **Sort**: full set including `view_count` (zeroed for now) and `relevance` (gated on Postgres).
- **Search infrastructure**: a `search.py` helper that picks `SearchVector`/`Rank`/`GIN` on Postgres and falls back to icontains on SQLite. Denormalized `search_vector` field, `pre_save` signal, `rebuild_search_vectors` command.
- **Autocomplete**: `/api/v1/locations/autocomplete/?q=…` grouped by city/locality/project, with caching.
- **Redis**: `django-redis` with LocMem fallback in dev. TTLs as per brief.
- **Seed**: bump to 50+ projects.
- **Tests**: full filter coverage + query counts + pagination + autocomplete + cache fallback path.

### My recommendation: Path A

The brief's own "Rules" section says: *"Param names match the frontend
exactly — if the UI sends `?bedrooms=2,3` then accept `bedrooms`"* and
*"Stop and ask if any filter from the frontend can't be implemented
cleanly with the current model schema — schema changes need a
heads-up, not a silent fix."*

Both of those steer toward Path A here. Building 12 filter params
without a UI to validate them against is the exact sort of speculation
that ages badly. Path A keeps the spec honest and the next frontend
update can drive the additions.

If you'd rather go Path B (you opted into floor plans speculatively in
step 4, so that's a reasonable call), I'll do it — just want the
go-ahead since it requires several non-trivial schema additions.

## 6. Implementation table (Path A — pending approval)

| UI control | Type | Model.Field | Query param | Notes |
| --- | --- | --- | --- | --- |
| Category pills | multi-select via repeated param or CSV | `Project.category` (FK slug) | `?category=<slug>` | Multi-value support added (`?category=residential,commercial`); empty = all. |
| Search box | text | `title`, `locality`, `tagline` icontains | `?search=...` | Stays plain icontains until Postgres comes online. |
| (no UI — future) | filter | `Project.city` slug | `?city=<slug>` | Already exists; documented for the UI. |
| (no UI — future) | filter | `Project.status` choices | `?status=<choice>` | Already exists. |
| (no UI — future) | filter | `Project.is_featured` bool | `?is_featured=true` | Already exists. |
| (no UI — future) | filter | `Project.developer` slug | `?developer=<slug>` | Already exists. |
| (no UI — future) | range filter (single-bound) | `Project.price_starting_lacs` | `?price_min=<n>&price_max=<n>` | New. Both bounds optional. |
| (no UI — future) | days-since filter | `Project.published_at` | `?posted_within_days=7` | New. |
| (no UI — future) | bool | derived from `Project.images` | `?has_image=true` | New. Annotated on queryset. |
| Sort | enum (no UI yet) | various | `?ordering=published_at,price_starting_lacs,-price_starting_lacs,title` | Default `-published_at,-id`. |
| Page size | int | n/a | `?page=N&page_size=N` (max 60) | `total_pages` added to envelope. |

## 7. Final implementation (after Path A approval)

This section is the frontend contract — every query param the
`/api/v1/projects/` endpoint accepts after step 5.

### Filters

| Param | Type | Source | Example | Notes |
| --- | --- | --- | --- | --- |
| `category` | CSV of slugs | `category__slug IN` | `?category=residential,commercial` | Matches the live tab pills. Empty/missing = all categories. |
| `city` | CSV of slugs | `city__slug IN` | `?city=noida,gurugram` | No UI yet; documented for the city-chips redesign. |
| `developer` | slug (single) | `developer__slug iexact` | `?developer=crc-group` | |
| `status` | choice | `Project.status` iexact | `?status=under_construction` | `new_launch / under_construction / ready_to_move / sold_out` |
| `is_featured` | boolean | `Project.is_featured` | `?is_featured=true` | |
| `price_min` | number (lakhs) | `price_starting_lacs__gte` | `?price_min=50` | Both bounds optional. |
| `price_max` | number (lakhs) | `price_starting_lacs__lte` | `?price_max=200` | |
| `posted_within_days` | int (> 0) | `published_at__gte = now - N days` | `?posted_within_days=7` | Zero or missing = no filter. |
| `has_image` | boolean | `Exists(images)` | `?has_image=true` | |
| `search` | text | DRF `SearchFilter` over `title`, `locality`, `tagline` (icontains) | `?search=terra` | Plain icontains until we move to Postgres. |
| `ordering` | sort key | DRF `OrderingFilter` | `?ordering=-price_starting_lacs` | Allowed: `published_at`, `featured_order`, `price_starting_lacs`, `title` (each with `-` prefix). Default: `-published_at, -id`. |

### Pagination envelope

```jsonc
{
  "count": 7,
  "total_pages": 3,
  "next": "http://.../projects/?page=2&page_size=3",
  "previous": null,
  "results": [ /* ... */ ]
}
```

- `?page=N` (1-indexed)
- `?page_size=N` — defaults to 20, capped at 60.
- `total_pages` is `ceil(count / page_size)`.

### Detail endpoint

`GET /api/v1/projects/<slug>/` and `GET /api/v1/projects/<id>/` return
the full nested shape (everything in §4 of `frontend-audit.md` plus
amenities, images, floor_plans, highlights, stats). Unchanged — listed
here for completeness.

### Featured endpoint

`GET /api/v1/projects/featured/` returns up to 6 `is_featured=True`
projects ordered by `featured_order`, in the lightweight list shape.

## 8. What gets documented as "deferred"

These are real product features but not in the current UI nor
schema. The brief calls them out; this file is where the team can find
them when the frontend grows.

- **BHK** (`bedrooms`) — add `Project.bedrooms` (smallint) + `?bhk=` filter
- **Carpet area / super built-up area** — add Decimal fields + range filters
- **Listing type** (sale / rent / PG / lease) — add field + filter; no rental inventory today
- **Furnishing** — add field + filter
- **Verified** — add field + filter
- **Amenities AND multi-select** — model M2M already exists; need filter param + `conjoined=True`
- **view_count + Most-viewed sort** — needs counter (probably step 6)
- **Relevance sort** — needs Postgres FTS machinery
- **Location autocomplete** — needs a consumer (search box redesign)
- **Postgres FTS + GIN index** — needs Postgres deployment
- **Redis caching** — needs sustained load to justify
