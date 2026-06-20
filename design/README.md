# Dishify design system

Shared visual language for the **React web app** and **iOS app**. Both clients should feel like the same product — same colors, spacing rhythm, and component styling — while still using **platform-native** navigation and controls.

This folder is the contract. Feature code on either platform should consume tokens from here, not invent one-off hex values.

---

## Why this exists

React and SwiftUI cannot share UI components. What they *can* share is:

- **Semantic color names** (`background`, `accent`, `error`, …)
- **Spacing and radius scales**
- **Typography scale** (size/weight names, not identical fonts)
- **Component recipes** (how a button or card should look)

Companies at scale solve this with a **design token file** (often JSON) that feeds CSS on web and Swift/asset catalogs on iOS. Dishify uses a lightweight version of that pattern.

**Goal:** brand consistency, not pixel-perfect clones. iOS keeps `NavigationStack`, SF Symbols, and 44pt tap targets; web keeps responsive layout, hover, and focus rings.

---

## Files in this folder

| File | Purpose |
|------|---------|
| [`tokens.json`](tokens.json) | **Source of truth** — edit colors/spacing here first |
| [`theme.css`](theme.css) | Web CSS custom properties (mirrors `tokens.json`) |
| [`components.md`](components.md) | Shared component specs (PrimaryButton, Card, TagChip, async states) |
| This README | Concept, usage, and **agent instructions** |

---

## Token values

Canonical values (keep `tokens.json`, `theme.css`, and iOS asset colors in sync):

### Colors

| Token | Light | Dark |
|-------|-------|------|
| `background` | `#f6f3ee` | `#1a1917` |
| `surface` | `#ffffff` | `#262522` |
| `textPrimary` | `#222222` | `#f6f3ee` |
| `textSecondary` | `#6b6560` | `#a8a29e` |
| `accent` | `#f28c66` | `#f28c66` |
| `primaryAction` | `#2b2a25` | `#f6f3ee` |
| `primaryActionText` | `#ffffff` | `#2b2a25` |
| `border` | `#e4ded7` | `#3d3a36` |
| `success` | `#2d6a4f` | `#52b788` |
| `error` | `#b42318` | `#f87171` |

### Spacing, radius, layout

| Category | Values |
|----------|--------|
| Spacing | `xs` 4, `sm` 8, `md` 16, `lg` 24, `xl` 32 |
| Radius | `sm` 8, `md` 12, `lg` 16 |
| Typography | `title` 28/bold, `headline` 18/semibold, `body` 16/regular, `caption` 13/regular |
| Elevation | Card shadow: `0 2px 8px rgba(0, 0, 0, 0.08)` |
| Layout | Min tap target 44; web content max width 720 |

---

## How to use — web (React / Vite)

1. Import the theme once at app root:

   ```tsx
   import "../../design/theme.css";
   ```

2. Use CSS variables in components — **never raw hex in feature views**:

   ```css
   .card {
     background: var(--color-surface);
     border: 1px solid var(--color-border);
     border-radius: var(--radius-md);
     padding: var(--spacing-md);
     box-shadow: var(--shadow-card);
   }

   .primary-button {
     background: var(--color-primary-action);
     color: var(--color-primary-action-text);
     border-radius: var(--radius-sm);
     min-height: var(--layout-min-tap-target);
     padding: 0 var(--spacing-lg);
     font-size: var(--font-size-headline);
     font-weight: var(--font-weight-headline);
   }
   ```

3. Follow recipes in [`components.md`](components.md) for shared UI patterns.

4. Dark mode is handled by `prefers-color-scheme` in `theme.css` — no extra JS required for defaults.

---

## How to use — iOS (SwiftUI)

1. Semantic colors live in `ios/Dishify/Assets.xcassets/` as named color sets (`Background`, `Surface`, `TextPrimary`, …) with **light and dark** appearances.

2. Access them through `ios/Dishify/Core/Theme.swift`:

   ```swift
   Text("Dishify")
       .font(Theme.Typography.title)
       .foregroundStyle(Theme.Colors.textPrimary)

   VStack(spacing: Theme.Spacing.md) { … }
       .padding(Theme.Spacing.md)
       .background(Theme.Colors.background)
   ```

