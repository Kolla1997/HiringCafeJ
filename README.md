# 🚀 HiringCafe Job Scraper

Automated job scraper that monitors project management and coordination jobs from HiringCafe, saves them to Excel, and sends notifications to Telegram.

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Auto%20Update-blue)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 📋 Features

- **Automated Scraping** - Runs every 2 hours via GitHub Actions
- **Smart Duplicate Detection** - Only adds new jobs to the database
- **Excel Persistence** - Maintains a growing database of all jobs found
- **Telegram Notifications** - Sends job alerts directly to your Telegram
- **Comprehensive Data** - Extracts job titles, companies, locations, requirements, tech tools, compensation, and more
- **CST Timezone** - All dates formatted to Central Time with 12-hour format
- **Fallback URLs** - Uses company website when available, HiringCafe as backup

## 📊 Data Collected

| Field | Description |
|-------|-------------|
| Company Name | Name of the hiring company |
| Job Title | Position title |
| Job URL | Direct link to apply (company website or HiringCafe fallback) |
| URL Source | Indicates if URL is direct or fallback |
| Location | Job location (city, state, country) |
| YOE | Years of experience required |
| Work Type | Remote, Hybrid, or Onsite |
| Seniority Level | Entry Level, Mid Level, Senior |
| Compensation | Salary range (if available) |
| Requirements Summary | Key qualifications and requirements |
| Commitment | Full Time, Part Time, Contract |
| Company Website | Company's homepage |
| Company Description | Brief company overview |
| Tech Tools | Required technical tools/skills |
| Posting Date | Date posted (CST timezone) |
