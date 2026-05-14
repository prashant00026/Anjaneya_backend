# Frontend Audit — Anjaneya Global Realty

**Target:** <https://anjaneya-871i.vercel.app/>
**Audit date:** 2026-05-14
**Method:** Playwright headless Chromium crawl + JS bundle inspection
(see `scripts/crawl_frontend.py`, `scripts/probe_bundle.py`,
`scripts/crawl_out/` for raw output).

## 1. Site nature

- **Stack:** Vite-built React SPA (single `index-*.js` bundle ~501 KB,
  no `__NEXT_DATA__`, asset paths `/assets/<name>-<hash>.<ext>`).
- **Deployment:** Vercel without SPA fallback configured — direct visits
  to any path other than `/` return **HTTP 404**.
- **Routing (declared in bundle, currently broken on direct URL):**
  - `/`           → Home
  - `/about`      → About Us
  - `/team`       → Our Team
  - `/projects`   → Projects list
  - `/projects/:id` → Project detail
  - `/contact`    → Contact
- **Currently functional via direct URL:** `/` only. The other routes
  resolve when navigated within the SPA, and the bundle ships all their
  copy and data, so they are valid for backend design purposes.
- **No API calls observed.** The frontend ships demo data hard-coded in
  the JS bundle. Nothing is fetched from a server today — the backend
  we are building will replace that hard-coded data.

## 2. Route map

| Route          | Purpose                                    | Status        |
| -------------- | ------------------------------------------ | ------------- |
| `/`            | Landing / marketing home                   | live          |
| `/about`       | About company, mission, story              | bundled, 404 server |
| `/team`        | Founders + leadership grid                 | bundled, 404 server |
| `/projects`    | Project listing with search + category tabs | bundled, 404 server |
| `/projects/:id`| Project detail (about, amenities, highlights, developer, location, gallery, enquiry sidebar) | bundled, 404 server |
| `/contact`     | Contact page (banner + form)               | bundled, 404 server |
| Footer dummy   | `Privacy Policy`, `Terms of Service`, `Disclaimer` (`href="#"`) | not built |
| Footer service links | `/` only — services are visual cards, not real pages | n/a |

External links: Instagram, LinkedIn (company + per-team-member),
Facebook, YouTube, WhatsApp (`wa.me`), `tel:+917311103111`,
`mailto:info@anjaneyaglobalrealty.com`, Google Maps embed per project.

## 3. Page-by-page inventory

### 3.1 Home `/`

**Sections:**

1. **Hero**
   - Tagline: `DELHI NCR'S PREMIER REAL ESTATE CONSULTANCY`
   - Headline: `Where Ambition Meets Opportunity`
   - Sub-copy paragraph
   - Primary CTA button: `Explore Properties`
   - Two hero stats:
     - `98+` — `Happy clients, countless smiles delivered`
     - `100Cr+` — `Property value managed with excellence`
   - City quick-links (in-page anchors): **Noida, Greater Noida, Gurugram** (`#noida`, `#greater-noida`, `#gurugram`)

2. **What We Offer** — three category cards (icon + image + features list):
   - **Residential Properties** — `3 & 4 BHK Apartments`, `Villas & Penthouses`, `Gated Communities`
   - **Commercial Properties** — `Grade A Offices`, `Retail Spaces`, `IT Parks & SEZs`
   - **Luxury & Ultra Premium** — `Sky Villas & Penthouses`, `Farmhouses & Estates`, `Branded Residences`

3. **Why Choose Us** — four value-prop cards (icon + title + description):
   - `Affordable Realty Options`
   - `Expertise You Can Trust`
   - `Market Intelligence Investment`
   - `Full Portfolio Access`

4. **Featured Properties** — 3 project cards each linking to `/projects/{id}`:
   - `COMMERCIAL · CRC The Flagship · Sector-140A, Noida · Premium Retail Shops & Commercial Spaces`
   - `RESIDENTIAL · Godrej Tropical Isle · Sector-146, Noida · Ultra-Luxury Apartments with Private Decks`
   - `RESIDENTIAL · Ace Terra · Yamuna Expressway, Noida · Modern Lifestyle Apartments in Gated Community`
   - Button: `View All Properties` → `/projects`

5. **Start Your Property Journey Today** — banner with CTA `Connect with us` (likely links to Contact / WhatsApp)

