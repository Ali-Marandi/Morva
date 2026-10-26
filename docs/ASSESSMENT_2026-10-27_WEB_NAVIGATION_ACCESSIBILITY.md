# Engineering Assessment — Web Navigation Accessibility

**Date:** 2026-10-27  
**Repository:** `Ali-Marandi/Morva`  
**Branch:** `feat/web-accessible-responsive-navigation-20261025`  
**Pull request:** [#212 — accessible and responsive module navigation](https://github.com/Ali-Marandi/Morva/pull/212)  
**Baseline:** `main` at `528e946f743e4718225543e7a7883809bcd698ef`

## Scope and finding

The navigation tranche improves mobile discoverability and keyboard operation. A second-pass review identified a real accessibility regression in the skip-link destination: `#main-content:focus { outline: none; }` suppressed the visible focus indicator after the link moved focus to the main landmark.

## Implementation

- Replace the outline suppression with an explicit visible outline on the main landmark.
- Add focus-outline utilities to both layout variants, so the target keeps keyboard-focus styling across the module and standard layouts.
- Keep the skip link target keyboard-focusable with `tabIndex={-1}`.
- Add a regression test for the skip-link target and focus-indicator utility classes.
- Keep the change isolated from payroll rules, legal values, persistence schema and production controls.

## CI root-cause history

- The original navigation candidate `025a5b6499726b9a984532c3577f5783ff1b7512` had green checks before the new focus regression was added.
- First fix candidate `e6f6b17217b145fe9bec5c3f3c619be472d25c86` exposed a brittle test assumption: Vite's `?raw` stylesheet import did not expose the source text expected by the regex assertion.
- The subsequent `readFileSync` attempt on `5ee2c2510c6a0ed1ca12fa39120791a3d5d6f5dd` failed the strict TypeScript gate because the web TypeScript project has no Node type declarations.
- The current implementation avoids a new dependency and avoids the raw CSS test fixture. It places the focus utility classes on both main landmarks and asserts those classes in the regression test. The explicit CSS outline remains in place.
- Acceptance depends on the exact current PR head passing tests, type-check, lint, production build, M3.16 and the relevant CI gates. Do not use a prior candidate's green status as evidence for the latest commit.

## Architecture and safety review

The change is limited to frontend layout, CSS and frontend tests. It adds no database migration, API contract, payroll arithmetic, statutory-rate data, provider call, payment operation, credential, secret or production authorization. All production-readiness gates remain fail-closed.

## Acceptance criteria

- Skip link resolves to the main landmark and that landmark can receive focus.
- Keyboard focus remains visually apparent on both standard and module layouts.
- Mobile module navigation, route identity, Escape behavior and focus restoration remain covered by tests.
- Exact-current-head frontend tests, type-check, lint, build, M3.16 and relevant full CI complete successfully.
- The PR remains open and unmerged pending verification and normal repository review.
