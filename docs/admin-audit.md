# Admin Audit — Step 8

Companion to [`frontend-audit.md`](./frontend-audit.md), [`backend-plan.md`](./backend-plan.md), [`features-spec.md`](./features-spec.md), [`search-spec.md`](./search-spec.md).

The Django admin IS the CMS for this site. Step 8's job is to polish
it. This audit catalogues (1) what's already there, (2) where the
brief's expectations don't match our schema, (3) what gets built.

## 1. Existing admin gaps

### `apps/projects.ProjectAdmin` — already 70% polished (step 4)

What's there:
- `list_display`, `list_filter`, `search_fields`, `autocomplete_fields`,
  `filter_horizontal` on amenities, `prepopulated_fields` for slug,
  `readonly_fields` including `cover_preview`, four inlines
  (Stats / Highlights / Images / FloorPlans), `fieldsets`, custom
  `bulk-upload-images` URL + action, custom `change_form_template`
  surfacing the bulk-upload link.

Gaps vs step 8 brief:
- No `list_display_links="title"` — currently every column links to detail.
- No thumbnail in list view (only `cover_preview` on the detail page).
- No `date_hierarchy = "created_at"`, no `list_per_page`, no `list_select_related` → potential N+1 from `category`, `city`, `developer` FKs in list view.
- No `list_editable` for quick `status` / `is_featured` toggles.
- No custom display methods for `locality_with_city` or Indian-format price.
- No actions: "Publish selected", "Unpublish", "Mark featured", "Unfeature", "Duplicate listing".
- No "View on site" link on the change form.
- No "Recent inquiries" sidebar on the change form.
- No `save_on_top = True`.
- No `save_model` hook to auto-stamp `published_at` (currently done in `Project.save()`, which is fine — note for the brief).

### `apps/enquiries.EnquiryAdmin` — already polished in steps 2 + 6

What's there:
- `list_display`, `list_filter`, `list_editable` on `status`, `search_fields`, `autocomplete_fields=("project",)`, `readonly_fields`, `date_hierarchy`, `fieldsets`, `actions=("mark_as_contacted","export_as_csv")`, `change_view` auto-flips `status: new → contacted`.

Gaps vs step 8 brief:
- No `phone_clickable` (`tel:` + `wa.me`) — high admin-workflow value.
- No `project_link` (linked title column).
- No `internal_notes` field — admins keep follow-up context elsewhere right now.
- No `last_contacted_at` / `contacted_by` — the brief's `Mark as contacted` should stamp who+when, not just flip status.
- Brief proposes `is_read` + `is_spam` booleans; we have a richer `status` choice (new / contacted / qualified / closed). `status=new` IS our "unread" — no need to duplicate.

### `apps/catalog` — basic `_NamedAdmin` shared across City / Category / Developer / Amenity

Has `list_display`, `list_editable`, `search`, `prepopulated_fields`. Missing thumbnail previews for `Developer.logo` and `Amenity.icon`.

### `apps/testimonials.TestimonialAdmin`, `apps/team.TeamMemberAdmin` — minimal but adequate

Standard `list_display` + `list_editable` + `search_fields`. No photo preview in list view.

### `apps/site_settings.SiteSettingsAdmin` + `CmsPageAdmin`

Already enforces singleton (changelist redirect to the only row, `has_add_permission` gated, `has_delete_permission=False`). `CmsPageAdmin` has slug prepopulated. `CmsPage.body` is a plain `TextField` rendered as Markdown by the frontend per the step 2 contract — **no rich-text editor**.

### `apps/notifications.FailedNotificationAdmin`

Already polished from step 7: retry action, test-email tool, date_hierarchy, search, read-only fields. No gaps.

## 2. Frontend cross-reference for CMS-style content

I re-checked the bundle (`scripts/crawl_out/bundle.txt`) for every CMS
hook the brief assumes. Verdict per bullet:

