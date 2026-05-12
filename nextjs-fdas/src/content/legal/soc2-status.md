# SOC 2 Type II Status

**Last updated:** May 9, 2026

## Plain statement, up front

AceAnalytics.dev is **not currently SOC 2 Type II certified**, and no SOC 2 Type II audit is presently underway. Where the AceAnalytics marketing surface references "SOC 2 Type II," it refers to the design posture of the tooling - the controls a SOC 2 Type II audit would test for - not to a completed attestation. No SOC 2 report exists for AceAnalytics.dev or any of its tools as of the date above.

This site is operated as a personal portfolio and demonstration project by an individual based in Birmingham, Alabama. A formal Type II audit is a meaningful undertaking and is appropriate only where there is a commercial customer base that warrants it. AceAnalytics.dev does not have one.

## What SOC 2 Type II actually is, briefly

SOC 2 is an auditing framework developed by the AICPA that evaluates a service organization's controls against five Trust Services Criteria: **security**, **availability**, **processing integrity**, **confidentiality**, and **privacy**. A **Type I** report describes the design of those controls at a point in time. A **Type II** report tests whether those controls operated effectively over a period - typically six to twelve months. A SOC 2 Type II attestation is issued by an independent licensed CPA firm, not self-certified.

Treat any vendor claim of "SOC 2 Type II" as unverified until you have seen the actual report (or a current bridge letter) from the issuing audit firm.

## Aspirational commitment and roadmap

If AceAnalytics.dev or any of its tools were ever to be offered commercially to financial-services customers, a SOC 2 Type II program would be a baseline expectation, not an upsell. The intended path would be:

1. **Foundational hardening (months 0-2).** Documented control objectives across the security, availability, and confidentiality criteria; SSO and MFA on every administrative surface; least-privilege IAM with quarterly access reviews; encrypted transit and at-rest storage; centralized audit logging with tamper-evident retention; backup and restore tested to a documented RTO/RPO.
2. **Policies and people (months 1-3).** Written information-security, incident-response, vendor-management, change-management, and acceptable-use policies. Security training and confidentiality acknowledgments for any contractor or collaborator with system access. A documented risk register reviewed quarterly.
3. **Readiness assessment and Type I (months 3-6).** Engage a qualified CPA firm (the same firm that would conduct the Type II) to run a readiness review, remediate gaps, and issue a Type I report describing the design of the controls.
4. **Audit window and Type II (months 6-18).** Operate the controls through an audit window of six to twelve months, with continuous evidence collection (typically through a compliance-automation platform such as Vanta, Drata, or Secureframe). The CPA firm tests operating effectiveness and issues the Type II report at the end of the window.
5. **Annual renewal.** Type II reports cover discrete windows; an annual renewal cadence with a bridge letter for the gap between report periods is the standard pattern.

The Operator's familiarity with this framework, the underlying control objectives, and the practical realities of running it inside a regulated financial institution is part of what this site is intended to demonstrate.

## Current security posture (no audit, but here is what is in place)

Even as a hobby site, the following baseline measures apply:

- **Transport security.** TLS on every endpoint; HSTS enabled; modern ciphers only.
- **Authentication.** Administrative access protected by SSO with multi-factor authentication. No shared accounts.
- **Data minimization.** Demonstration uploads are processed transiently and deleted by default within twenty-four hours. The site does not retain customer financial data.
- **Logging.** Application and access logs are retained for a limited period for debugging and abuse detection. Access to logs is restricted to the Operator.
- **Secrets management.** Credentials are kept in a managed secrets store; no secrets are committed to source control.
- **Backups.** Site content and configuration are version-controlled and backed up.
- **Incident handling.** A material security incident affecting any individual whose information was provided to the site would be communicated to that individual within a reasonable time, generally not to exceed seventy-two hours after confirmation.

These are reasonable practices for a personal site - they are not, and are not represented to be, a substitute for an audited SOC 2 program.

## Reporting a security concern

Suspected vulnerabilities or security concerns should be reported to **security@aceanalytics.dev**. Reports made in good faith will be acknowledged and investigated; the Operator will not pursue legal action against good-faith researchers who follow responsible-disclosure norms.

## Contact

For questions about this page, the security posture of the site, or what a future formal compliance program would look like, contact **hello@aceanalytics.dev**.