3. Global tint stays on `AccentColor` in the asset catalog (matches `accent` token).

4. **Do not** use `.foregroundStyle(.secondary)` for branded secondary text when `Theme.Colors.textSecondary` is intended — system secondary grays differ slightly from our token.

5. See [`components.md`](components.md) for button/card/chip specs. Use `Theme.Spacing` and `Theme.Radius` for padding and corner radius.

---

## Changing the design

1. Edit [`tokens.json`](tokens.json).
2. Sync [`theme.css`](theme.css) (CSS variables under `:root` and `@media (prefers-color-scheme: dark)`).
3. Sync iOS color sets in `Assets.xcassets` (light + dark entries per semantic color).
4. Update the [Token values](#token-values) table in this README if you change defaults.
5. Do **not** change colors only in a feature view or screen.

Optional later: add [Style Dictionary](https://amzn.github.io/style_dictionary/) to generate `theme.css` and Xcode colors from `tokens.json` automatically.

---

## Rules for humans and agents

### Do

- Read this README and `tokens.json` before building any UI.
- Use semantic token names (`Theme.Colors.surface`, `var(--color-surface)`).
- Implement shared components per [`components.md`](components.md).
- Keep platform-native patterns (iOS navigation, web focus/hover).
- Handle loading, error, and empty states consistently on every data screen.

### Do not

- Hard-code hex/rgb in feature code (`#f28c66`, `Color(red:…)` outside `Theme.swift`).
- Introduce a second palette in one platform only.
- Copy React component structure into SwiftUI (or vice versa) — copy the **recipe**, not the code.
- Skip dark-mode variants when adding a new semantic color.

---

## Agent implementation guide

Paste the relevant block at the start of a Cursor (or other) agent session when working on UI.

### Any UI task

```
Read design/README.md, design/tokens.json, and design/components.md before editing UI.
Use semantic design tokens only — no raw hex in feature views.
If you change a color or spacing value, update tokens.json first and sync theme.css + iOS Assets.
```

### Web agent scope

```
SCOPE: Only edit files under frontend/ (when it exists) and design/.
For styling: import design/theme.css and use CSS variables (--color-*, --spacing-*, --radius-*).
Follow design/components.md for PrimaryButton, Card, TagChip, and async states.
Do NOT edit backend/, keycloak/, or docs/API.md unless explicitly asked.
```

### iOS agent scope

```
SCOPE: Only edit files under ios/.
For styling: use Theme.* from ios/Dishify/Core/Theme.swift and semantic colors in Assets.xcassets.
Follow design/components.md and design/tokens.json. No raw hex in Features/ views.
Read docs/API.md for networking; do not change the API contract.
Prefer one ios/IMPLEMENTATION_PLAN.md step per session.
```

### Creating the token files (bootstrap)

If `design/tokens.json`, `design/theme.css`, or `ios/Dishify/Core/Theme.swift` are missing, create them from the [Token values](#token-values) section and the iOS/web usage examples above. Add these iOS asset color sets with light **and** dark appearances:

`Background`, `Surface`, `TextPrimary`, `TextSecondary`, `PrimaryAction`, `PrimaryActionText`, `Border`, `Success`, `Error` (plus existing `AccentColor`).

Wire `Theme.swift` into the Xcode project and use it in new screens from Step 5 (Auth) onward in [`ios/IMPLEMENTATION_PLAN.md`](../ios/IMPLEMENTATION_PLAN.md).

---

## What “same look” does not mean

| Same across platforms | Allowed to differ |
|----------------------|-------------------|
| Brand colors, spacing, card/button shape | Font family (SF Pro vs system web stack) |
| Content hierarchy and screen flow | Navigation chrome (tabs vs header) |
| Loading / error / empty treatment | Gestures, hover, keyboard focus |
| Component recipes in `components.md` | Exact shadow rendering |

Users should recognize Dishify on both platforms without the apps feeling like a website crammed into iOS.

---

## Related docs

- [`components.md`](components.md) — shared component recipes
- [`ios/IMPLEMENTATION_PLAN.md`](../ios/IMPLEMENTATION_PLAN.md) — iOS build steps (Step 11 = polish + a11y)
- [`TODO`](../TODO) — web frontend Phase 3 (Vite + React)
