import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# Alpha Vantage API key (not used yet but kept for future use)
alpha_vantage_api = "FX998CWBI5L51900"

@st.cache_data
def get_sector_data():
    try:
        url = "https://finviz.com/groups.ashx?g=industry&v=152&o=name"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://finviz.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Add a delay to avoid being blocked
        time.sleep(1)
        
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            st.error(f"Failed to fetch data: HTTP {res.status_code}")
            return pd.DataFrame({"Error": ["Failed to fetch data"]})
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Try to find the table - first attempt with class="table-light"
        table = soup.find("table", class_="table-light")
        
        # If that fails, try other common table classes or attributes
        if table is None:
            # Try finding any table with sector data
            tables = soup.find_all("table")
            for t in tables:
                if t.find("td", text=lambda x: x and "Technology" in x):
                    table = t
                    break
        
        # If we still don't have a table, return empty DataFrame with error
        if table is None:
            st.error("Could not find sector data table on the page")
            return pd.DataFrame({"Error": ["Table not found on page"]})
        
        rows = table.find_all("tr")[1:]  # Skip header row
        
        data = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5: 
                continue
            
            # Try to extract data safely
            try:
                sector = cols[1].text.strip() if len(cols) > 1 else "Unknown"
                pe = cols[2].text.strip() if len(cols) > 2 else "N/A"
                ps = cols[3].text.strip() if len(cols) > 3 else "N/A"
                pb = cols[4].text.strip() if len(cols) > 4 else "N/A"
                div = cols[5].text.strip() if len(cols) > 5 else "N/A"
                
                data.append({
                    "Sector": sector,
                    "P/E": pe,
                    "P/S": ps,
                    "P/B": pb,
                    "Dividend": div,
                })
            except Exception as e:
                st.warning(f"Error parsing row: {e}")
                continue
                
        if not data:
            return pd.DataFrame({"Error": ["No data found in table"]})
            
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Error fetching sector data: {e}")
        return pd.DataFrame({"Error": [str(e)]})
        
def get_companies_by_industry(industry):
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd

    industry_slug = f"ind_{industry.lower().replace(' ', '')}"
    url = f"https://finviz.com/screener.ashx?v=152&f={industry_slug}&c=1,2,7,8,9,10,75"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    print("URL", url)

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return pd.DataFrame({"Error": [f"Failed to fetch Finviz page (HTTP {res.status_code})"]})

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", class_="screener_table")
    if table is None:
        return pd.DataFrame({"Error": ["❌ Could not find screener_table in HTML."]})

    rows = table.find_all("tr")[1:]  # skip header

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        try:
            print("Should be ticker: ", cols[0].text.strip())
            print("Should be company: ", cols[1].text.strip())
            print("Should be p/e: ", cols[2].text.strip())
            print("Should be fwd p/e: ", cols[3].text.strip())
            print("Should be peg: ", cols[4].text.strip())
            print("Should be p/s: ", cols[5].text.strip())
            print("Should be dividend: ", cols[6].text.strip())
            data.append({
                "Ticker": cols[0].text.strip(),
                "Company": cols[1].text.strip(),
                "P/E": cols[2].text.strip(),
                "Fwd P/E": cols[3].text.strip(),
                "PEG": cols[4].text.strip(),
                "P/S": cols[5].text.strip(),
                "Dividend": cols[6].text.strip(),
            })
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue

    return pd.DataFrame(data)




# Main app
st.title("US Stock Market Sector Multiples")
st.write("This app shows valuation multiples for different market sectors.")
st.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Add a loading spinner
with st.spinner("Fetching sector data..."):
    df = get_sector_data()

# Check if we got valid data
if "Error" in df.columns:
    st.error("Failed to retrieve sector data. Please try again later.")
