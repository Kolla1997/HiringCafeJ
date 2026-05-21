import requests
import json
import pandas as pd
import time
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
import pytz

# Telegram Bot Configuration
# You need to create a bot with @BotFather on Telegram
TELEGRAM_BOT_TOKEN = "8804499203:AAExrSKL9EvdVZG5sXMcaGMoYrHpa6cmGwI"  # Replace with your bot token
TELEGRAM_CHAT_ID = "-1003716176854"      # Replace with your chat ID (can be channel ID or personal chat ID)

def send_telegram_message(message, parse_mode='HTML'):
    """Send a message to Telegram channel/chat"""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("⚠ Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✓ Telegram message sent successfully")
            return True
        else:
            print(f"✗ Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error sending Telegram message: {e}")
        return False

def send_telegram_job_summary(df_new_jobs, total_jobs_added, existing_count):
    """Send a summary of new jobs to Telegram"""
    if df_new_jobs.empty:
        message = "🔍 Job Search Update\n\n"
        message += "✓ No new jobs found. Excel is up to date!\n"
        message += f"📊 Total jobs in database: {existing_count}"
        send_telegram_message(message)
        return
    
    # Create summary message
    message = "🚀 NEW JOBS ALERT! 🚀\n\n"
    message += f"📈 Found {total_jobs_added} new job(s)!\n"
    message += f"📊 Total jobs in Excel: {existing_count + total_jobs_added}\n\n"

    
    # Add work type distribution
    work_types = df_new_jobs['Work Type'].value_counts()
    if not work_types.empty:
        message += "📍Work Types:\n"
        for work_type, count in work_types.items():
            message += f"  • {work_type}: {count}\n"
    message += f"\n⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}"
    
    send_telegram_message(message)

def send_telegram_job_details(job, job_number, total_jobs):
    """Send detailed job information to Telegram"""

    # Requirements summary
    requirements = job.get('Requirements Summary', 'N/A')
    if len(requirements) > 200:
        requirements = requirements[:197] + "..."

    # Tech tools
    tech_tools = job.get('Tech Tools', 'N/A')

    # Apply link
    job_url = job.get('Job URL', 'N/A')

    # Create clean Telegram message
    message = (
        f"🚀 Job Opportunity #{job_number}/{total_jobs}\n\n"

        f"💼 {job.get('Job Title', 'Not Found')}\n"
        f"🏢 {job.get('Company Name', 'Unknown Company')}\n"
        f"📍 {job.get('Location', 'Location not listed')}\n"
        f"🧑‍💻 Experience: {job.get('YOE', 'Not Found')}\n"
        f"🏠 Work Type: {job.get('Work Type', 'Not Found')}\n"
        f"💰 Compensation: {job.get('Compensation', 'Not Found')}\n"
        f"🕒 Posted: {job.get('Posting Date', 'Not Found')}\n\n"

        f"📝 Requirements:\n{requirements}\n\n"
    )

    # Add tech tools only if available
    if tech_tools != 'N/A' and tech_tools:
        message += f"🛠️ Tech Stack: {tech_tools}\n\n"

    # Add apply/company link
    if job_url != 'N/A' and job_url:
        message += f"🔗 Apply Here:\n{job_url}\n"
    else:
        message += (
            f"🌐 Company Website:\n"
            f"{job.get('Company Website', 'N/A')}\n"
        )

    message += "\n━━━━━━━━━━━━━━━━━━"

    send_telegram_message(message)

def send_telegram_batch_jobs(df_new_jobs, max_jobs_to_send=10):
    """Send batch of new jobs to Telegram (limited to avoid spam)"""
    if df_new_jobs.empty:
        return
    
    # Send summary first
    send_telegram_job_summary(df_new_jobs, len(df_new_jobs), 0)
    
    # Send individual job details (limit to avoid overwhelming)
    jobs_to_send = min(len(df_new_jobs), max_jobs_to_send)
    
    if jobs_to_send > 0:
        time.sleep(1)  # Small delay between summary and details
        
        for i in range(jobs_to_send):
            job = df_new_jobs.iloc[i].to_dict()
            send_telegram_job_details(job, i + 1, jobs_to_send)
            time.sleep(0.5)  # Delay between messages to avoid rate limiting
        
        if len(df_new_jobs) > max_jobs_to_send:
            remaining = len(df_new_jobs) - max_jobs_to_send
            message = f"\n📌 And {remaining} more job(s)! Check the Excel file for full details."
            send_telegram_message(message)

