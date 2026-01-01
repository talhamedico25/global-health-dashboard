"""
Global Health Data Dashboard
An interactive dashboard aggregating global health indicators from WHO and World Bank APIs.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import requests_cache
from datetime import timedelta

# Enable caching for API requests
requests_cache.install_cache('health_data_cache', expire_after=timedelta(hours=24))

# Page configuration
st.set_page_config(
    page_title="Global Health Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stPlotlyChart {
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==================== Data Fetching Functions ====================

# World Bank indicator codes
WORLD_BANK_INDICATORS = {
    "Life Expectancy at Birth": "SP.DYN.LE00.IN",
    "Under-5 Mortality Rate (per 1000)": "SH.DYN.MORT",
    "Infant Mortality Rate (per 1000)": "SP.DYN.IMRT.IN",
    "Immunization, DPT (% of children ages 12-23 months)": "SH.IMM.IDPT",
    "Immunization, Measles (% of children ages 12-23 months)": "SH.IMM.MEAS",
    "GDP per Capita (current US$)": "NY.GDP.PCAP.CD",
    "Health Expenditure (% of GDP)": "SH.XPD.CHEX.GD.ZS",
    "Physicians (per 1,000 people)": "SH.MED.PHYS.ZS",
    "Hospital Beds (per 1,000 people)": "SH.MED.BEDS.ZS",
}

# Region groupings
REGIONS = {
    "All Regions": None,
    "East Asia & Pacific": "EAS",
    "Europe & Central Asia": "ECS",
    "Latin America & Caribbean": "LCN",
    "Middle East & North Africa": "MEA",
    "North America": "NAC",
    "South Asia": "SAS",
    "Sub-Saharan Africa": "SSF",
}

# Income groups
INCOME_GROUPS = {
    "All Income Levels": None,
    "High Income": "HIC",
    "Upper Middle Income": "UMC",
    "Lower Middle Income": "LMC",
    "Low Income": "LIC",
}

# Sample countries for quick selection
SAMPLE_COUNTRIES = {
    "United States": "USA",
    "United Kingdom": "GBR",
    "Germany": "DEU",
    "France": "FRA",
    "China": "CHN",
    "India": "IND",
    "Brazil": "BRA",
    "Japan": "JPN",
    "Nigeria": "NGA",
    "South Africa": "ZAF",
    "Kenya": "KEN",
    "Pakistan": "PAK",
    "Indonesia": "IDN",
    "Mexico": "MEX",
    "Russia": "RUS",
    "Canada": "CAN",
    "Australia": "AUS",
    "Egypt": "EGY",
    "Bangladesh": "BGD",
    "Ethiopia": "ETH",
}


@st.cache_data(ttl=86400)
def fetch_all_countries():
    """Fetch list of all countries from World Bank API."""
    url = "https://api.worldbank.org/v2/country?format=json&per_page=300"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                countries = {}
                for country in data[1]:
                    if country.get('region', {}).get('value') != 'Aggregates':
                        countries[country['name']] = country['id']
                return dict(sorted(countries.items()))
    except Exception as e:
        st.warning(f"Could not fetch country list: {e}")
    return SAMPLE_COUNTRIES


@st.cache_data(ttl=86400)
def fetch_world_bank_data(indicator_code, countries, start_year, end_year):
    """Fetch data from World Bank API for specified indicator and countries."""
    country_codes = ";".join(countries)
    url = f"https://api.worldbank.org/v2/country/{country_codes}/indicator/{indicator_code}"
    params = {
        "format": "json",
        "date": f"{start_year}:{end_year}",
        "per_page": 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1 and data[1]:
                records = []
                for item in data[1]:
                    if item['value'] is not None:
                        records.append({
                            'country': item['country']['value'],
                            'country_code': item['countryiso3code'],
                            'year': int(item['date']),
                            'value': float(item['value'])
                        })
                return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
    
    return pd.DataFrame()


@st.cache_data(ttl=86400)
def fetch_countries_by_region(region_code):
    """Fetch countries belonging to a specific region."""
    url = f"https://api.worldbank.org/v2/country?region={region_code}&format=json&per_page=100"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                return {c['name']: c['id'] for c in data[1]}
    except:
        pass
    return {}


@st.cache_data(ttl=86400)
def fetch_countries_by_income(income_code):
    """Fetch countries belonging to a specific income group."""
    url = f"https://api.worldbank.org/v2/country?incomeLevel={income_code}&format=json&per_page=100"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                return {c['name']: c['id'] for c in data[1]}
    except:
        pass
    return {}


# ==================== Visualization Functions ====================

def create_line_chart(df, indicator_name):
    """Create an interactive line chart for time series data."""
    if df.empty:
        return None
    
    fig = px.line(
        df,
        x='year',
        y='value',
        color='country',
        markers=True,
        title=f'{indicator_name} Over Time',
        labels={'value': indicator_name, 'year': 'Year', 'country': 'Country'}
    )
    
    fig.update_layout(
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


def create_bar_chart(df, indicator_name, year):
    """Create a bar chart comparing countries for a specific year."""
    if df.empty:
        return None
    
    year_data = df[df['year'] == year].sort_values('value', ascending=True)
    
    if year_data.empty:
        return None
    
    fig = px.bar(
        year_data,
        x='value',
        y='country',
        orientation='h',
        title=f'{indicator_name} by Country ({year})',
        labels={'value': indicator_name, 'country': 'Country'},
        color='value',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


def create_scatter_comparison(df1, df2, indicator1_name, indicator2_name, year):
    """Create a scatter plot comparing two indicators."""
    if df1.empty or df2.empty:
        return None
    
    data1 = df1[df1['year'] == year][['country', 'value']].rename(columns={'value': 'x'})
    data2 = df2[df2['year'] == year][['country', 'value']].rename(columns={'value': 'y'})
    
    merged = pd.merge(data1, data2, on='country')
    
    if merged.empty:
        return None
    
    fig = px.scatter(
        merged,
        x='x',
        y='y',
        text='country',
        title=f'{indicator1_name} vs {indicator2_name} ({year})',
        labels={'x': indicator1_name, 'y': indicator2_name},
        trendline='ols'
    )
    
    fig.update_traces(textposition='top center', marker=dict(size=12))
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    
    return fig


def create_world_map(df, indicator_name, year):
    """Create a choropleth map for the selected indicator and year."""
    if df.empty:
        return None
    
    year_data = df[df['year'] == year]
    
    if year_data.empty:
        return None
    
    fig = px.choropleth(
        year_data,
        locations='country_code',
        color='value',
        hover_name='country',
        title=f'{indicator_name} ({year})',
        color_continuous_scale='RdYlGn',
        labels={'value': indicator_name}
    )
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=60, b=0),
        geo=dict(showframe=False, showcoastlines=True)
    )
    
    return fig


# ==================== Main Application ====================

def main():
    # Header
    st.markdown('<p class="main-header">🌍 Global Health Data Dashboard</p>', unsafe_allow_html=True)
    st.markdown("""
    <p style="text-align: center; color: #666; margin-bottom: 2rem;">
    Explore global health indicators from the World Bank. Compare countries, 
    track trends over time, and discover insights about health disparities worldwide.
    </p>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard Controls")
        
        # Indicator selection
        st.subheader("Select Indicators")
        primary_indicator = st.selectbox(
            "Primary Indicator",
            options=list(WORLD_BANK_INDICATORS.keys()),
            index=0
        )
        
        secondary_indicator = st.selectbox(
            "Secondary Indicator (for comparison)",
            options=["None"] + list(WORLD_BANK_INDICATORS.keys()),
            index=0
        )
        
        # Time range
        st.subheader("Time Period")
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input("Start Year", min_value=1960, max_value=2023, value=2000)
        with col2:
            end_year = st.number_input("End Year", min_value=1960, max_value=2023, value=2022)
        
        # Region filter
        st.subheader("Filters")
        selected_region = st.selectbox("Region", options=list(REGIONS.keys()))
        selected_income = st.selectbox("Income Group", options=list(INCOME_GROUPS.keys()))
        
        # Country selection
        st.subheader("Select Countries")
        
        # Get countries based on filters
        if REGIONS[selected_region]:
            available_countries = fetch_countries_by_region(REGIONS[selected_region])
        elif INCOME_GROUPS[selected_income]:
            available_countries = fetch_countries_by_income(INCOME_GROUPS[selected_income])
        else:
            available_countries = fetch_all_countries()
        
        if not available_countries:
            available_countries = SAMPLE_COUNTRIES
        
        # Default selection
        default_countries = ["United States", "India", "Germany", "Nigeria", "Brazil"]
        default_selection = [c for c in default_countries if c in available_countries][:5]
        
        selected_countries = st.multiselect(
            "Choose up to 10 countries",
            options=list(available_countries.keys()),
            default=default_selection,
            max_selections=10
        )
        
        # Quick selection buttons
        st.caption("Quick Select:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Top 5 GDP"):
                st.session_state['quick_select'] = ["United States", "China", "Japan", "Germany", "India"]
        with col2:
            if st.button("BRICS"):
                st.session_state['quick_select'] = ["Brazil", "Russia", "India", "China", "South Africa"]
    
    # Check for quick selection
    if 'quick_select' in st.session_state:
        selected_countries = [c for c in st.session_state['quick_select'] if c in available_countries]
        del st.session_state['quick_select']
    
    # Main content
    if not selected_countries:
        st.warning("⚠️ Please select at least one country from the sidebar.")
        return
    
    # Get country codes
    country_codes = [available_countries[c] for c in selected_countries if c in available_countries]
    
    # Fetch data
    with st.spinner("Fetching data from World Bank API..."):
        primary_data = fetch_world_bank_data(
            WORLD_BANK_INDICATORS[primary_indicator],
            country_codes,
            start_year,
            end_year
        )
        
        if secondary_indicator != "None":
            secondary_data = fetch_world_bank_data(
                WORLD_BANK_INDICATORS[secondary_indicator],
                country_codes,
                start_year,
                end_year
            )
        else:
            secondary_data = pd.DataFrame()
    
    if primary_data.empty:
        st.error("❌ No data available for the selected parameters. Try different countries or time period.")
        return
    
    # Display metrics
    st.subheader("📈 Key Statistics")
    latest_year = primary_data['year'].max()
    latest_data = primary_data[primary_data['year'] == latest_year]
    
    cols = st.columns(4)
    if not latest_data.empty:
        with cols[0]:
            st.metric("Latest Year", latest_year)
        with cols[1]:
            st.metric("Average", f"{latest_data['value'].mean():.2f}")
        with cols[2]:
            st.metric("Highest", f"{latest_data['value'].max():.2f}")
        with cols[3]:
            st.metric("Lowest", f"{latest_data['value'].min():.2f}")
    
    # Charts
    st.divider()
    
    # Tab layout for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Trend Analysis", "📊 Country Comparison", "🗺️ World Map", "🔬 Correlation"])
    
    with tab1:
        st.subheader(f"{primary_indicator} Over Time")
        line_chart = create_line_chart(primary_data, primary_indicator)
        if line_chart:
            st.plotly_chart(line_chart, use_container_width=True)
        
        if not secondary_data.empty:
            st.subheader(f"{secondary_indicator} Over Time")
            secondary_line = create_line_chart(secondary_data, secondary_indicator)
            if secondary_line:
                st.plotly_chart(secondary_line, use_container_width=True)
    
    with tab2:
        comparison_year = st.slider(
            "Select Year for Comparison",
            min_value=start_year,
            max_value=end_year,
            value=end_year,
            key="bar_year"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            bar_chart = create_bar_chart(primary_data, primary_indicator, comparison_year)
            if bar_chart:
                st.plotly_chart(bar_chart, use_container_width=True)
        
        with col2:
            if not secondary_data.empty:
                bar_chart2 = create_bar_chart(secondary_data, secondary_indicator, comparison_year)
                if bar_chart2:
                    st.plotly_chart(bar_chart2, use_container_width=True)
    
    with tab3:
        map_year = st.slider(
            "Select Year for Map",
            min_value=start_year,
            max_value=end_year,
            value=end_year,
            key="map_year"
        )
        world_map = create_world_map(primary_data, primary_indicator, map_year)
        if world_map:
            st.plotly_chart(world_map, use_container_width=True)
    
    with tab4:
        if not secondary_data.empty:
            scatter_year = st.slider(
                "Select Year for Correlation",
                min_value=start_year,
                max_value=end_year,
                value=end_year,
                key="scatter_year"
            )
            scatter_plot = create_scatter_comparison(
                primary_data, secondary_data,
                primary_indicator, secondary_indicator,
                scatter_year
            )
            if scatter_plot:
                st.plotly_chart(scatter_plot, use_container_width=True)
            else:
                st.info("Not enough overlapping data to create correlation plot.")
        else:
            st.info("Select a secondary indicator to compare correlations between indicators.")
    
    # Data table
    st.divider()
    with st.expander("📋 View Raw Data"):
        st.dataframe(
            primary_data.sort_values(['country', 'year'], ascending=[True, False]),
            use_container_width=True
        )
        
        # Download button
        csv = primary_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"health_data_{primary_indicator.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>Data source: <a href="https://data.worldbank.org" target="_blank">World Bank Open Data</a></p>
    <p>Built with ❤️ using Streamlit and Plotly</p>
    <p>Created by <a href="mtalhafayyaz.netlify.app" target="_blank">Talha Fayyaz</a></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
