import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_companies_by_industry_bs(industry, max_pages=5):
    industry_slug = f"ind_{industry.lower().replace(' ', '').replace('-', '').replace('&', '')}"
    base_url = f"https://finviz.com/screener.ashx?v=152&f={industry_slug}&c=1,2,6,7,8,10,11,75,21,82,39,40,41,63"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }

    all_data = []
    
    for page in range(max_pages):
        start_row = page * 20 + 1
        url = f"{base_url}&r={start_row}" if page > 0 else base_url
        res = requests.get(url, headers=headers)
        
        if res.status_code != 200:
            break

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="screener_table")
        if not table:
            break
        
        rows = table.find_all("tr")[1:]  # Skip header
        if not rows:
            break
        
        for row in rows:
            cols = row.find_all("td")
            logger.info(f"Got cols: {cols}")
            if len(cols) < 15:
                continue
            
            all_data.append({
                "Ticker": cols[1].text.strip(),
                "Company": cols[2].text.strip(),
                "Market cap": cols[3].text.strip(),
                "P/E": cols[4].text.strip(),
                "Fwd P/E": cols[5].text.strip(),
                "P/S": cols[6].text.strip(),
                "P/B": cols[7].text.strip(),
                "Dividend": cols[8].text.strip(),
                "Sales 5Y growth": cols[9].text.strip(),
                "Sales": cols[10].text.strip(),
                "Gross Margin": cols[11].text.strip(),
                "Operating Margin": cols[12].text.strip(),
                "Profit Margin": cols[13].text.strip(),
                "Avg. volume": cols[14].text.strip()
            })

        time.sleep(1)  # Be polite

    return pd.DataFrame(all_data)
