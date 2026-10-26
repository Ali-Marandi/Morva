# Web Navigation Accessibility Milestone

**Repository:** `Ali-Marandi/Morva`  
**Tracking PR:** [#212](https://github.com/Ali-Marandi/Morva/pull/212)  
**Branch:** `feat/web-accessible-responsive-navigation-20261025`  
**State:** In progress until exact-head CI and review gates finish

## Goal

Make module discovery and navigation usable on desktop and mobile, including keyboard users, while preserving existing application routing semantics.

## Implemented scope

- Complete mobile module catalogue.
- Expanded/controls semantics and current-module indication.
- Close navigation on Escape and restore focus to its trigger.
- Close navigation when keyboard focus leaves the header.
- Skip-to-main-content link and focusable main landmark.
- Visible focus outline on the skip-link destination, supported by explicit CSS and focus utility classes.
- Reduced-motion handling.
- Unique identifiers for nested module navigation routes and regression coverage.

## Validation gates

- [ ] Frontend unit/component tests pass on the exact current PR head.
- [x] TypeScript type check passed on the current code candidate observed during this execution; rerun remains required after every subsequent commit.
- [x] Lint passed on the current code candidate observed during this execution; rerun remains required after every subsequent commit.
- [x] Production web build passed on the current code candidate observed during this execution; rerun remains required after every subsequent commit.
- [ ] M3.16 self-service UX/reporting gate passes on the exact current PR head.
- [ ] Relevant full CI completes successfully on the exact current PR head.
- [ ] PR review and ancestry are rechecked before merge.

Prior failures are documented in the linked PR body and the engineering assessment. The candidate is not considered green merely because some individual checks have passed.

## Scope exclusions

No payroll arithmetic or legal-rule change, database migration, provider/payment execution, credential/secret change, production authorization or deployment is included.