6. **Testimonials**
   - 3 testimonials hard-coded:
     - `Rajiv Kapoor` / `Business Owner`
     - `Priya Sharma` / `IT Professional`
     - `Vikram Malhotra` / `Retail Entrepreneur`
   - Each has: `name`, `role`, `content`, `image` (currently a single shared avatar)

### 3.2 Projects list `/projects`

Controls visible in the bundle:

- **Category tab pills** (UI: rounded pill row) — values are pulled from the project records, so the set is whatever appears: `Commercial`, `Residential`, plus an implicit `All`.
- **Search input** — `placeholder: "Search by name, location"` (single text input that filters by `title` and `location`).
- **Pagination** — prev/next chevron buttons (`size-40 sm:size-56`), so list is paginated client-side.

**Project records currently shipped (8 total):**

| id | category    | title                  | location               | tagline                                        | city       |
| -- | ----------- | ---------------------- | ---------------------- | ---------------------------------------------- | ---------- |
| 1  | Commercial  | CRC The Flagship       | Sector-140A, Noida     | Premium Retail Shops & Commercial Spaces       | Noida      |
| 2  | Residential | Godrej Tropical Isle   | Sector-146, Noida      | Ultra-Luxury Apartments with Private Decks     | Noida      |
| 3  | Residential | Ace Terra              | Yamuna Expressway, Noida | Modern Lifestyle Apartments in Gated Community | Noida      |
| 1  | Commercial  | CRC The Flagship       | Sector-140A, Noida     | Premium Retail Shops & Commercial Spaces       | Noida      |
| 2  | Residential | Sunrise Residency      | Sector-45, Gurgaon     | Modern Apartments with Green Spaces            | Gurugram   |
| 3  | Commercial  | Group 108              | Sector-62, Noida       | Warehouse and Distribution Centers             | Noida      |
| 4  | Residential | Harmony Heights        | Sector-21, Faridabad   | Integrated Living, Shopping, and Office Spaces | Faridabad  |
| 5  | Residential | Eldeco Echo of Eden    | Sector-17, Ghaziabad   | State-of-the-Art School Campus                 | Ghaziabad  |

> The first three rows are the **Featured** subset on the home page; the
> second block (with `city` populated) is the **Projects list** record
> shape. The two arrays use overlapping IDs — backend should consolidate
> into a single `Project` table where `is_featured` flags the featured ones.

### 3.3 Project detail `/projects/:id`

Anchored sub-sections (in-page nav): `#about`, `#amenities`, `#highlights`, `#developers`, `#location`.

- **Header / hero**: project image, category badge (CAPS, e.g. `COMMERCIAL`), `RERA APPROVED` badge (where applicable), title, location.
- **Stats panel** (5 stats, only fully populated for project #1; shape:
  `{ label, value, icon }`):
  - `Property status` — e.g. `Under Construction`
  - `Property Type`   — e.g. `Retail/Office Space`
  - `Price Starts from` — e.g. `80 Lacs*`
  - `Sizes` — e.g. `360 Sq.Ft. onwards`
  - `Developer` — e.g. `CRC GROUP`
