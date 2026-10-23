# SMART Mock Interview — Design System (Stage 9A.3)

Derived with the UI/UX Pro Max workflow (`search.py --design-system`, plus focused `ux`, `typography`, `style`, `landing` searches) and adapted to this project's constraints (Flask, no CDN, strict CSP, no build step). Source of truth for the implementation is `src/demo/static/app.css`.

## Direction
- **Style:** Dark Mode (OLED) with glass used only for navigation and sticky action bars (skill rule `blur-purpose`). One primary CTA per view (`primary-action`).
- **Pattern:** Hero (animated product preview) → quick-start cards → personal practice → how it works. No percentages on the home page.
- **Navigation:** floating top bar on desktop with a sliding active indicator; fixed bottom tab bar (4 items, icon + label) below 820px; the interview page hides primary navigation (distraction-free) and offers "Leave interview (saved)".

## Tokens
| Role | Value |
|---|---|
| Background | `#05070e` (OLED black-navy) with soft aurora lighting |
| Surface | `rgba(255,255,255,.045)` + 1px `rgba(255,255,255,.09)` border |
| Primary / CTA | `#22c55e` → `#4ade80` gradient, text `#04150b` (≥ 8:1) |
| Experimental / difficulty | amber `#f6c869` (dashed borders = experimental) |
| Secondary light | violet `#a78bfa` (code reading), sky `#7dd3fc` (links) |
| Text | `#e9eefb`, muted `#9aa8c2` (≥ 4.5:1 on all surfaces) |
Spacing 4/8/12/16/24/32/48/72 · radii 10/16/24/pill · type: system Segoe UI Variable (no network fonts), display 700–760 with −0.03 to −0.045em tracking, body 16.5/1.6, labels 12.5px caps +0.14em.

## Motion
Entrances once (rise/sweep/draw, stagger 50ms); hero preview types its sample answer once; pointer tilt on fine pointers only; three slow transform-only aurora drifts (compositor). Everything off under `prefers-reduced-motion`. Never on the interview page except the progress sweep.

## Meaning of colour (never colour alone — always a text label)
Green = default similarity layer · amber dashed = experimental concept check · violet dashed = code reading (text only, never executed).
