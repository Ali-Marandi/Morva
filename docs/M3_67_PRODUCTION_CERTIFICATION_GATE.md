# M3.67 — Production Certification Evidence Gate

M3.67 is the final software-side boundary before a real production certification decision.

It requires a successfully independently verified M3.64/M3.65 readiness chain and a complete
M3.66 external-certification evidence registry covering exactly twelve roles:

- legal approval
- finance approval
- security assessment
- operations approval
- authoritative master data
- official adapters
- reconciliation evidence
- DR exercise
- load validation
- release certification
- publication evidence
- deployment validation

Every external evidence item must be bound to the exact repository and candidate SHA, be
marked verified, carry a digest and a timezone-aware verification time, and not be expired
at evaluation time.

M3.67 does not create, approve, invent or execute production certification. It emits only a
write-once, fingerprinted evidence gate. Real-world certification and production promotion
remain external actions.
