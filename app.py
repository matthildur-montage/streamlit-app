import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from finviz_bs import get_companies_by_industry_bs
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@st.cache_data
def get_sector_data():
    try:
        url = "https://finviz.com/groups.ashx?g=industry&v=152&o=name&c=0,1,2,3,4,6,7,10,13,22,24,25,26"
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
            if len(cols) < 9: 
                continue
            
            # Try to extract data safely
            try:
                sector = cols[1].text.strip() if len(cols) > 1 else "Unknown"
                marketcap = cols[2].text.strip() if len(cols) > 2 else "N/A"
                pe = cols[3].text.strip() if len(cols) > 3 else "N/A"
                fwd_pe = cols[4].text.strip() if len(cols) > 4 else "N/A"
                ps = cols[5].text.strip() if len(cols) > 5 else "N/A"
                pb = cols[6].text.strip() if len(cols) > 6 else "N/A"
                dividend = cols[7].text.strip() if len(cols) > 7 else "N/A"
                sales_growth = cols[8].text.strip() if len(cols) > 8 else "N/A"
                volume = cols[9].text.strip() if len(cols) > 9 else "N/A"
                
                data.append({
                    "Sector": sector,
                    "Market cap": marketcap,
                    "P/E": pe,
                    "Fwd P/E": fwd_pe,
                    "P/S": ps,
                    "P/B": pb,
                    "Dividend": dividend,
                    "Sales 5Y growth": sales_growth,
                    "Avg. volume": volume
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

# Main app
st.title("US Stock Market Sector Multiples")
st.write("This app shows valuation multiples for different market sectors.")
st.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

if "previous_sectors" not in st.session_state:
    st.session_state.previous_sectors = []
if "company_data" not in st.session_state:
    st.session_state.company_data = {}  # sector -> DataFrame

# Add a loading spinner
with st.spinner("Fetching sector data..."):
    df = get_sector_data()

# Check if we got valid data
if "Error" in df.columns:
    st.error("Failed to retrieve sector data. Please try again later.")
else:
    # Display the data
    st.dataframe(df.reset_index(drop=True), use_container_width=True, hide_index=True)
    if not df.empty:
        # Add visualization section
        st.subheader("Sector Comparison Visualization")
        
        # Convert metrics to numeric values for plotting
        numeric_df = df.copy()
        # Define sector metrics
        sector_metrics = ["Market cap", "P/E", "P/S", "P/B", "Dividend", "Sales 5Y growth", "Avg. volume"]
        
        for col in sector_metrics:
            if col in numeric_df.columns:
                formatted_col = col + "_formatted"
                numeric_df[formatted_col] = df[col].copy()
                numeric_df[col] = (
                    numeric_df[col]
                    .str.replace(",", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .str.replace("B", "", regex=False)
                    .str.replace("M", "", regex=False)
                    .str.replace("K", "", regex=False)
                    .replace("N/A", None)
                )
                numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')
        
        # Create two columns for the controls
        col1, col2 = st.columns(2)
        
        with col1:
            # Multi-select for sectors
            sectors_to_compare = st.multiselect(
                "Select Sectors to Compare",
                options=numeric_df["Sector"].tolist(),
                default=[]
            )
        
        with col2:
            # Select metric to visualize - only show metrics available in sector data
            metric_to_plot = st.selectbox("Select Metric to Compare", sector_metrics)
        
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
                display_comparison_df = comparison_df.copy()
                for metric in sector_metrics:
                    metric_formatted = metric + "_formatted"
                    display_comparison_df[metric] = comparison_df[metric_formatted]
                st.write("Comparison Values:")
                st.dataframe(
                    display_comparison_df[["Sector", metric_to_plot]].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )
                #df = df.drop(columns=[col for col in df.columns if "_formatted" in col])
        else:
            st.info("Please select at least one sector to visualize")


        if sectors_to_compare and len(sectors_to_compare) > 0:
            # Step 1: See which new sectors are selected
            new_sectors = list(set(sectors_to_compare) - set(st.session_state.previous_sectors))
            for sector in new_sectors:
                with st.spinner(f"Fetching company data for {sector}..."):
                    logger.info(f"Getting new data for {sector}")
                    st.session_state.company_data[sector] = get_companies_by_industry_bs(sector, 100)
            st.session_state.previous_sectors = sectors_to_compare
            # Step 2: Remove unselected sectors from memory
            for sector in list(st.session_state.company_data.keys()):
                if sector not in sectors_to_compare:
                    del st.session_state.company_data[sector]
                    
            # Step 3: Render tabs for all selected sectors
            tabs = st.tabs(sectors_to_compare)
            for i, sector in enumerate(sectors_to_compare):
                company_df = st.session_state.company_data.get(sector)
                with tabs[i]:
                    if company_df is None or company_df.empty:
                        st.warning(f"No company data available for {sector}")
                    else:
                        if "Error" in company_df.columns:
                            st.warning(f"Company data for {sector} could not be loaded: {company_df['Error'].iloc[0]}")
                        else:
                            # Process the company data
                            company_metrics = ["Market cap", "P/E", "Fwd P/E", "P/S", "P/B", "Dividend", "Sales 5Y growth", "Sales"]
                            # First, create a copy of the original formatted values
                            for col in company_metrics:
                                if col in company_df.columns:
                                    # Create a new column for the formatted display values
                                    company_df[f"{col}_formatted"] = company_df[col].copy()
                            logger.info(f"After adding formatted columns: {company_df.columns}")
                            logger.info(f"MC Values: {company_df["Market cap_formatted"]}")
                            # Then convert to numeric for sorting and calculations
                            for col in company_metrics:
                                if col in company_df.columns and "formatted" not in col:
                                    # For columns that might have B/M suffixes (Market cap, Sales)
                                    if col in ["Market cap", "Sales", "Avg. volume"]:
                                        # Convert values to numeric with proper scaling
                                        def convert_value(val):
                                            if isinstance(val, str):
                                                val = val.replace(",", "")
                                                if "B" in val:
                                                    return float(val.replace("B", "")) * 1000  # Convert B to M for consistent scale
                                                elif "M" in val:
                                                    return float(val.replace("M", ""))
                                                elif "K" in val:
                                                    return float(val.replace("K", "")) / 1000  # Convert K to M
                                                else:
                                                    try:
                                                        return float(val) / 1000000  # Convert raw numbers to M
                                                    except:
                                                        return None
                                            return val
                                        company_df[col] = company_df[col].apply(convert_value)
                                    else:
                                        # For other metrics, just remove % and convert to numeric
                                        try:
                                            company_df[col] = (
                                                company_df[col]
                                                .str.replace(",", "", regex=False)
                                                .str.replace("%", "", regex=False)
                                                .replace("N/A", None)
                                            )
                                            company_df[col] = pd.to_numeric(company_df[col], errors='coerce')
                                        except Exception as e:
                                            pass
                            
                            # See if we have the same metric as above for plotting
                            company_metric = metric_to_plot
                            if metric_to_plot not in company_df.columns:
                                # Find the first available metric
                                for m in company_metrics:
                                    if m in company_df.columns:
                                        company_metric = m
                                        st.info(f"{metric_to_plot} is not available for companies. Showing {company_metric} instead.")
                                        break
                            
                            top_companies = company_df.sort_values(by="Market cap", ascending=False).dropna(subset=["Market cap"]).head(10)
                            if not top_companies.empty:
                                st.write(f"Top 10 companies by market cap")
                                # Create a display dataframe with formatted values
                                display_df = top_companies[["Ticker", "Company"]].copy()
                                
                                # Add formatted columns where available
                                for col in company_metrics:
                                    if f"{col}_formatted" in top_companies.columns:
                                        logger.info(f"Displaying formatted: {top_companies["Market cap_formatted"]}")
                                        display_df[col] = top_companies[f"{col}_formatted"]
                                    elif col in top_companies.columns:
                                        logger.info(f"Notformatted: {top_companies[col]}")
                                        display_df[col] = top_companies[col]
                                
                                st.dataframe(display_df, use_container_width=True, hide_index=True)
                                
                                st.bar_chart(data=top_companies.set_index("Ticker")[company_metric], use_container_width=True)
                            else:
                                st.warning(f"No valid company data available for {sector} with {company_metric} values")
    else:
        st.warning(f"No valid numeric data available for {metric_to_plot} in the selected sectors")
        
            
    # Add some explanations
    st.markdown("""
    ### Valuation Metrics Explained
    - **Market cap**: Market Capitalization - total value of a company's outstanding shares, indicating company size
    - **P/E Ratio**: Price-to-Earnings ratio - how much investors are willing to pay per dollar of earnings
    - **Fwd P/E**: Forward Price-to-Earnings ratio - based on forecasted earnings for the next 12 months
    - **P/S Ratio**: Price-to-Sales ratio - company's market cap divided by its revenue
    - **P/B Ratio**: Price-to-Book ratio - market value of a company relative to its book value
    - **Dividend**: Dividend yield - annual dividends relative to share price
    - **Sales 5Y growth**: 5-year sales growth rate - measures company's revenue growth over 5 years
    - **Sales**: Total revenue generated by the company
    - **Gross Margin**: Gross profit divided by revenue - measures production efficiency
    - **Operating Margin**: Operating income divided by revenue - measures operational efficiency
    - **Profit Margin**: Net income divided by revenue - measures overall profitability
    - **Avg. volume**: Average trading volume - indicates stock's liquidity and trading activity
    """)