| Brief CMS need | What the frontend actually shows | Verdict |
| --- | --- | --- |
| Homepage hero / banner / carousel | **Single fixed hero**: `"DELHI NCR'S PREMIER REAL ESTATE CONSULTANCY"` + `"Where Ambition Meets Opportunity"`. No carousel, no slide rotation. | Skip `HomepageBanner` model. The hero copy can live on `SiteSettings` if we ever want to edit it. |
| Featured cities or localities | `"Find Property in Noida / Greater Noida / Gurugram"` — three chips that are **in-page anchors** (`#noida`, etc.), not editable tiles linking to filters. | Skip `FeaturedCity` / `FeaturedLocality` models. The chip list is hard-coded React; admins can't change which 3 appear without a frontend deploy anyway. |
| Testimonials | 3 testimonials shown. Already modelled in `apps/testimonials.Testimonial` (step 2). | Already done. |
| Blog / news / articles | **None** — no blog route, no articles, no news. | Skip. |
| FAQ section | **None** — no FAQ on any page. | Skip `FAQ` model. |
| About page content | Bundled at `/about` (server-404 today). | Already covered by `CmsPage(slug="about")`. |
| Footer links / contact info | Footer renders phone, email, address, social links. Already on `SiteSettings`. | Already done. |
| Other editable text | Hero stats (`98+`, `100Cr+`) and labels — already on `SiteSettings`. "Featured Properties" row — already via `Project.is_featured`. | Already done. |

**Net new CMS models from this audit: zero.** Everything the frontend
exposes for editorial control already has a model in
`apps/site_settings` or `apps/testimonials`.

## 3. Schema gaps vs the brief's `Property` admin spec

The brief assumes a typical Indian real-estate listing schema. Our
`Project` model deferred most of those fields in step 5 Path A
("match the frontend, don't speculate"). The frontend still doesn't
have UI for any of them.

| Brief field used by admin | On `Project`? | Comments |
| --- | --- | --- |
| `title`, `slug`, `description`, `status`, `category`, `city`, `developer`, `cover_image`, `is_featured`, `featured_order`, `is_published`, `published_at`, `created_at`, `updated_at`, `amenities` (M2M), `rera_number`, `map_embed_url`, `tagline`, `property_type` (string), `price_starting_lacs`, `price_display`, `size_display` | ✅ all present | |
| `bhk` | ❌ | deferred step 5 |
| `bathrooms` | ❌ | deferred |
| `carpet_area_sqft` / `super_builtup_area_sqft` | ❌ — we only have `size_display` (string) | deferred |
| `furnishing` | ❌ | deferred |
| `floor` / `total_floors` / `facing` | ❌ | deferred |
| `latitude` / `longitude` / `pin_code` / `address` | ❌ — we store the embed URL only | deferred |
| `listing_type` (sale / rent / pg) | ❌ — no rental content on the live site | deferred |
| `price` (single decimal), `price_negotiable`, `maintenance_charge`, `security_deposit`, `age_of_property` | ❌ | deferred |
| `view_count` / `share_count` / `is_verified` | ❌ | deferred step 6 |
| `created_by` / `owner` FK to auth.User | ❌ — single-admin scenario today | deferred |

Almost every "Specifications" / "Pricing" / "Stats" fieldset bullet in
the brief depends on fields we don't have. Reading the brief
literally would re-open all the schema work we left for "when the
frontend grows that UI."

## 4. Recommended scope (with reasoning)

### Path A — match what exists (recommended)

Build the items that pay off for actual day-to-day admin work and
don't require speculation:

1. **`django-unfold` theme** — modern look, dark mode, sidebar grouping ("Listings / Inquiries / Content / System"). Real UX win, low risk.
2. **Project admin polish** within current schema:
   - `thumbnail()` callable in list_display
   - `locality_with_city()` callable
   - `price_formatted()` callable using `price_starting_lacs` in Indian format ("₹ 80 L", "₹ 1.2 Cr")
   - `list_display_links = ("title",)`, `list_select_related = ("category", "city", "developer")`, `date_hierarchy = "created_at"`, `list_per_page = 25`, `save_on_top = True`
   - `list_editable = ("status", "is_featured")`
   - Actions: `publish`, `unpublish`, `feature`, `unfeature`, `duplicate_listing`
   - "View on site" link on the change form when `is_published`
   - "Recent enquiries (5)" panel on the change form via `extra_context`
