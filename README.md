# External Data Monitor - Baseline Project

Professional Python script that:
- Consumes public APIs (currently JSONPlaceholder /users)
- Validates data structure          
- Saves results to timestamped CSV and JSON files
- Logs detailed execution and errors

## Data Validation Logic

### Required fields
- id: Unique identifier required for tracking records
- name: Primary human-readable identifier
- email: Required for contact and system integrations
- phone: Required for potential outreach or CRM use

### Optional fields
- address: Not always needed depending on use case
- website: Informational only

### Discarded fields
- company: Removed to reduce noise and because it's not required for the current automation scope

Part of the **DEFINITIVE PLAN - Python + Automations (6 months)**  
Philosophy: Living systems that don't die.

## Installation
```bash
pip install pandas requests
## Dependencies
See `requirements.txt` for exact versions.

Install with:
```bash
pip install -r requirements.txt
