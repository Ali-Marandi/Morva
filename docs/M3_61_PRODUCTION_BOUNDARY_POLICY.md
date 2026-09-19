# M3.61 — Production Boundary Policy Scanner

## Purpose

M3.61 adds a deterministic static policy gate for the release and deployment-boundary
workflows introduced by M3.54 through M3.60.

## Rules

The scanner rejects direct Release creation, edit, delete or asset-upload commands;
git push/tag mutation; direct kubectl, Helm or Terraform deployment mutation; workflow
contents: write permissions; and private-key or common GitHub credential markers.

The result is a fingerprinted receipt and a write-once output.

## Safety boundary

M3.61 performs no deployment, publication or repository mutation. It is a static
verification gate only.