- **About** — 2–3 paragraph description.
- **Amenities** — grid of icon tiles. Visible amenities (project #1):
  `Hi-Tech Security`, `Ample Parking`, `24/7 Power Backup`,
  `High-speed Internet`, `Hi-speed Elevators`, `Business lounges`,
  `Biometric Entry`, `ATMs & Bank Facilities`, `EV Charging Stations`,
  `Pharmacy & Health Care`.
- **Key Highlights** — bullet list (free-form strings).
- **About Developer** — developer name + paragraph(s).
- **Location** — Google Maps `iframe` embed (per-project URL).
- **Project Gallery** — horizontal drag carousel of images.
- **Sidebar Enquiry form** (sticky):
  - `text` — `Your full name`
  - `tel`  — `Mobile number`
  - `email` — `Email id`
  - `textarea` — `Any specific requirements?`
  - Submit button — currently `e.preventDefault()` (no backend wired).

### 3.4 About `/about`

- Section subtitle: `OUR STORY`. Title `About …`.
- Founder image (`kg = Founder of Anjaneya Global Realty`).
- Mostly long-form copy (mission / story / philosophy). No structured
  data beyond `image` + paragraphs.

### 3.5 Team `/team`

Each card:

| Field         | Example                                              |
| ------------- | ---------------------------------------------------- |
| `name`        | `Rohit Aggarwal`                                     |
| `image`       | hashed asset                                         |
| `designation` | `Founder & CEO`                                      |
| `description` | array of paragraphs (bio)                            |
| `socials`     | `linkedin` URL                                       |

Members shipped: Rohit Aggarwal (Founder & CEO), Vikrant Singh (Co-Founder & COO), Raunak Verma (Co-Founder & CMO), Upender Singh (Director — Investment Strategy).

### 3.6 Contact `/contact`

- Banner image `contact-us-banner-Crb61iuz.png`.
- Same enquiry form as the project sidebar (name / mobile / email / requirements).
- Also surfaces: address, phone, email, Google Maps embed of the office, social links.

### 3.7 Footer (global)

- **Quick Links:** Home, About Us, Our Team, Projects, Contact Us
- **Our Services** (display-only, `href="#"`): Residential Advisory, Commercial Real Estate, Luxury Properties, Investment Consulting, Property Management, NRI Services
- **Contact:**
  - Address: `Office No. 106, 1st Floor, Tower 4, Assotech Business Cresterra, Sector 135, Noida Expressway, Noida – 201304`
  - Phone:  `+91 73111 03111`
  - Email:  `info@anjaneyaglobalrealty.com`
- **Social:** Instagram, LinkedIn (company), Facebook, YouTube
- Floating WhatsApp button (`wa.me/917311103111?text=Hi%2C%20I'm%20interested...`)
- Copyright: `© 2026 Anjaneya Global Realty`
- Legal links exist as visual text but go nowhere (`href="#"`).

## 4. Inferred entities

| Entity            | Source                                                       | Confidence |
| ----------------- | ------------------------------------------------------------ | ---------- |
| **Project**       | Featured cards + Projects-list array + detail page           | High       |
| **City**          | "Find Property in" + `city` field on list records (Noida, Greater Noida, Gurugram, Faridabad, Ghaziabad) | High       |
| **Locality** (sector / area string within a city) | `location` field on projects | Medium — currently a free-text string; could stay flat or be its own table |
| **Category**      | Three top-level cards on home + filter pills on Projects list (`Residential`, `Commercial`, `Luxury & Ultra Premium`) | High |
| **Developer / Builder** | Project stats panel (`Developer: CRC GROUP`) + "About Developer" section | High |
| **Amenity**       | Amenity grid on project detail (icon + name)                 | High       |
| **ProjectHighlight** (bullet) | "Key Highlights" list on project detail            | High       |
| **ProjectImage** (gallery)    | Project Gallery carousel                          | High       |
| **TeamMember**    | Team page records                                            | High       |
| **Testimonial**   | Home page testimonial carousel                               | High       |
| **Service** (footer) | "Our Services" list                                        | Medium — currently static text; may become a CMS list |
| **Enquiry / Enquiry** | Contact-page form + project sidebar form (same shape)    | High       |
| **CompanyStat**   | Hero `98+` / `100Cr+`                                        | Low — could just be hard-coded site settings |
| **SiteSettings**  | Phone, email, address, social links, copyright year         | High (single-row config) |
| **CmsPage**       | About page; legal pages (Privacy/Terms/Disclaimer) referenced but not built | Medium |

## 5. Inferred enums

| Enum                       | Values seen                                                              |
| -------------------------- | ------------------------------------------------------------------------ |
| `Project.category`         | `Residential`, `Commercial`, `Luxury` (Luxury & Ultra Premium)            |
| `Project.status` (display) | `Under Construction` (more values likely: `Ready to Move`, `New Launch`, `Sold Out`) |
| `Project.property_type`    | Free-text in UI (`Retail/Office Space`, etc.) — keep as `CharField` or join table |
| `Project.city`             | `Noida`, `Greater Noida`, `Gurugram`, `Faridabad`, `Ghaziabad` (Delhi NCR set; expandable) |
| `TeamMember.role`/designation | Free-text (`Founder & CEO`, `Co-Founder & COO`, etc.)                  |
| `Enquiry.source`           | Implied: `contact_page` vs `project_sidebar` (we can stamp this server-side) |

## 6. Fields the UI implies but doesn't currently render

Listed for backend planning — only include if cheap, otherwise wait.

- Project: `slug` (for `/projects/<slug>` SEO-friendly URLs — current routes use numeric id but slug is conventional and cheap)
- Project: `is_featured` (boolean, to drive the Home page Featured row)
- Project: `published_at` / `is_published` (so admin can stage drafts)
- Project: `rera_number` (the badge says "RERA APPROVED"; for an ad-grade site this is regulated content)
- Project: `latitude` / `longitude` (Google Maps embed today uses a hard-coded `pb=` URL — backend can store coords and either generate the embed or pass through a stored URL)

## 7. What the frontend does **NOT** imply

(Important: these were on the "nice to have" list in the brief but the
live UI has zero affordance for them — so the backend should **not**
scaffold these in step C without an explicit go-ahead.)

- **User accounts for end-users** — no login, signup, forgot-password, profile UI anywhere. (Admin-only auth is still needed.)
- **Favorites / wishlist** — no heart icon, no `/favorites` route, no "save" affordance on any card.
- **Reviews / ratings** — testimonials are editorial, not user-submitted; no rating widget anywhere.
- **Site-visit / appointment booking** — the enquiry form is generic ("Any specific requirements?"). No date picker, no time slot, no `/schedule-visit`.
- **Search filters beyond category + text** — no BHK filter, no price-range slider, no area slider, no status filter, no amenities filter. Only the single name/location search + category pills.
- **Sorting** — no sort dropdown on the projects list.
- **Sale / Rent toggle** — no rent listings, no `listing_type` field in any record.
- **Property posting by sellers/agents** — no "Post your property" CTA, no agent dashboard. (Bundle has a single `xr` nav component; no admin/agent routes.)
- **Blog** — referenced in our default route list but not present in the bundle.

## 8. Open questions

1. **Are end-user accounts in scope at all?** Strict-frontend reading says no. The step-1 brief said `AUTH_USER_MODEL = "accounts.User"` with `buyer/seller/agent/admin` roles. **Recommendation:** scaffold `accounts.User` with `phone` + `role` (defaulting to `admin`/`staff`/`agent`) so Django admin works and we can wire enquiries to staff — but skip buyer/seller signup endpoints until a frontend flow exists.

2. **Project ID vs slug.** Frontend uses `/projects/1`. **Recommendation:** keep numeric `id` as the PK for compatibility and add a `slug` field (unique) so the frontend can switch to `/projects/<slug>` later without a migration.

3. **City vs Locality.** Today `location` is a single free-text string like "Sector-140A, Noida". **Recommendation:** model `City` (with the Delhi NCR set) and keep `locality` as a `CharField` on `Project` for now — splitting Locality into its own table is overkill until the UI starts filtering by sector.

4. **Amenities normalization.** Each project ships its own amenity array (name + icon filename). **Recommendation:** model `Amenity` as its own table and many-to-many onto `Project`, so the admin can curate the icon set once.

5. **Developer normalization.** Each project shows a developer name + description. Multiple projects may share a developer (e.g. multiple CRC projects). **Recommendation:** model `Developer` as its own table, FK from `Project`.

6. **Highlights & Gallery cardinality.** Both are project-scoped lists. **Recommendation:** `ProjectHighlight` (text + order) and `ProjectImage` (file + caption + order + is_cover) as child tables.

7. **Enquiry routing.** The form has no "for which project?" hidden field today. **Recommendation:** add an optional `project` FK on `Enquiry` so the project-detail sidebar can submit with `project_id` set — backwards-compatible with the contact-page form (which leaves it null).

8. **Hero stats.** "98+" and "100Cr+" are currently hard-coded. **Recommendation:** put them on a singleton `SiteSettings` model so admin can update without a deploy. Don't bother modeling them as a list.

9. **Testimonials moderation.** Only 3 editorial testimonials exist. **Recommendation:** `Testimonial` model with `is_active` + `order` fields; no user submission flow.

10. **Maps embed.** The detail page hard-codes a Google Maps `iframe` URL per project. **Recommendation:** store `map_embed_url` as a `URLField` on `Project` (admin pastes the embed src). Latitude/longitude is overkill for now.

11. **Service items in the footer.** All 6 service items currently link to `/` — they're decorative. **Recommendation:** skip a `Service` model entirely; if needed later, a singleton list on `SiteSettings` is enough.

12. **Featured selection.** The "Featured Properties" row on Home is a hard-coded subset (3 projects). **Recommendation:** `is_featured: bool` + `featured_order: int` on `Project`; queryset = `Project.objects.filter(is_featured=True).order_by('featured_order')[:3]`.

## 9. Raw data location

- `scripts/crawl_out/sitemap.json` — every URL crawled + HTTP status + outbound links
- `scripts/crawl_out/pages/<slug>.json` — full per-page dump (HTML, links, images, forms, headings, body text, captured XHR/fetch)
- `scripts/crawl_out/bundle.txt` — concatenated JS bundle (501 KB) for inspecting hard-coded data
