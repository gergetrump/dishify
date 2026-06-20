# Shared component recipes

Visual specs for components that exist on both web and iOS. Implement each platform natively; match these recipes, not each other's source code.

## PrimaryButton

| Property | Value |
|----------|-------|
| Background | `primaryAction` token |
| Label color | `primaryActionText` token |
| Corner radius | `radius.sm` (8) |
| Min height | 44pt / 44px |
| Horizontal padding | `spacing.lg` (24) |
| Font | `headline` typography scale |

Use for main CTAs: "Sign in", "Get recommendations", "Save preferences".

## Card

| Property | Value |
|----------|-------|
| Background | `surface` token |
| Border | 1px solid `border` token |
| Corner radius | `radius.md` (12) |
| Shadow | `elevation.card` (web); subtle shadow or border on iOS |
| Padding | `spacing.md` (16) |

Use for recipe results, preference groups, and form sections.

## TagChip

| Property | Value |
|----------|-------|
| Background | `background` token |
| Border | 1px solid `border` token |
| Corner radius | `radius.sm` (8) |
| Padding | `spacing.xs` vertical, `spacing.sm` horizontal |
| Font | `caption` typography scale |
| Selected state | `accent` border or fill at 15% opacity |

Use for diet/allergen tags and pantry ingredient pills.

## Screen layout

| Property | Value |
|----------|-------|
| Page background | `background` token |
| Content max width | `layout.contentMaxWidth` (720) on web |
| Screen padding | `spacing.md` (16) |
| Section spacing | `spacing.lg` (24) between major blocks |

## Async states (loading / error / empty)

| State | Treatment |
|-------|-----------|
| Loading | Centered spinner or progress; `textSecondary` caption |
| Error | `error` color for message; PrimaryButton to retry |
| Empty | `textSecondary` body copy; optional accent icon |

Every data-driven screen should handle all three states consistently.
