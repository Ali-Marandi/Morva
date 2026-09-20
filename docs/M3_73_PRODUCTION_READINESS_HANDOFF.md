# M3.73 — Production Readiness Handoff Manifest

M3.73 defines a deterministic, write-once manifest for transferring production-readiness
evidence between controlled parties without trusting filenames or implicit contents.

Each source is bound by relative path, SHA-256 and exact byte size. Verification rejects
tampered files, missing files, unexpected extra files, traversal paths and private-key or
credential markers.

The handoff is evidence transport only. It is not a production certification, approval,
publication, promotion or deployment mechanism.
