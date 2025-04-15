import pandas as pd
import asyncio
from playwright.async_api import async_playwright
import time
import logging
import os
import subprocess
import sys

def ensure_playwright_browsers_installed():
    browser_path = "/home/appuser/.cache/ms-playwright"
    if not os.path.exists(browser_path):
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
        except Exception as e:
            import streamlit as st
            st.error(f"Could not install Chromium for Playwright: {e}")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_playwright_browsers():
    """Ensure Playwright browsers are installed, attempt to install if missing."""
    try:
        logger.info("Checking Playwright browser installation...")
        # Check if browser is already installed
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--help"],
            capture_output=True,
            text=True
        )
        
        if "chromium" not in result.stdout.lower():
            logger.info("Installing Playwright browsers...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True
            )
            logger.info("Playwright browsers installed successfully")
        else:
            logger.info("Playwright browsers already installed")
            
        return True
    except Exception as e:
        logger.error(f"Failed to install Playwright browsers: {e}")
        return False

async def get_companies_by_industry_async(industry, max_pages=5):
    """
    Fetch company data for a specific industry using Playwright for browser automation.
    This is more resilient against anti-scraping measures.
    
    Args:
        industry (str): Industry name to fetch data for
        max_pages (int): Maximum number of pages to fetch
        
    Returns:
        pd.DataFrame: DataFrame containing company data
    """
    industry_slug = f"ind_{industry.lower().replace(' ', '').replace('-','').replace('&','')}"
    base_url = f"https://finviz.com/screener.ashx?v=152&f={industry_slug}&c=1,2,6,7,8,10,11,75,21,82,39,40,41,63"
    
    all_data = []
    
    try:
        if not ensure_playwright_browsers():
            return pd.DataFrame({"Error": ["Failed to install Playwright browsers"]})
        
        async with async_playwright() as p:
            # Launch browser with stealth mode and cloud-friendly options
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            
            # Add stealth mode behavior
            await context.add_init_script("""
                // Overwrite the `navigator.webdriver` property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            
            page = await context.new_page()
            
            # Enable console logging
            page.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))
            
            for current_page in range(1, max_pages + 1):
                # Calculate the starting row for pagination
                start_row = (current_page - 1) * 20 + 1
                
                # Only add the row parameter if we're not on the first page
                current_url = base_url if current_page == 1 else f"{base_url}&r={start_row}"
                
                logger.info(f"Fetching page {current_page}, URL: {current_url}")
                
                # Navigate to the page
                await page.goto(current_url, timeout=60000)
                logger.info(f"Got page {current_url}")
                
                # Wait for the table to be visible
                try:
                    await page.wait_for_selector("table.screener_table", timeout=60000)
                except Exception as e:
                    logger.error(f"Table not found: {e}")
                    # Try to find any table that might contain the data
                    table_exists = await page.query_selector("table")
                    if not table_exists and current_page == 1:
                        return pd.DataFrame({"Error": ["Could not find data table in page"]})
                    elif not table_exists:
                        break
                
                # Extract the data from the table
                rows = await page.query_selector_all("table.screener_table tr:not(:first-child)")
                
                if not rows:
                    logger.info("No rows found, ending pagination")
                    break
                
                logger.info(f"Found {len(rows)} rows on page {current_page}")
                
                page_data = []
                for row in rows:
                    try:
                        # Get all cells in the row
                        cells = await row.query_selector_all("td")
                        
                        if len(cells) < 13:
                            continue
                        
                        # Extract text from each cell
                        ticker = await cells[0].text_content() if len(cells) > 0 else "Unknown"
                        company = await cells[1].text_content() if len(cells) > 1 else "Unknown"
                        marketcap = await cells[2].text_content() if len(cells) > 2 else "N/A"
                        pe = await cells[3].text_content() if len(cells) > 3 else "N/A"
                        fwd_pe = await cells[4].text_content() if len(cells) > 4 else "N/A"
                        ps = await cells[5].text_content() if len(cells) > 5 else "N/A"
                        pb = await cells[6].text_content() if len(cells) > 6 else "N/A"
                        dividend = await cells[7].text_content() if len(cells) > 7 else "N/A"
                        sales_growth = await cells[8].text_content() if len(cells) > 8 else "N/A"
                        sales = await cells[9].text_content() if len(cells) > 9 else "N/A"
                        gm = await cells[10].text_content() if len(cells) > 10 else "N/A"
                        opm = await cells[11].text_content() if len(cells) > 11 else "N/A"
                        pm = await cells[12].text_content() if len(cells) > 12 else "N/A"
                        avg_volume = await cells[13].text_content() if len(cells) > 13 else "N/A"
                        
                        # Clean up the text (strip whitespace)
                        ticker = ticker.strip()
                        company = company.strip()
                        marketcap = marketcap.strip()
                        pe = pe.strip()
                        fwd_pe = fwd_pe.strip()
                        ps = ps.strip()
                        pb = pb.strip()
                        dividend = dividend.strip()
                        sales_growth = sales_growth.strip()
                        sales = sales.strip()
                        gm = gm.strip()
                        opm = opm.strip()
                        pm = pm.strip()
                        avg_volume = avg_volume.strip()
                        
                        page_data.append({
                            "Ticker": ticker,
                            "Company": company,
                            "Market cap": marketcap,
                            "P/E": pe,
                            "Fwd P/E": fwd_pe,
                            "P/S": ps,
                            "P/B": pb,
                            "Dividend": dividend,
                            "Sales 5Y growth": sales_growth,
                            "Sales": sales,
                            "Gross Margin": gm,
                            "Operating Margin": opm,
                            "Profit Margin": pm,
                            "Avg. volume": avg_volume
                        })
                    except Exception as e:
                        logger.error(f"Error parsing row: {e}")
                        continue
                
                if not page_data:
                    logger.info("No data extracted from page, ending pagination")
                    break
                
                all_data.extend(page_data)
                
                # Check if there are more pages
                pagination = await page.query_selector("td#screener_pagination")
                if pagination:
                    # Look for links to pages beyond our current page
                    next_page_exists = False
                    page_links = await pagination.query_selector_all("a.screener-pages")
                    
                    # Get all page numbers
                    page_numbers = []
                    for link in page_links:
                        try:
                            text = await link.text_content()
                            page_numbers.append(text.strip())
                        except:
                            pass
                    
                    logger.info(f"Page numbers found: {page_numbers}")
                    
                    for link in page_links:
                        try:
                            text = await link.text_content()
                            page_num = int(text.strip())
                            if page_num > current_page:
                                next_page_exists = True
                                break
                        except:
                            # Skip links that don't have a page number
                            continue
                    
                    if not next_page_exists:
                        logger.info("No next page links found, ending pagination")
                        break
                else:
                    # No pagination found, so we're done
                    logger.info("No pagination element found, ending pagination")
                    break
                
                # Add a delay between pages to be polite
                await asyncio.sleep(2)
            
            await browser.close()
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return pd.DataFrame({"Error": [f"Unexpected error: {str(e)}"]})
    
    if not all_data:
        return pd.DataFrame({"Error": ["No data found for this industry"]})
    
    return pd.DataFrame(all_data)

def get_companies_by_industry(industry, max_pages=5):
    """
    Synchronous wrapper for the async function to fetch company data.
    
    Args:
        industry (str): Industry name to fetch data for
        max_pages (int): Maximum number of pages to fetch
        
    Returns:
        pd.DataFrame: DataFrame containing company data
    """
    return asyncio.run(get_companies_by_industry_async(industry, max_pages))