def scrape_hiring_cafe_page(url, page_num):
    """Scrape a single page of HiringCafe results"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    print(f"  Fetching page {page_num + 1}...")
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"    Failed with status code: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')
    
    if not script_tag:
        print(f"    Could not find __NEXT_DATA__ on page {page_num + 1}")
        return None
    
    data = json.loads(script_tag.string)
    
    # Extract jobs and pagination info
    jobs = data['props']['pageProps'].get('ssrHits', [])
    total_count = data['props']['pageProps'].get('ssrTotalCount', 0)
    is_last_page = data['props']['pageProps'].get('ssrIsLastPage', False)
    
    print(f"    Found {len(jobs)} jobs (Total so far: {total_count})")
    
    return {
        'jobs': jobs,
        'soup': soup,
        'total_count': total_count,
        'is_last_page': is_last_page
    }

def extract_fallback_url_from_soup(soup, job_title):
    """Extract HiringCafe job URL from HTML as fallback"""
    try:
        job_cards = soup.find_all('div', class_=re.compile(r'rounded-xl border border-gray-200'))
        
        for card in job_cards:
            title_element = card.find('span', class_=re.compile(r'font-bold text-start line-clamp'))
            if title_element and title_element.text.strip() == job_title:
                job_link = card.find('a', href=re.compile(r'/job/'))
                if job_link:
                    return "https://hiring.cafe" + job_link.get('href')
        
        return None
    except:
        return None

def format_to_cst(posting_date_str):
    """Convert posting date to CST time zone with 12-hour format"""
    if not posting_date_str or posting_date_str == 'N/A':
        return 'N/A'
    
    try:
        if '.' in posting_date_str:
            posting_date_str = posting_date_str.split('.')[0] + 'Z'
        
        utc_time = datetime.strptime(posting_date_str, '%Y-%m-%dT%H:%M:%SZ')
        utc_time = pytz.UTC.localize(utc_time)
        cst_timezone = pytz.timezone('US/Central')
        cst_time = utc_time.astimezone(cst_timezone)
        formatted_date = cst_time.strftime('%Y-%m-%d %I:%M:%S %p %Z')
        
        return formatted_date
    except Exception as e:
        try:
            if 'Z' in posting_date_str:
                clean_date = posting_date_str.replace('Z', '')
                if '.' in clean_date:
                    utc_time = datetime.strptime(clean_date, '%Y-%m-%dT%H:%M:%S.%f')
                else:
                    utc_time = datetime.strptime(clean_date, '%Y-%m-%dT%H:%M:%S')
                
                utc_time = pytz.UTC.localize(utc_time)
                cst_timezone = pytz.timezone('US/Central')
                cst_time = utc_time.astimezone(cst_timezone)
                formatted_date = cst_time.strftime('%Y-%m-%d %I:%M:%S %p %Z')
                return formatted_date
        except:
            pass
        
        return posting_date_str

def extract_job_data(job, soup=None):
    """Extract relevant information from a job object"""
    
    v5_data = job.get('v5_processed_job_data', {})
    enriched_company = job.get('enriched_company_data', {})
    job_info = job.get('job_information', {})
    
    # Try to get direct application URL first
    direct_url = job.get('apply_url', '')
    
    fallback_url = None
    if (not direct_url or direct_url == 'N/A' or 'adp.com' in direct_url or 'workforcenow' in direct_url) and soup:
        job_title = job_info.get('title', '')
        if job_title:
            fallback_url = extract_fallback_url_from_soup(soup, job_title)
    
    if direct_url and direct_url != 'N/A':
        final_job_url = direct_url
        url_source = "Direct Apply URL"
    elif fallback_url:
        final_job_url = fallback_url
        url_source = "HiringCafe Fallback URL"
    else:
        final_job_url = 'N/A'
        url_source = 'Not Available'
    
    compensation = []
    yearly_min = v5_data.get('yearly_min_compensation')
    yearly_max = v5_data.get('yearly_max_compensation')
    if yearly_min and yearly_max:
        compensation.append(f"${int(yearly_min/1000)}k-${int(yearly_max/1000)}k/yr")
    elif yearly_min:
        compensation.append(f"${int(yearly_min/1000)}k/yr")
    
    hourly_min = v5_data.get('hourly_min_compensation')
    hourly_max = v5_data.get('hourly_max_compensation')
    if hourly_min and hourly_max:
        compensation.append(f"${int(hourly_min)}-${int(hourly_max)}/hr")
    elif hourly_min:
        compensation.append(f"${int(hourly_min)}/hr")
    
    tech_tools = v5_data.get('technical_tools', [])
    if isinstance(tech_tools, list):
        tech_tools_str = ', '.join(tech_tools) if tech_tools else 'N/A'
    else:
        tech_tools_str = str(tech_tools) if tech_tools else 'N/A'
    
    yoe = v5_data.get('min_industry_and_role_yoe')
    yoe_str = f"{yoe}+ YOE" if yoe and yoe > 0 else "Entry Level (0+ YOE)" if yoe == 0 else "Not specified"
    
    company_website = enriched_company.get('homepage_uri', 'N/A')
    if company_website and company_website != 'N/A' and not company_website.startswith(('http://', 'https://')):
        company_website = f"https://{company_website}"
    
    posting_date_raw = v5_data.get('estimated_publish_date', 'N/A')
    formatted_posting_date = format_to_cst(posting_date_raw)
    
    return {
        'Company Name': enriched_company.get('name', 'N/A'),
        'Job Title': job_info.get('title', 'N/A'),
        'Job URL': final_job_url,
        'URL Source': url_source,
        'Location': v5_data.get('formatted_workplace_location', 'N/A'),
        'YOE': yoe_str,
        'Work Type': v5_data.get('workplace_type', 'Not specified'),
        'Seniority Level': v5_data.get('seniority_level', 'N/A'),
        'Compensation': ', '.join(compensation) if compensation else 'Not specified',
        'Requirements Summary': v5_data.get('requirements_summary', 'N/A'),
        'Commitment': ', '.join(v5_data.get('commitment', [])),
        'Company Website': company_website,
        'Company Description': enriched_company.get('tagline', 'N/A'),
        'Tech Tools': tech_tools_str,
        'Posting Date': formatted_posting_date
    }

def load_existing_jobs(excel_filename='hiring_cafe_jobs.xlsx'):
    """Load existing jobs from Excel file if it exists"""
    if os.path.exists(excel_filename):
        try:
            df_existing = pd.read_excel(excel_filename)
            print(f"✓ Loaded {len(df_existing)} existing jobs from '{excel_filename}'")
            return df_existing
        except Exception as e:
            print(f"⚠ Error loading existing Excel file: {e}")
            return pd.DataFrame()
    else:
        print(f"ℹ No existing Excel file found. Will create new one.")
        return pd.DataFrame()

def save_jobs_to_excel(df, excel_filename='hiring_cafe_jobs.xlsx'):
    """Save jobs DataFrame to Excel file"""
    try:
        df.to_excel(excel_filename, index=False)
        print(f"✓ Saved {len(df)} jobs to '{excel_filename}'")
        return True
    except Exception as e:
        print(f"✗ Error saving to Excel: {e}")
        print("  Make sure you have openpyxl installed: pip install openpyxl")
        return False

def get_job_unique_key(job_dict):
    """Create a unique key for each job to identify duplicates"""
    job_url = job_dict.get('Job URL', '')
    job_title = job_dict.get('Job Title', '')
    company_name = job_dict.get('Company Name', '')
    
    if job_url and job_url != 'N/A':
        return f"{job_url}_{job_title}"
    else:
        return f"{company_name}_{job_title}_{job_dict.get('Location', '')}"

def find_new_jobs(new_jobs_list, existing_df):
    """Find jobs that don't exist in the existing DataFrame"""
    if existing_df.empty:
        print("  No existing jobs. All new jobs will be added.")
        return new_jobs_list
    
    existing_keys = set()
    for _, row in existing_df.iterrows():
        key = get_job_unique_key(row.to_dict())
        existing_keys.add(key)
    
    new_jobs = []
    for job in new_jobs_list:
        key = get_job_unique_key(job)
        if key not in existing_keys:
            new_jobs.append(job)
    
    print(f"  Found {len(new_jobs)} new jobs out of {len(new_jobs_list)} total")
    return new_jobs

