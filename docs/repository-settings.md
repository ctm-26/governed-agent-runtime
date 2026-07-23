# Recommended GitHub Repository Settings

Repository: `ctm-26/governed-agent-runtime` initially, with transfer to an organization after naming and governance review.

## General

- Visibility: public
- Default branch: `main`
- Issues: enabled
- Discussions: optional during early research
- Wiki: disabled; documentation remains versioned in the repository
- Projects: optional
- Automatically delete head branches: enabled
- Merge method: squash merge only during pre-1.0

## Security

- Private vulnerability reporting: enabled
- Dependency graph: enabled
- Dependabot alerts: enabled
- Dependabot security updates: enabled
- Secret scanning and push protection: enabled where available
- Code scanning: enable when executable code is added
- GitHub Actions permissions: read-only by default; grant write permissions per workflow only

## `main` ruleset, solo-maintainer stage

- Require a pull request before merging
- Require status checks after CI exists
- Require conversation resolution
- Block force pushes
- Block branch deletion
- Require linear history
- Required approvals: 0 until an independent maintainer exists
- Allow administrator bypass only for documented emergencies

Requiring one external approval while there is only one maintainer would deadlock the repository. Increase required approvals to one as soon as a second active maintainer exists.

## Later hardening

- Require signed commits or verified signatures after contributor tooling is documented
- Require CODEOWNERS review for specification, policy, and security paths
- Add release provenance and attestations
- Pin GitHub Actions by full commit digest
- Adopt OpenSSF Scorecard and SLSA controls incrementally
