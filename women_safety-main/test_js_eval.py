import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# Initialize session state variables - ensure these are initialized before any use
# Using dict.get() method to ensure we have default values even if the keys don't exist
if 'page' not in st.session_state:
    st.session_state['page'] = 'safety_check'
if 'lat' not in st.session_state:
    st.session_state['lat'] = None
if 'lon' not in st.session_state:
    st.session_state['lon'] = None
if 'safety_history' not in st.session_state:
    st.session_state['safety_history'] = []
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

# Function to reverse geocode (convert lat/lon to human-readable address)
def reverse_geocode(lat, lon):
    api_key = "995fb40a98f24267a32528a5e5f3aa4b"  # Your OpenCage API key
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if data['results']:
            location = data['results'][0]['formatted']
            
            # Try to extract district or city for better matching with your dataset
            components = data['results'][0].get('components', {})
            district = components.get('county') or components.get('state_district') or components.get('city')
            
            return location, district
        else:
            return "Location not found", None
    except Exception as e:
        st.error(f"Error in geocoding: {e}")
        return "Error fetching location", None

# Function to check the safety of the area
def check_area_safety_page():
    st.title("🛰️ Check Area Safety")
    
    # Create a container for location data
    location_container = st.container()

    # Get location from URL query parameters if available
    query_params = st.query_params
    
    # Check for lat/lon in query params (from regular geolocation)
    if 'lat' in query_params and 'lon' in query_params:
        try:
            st.session_state['lat'] = float(query_params['lat'][0])
            st.session_state['lon'] = float(query_params['lon'][0])
            # Clear params to avoid reprocessing
            st.experimental_set_query_params()
        except (ValueError, TypeError) as e:
            st.error(f"Invalid coordinates in URL parameters: {e}")
    
    # Check for tracking coordinates in query params
    if 'track_lat' in query_params and 'track_lon' in query_params:
        try:
            st.session_state['lat'] = float(query_params['track_lat'][0])
            st.session_state['lon'] = float(query_params['track_lon'][0])
            # Clear params to avoid reprocessing
            st.experimental_set_query_params()
        except (ValueError, TypeError) as e:
            st.error(f"Invalid tracking coordinates: {e}")
    
    # Display location fetch button if no location is set
    # Safely access session state with get() to avoid KeyError
    if st.session_state.get('lat') is None or st.session_state.get('lon') is None:
        with location_container:
            st.write("Click the button below to fetch your location:")
            
            # Improved geolocation HTML component
            st.components.v1.html("""
                <button id="getLocationBtn" style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                    border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">
                    Get My Location
                </button>
                <div id="status" style="margin-top: 10px; padding: 8px; background-color: #f0f2f6; 
                    border-radius: 4px; display: none;">
                </div>
                
                <script>
                    // Wait for the DOM to be fully loaded
                    document.addEventListener('DOMContentLoaded', function() {
                        // Get location button click handler
                        document.getElementById('getLocationBtn').addEventListener('click', function() {
                            getLocation();
                        });
                    });
                    
                    // Function to get location
                    function getLocation() {
                        const statusDiv = document.getElementById('status');
                        statusDiv.style.display = 'block';
                        statusDiv.innerHTML = 'Accessing your location...';
                        
                        if (navigator.geolocation) {
                            navigator.geolocation.getCurrentPosition(
                                function(position) {
                                    const lat = position.coords.latitude;
                                    const lon = position.coords.longitude;
                                    statusDiv.innerHTML = 'Location found! Redirecting...';
                                    
                                    // Add a small delay to make sure user sees the message
                                    setTimeout(function() {
                                        // Redirect with coordinates as query parameters
                                        window.top.location.href = window.top.location.pathname + '?lat=' + lat + '&lon=' + lon;
                                    }, 500);
                                }, 
                                function(error) {
                                    let message = 'Error: ';
                                    switch(error.code) {
                                        case error.PERMISSION_DENIED:
                                            message += 'Permission denied. Please allow location access in your browser settings.';
                                            break;
                                        case error.POSITION_UNAVAILABLE:
                                            message += 'Location information is unavailable.';
                                            break;
                                        case error.TIMEOUT:
                                            message += 'The request to get user location timed out.';
                                            break;
                                        case error.UNKNOWN_ERROR:
                                            message += 'An unknown error occurred.';
                                            break;
                                    }
                                    statusDiv.innerHTML = message;
                                }, 
                                {
                                    enableHighAccuracy: true,
                                    timeout: 10000,
                                    maximumAge: 0
                                }
                            );
                        } else {
                            statusDiv.innerHTML = 'Geolocation is not supported by this browser.';
                        }
                    }
                </script>
            """, height=120)
    
    # Once lat and lon are stored, check for safety
    # Safely access session state with get() to avoid KeyError
    if st.session_state.get('lat') is not None and st.session_state.get('lon') is not None:
        lat = st.session_state.get('lat')
        lon = st.session_state.get('lon')
        
        # Show the coordinates
        st.write(f"Your coordinates: {lat:.6f}, {lon:.6f}")
        
        # Get the location name from reverse geocoding
        location, district = reverse_geocode(lat, lon)
        st.write(f"Detected location: {location}")
        if district:
            st.write(f"District/City: {district}")
        
        try:
            # For demonstration, create dummy crime data if file not found
            try:
                df = pd.read_csv("assets/combined_crime_data.csv")
            except FileNotFoundError:
                # Create dummy data for testing
                st.warning("Crime data file not found. Using demo data for testing.")
                df = pd.DataFrame({
                    "District": [district if district else "Demo District"],
                    "Year": [2023],
                    "Rape": [15],
                    "Murder": [5]
                })
            
            # Print available districts to help with debugging
            if not df.empty:
                available_districts = df["District"].unique()
                st.write("Available districts in dataset:", available_districts[:5], 
                        "..." if len(available_districts) > 5 else "")
                
                # Search for the district in the data
                # Case-insensitive search and partial matching
                if district:
                    district_data = df[df["District"].str.lower().str.contains(district.lower(), na=False)]
                else:
                    # If no district found, use first district as demo
                    st.warning("No district information. Using first district from data for demo.")
                    district_data = df.head(1)
                
                if not district_data.empty:
                    # Get the most recent data (last year)
                    if "Year" in district_data.columns:
                        recent = district_data[district_data["Year"] == district_data["Year"].max()]
                        
                        # Make sure the required columns exist
                        if "Rape" in recent.columns and "Murder" in recent.columns:
                            # Display recent crime stats
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Recent Rape Cases", int(recent["Rape"].values[0]))
                            with col2:
                                st.metric("Recent Murder Cases", int(recent["Murder"].values[0]))
                            
                            # Calculate total crimes for safety assessment
                            total_crimes = int(recent["Rape"].values[0]) + int(recent["Murder"].values[0])
                            
                            # Display safety assessment
                            is_safe = total_crimes <= 20
                            if is_safe:
                                st.success("✅ This area is marked *Safe* based on recent data.")
                            else:
                                st.error("❌ This area is marked *Unsafe* based on recent data.")
                            
                            # Record this safety check in history
                            st.session_state['safety_history'].append({
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'location': location,
                                'district': district if district else "Unknown",
                                'coordinates': f"{lat:.6f}, {lon:.6f}",
                                'safe': is_safe,
                                'total_crimes': total_crimes
                            })
                            st.session_state['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Show safety history if available
                            if len(st.session_state['safety_history']) > 1:
                                st.write("---")
                                st.write("📊 **Safety History**")
                                
                                history_df = pd.DataFrame(st.session_state['safety_history'])
                                st.dataframe(history_df, use_container_width=True)
                                
                                # Show movement safety summary
                                safe_locations = sum(1 for entry in st.session_state['safety_history'] if entry['safe'])
                                unsafe_locations = len(st.session_state['safety_history']) - safe_locations
                                
                                st.write(f"🔍 **Safety Summary**: You've been in {safe_locations} safe and {unsafe_locations} unsafe areas.")
                                
                                if unsafe_locations > 0:
                                    st.warning("⚠️ Your movement history includes unsafe areas. Please be cautious.")
                                else:
                                    st.success("👍 All your tracked locations are in safe areas.")
                        else:
                            st.warning("Required crime data columns not found in the dataset.")
                    else:
                        st.warning("Year column not found in the dataset.")
                else:
                    st.warning(f"Crime data for {district if district else location} not found in our database.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Add location tracking feature
    st.write("---")
    st.write("📍 **Location Tracking**")
    
    track_location = st.checkbox("Track my location continuously", value=False)
    
    if track_location:
        st.components.v1.html("""
            <div style="background-color: #e8f4f9; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                <p>📡 <b>Live tracking enabled</b>. Your location will be continuously monitored for safety alerts.</p>
                <p id="tracking_status">Waiting for location updates...</p>
            </div>
            
            <script>
                // Set up tracking on page load
                document.addEventListener('DOMContentLoaded', function() {
                    startTracking();
                });
                
                let watchId;
                let lastUpdate = new Date().getTime();
                const UPDATE_THRESHOLD = 5000; // 5 seconds minimum between updates
                
                function startTracking() {
                    if (navigator.geolocation) {
                        document.getElementById('tracking_status').innerText = 'Tracking started...';
                        
                        watchId = navigator.geolocation.watchPosition(
                            function(position) {
                                const currentTime = new Date().getTime();
                                const lat = position.coords.latitude;
                                const lon = position.coords.longitude;
                                
                                document.getElementById('tracking_status').innerText = 
                                    'Position updated: ' + new Date().toLocaleTimeString();
                                
                                // Only redirect if enough time has passed since last update
                                if (currentTime - lastUpdate > UPDATE_THRESHOLD) {
                                    lastUpdate = currentTime;
                                    // Use top level location to ensure proper redirection in Streamlit iframe
                                    window.top.location.href = window.top.location.pathname + 
                                        '?track_lat=' + lat + '&track_lon=' + lon;
                                }
                            },
                            function(error) {
                                document.getElementById('tracking_status').innerText = 
                                    'Error tracking: ' + error.message;
                            },
                            {
                                enableHighAccuracy: true,
                                maximumAge: 30000,
                                timeout: 27000
                            }
                        );
                    } else {
                        document.getElementById('tracking_status').innerText = 
                            'Geolocation is not supported by this browser.';
                    }
                }
            </script>
        """, height=120)
    
    # Option to manually enter coordinates (as a fallback)
    st.write("---")
    st.write("Or enter coordinates manually:")
    
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.text_input("Latitude", value=st.session_state.get('lat', "") if st.session_state.get('lat') is not None else "")
    with col2:
        manual_lon = st.text_input("Longitude", value=st.session_state.get('lon', "") if st.session_state.get('lon') is not None else "")
    
    if st.button("Check This Location"):
        if manual_lat and manual_lon:
            try:
                st.session_state['lat'] = float(manual_lat)
                st.session_state['lon'] = float(manual_lon)
                st.experimental_rerun()
            except ValueError:
                st.error("Please enter valid coordinates")
        else:
            st.error("Please enter both latitude and longitude")
    
    # Button to clear location data
    if st.session_state.get('lat') is not None:
        if st.button("Clear Location Data", key="clear_location"):
            st.session_state['lat'] = None
            st.session_state['lon'] = None
            st.session_state['safety_history'] = []
            st.experimental_rerun()
    
    # Back to Dashboard button
    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_helpline"):
        st.session_state['page'] = 'dashboard'
        st.rerun()

# Make sure all session state variables are initialized before running the app
keys_to_check = ['page', 'lat', 'lon', 'safety_history', 'last_update']
for key in keys_to_check:
    if key not in st.session_state:
        st.session_state[key] = None
        
# If safety_history is None, initialize as empty list
if st.session_state.get('safety_history') is None:
    st.session_state['safety_history'] = []

# Example usage to simulate the check area safety page
check_area_safety_page()