3. **Enquiry admin polish** within current schema:
   - `phone_clickable` (tel: + wa.me)
   - `project_link` (clickable title)
   - **New light schema additions** (we said don't speculate, but these are zero-UI admin-internal fields, no frontend impact): `internal_notes` TextField, `last_contacted_at` DateTimeField, `contacted_by` CharField. Used purely by staff during follow-up.
   - "Mark as contacted" action gets enhanced to stamp `last_contacted_at` + `contacted_by = request.user.username` in addition to flipping `status`.
   - Row-level styling: `status=new` shows a coloured highlight via `django-unfold`'s row styling if available.
4. **Catalog admin** — thumbnails for `Developer.logo`, `Amenity.icon`, `TeamMember.photo`, `Testimonial.photo`.
5. **`django-import-export`** — `Project`, `City`, `Category`, `Developer`, `Amenity`, `Enquiry` (export-only). CSV / XLSX. Reasonable FK lookups by slug.
6. **`django-simple-history`** — `Project` + `Enquiry`. Adds a History tab in admin with diff + actor. Useful even for a single admin: "what did I change yesterday?"
7. **Custom dashboard** — override admin index template with:
   - Total projects (published vs draft)
   - Featured count
   - New enquiries today / this week / total
   - Unread (`status=new`) count, linked
   - Recent enquiries (last 10)
   - Recent projects (last 10)
8. **Query polish**:
   - `list_select_related` everywhere it crosses a FK
   - Confirm autocomplete on `EnquiryAdmin.autocomplete_fields = ("project",)` already done; add it to anywhere else needed
9. **`docs/admin-guide.md`** — non-technical staff onboarding doc.
10. **Tests** — smoke load every admin page (changelist + change form), action correctness, history tab loads, import/export round-trips.

### Path B — full brief, with schema additions

Adds on top of Path A:
- `bhk`, `bathrooms`, `carpet_area_sqft`, `super_builtup_area_sqft`, `furnishing`, `floor`, `total_floors`, `facing`, `latitude`, `longitude`, `pin_code`, `address`, `listing_type`, `price_negotiable`, `maintenance_charge`, `security_deposit`, `age_of_property`, `view_count`, `share_count`, `is_verified`, `created_by` on `Project`
- Brand-new CMS models: `HomepageBanner`, `FeaturedCity`, `FAQ` — with admin + public endpoints
- `TinyMCE` on `CmsPage.body` (changes the Markdown contract)
- `django-admin-sortable2` for drag-reorder on inlines
- Permission groups: Super Admin / Content Manager / Inquiry Manager / Agent — with `created_by` filtering for Agent
- `is_read` + `is_spam` on `Enquiry` (parallel to existing `status`)

This is most of step 5 Path B + step 6 Path B + step 8's full CMS catalog. Real cost: 7–10 new migrations, schema redesign, plus admin/serializer/endpoint maintenance for models nothing currently consumes.

### Path C — Path A + selected B items

If there are specific B items you want (e.g. `listing_type` because
rent listings are coming, or `created_by` because a second admin is
joining), pick them and skip the rest.

## 5. My recommendation: Path A

Same reasoning as steps 5/6/7 — the brief assumes a generic Indian
real-estate listing app, the actual frontend exposes a much narrower
surface. Path A captures every admin enhancement the live admins
will feel, drops the speculative schema and CMS catalog, and leaves
clear hooks for Path B items when they're actually needed.

Quick estimate of what Path A is worth:
- `django-unfold`: every admin page gets a meaningful visual upgrade
- Project admin polish: ~30s saved per listing edit × dozens per day
- Enquiry admin polish: callable phone links remove the copy-paste-into-WhatsApp dance
- `django-simple-history`: the "who changed this" question stops being a Slack thread
- Dashboard: every admin login starts on a useful page

Skipped surface that doesn't pay off yet:
- HomepageBanner / FeaturedCity / FAQ models with no frontend consumer
- Schema additions whose only consumer would be the admin form itself
- Permission groups for a single-admin scenario
- TinyMCE for 4 pages no UI currently renders

## 6. Decision needed

Picking Path A is my recommendation. If you want a Path B subset
(e.g. `listing_type` because rentals are coming, or `created_by` +
permissions because a second admin joined), name it and I'll fold it
in. Asking once before any code changes.
