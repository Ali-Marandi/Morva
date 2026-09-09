# Rule Activation Provenance Contract

A rule pack may be activated only when the selected components have complete, immutable provenance.

For every selected component, activation requires:

1. The Rule Pack is `approved` or `published` and carries immutable rules/source hashes.
2. Matching rule evidence exists for the component and is `approved` or `published`.
3. The evidence contains legal issuer, article, population scope, source hash, and regression-suite hash.
4. The evidence has a reviewer and approver, and they are distinct actors.
5. The evidence has an approval timestamp.
6. The referenced legal source exists and is `approved` or `published`.
7. The legal source document hash exactly matches the evidence source hash.

These checks are deliberately structural. They do not invent statutory rates, exemptions, or population-specific treatments. A missing or inconsistent legal record blocks activation rather than silently choosing a default.
