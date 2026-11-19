# Security Incident Response — Nova Retail

## Severity classification
- SEV1: personal data breach or outage of critical systems. Immediate 24/7 response.
- SEV2: compromise of a privileged account or malware on an endpoint. Response within 1 hour.
- SEV3: targeted phishing with no confirmed compromise. Response within 4 hours.
- SEV4: low-criticality misconfiguration or vulnerability finding. Response within 5 days.

## Legal deadlines
Any breach affecting personal data must be notified to the supervisory authority
within a maximum of 72 hours from the moment it becomes known.

If there is a high risk to people's rights, affected individuals are also notified
without undue delay.

## Incident roles
- Incident Commander: coordinates response and communications.
- Security Analyst: investigates the cause and contains the incident.
- Comms Lead: manages internal and external communication.
- Legal & DPO: assesses regulatory obligations.

## Response workflow
1. Detection and logging of the incident in the ticketing system with a severity.
2. Containment: isolate devices, revoke credentials, block indicators.
3. Eradication: remove the root cause and apply patches.
4. Recovery: restore services and validate integrity.
5. Blameless postmortem within 5 working days.

## Communication
SEV1 incidents are reported to the executive committee within 30 minutes.
No public statements are made without approval from Comms and Legal.

## Evidence
Logs and evidence are preserved for at least 12 months.
Forensic images are stored encrypted with access restricted to 3 people.

## Drills
An incident drill runs every 6 months and a simulated phishing campaign every quarter.
The target is to keep the click rate below 5%.
