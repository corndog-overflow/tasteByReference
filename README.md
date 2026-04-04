# taste by reference

A recipe discovery engine built on a multi-threaded ETL pipeline and a local LLM.

## but how?

Recipes are collected through a three-stage ETL pipeline running concurrently across threads:

- **Extract** — a Beautiful Soup web scraper pulls raw page text from recipe sites
- **Transform** — a local LLM parses the text into validated JSON
- **Load** — parsed records are written to a local SQLite database

Multi-threading keeps all three stages working continuously in parallel, so the scraper, LLM inference, and database writes never block each other.

## Interface

A PyQt desktop UI reads from the database and lets you browse recipes by filter.

<img width="719" height="407" alt="image" src="https://github.com/user-attachments/assets/9c1f2861-9991-4cec-986f-f77752af90c1" />
<img width="719" height="85" alt="image" src="https://github.com/user-attachments/assets/8f6ceefb-22df-4094-806b-48dc4b6670c1" />

