# app.py
import streamlit as st

# --- Set wide layout - THIS MUST BE THE FIRST STREAMLIT COMMAND ---
st.set_page_config(layout="wide")
# --- End set_page_config ---


import os
import json

# Import db module early to ensure init_db() is called (place after set_page_config)
# Also ensures bcrypt and pymongo are imported early
import db

# Import all page modules (place after set_page_config)
# Ensure these files exist in your project directory
import login
import dashboard
import signup # Make sure you have signup.py
import add_contacts_page
import helpline_numbers_page
import triggers_page
import developed_by_page
import how_to_use_page
import live_video_page # Kept import and routing in case you want to add content later
import location # Import location module as it might set session state early
import check_area_safety_page
import crime_analysis_page

# Define the path for the contacts data file (No longer used for contacts storage with DB)
# CONTACTS_FILE = "user_contacts.json"

# --- Session State Initialization ---
# Initialize 'page' if not exists, default to 'login'
if 'page' not in st.session_state:
    st.session_state.page = 'login'
    

# 'user_contacts' list might still be used temporarily, but contacts are loaded from DB
if 'user_contacts' not in st.session_state:
    st.session_state.user_contacts = []

# This flag for file loading is no longer needed with DB
# if 'contacts_loaded' not in st.session_state:
#     st.session_state.contacts_loaded = False

# Initialize location-related session state
if 'last_known_location' not in st.session_state:
     st.session_state.last_known_location = None

if 'sos_triggered' not in st.session_state:
     st.session_state.sos_triggered = False

if 'sos_pending_location' not in st.session_state:
    st.session_state.sos_pending_location = False

# Store page functions in session state for easier access and persistence across reruns
# This dictionary defines your app's pages and their corresponding functions
if 'pages' not in st.session_state:
    st.session_state.pages = {
        'login': login.login_page,
        'signup': signup.signup_page,
        'dashboard': dashboard.dashboard,
        'add_contacts_page': add_contacts_page.add_contacts_page,
        'helpline_numbers_page': helpline_numbers_page.helpline_numbers_page,
        'triggers_page': triggers_page.triggers_page,
        'developed_by_page': developed_by_page.developed_by_page,
        'how_to_use_page': how_to_use_page.how_to_use_page,
        'live_video_page': live_video_page.live_video_page,
        'check_area_safety_page': __import__("check_area_safety_page").check_area_safety_page,
        'crime_analysis_page': __import__("crime_analysis_page").show_crime_analysis,
    }


# --- Removed JSON contacts loading logic ---
# The contacts are now managed via the database functions in db.py


# --- Run the current page based on session state ---
current_page_key = st.session_state.page

# Get the function corresponding to the current page key from the session state dictionary
current_page_func = st.session_state.pages.get(current_page_key)

# Execute the function for the current page
if current_page_func:
    try:
        current_page_func()
    except Exception as e:
        # Catch potential errors within page execution
        st.error(f"An error occurred while rendering the page: {e}")
        print(f"Error rendering page '{current_page_key}': {e}")
        # Optional: Redirect to login or show an error page
        # st.session_state.page = 'login'
        # st.rerun()
else:
    # Handle cases where the session state page key is invalid (shouldn't happen if setting valid keys)
    st.error(f"Configuration Error: Page '{current_page_key}' not found in page mapping!")
    st.session_state.page = 'login' # Redirect to a known page
    st.rerun()