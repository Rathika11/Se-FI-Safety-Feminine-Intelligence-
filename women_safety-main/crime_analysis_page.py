import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

# Define the path to the CSV file
CSV_PATH = "assets/combined_crime_data.csv"

def show_crime_analysis():
    # Set page title
    st.title("Crime Data Analytics Dashboard")
    st.write(f"Report generated on: {datetime.now().strftime('%B %d, %Y')}")
    
    # Apply custom styling with CSS
    st.markdown("""
    <style>
    .reportview-container .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px 15px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    div.stButton > button {
        background-color: #4e7cad;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # Check if the CSV file exists before trying to read it
    if not os.path.exists(CSV_PATH):
        st.error(f"Error: CSV file not found at {CSV_PATH}")
        st.write("Please make sure 'combined_crime_data.csv' is in the 'assets' folder.")
        if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_analysis_error"):
            st.session_state['page'] = 'dashboard'
            st.rerun()
        return

    try:
        # Load data
        df = pd.read_csv(CSV_PATH)
        
        # Check required columns
        required_columns = ['STATE/UT', 'RAPE', 'MURDER', 'YEAR', 'DISTRICT']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            st.error(f"Error: Missing required columns in CSV: {', '.join(missing)}")
            st.write("Please check your CSV file header. Expected:", required_columns)
            if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_analysis_col_error"):
                st.session_state['page'] = 'dashboard'
                st.rerun()
            return

        # Data preprocessing
        # Convert year to numeric and handle any conversion errors
        df['YEAR'] = pd.to_numeric(df['YEAR'], errors='coerce')
        df = df.dropna(subset=['YEAR'])
        df['YEAR'] = df['YEAR'].astype(int)
        
        # Create sidebar for filtering
        st.sidebar.header("Filters")
        
        # Year range slider
        years = sorted(df['YEAR'].unique())
        if len(years) > 1:
            year_range = st.sidebar.slider(
                "Select Year Range",
                min_value=int(min(years)),
                max_value=int(max(years)),
                value=(int(min(years)), int(max(years)))
            )
            filtered_df = df[(df['YEAR'] >= year_range[0]) & (df['YEAR'] <= year_range[1])]
        else:
            filtered_df = df
        
        # State selection
        all_states = sorted(filtered_df['STATE/UT'].unique())
        selected_states = st.sidebar.multiselect(
            "Select States/UTs",
            options=all_states,
            default=all_states[:5] if len(all_states) > 5 else all_states
        )
        
        if selected_states:
            filtered_df = filtered_df[filtered_df['STATE/UT'].isin(selected_states)]
        
        # Show data summary in sidebar
        st.sidebar.header("Data Summary")
        st.sidebar.info(f"""
        - Years: {min(filtered_df['YEAR'])} - {max(filtered_df['YEAR'])}
        - States/UTs: {len(filtered_df['STATE/UT'].unique())}
        - Districts: {len(filtered_df['DISTRICT'].unique())}
        - Total Records: {len(filtered_df)}
        """)
        
        # Display key metrics
        st.header("Key Crime Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            total_murder = filtered_df['MURDER'].sum()
            st.metric("Total Murder Cases", f"{int(total_murder):,}")
        
        with col2:
            total_rape = filtered_df['RAPE'].sum()
            st.metric("Total Rape Cases", f"{int(total_rape):,}")
        
        # Time series analysis
        st.header("Crime Trends Over Time")
        yearly_trend = filtered_df.groupby('YEAR')[['RAPE', 'MURDER']].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(yearly_trend['YEAR'], yearly_trend['MURDER'], marker='o', linewidth=2, label='Murder')
        ax.plot(yearly_trend['YEAR'], yearly_trend['RAPE'], marker='s', linewidth=2, label='Rape')
        ax.set_xlabel('Year')
        ax.set_ylabel('Number of Cases')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        st.pyplot(fig)
        
        # State-wise Analysis
        st.header("State-wise Crime Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top States with Most Murder Cases
            top_murder_states = filtered_df.groupby('STATE/UT')['MURDER'].sum().sort_values(ascending=False).head(10)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.barplot(x=top_murder_states.values, y=top_murder_states.index, ax=ax, palette='Reds_r')
            ax.set_title('Top 10 States - Murder Cases')
            ax.set_xlabel('Number of Cases')
            ax.set_ylabel('State/UT')
            plt.tight_layout()
            st.pyplot(fig)
            
        with col2:
            # Top States with Most Rape Cases
            top_rape_states = filtered_df.groupby('STATE/UT')['RAPE'].sum().sort_values(ascending=False).head(10)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.barplot(x=top_rape_states.values, y=top_rape_states.index, ax=ax, palette='Purples_r')
            ax.set_title('Top 10 States - Rape Cases')
            ax.set_xlabel('Number of Cases')
            ax.set_ylabel('State/UT')
            plt.tight_layout()
            st.pyplot(fig)
        
        # District Analysis
        st.header("District-level Crime Analysis")
        
        # Get top 15 districts by total crime
        district_crime = filtered_df.groupby('DISTRICT')[['MURDER', 'RAPE']].sum()
        district_crime['TOTAL'] = district_crime['MURDER'] + district_crime['RAPE']
        top_districts = district_crime.sort_values('TOTAL', ascending=False).head(15)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        district_data = top_districts.reset_index()
        
        # Create stacked bar chart
        p1 = ax.barh(district_data['DISTRICT'], district_data['MURDER'], color='crimson', label='Murder')
        p2 = ax.barh(district_data['DISTRICT'], district_data['RAPE'], left=district_data['MURDER'], 
                    color='purple', label='Rape')
        
        ax.set_title('Top 15 Districts by Crime Volume')
        ax.set_xlabel('Number of Cases')
        ax.set_ylabel('District')
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        
        # Key Insights section
        st.header("Key Insights")
        
        # Calculate some insights
        highest_murder_state = top_murder_states.index[0]
        highest_rape_state = top_rape_states.index[0]
        
        # Get trend direction
        if len(yearly_trend) > 1:
            murder_trend = "increasing" if yearly_trend['MURDER'].iloc[-1] > yearly_trend['MURDER'].iloc[0] else "decreasing"
            rape_trend = "increasing" if yearly_trend['RAPE'].iloc[-1] > yearly_trend['RAPE'].iloc[0] else "decreasing"
        else:
            murder_trend = rape_trend = "unchanged"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Crime Hotspots")
            st.markdown(f"""
            - {highest_murder_state} has the highest reported murder cases
            - {highest_rape_state} has the highest reported rape cases
            - Murder cases are {murder_trend} over the selected time period
            - Rape cases are {rape_trend} over the selected time period
            """)
            
        with col2:
            st.subheader("Recommendations")
            st.markdown(f"""
            - Focus law enforcement resources in {highest_murder_state} and {highest_rape_state}
            - Conduct detailed analysis on districts with high crime rates
            - Review prevention strategies in areas showing increasing trends
            - Implement targeted intervention programs based on crime patterns
            """)
        
        # Data Explorer (Optional - can be expanded/collapsed)
        with st.expander("Data Explorer", expanded=False):
            st.subheader("Explore Raw Data")
            
            # Column selection
            columns_to_display = st.multiselect(
                "Select columns to display",
                options=filtered_df.columns.tolist(),
                default=['STATE/UT', 'DISTRICT', 'YEAR', 'RAPE', 'MURDER']
            )
            
            if columns_to_display:
                st.dataframe(filtered_df[columns_to_display])
            else:
                st.info("Please select at least one column to display data.")
        
        # Download options
        st.header("Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Convert the filtered DataFrame to CSV
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download Raw Data as CSV",
                data=csv,
                file_name=f"crime_data_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        
        with col2:
            # Export summary data
            summary_df = pd.DataFrame({
                'State': top_murder_states.index,
                'Murder_Cases': top_murder_states.values
            })
            summary_csv = summary_df.to_csv(index=False)
            st.download_button(
                label="Download Summary Report as CSV",
                data=summary_csv,
                file_name=f"crime_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        
        # Navigation
        st.markdown("---")
        if st.button("⬅️ Back to Dashboard", key="back_to_dashboard"):
            st.session_state['page'] = 'dashboard'
            st.rerun()

    except Exception as e:
        st.error(f"An error occurred while processing the crime data: {e}")
        st.error("Please check your data file format and try again.")
        
        if st.button("⬅️ Back to Dashboard", key="back_error"):
            st.session_state['page'] = 'dashboard'
            st.rerun()

# Uncomment for testing directly
# if __name__ == "__main__":
#     show_crime_analysis()