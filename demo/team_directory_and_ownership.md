# Team Directory and Service Ownership — Game Studio

> Fictional demo document for Studio Agent Nexus. All people, emails, and assignments are
> invented and safe for public demonstration. Contacts use the reserved `example.invalid`
> domain.

This directory records who owns each backend service for Game Title and who is on call. Use
it to route questions and incidents to the most directly responsible person.

## Service ownership

| Service | Team | Owner | Contact |
|---------|------|-------|---------|
| Authoritative game servers | Backend | Mara Devlin | mara.devlin@example.invalid |
| Matchmaking & lobby | Backend | Tomas Reyes | tomas.reyes@example.invalid |
| Auth & identity linking | Backend | Priya Anand | priya.anand@example.invalid |
| Server fleet & autoscaling | Infra | Sven Holt | sven.holt@example.invalid |
| CI/CD & environments | Infra | Dana Okafor | dana.okafor@example.invalid |
| Event pipeline & warehouse | Data | Lena Fischer | lena.fischer@example.invalid |
| Analytics & metrics | Data | Hiro Tanaka | hiro.tanaka@example.invalid |
| QA & release validation | QA | Nadia Brooks | nadia.brooks@example.invalid |
| Live ops & production | Production | Omar Haddad | omar.haddad@example.invalid |

## On-call rotation (beta)

- **Primary on-call (backend/matchmaking):** Tomas Reyes
- **Primary on-call (infra/fleet):** Sven Holt
- **Primary on-call (data/pipeline):** Lena Fischer
- **Escalation / incident commander:** Omar Haddad

On-call rotates weekly. The incident commander owns severity calls and external
communication during an incident.

## Routing guidance

- Matchmaking wait times or queue issues → Tomas Reyes (Backend).
- Server capacity, autoscaling, or deploys → Sven Holt (Infra).
- Missing or delayed analytics events → Lena Fischer (Data).
- Retention or monetization dashboards → Hiro Tanaka (Data).
- Release sign-off and milestone status → Omar Haddad (Production).

## Fallback

If a request concerns private personal data, salaries, or any real individual, the answer
is not available in these fictional documents and the assistant should decline.
