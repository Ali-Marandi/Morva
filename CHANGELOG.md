# Changelog

All notable Morva implementation and distribution changes are recorded here.

## 1.0.0 — 2026-09-04 Enterprise Web Platform Release

### Web Platform (New)
- **World-class web platform redesign** - React 18 + TypeScript + Tailwind CSS
- **14 components and 6 feature pages** implemented:
  - Dashboard with KPIs, charts, and activity feed
  - Employees management with filter and status tracking
  - Payroll processing with visualization and controls
  - Approvals workflow with multi-status filtering
  - Reports generation and distribution
  - Settings and configuration management
- **7 routes** with React Router v6 navigation
- **Responsive design** (Mobile First: 320px, 768px, 1024px+)
- **WCAG AA accessibility** compliance
- **Bundle optimization** with Vite, code splitting, and manual chunking
- **GitHub Pages deployment** ready with /Morva/ base path
- **Production build** validated: ~566 KB (gzip: ~159 KB)
- **Comprehensive documentation**:
  - BUILD_GUIDE.md with deployment instructions
  - PRODUCTION_CERTIFICATION_GATES.md with 10 certification gates
  - NEXT_PHASE_ROADMAP.md with 10-phase implementation roadmap

### Backend & Core (Existing)
- Enterprise payroll hardening consolidated the canonical payroll lifecycle
- Fail-closed production boundaries for legal rules and external payments
- Durable audit chain, rule evidence, sensitive-field protections
- Hierarchical authorization and integration messaging foundations
- Employee payroll artifacts with payslip provenance and replay capabilities
- Production calculation remains blocked without required certifications

### CI/CD & Deployment
- GitHub Actions workflows validated (`.github/workflows/ci.yml`)
- Web Pages deployment pipeline active (`.github/workflows/web-pages.yml`)
- npm dependencies updated and audited
- Production build configuration optimized

### Documentation
- Updated README.md with web platform details
- 10 production certification gates documented
- 10-phase technical roadmap for backend integration
- FINAL_COMPLETION_SUMMARY.md with implementation metrics

### Distribution status

- **Package version:** `1.0.0`
- **Canonical branch:** `main`
- **GitHub Pages deployment:** Active at `https://ali-marandi.github.io/Morva/`
- **Web platform status:** ✅ Production-ready
- **Backend status:** Enterprise validation candidate
- **Release tag:** `v1.0.0`

> Software versioning and distribution do not constitute authorization for real payroll or payment release. See PRODUCTION_CERTIFICATION_GATES.md for required evidence.

## Previous Releases

### 1.0.0 — Enterprise validation lineage (Core implementation)

- Enterprise payroll hardening consolidated the canonical payroll lifecycle and fail-closed production boundaries.
- PostgreSQL migrations became part of the CI validation path.
- Durable audit chain, rule evidence, sensitive-field protections, hierarchical authorization and integration messaging foundations are maintained.
- Employee payroll artifacts, payslip provenance and deterministic historical replay are persisted.
- Production calculation remains blocked without approved legal Rule Sets, authoritative source data and required external certifications.