else:
    # Display the data
    st.dataframe(df.reset_index(drop=True), use_container_width=True, hide_index=True)
    
    # Optional: Add filtering
    if not df.empty:
        sector_filter = st.selectbox("Filter by Sector", ["All"] + df["Sector"].tolist())
        if sector_filter != "All":
            filtered_df = df[df["Sector"] == sector_filter]
            st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True, hide_index=True)
        
        # Add visualization section
        st.subheader("Sector Comparison Visualization")
        
        # Convert metrics to numeric values for plotting
        numeric_df = df.copy()
        for col in ["P/E", "P/S", "P/B", "Dividend"]:
            numeric_df[col] = (
                numeric_df[col]
                .str.replace("B", "", regex=False)
                .str.replace("M", "", regex=False)
                .str.replace("%", "", regex=False)
                .replace("N/A", None)
            )
            numeric_df[col] = pd.to_numeric(numeric_df[col], errors="coerce")

        # Create two columns for the inputs
        col1, col2 = st.columns(2)
        
        with col1:
            # Multi-select for sectors
            sectors_to_compare = st.multiselect(
                "Select Sectors to Compare",
                options=numeric_df["Sector"].tolist(),
                default=[]
            )
        
        with col2:
            # Select metric to visualize
            metric_to_plot = st.selectbox("Select Metric to Compare", ["P/E", "P/S", "P/B", "Dividend"])
        
        # Create bar chart for selected sectors and metric
        if sectors_to_compare:
            # Filter the dataframe for selected sectors
            comparison_df = numeric_df[numeric_df["Sector"].isin(sectors_to_compare)]
            
            if not comparison_df.empty and not comparison_df[metric_to_plot].isna().all():
                # Sort by the selected metric for better visualization
                comparison_df = comparison_df.sort_values(by=metric_to_plot, ascending=False)
                
                # Create the bar chart
                st.bar_chart(
                    data=comparison_df.set_index("Sector")[metric_to_plot],
                    use_container_width=True
                )
                
                # Display a table with the values for reference
                st.write("Comparison Values:")
                comparison_table = comparison_df[["Sector", metric_to_plot]].copy()
                comparison_table[metric_to_plot] = comparison_table[metric_to_plot].round(2)
                st.dataframe(comparison_table.reset_index(drop=True), use_container_width=True, hide_index=True)
                
                # Show top companies for each selected sector
                st.subheader("Top Companies in Selected Sectors")
                
                # Create tabs for each selected sector
                if len(sectors_to_compare) > 0:
                    tabs = st.tabs(sectors_to_compare)
                    
                    for i, sector in enumerate(sectors_to_compare):
                        with tabs[i]:
                            with st.spinner(f"Fetching company data for {sector}..."):
                                company_df = get_companies_by_industry(sector)
                            
                            if "Error" in company_df.columns:
                                st.warning(f"Company data for {sector} could not be loaded.")
                            else:
                                # Process the company data
                                for col in ["P/E", "P/S", "P/B", "Dividend"]:
                                    company_df[col] = (
                                        company_df[col]
                                        .str.replace(",", "", regex=False)
                                        .str.replace("%", "", regex=False)
                                        .replace("N/A", None)
                                    )
                                    company_df[col] = pd.to_numeric(company_df[col], errors='coerce')
                                
                                # Use the same metric that was selected for sector comparison
                                top_companies = company_df.sort_values(by=metric_to_plot, ascending=False).dropna(subset=[metric_to_plot]).head(10)
                                
                                if not top_companies.empty:
                                    st.write(f"Top 10 companies by {metric_to_plot}")
                                    st.dataframe(top_companies, use_container_width=True, hide_index=True)
                                    
                                    st.bar_chart(data=top_companies.set_index("Ticker")[metric_to_plot], use_container_width=True)
                                else:
                                    st.warning(f"No valid company data available for {sector}")
            else:
                st.warning(f"No valid numeric data available for {metric_to_plot} in the selected sectors")
        else:
            st.info("Please select at least one sector to visualize")

    # Only show the single sector company view if we're filtering by a specific sector
    # and not using the multi-sector comparison
    if sector_filter != "All" and not sectors_to_compare:
        st.subheader(f"Top Companies in {sector_filter}")

        with st.spinner("Fetching company data..."):
            company_df = get_companies_by_industry(sector_filter)
        
        if "Error" in company_df.columns:
            st.warning("Company data could not be loaded.")
        else:
            for col in ["P/E", "P/S", "P/B", "Dividend"]:
                company_df[col] = (
                    company_df[col]
                    .str.replace(",", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .replace("N/A", None)
                )
                company_df[col] = pd.to_numeric(company_df[col], errors='coerce')

            metric = st.selectbox("Metric to visualize for companies", ["P/E", "P/S", "P/B", "Dividend"])
            
            top_companies = company_df.sort_values(by=metric, ascending=False).dropna(subset=[metric]).head(10)

            st.write(f"Top 10 companies by {metric}")
            st.dataframe(top_companies, use_container_width=True)

            st.bar_chart(data=top_companies.set_index("Ticker")[metric], use_container_width=True)

            
    # Add some explanations
    st.markdown("""
    ### Valuation Metrics Explained
    - **P/E Ratio**: Price-to-Earnings ratio - how much investors are willing to pay per dollar of earnings
    - **P/S Ratio**: Price-to-Sales ratio - company's market cap divided by its revenue
    - **P/B Ratio**: Price-to-Book ratio - market value relative to book value
    - **Dividend**: Dividend yield - annual dividends relative to share price
    """)
