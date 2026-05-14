# Media Audit — Anjaneya Backend

Audit of every `ImageField` / `FileField` currently in the codebase,
cross-referenced against [`frontend-audit.md`](./frontend-audit.md).

## 1. Existing file/image fields

| App              | Model         | Field         | Multiplicity            | Current `upload_to` | Frontend section that consumes it |
| ---------------- | ------------- | ------------- | ----------------------- | --------------------- | --------------------------------- |
| `projects`       | `Project`     | `cover_image` | One per project         | `projects/<id>/cover/<filename>` (callable) | Project card image (home + projects list); detail-page hero |
| `projects`       | `ProjectImage`| `image`       | Many per project (FK)   | `projects/<project_id>/gallery/<filename>` (callable) | Project detail "Project Gallery" carousel |
| `catalog`        | `Developer`   | `logo`        | One per developer       | `developers/`         | Project detail "About Developer" section (logo placeholder) |
| `catalog`        | `Amenity`     | `icon`        | One per amenity         | `amenities/`          | Project detail "Amenities" grid (icon tile) |
| `team`           | `TeamMember`  | `photo`       | One per member          | `team/`               | `/team` member card |
| `testimonials`   | `Testimonial` | `photo`       | One per testimonial     | `testimonials/`       | Home testimonial card avatar |
| `site_settings`  | `CmsPage`     | `hero_image`  | One per page            | `cms/`                | About / Privacy / Terms / Disclaimer banner |

There are **zero `FileField` fields** in the codebase today — only images.

## 2. Frontend cross-reference

