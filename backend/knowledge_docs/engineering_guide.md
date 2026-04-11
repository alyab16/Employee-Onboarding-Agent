# Engineering Onboarding Guide

## First 30 Days
- Complete all four onboarding training modules (T1–T4)
- Set up your local development environment using the Engineering Handbook (Confluence: ENG-SETUP)
- Shadow your team lead on at least 3 code reviews
- Pick up a "good first issue" from Jira within week 2
- Schedule 1:1s with your manager (weekly), tech lead (weekly), and 3 teammates (one-time intro)

## Development Environment
- Primary IDE: VS Code (company license via VS Code Server for remote dev)
- Monorepo managed with Nx; run `nx affected` to build/test only changed code
- All engineers use Mac or Linux; Windows requires WSL2
- Local secrets: use Doppler (never commit secrets to git)
- Docker Desktop required for service dependencies

## Git and Code Review Process
- Branch naming: `[type]/[ticket-id]-[short-description]` (e.g., `feat/ENG-123-add-login`)
- Commit messages follow Conventional Commits (feat, fix, chore, docs, refactor)
- All PRs require **2 approvals** before merge; at least 1 must be from a senior engineer (L4+)
- PRs should be small (<400 lines changed); large PRs require prior design doc
- Squash merge to main; delete branch after merge

## Testing Standards
- Unit test coverage minimum: 80% for new code
- Integration tests required for any new API endpoint
- E2E tests (Playwright) for critical user flows
- All tests must pass in CI (CircleCI) before review is requested

## Deployment Process
1. Merge to `main` triggers CI pipeline (lint, test, build)
2. Automatic deploy to staging; engineers validate within 24 hours
3. Production deploy: requires approval from your team lead + passes smoke tests
4. Rollback: `nx rollback [service]` — available to L3+ engineers
5. Post-deploy monitoring: check Datadog dashboard for 30 minutes

## On-Call Rotation (L3+)
- Engineers L3+ rotate on-call weekly; PagerDuty handles alerting
- On-call engineers must respond to P1 alerts within 15 minutes
- Runbooks for common incidents: Confluence > ENG > On-Call Runbooks
- On-call week is compensated with comp time (1 day per on-call week)

## Architecture Overview
- Backend: Python (FastAPI) microservices deployed on AWS ECS
- Frontend: Next.js on Vercel
- Data: PostgreSQL (RDS), Redis (ElastiCache), S3 for object storage
- Event streaming: Kafka
- CI/CD: CircleCI → ECR → ECS
- Infrastructure as code: Terraform (managed by L4+ / Platform team)

## Key Channels
- `#engineering`: General engineering discussion
- `#deploys`: Deployment notifications
- `#incidents`: Active incident coordination
- `#eng-random`: Off-topic banter
