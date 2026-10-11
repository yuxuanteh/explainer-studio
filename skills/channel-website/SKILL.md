---
name: channel-website
description: Create, customise and publish the channel's free website (GitHub Pages + Pages CMS) from the explainer-studio-site template - home page, auto-updating YouTube videos, bilingual blog, quizzes, gallery, About page, optional live earthquake monitor - and change its logo, colours, fonts, texts, languages, menu and pages later. Use when the user wants a website / homepage / blog for their channel, says "make my channel website", or asks to change the site's design, logo, fonts, colours, pages or wording.
---

# Channel website

Template: https://github.com/yuxuanteh/explainer-studio-site (Astro 5, deployed by GitHub Actions to GitHub Pages,
posts written in Pages CMS). Its `README.md` ("What to change where") and `CLAUDE.md` describe the code; read
them after cloning. Work in small steps, show the result, and **stop for confirmation** after the interview, before
anything is published, and after the first deploy.

## 1 · Interview (one message, then wait)
Reuse what CHANNEL.md already says (name, links, palette, fonts, languages) and only ask what is missing:
- GitHub account (check with `gh auth status`; if `gh` is missing or not logged in, ask the user to install it
  and run `gh auth login` themselves - never handle their password or token).
- Site languages: the template is Chinese (main) + English (`/en/`). Other pairs are possible (see step 4).
- Name as shown top-left (two lines), author name, home page kicker, title, tagline, intro text in each language.
- YouTube channel URL and ID (`UC...`: YouTube Studio -> Settings -> Channel -> Advanced settings), Instagram,
  LinkedIn, email (optional; it will be public).
- Logo (SVG or a large PNG) - or "make one for me"; colours; fonts (Google Fonts).
- Which pages to keep: videos, blog, quizzes, gallery (and what it shows: rocks, plants, photos...), about,
  earthquake monitor (only fits earth-science channels).
- Blog categories and video series names.

## 2 · Create the repo (after a clear yes - it is public)
```bash
gh repo create <user>.github.io --public --template yuxuanteh/explainer-studio-site --clone
```
Use `<user>.github.io` unless the user already has one: other names put the site on a sub-path and images
inside posts break. Clone into a normal (non-synced) folder or the project folder; never run `npm ci` inside a
Google Drive / OneDrive folder - build in a temporary clone.

## 3 · Customise
| Request | Change |
|---|---|
| Name, links, hero texts, channel ID | `src/data/site.json` |
| Every button / heading | `src/data/ui.json` (both languages; new keys also go in the `ui` block of `.pages.yml`) |
| Colours | `:root` tokens at the top of `src/styles/global.css` (dark and light "paper" sections; check contrast) and the hero stripes in `src/views/Home.astro` |
| Fonts | Google Fonts `<link>` in `src/layouts/Base.astro` + `--font-sans/-serif/-cjk-serif/-display` in `global.css` |
| Logo | `public/logo-mark.svg` (nav, 1:1), `favicon.svg`, `favicon.ico` (16-64 px), `apple-touch-icon.png` (180 px), `og-default.png` (1200x630 share image) - generate all from one source with Pillow; if the studio has `brand/logo/`, reuse those files |
| Menu / remove a page | `src/components/Nav.astro` + delete `src/pages/<page>.astro`, `src/pages/en/<page>.astro`, `src/views/<View>.astro`, its `.pages.yml` block |
| Categories, series, gallery types | `src/lib/i18n.ts`, `src/content.config.ts`, `.pages.yml` - keep all three in step |
| Editor in the user's language | translate the labels in `.pages.yml` |
| About page, sample post / quiz | `src/content/pages/about-*.md`; replace or delete `hello-world-*` and `sample-*` |

Show changes before publishing: if Node.js 22 is available, `npm install && npm run build` in a temporary clone
and screenshot with the built-in browser (`npm run preview`); otherwise push and check the deployed site.

## 4 · Other languages
`zh`/`en` are wired through `src/lib/i18n.ts` (`Lang` type, `url()` prefix `/en`), `ui.json` keys,
`content.config.ts` enums, `twins.ts`, the `src/pages/en/` folder and `.pages.yml` selects. For a different pair
(e.g. `ms` + `en`), rename consistently in all of these and in post front-matter; for a single language, keep
`zh` as the internal code if that is less work but change every label. Rebuild and click through every page.

## 5 · Publish and connect
1. Commit with a clear message, `git push`.
2. Turn on Pages with Actions as the source:
   `gh api -X POST repos/<user>/<user>.github.io/pages -f build_type=workflow` (if it already exists, use `-X PUT`).
   Then `gh run watch` (or `gh run list`) until the deploy is green, and open `https://<user>.github.io`.
3. The user connects Pages CMS themselves: https://app.pagescms.org -> sign in with GitHub -> install the app for
   this repo only -> open the repo. Explain the sections (blog posts, quizzes, gallery, video series, did-you-know
   cards, about, site settings, site texts).
4. Optional auto-translate: the user runs `claude setup-token` and adds the token as the repo secret
   `CLAUDE_CODE_OAUTH_TOKEN` (Settings -> Secrets and variables -> Actions). Without it the workflow skips.

## 6 · Link it to the episode pipeline
- In `studio.toml`: `[paths] videos_json = "<site>/src/data/videos.json"` (dedup in new_episode.py) and
  `blog_images = "<site>/public/uploads/blog"`.
- In CHANNEL.md "Publishing": blog posts go to `<site>/src/content/posts/<date>-<slug>-<lang>.md`, quizzes to
  `src/content/quizzes/<slug>-<lang>.json`, covers to `public/uploads/`, and the front-matter fields from
  `src/content.config.ts`. Always `git pull` before writing and push only after the director approves.

## Later changes
For "change the font / colour / logo / menu / wording" requests: `git pull`, make the change from the table above,
show it (build preview or screenshots), push after a yes, wait for the green deploy, send the live link.