| Brief expected | Status |
| --- | --- |
| Property main / cover image | ✅ `Project.cover_image` |
| Property gallery (multiple, ordered) | ✅ `ProjectImage` (FK from Project) |
| **Floor plans (multiple, with optional label like "Ground Floor")** | ❌ **No model exists, and the frontend has no floor-plans section** ([`frontend-audit.md §3.3`](./frontend-audit.md#33-project-detail-projectsid)). |
| Project / society images | ✅ Same as gallery above (frontend uses "Project" interchangeably with the listing). |
| Banner / hero for CMS | ✅ `CmsPage.hero_image` |
| (Bonus, not in brief) Developer logos, amenity icons, team photos, testimonial photos | ✅ all present |

## 3. Observations worth flagging

1. **`upload_to` for the four catalog-style images is plain strings**
   (`amenities/`, `developers/`, `team/`, `testimonials/`, `cms/`). Per
   the step 4 rules, every upload path should be a UUID-renaming
   callable. These five will be moved to callables in Phase B.

2. **`Project.cover_image` callable uses `instance.id or 'new'`** —
   on first save the file lands under `projects/new/cover/<file>` and
   stays there. This is broken for any project created with an
   uploaded cover. Fix in Phase B: move the file or rename the callable
   so it uses the slug (always populated before `save()`) or use a
   `pre_save`/`post_save` rename.

3. **`ProjectImage.image` callable** uses `instance.project_id`, which
   IS populated for the inline case — that one works.

4. **No `is_primary` / `order` / `alt_text` / `caption-as-displayed`
   fields on `ProjectImage`** — only `display_order` (already covers
   ordering) and `caption`. Phase B adds `is_primary` and `alt_text`
   per the brief; `display_order` is already the brief's `order`.

5. **The live frontend renders the same placeholder image for every
   project today** (`bungalow-DFBpqGu6.png` is reused for all three
   featured cards). All the media work here is for **future** rendering
   — no production frontend code consumes uploaded media URLs yet.

## 4. Decisions needed before Phase B

Two items where the step 4 brief and the frontend audit disagree;
calling them out so the rule at the bottom of the brief ("Stop and ask
before adding any media field not implied by the frontend audit")
isn't silently overridden.

### Q1. Should we add a `FloorPlan` model?

- **Frontend audit:** floor plans are not mentioned anywhere. The CRC
  detail page (the only fully-fleshed project) has Gallery, Amenities,
  Key Highlights, About Developer, Location, and stats — no floor
  plans block, no anchor `#floor-plans` in the in-page nav, nothing in
  the bundle.
- **Brief at top:** assumes floor plans by default and references them
  throughout Phase B (upload paths, validators, serializers, admin,
  endpoints, seed data).
- **Recommendation:** **skip floor plans for now.** Real-estate
  backends commonly grow them, but adding a model + endpoints + seed
  data for something with zero UI surface today is scope creep. The
  next time the frontend introduces a floor-plans block we add the
  model in a self-contained PR. Asking before proceeding.

### Q2. Admin-only **write API** endpoints for image management

In step 2 we agreed: *no API write endpoints — admin uses `/admin/`.*
The step 4 brief reverses that for media (`POST /api/v1/projects/<id>/images/`,
etc.) with `IsAdminUser`.

- **Recommendation:** **build them, gated by `IsAdminUser` + the
  existing AllowAny default** (so anonymous requests just hit 401/403).
  Inline admin upload alone tops out around 5–10 images per page load;
  for a gallery upload pipeline, an API endpoint is the right tool.
- I'll add `rest_framework.authentication.SessionAuthentication` to
  the DRF defaults so admins logged into `/admin/` can call these via
  browser; JWT remains supported.

## 5. Phase B scope (with user decisions applied)

User decided: **floor plans IN, admin-only write API IN.**

New model (Phase B):

| App | Model | Field | Notes |
| --- | --- | --- | --- |
| `projects` | `FloorPlan` | `project` FK, `file` (image OR pdf), `label` (e.g. "Ground Floor"), `display_order`, `caption`, `alt_text` | Multiple per project. File field validated for `image/jpeg`, `image/png`, `image/webp`, or `application/pdf`. 10 MB ceiling. |

1. Pillow ✓, plus `django-imagekit` and `python-magic` (+ `python-magic-bin` on Windows). Refresh `requirements.txt`.
2. `apps/common/upload_paths.py` with UUID-renaming callables for: project cover, project gallery, **floor plans**, developer logo, amenity icon, team photo, testimonial photo, CMS hero.
3. `apps/common/validators.py`: `validate_image_size`, `validate_image_dimensions`, `validate_image_mimetype` (real mime via `python-magic`), `validate_floor_plan` (image OR pdf, 10 MB).
4. `django-imagekit` `ImageSpecField`s on `Project.cover_image` and `ProjectImage.image` for thumbnail / medium / large.
5. `ProjectImage` gains `is_primary`, `alt_text`. Single-primary invariant enforced in `save()`. Manager method `primary()` returns the flagged primary or first-by-order fallback.
6. `FloorPlan` model added with FK to `Project`, `file` (FileField — supports PDF too), `label`, `display_order`, `caption`, `alt_text`.
7. Serializers: list = lightweight (cover + image count), detail = nested image variants + nested floor plans. `use_url=True` everywhere, `request` in context.
8. Admin-only API: `POST/PATCH/DELETE /api/v1/projects/<id>/images/[<image_id>/]` and `/floor-plans/[<id>/]`. Gated by `IsAdminUser` + `SessionAuthentication` added to defaults.
9. `post_delete` signals — delete file + imagekit derivatives for every model with a media field. Registered in each app's `apps.py ready()`.
10. Admin inlines with image previews + bulk-upload action.
11. Settings: `FILE_UPLOAD_MAX_MEMORY_SIZE`, `DATA_UPLOAD_MAX_MEMORY_SIZE`, `IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY`, named constants for image-size / dimension / floor-plan limits.
12. `production.py` gets a **commented-out** S3 block via `django-storages` with a `TODO: enable when deploying` note.
13. `seed_projects` generates 3–6 placeholder images + 1 placeholder floor plan per project with Pillow. First image flagged `is_primary`.
14. Tests for: valid upload 201; oversize → 400; `.exe` renamed to `.jpg` → 400; setting `is_primary` flips other images; project delete cascades + removes files; thumbnail URL resolves; anonymous upload → 401/403; floor-plan PDF accepted; floor-plan size limit.
15. `check` clean, `migrate` clean, `/api/docs/` shows multipart endpoints with file fields, `/admin/` previews load.