def scrape_all_pages(base_url, max_pages=None, delay_between_requests=1):
    """Scrape all pages of HiringCafe results"""
    
    all_jobs = []
    page_num = 0
    
    print("="*100)
    print("STARTING SCRAPE")
    print("="*100)
    
    while True:
        if '?' in base_url:
            url = f"{base_url}&page={page_num}"
        else:
            url = f"{base_url}?page={page_num}"
        
        result = scrape_hiring_cafe_page(url, page_num)
        
        if not result or not result['jobs']:
            print(f"\n✓ No more jobs found. Stopping at page {page_num + 1}")
            break
        
        for job in result['jobs']:
            all_jobs.append(extract_job_data(job, result.get('soup')))
        
        print(f"  Total jobs collected: {len(all_jobs)}")
        
        if result['is_last_page']:
            print(f"\n✓ Reached last page ({page_num + 1})")
            break
        
        if max_pages and page_num + 1 >= max_pages:
            print(f"\n✓ Reached max pages limit ({max_pages})")
            break
        
        page_num += 1
        
        if delay_between_requests > 0:
            time.sleep(delay_between_requests)
    
    return all_jobs

# Main execution
if __name__ == "__main__":
    excel_filename = 'hiring_cafe_jobs.xlsx'
    base_url = "https://hiring.cafe/?searchState=%7B%22locations%22%3A%5B%7B%22id%22%3A%22FxY1yZQBoEtHp_8UEq7V%22%2C%22types%22%3A%5B%22country%22%5D%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22formatted_address%22%3A%22United+States%22%2C%22population%22%3A327167434%2C%22workplace_types%22%3A%5B%5D%2C%22options%22%3A%7B%22flexible_regions%22%3A%5B%22anywhere_in_continent%22%2C%22anywhere_in_world%22%5D%7D%7D%5D%2C%22sortBy%22%3A%22date%22%2C%22dateFetchedPastNDays%22%3A2%2C%22seniorityLevel%22%3A%5B%22No+Prior+Experience+Required%22%2C%22Entry+Level%22%2C%22Mid+Level%22%5D%2C%22jobTitleQuery%22%3A%22%5C%22Project+manager%5C%22%2C+%5C%22Project+coordinator%5C%22%2C+%5C%22Implementation+coordinator%5C%22%2C+%5C%22Learning+and+development+manager%5C%22%2C+%5C%22Learning+and+development+coordinator%5C%22%2C+%5C%22Strategy+and+operations+analyst%5C%22%22%7D"

    send_telegram_message("🔄 Job Scraper Started new ession...")
    
    # Load existing jobs
    print("\n" + "="*100)
    print("LOADING EXISTING DATA")
    print("="*100)
    existing_df = load_existing_jobs(excel_filename)
    
    # Scrape all pages
    all_jobs = scrape_all_pages(base_url, max_pages=None, delay_between_requests=1)
    
    if not all_jobs:
        print("\n⚠ No jobs were scraped. Please check your connection or URL.")
        send_telegram_message("❌ **Job Scraper Error**\n\nNo jobs were found. Please check the connection or URL.")
        exit()
    
    # Find only new jobs
    print("\n" + "="*100)
    print("CHECKING FOR NEW JOBS")
    print("="*100)
    jobs_to_add = find_new_jobs(all_jobs, existing_df)
    
    if not jobs_to_add:
        print("\n✓ No new jobs found. Your Excel file is up to date!")
        send_telegram_message(f"✅ No New Jobs Found")
        
        if not existing_df.empty:
            print("\n" + "="*100)
            print("CURRENT Excel SUMMARY")
            print("="*100)
            print(f"Total Jobs in Excel: {len(existing_df)}")
        exit()
    
    # Create DataFrame with new jobs only
    new_jobs_only_df = pd.DataFrame(jobs_to_add)
    
    # Combine existing and new jobs
    if existing_df.empty:
        final_df = new_jobs_only_df
        print(f"\n✓ Created new database with {len(final_df)} jobs")
    else:
        final_df = pd.concat([existing_df, new_jobs_only_df], ignore_index=True)
        print(f"\n✓ Added {len(jobs_to_add)} new jobs to existing {len(existing_df)} jobs")
        print(f"  Total jobs now: {len(final_df)}")
    
    # Save to Excel
    print("\n" + "="*100)
    print("SAVING TO EXCEL")
    print("="*100)
    if save_jobs_to_excel(final_df, excel_filename):
        # Send new jobs to Telegram
        print("\n" + "="*100)
        print("SENDING TO TELEGRAM")
        print("="*100)
        send_telegram_batch_jobs(new_jobs_only_df, max_jobs_to_send=1000)
        
        # Display summary
        print("\n" + "="*100)
        print("NEW JOBS ADDED SUMMARY")
        print("="*100)
        print(f"Number of new jobs added: {len(jobs_to_add)}")
        
        if len(jobs_to_add) > 0:
            print("\nFirst 5 new jobs added:")
            for i in range(min(5, len(jobs_to_add))):
                job = jobs_to_add[i]
                print(f"\n  {i+1}. {job['Job Title']}")
                print(f"     Company: {job['Company Name']}")
                print(f"     Location: {job['Location']}")
        
        print("\n" + "="*100)
        print("FINAL DATABASE STATISTICS")
        print("="*100)
        print(f"Total Jobs: {len(final_df)}")
        print(f"Unique Companies: {final_df['Company Name'].nunique()}")
