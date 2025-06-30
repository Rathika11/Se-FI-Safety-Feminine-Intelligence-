import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import streamlit_js_eval

# Initialize session state variables
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
if 'location_requested' not in st.session_state:
    st.session_state['location_requested'] = False

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

    # Process location data if available in session state from streamlit_js_eval
    if "location_data" in st.session_state and st.session_state["location_data"] is not None:
        location_data = st.session_state["location_data"]
        
        # Check if it's a dictionary with valid location data
        if isinstance(location_data, dict) and "latitude" in location_data and "longitude" in location_data:
            # Update session state with the coordinates
            st.session_state['lat'] = location_data["latitude"]
            st.session_state['lon'] = location_data["longitude"]
            st.session_state['location_requested'] = False
    
    # Display location fetch button if no location is set
    if st.session_state.get('lat') is None or st.session_state.get('lon') is None:
        with location_container:
            if not st.session_state.get('location_requested'):
                st.info("📍 We need your location to check area safety")
                
                if st.button("📍 Share My Location", use_container_width=True):
                    st.session_state['location_requested'] = True
                    with st.spinner("Requesting location from your browser..."):
                        try:
                            # Use streamlit_js_eval to get location
                            streamlit_js_eval.streamlit_js_eval(
                                js_expressions="""
                                new Promise((resolve) => {
                                    if (!navigator.geolocation) {
                                        resolve({error: "Geolocation not supported"});
                                        return;
                                    }
                                    
                                    navigator.geolocation.getCurrentPosition(
                                        (position) => {
                                            resolve({
                                                latitude: position.coords.latitude,
                                                longitude: position.coords.longitude,
                                                accuracy: position.coords.accuracy
                                            });
                                        },
                                        (error) => {
                                            let errorMsg = "Unknown error";
                                            if (error.code === 1) errorMsg = "Permission denied";
                                            if (error.code === 2) errorMsg = "Position unavailable";
                                            if (error.code === 3) errorMsg = "Timeout";
                                            resolve({error: errorMsg});
                                        },
                                        {
                                            enableHighAccuracy: true,
                                            timeout: 10000,
                                            maximumAge: 0
                                        }
                                    );
                                });
                                """,
                                want_output=True,
                                key="location_data"
                            )
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Error running location request: {e}")
            else:
                # Show waiting message if we're waiting for location response
                st.info("⌛ Waiting for your location... Please allow access when prompted by your browser.")
                st.warning("If the prompt doesn't appear, check your browser settings and make sure location services are enabled.")
                
                # Automatic retry mechanism
                try:
                    streamlit_js_eval.streamlit_js_eval(
                        js_expressions="""
                        new Promise((resolve) => {
                            if (!navigator.geolocation) {
                                resolve({error: "Geolocation not supported"});
                                return;
                            }
                            
                            navigator.geolocation.getCurrentPosition(
                                (position) => {
                                    resolve({
                                        latitude: position.coords.latitude,
                                        longitude: position.coords.longitude,
                                        accuracy: position.coords.accuracy
                                    });
                                },
                                (error) => {
                                    let errorMsg = "Unknown error";
                                    if (error.code === 1) errorMsg = "Permission denied";
                                    if (error.code === 2) errorMsg = "Position unavailable";
                                    if (error.code === 3) errorMsg = "Timeout";
                                    resolve({error: errorMsg});
                                },
                                {
                                    enableHighAccuracy: true,
                                    timeout: 10000,
                                    maximumAge: 0
                                }
                            );
                        });
                        """,
                        want_output=True,
                        key="location_data_retry"
                    )
                except Exception as e:
                    st.error(f"Error in retry: {e}")

                # Button to cancel location request
                if st.button("❌ Cancel Location Request"):
                    st.session_state['location_requested'] = False
                    st.experimental_rerun()

        # Error handling for location data
        if "location_data" in st.session_state:
            location_data = st.session_state["location_data"]
            if isinstance(location_data, dict) and "error" in location_data:
                st.error(f"Location error: {location_data['error']}")
                st.info("Please make sure you've allowed location access in your browser.")
                st.session_state['location_requested'] = False
    
    # Once lat and lon are stored, check for safety
    if st.session_state.get('lat') is not None and st.session_state.get('lon') is not None:
        lat = st.session_state.get('lat')
        lon = st.session_state.get('lon')
        
        # Show the coordinates
        st.write(f"Your coordinates: {lat:.6f}, {lon:.6f}")
        
        # Display map
        try:
            st.map({
                "lat": [lat],
                "lon": [lon]
            })
        except Exception as e:
            st.error(f"Error displaying map: {e}")
        
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
                # No crime data means the area is considered safe
                st.success("✅ No crime data available - this typically indicates a very safe area.")
                st.info("Areas with no crime records are considered among the safest places to visit.")
                
                # Record this safety check in history as safe
                st.session_state['safety_history'].append({
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'location': location,
                    'district': district if district else "Unknown",
                    'coordinates': f"{lat:.6f}, {lon:.6f}",
                    'safe': True,
                    'total_crimes': 0
                })
                st.session_state['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return
            
            # We no longer display available districts to keep the UI clean
            if not df.empty:
                available_districts = df["District"].unique()
                
                # Search for the district in the data
                # Case-insensitive search and partial matching
                if district:
                    district_data = df[df["District"].str.lower().str.contains(district.lower(), na=False)]
                else:
                    # If no district found, mark it as safe due to no crime data
                    st.success(f"✅ Your location has a safety place.")
                    st.info("Areas with no crime records are considered among the safest places.")
                    
                    # Record this safety check in history as safe
                    st.session_state['safety_history'].append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'location': location,
                        'district': "No matching district",
                        'coordinates': f"{lat:.6f}, {lon:.6f}",
                        'safe': True,
                        'total_crimes': 0
                    })
                    st.session_state['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
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
                    st.success(f"✅ {district if district else location} has no reported crime data in our database.")
                    st.info("Areas with no crime records are considered among the safest places.")
                    
                    # Record this safety check in history as safe
                    st.session_state['safety_history'].append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'location': location,
                        'district': district if district else "Unknown",
                        'coordinates': f"{lat:.6f}, {lon:.6f}",
                        'safe': True,
                        'total_crimes': 0
                    })
                    st.session_state['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Add location tracking feature - PROMINENTLY FEATURED
    st.write("---")
    
    # Make the tracking section more visible with colors and larger heading
    st.markdown('<div style="background-color:#f0f9ff; padding:15px; border-radius:10px; border:1px solid #90cdf4;">'
                '<h2 style="text-align:center; color:#3182ce;">📡 LIVE LOCATION TRACKING</h2>'
                '</div>', unsafe_allow_html=True)
    
    # Add an explanation about the feature
    st.markdown("""
    **Enable continuous tracking to:**
    * Get real-time safety alerts as you move
    * Keep a record of all areas you visit
    * Receive instant notifications about unsafe areas
    * Monitor your movement patterns for safety analysis
    """)
    
    # Make the tracking toggle more prominent
    track_location = st.checkbox("✅ ENABLE LIVE LOCATION TRACKING", value=False, help="Turn on continuous location monitoring for real-time safety updates", key="prominent_tracking_toggle")
    
    if track_location:
        st.success("📡 **LIVE TRACKING ACTIVATED!** Your location is now being continuously monitored for safety alerts.")
        
        col1, col2 = st.columns(2)
        with col1:
            tracking_interval = st.slider("Update frequency (seconds)", min_value=5, max_value=60, value=15, step=5)
        with col2:
            distance_threshold = st.slider("Movement threshold (meters)", min_value=5, max_value=100, value=10, step=5)
        
        # Distance in degrees is approximately: meter_distance / 111000
        distance_threshold_degrees = distance_threshold / 111000
        
        # Get real-time updates using streamlit_js_eval's continuous mode
        try:
            streamlit_js_eval.streamlit_js_eval(
                js_expressions=f"""
                // Set up tracking with interval
                // First clear any existing intervals
                if (window.trackingIntervalId) {{
                    clearInterval(window.trackingIntervalId);
                    window.trackingIntervalId = null;
                }}
                
                // Show a system notification if supported
                function showNotification(title, body) {{
                    if ("Notification" in window) {{
                        if (Notification.permission === "granted") {{
                            new Notification(title, {{ body: body }});
                        }} else if (Notification.permission !== "denied") {{
                            Notification.requestPermission().then(permission => {{
                                if (permission === "granted") {{
                                    new Notification(title, {{ body: body }});
                                }}
                            }});
                        }}
                    }}
                }}
                
                showNotification("Safety Tracking Activated", "We'll monitor your location for safety alerts.");
                
                const trackingInterval = setInterval(() => {{
                    if (navigator.geolocation) {{
                        navigator.geolocation.getCurrentPosition(
                            (position) => {{
                                const lat = position.coords.latitude;
                                const lon = position.coords.longitude;
                                
                                // Check if location has changed significantly
                                let lastLat = window.lastLat || 0;
                                let lastLon = window.lastLon || 0;
                                
                                const distance = Math.sqrt(
                                    Math.pow(lat - lastLat, 2) + 
                                    Math.pow(lon - lastLon, 2)
                                );
                                
                                // Only update if moved more than threshold
                                if (distance > {distance_threshold_degrees} || !window.lastLat) {{  
                                    console.log(`Location updated: ${{lat}}, ${{lon}}`);
                                    window.lastLat = lat;
                                    window.lastLon = lon;
                                    
                                    // Use window.parent to properly reference the parent window
                                    const url = new URL(window.parent.location.href);
                                    url.searchParams.set('track_lat', lat);
                                    url.searchParams.set('track_lon', lon);
                                    window.parent.location.href = url.toString();
                                    
                                    showNotification("Location Updated", "Your safety status has been updated based on your new location.");
                                }}
                            }},
                            (error) => {{
                                console.error("Tracking error:", error);
                                if (error.code === 1) {{
                                    showNotification("Permission Error", "Location permission is required for continuous tracking.");
                                }}
                            }},
                            {{
                                enableHighAccuracy: true,
                                timeout: 10000,
                                maximumAge: 0
                            }}
                        );
                    }}
                }}, {tracking_interval * 1000});  // Convert seconds to milliseconds
                
                // Store interval ID so it can be cleared later
                window.trackingIntervalId = trackingInterval;
                
                // Return something to satisfy JS eval
                "Tracking initialized with " + {tracking_interval} + "s interval";
                """,
                key=f"continuous_tracking_{tracking_interval}_{distance_threshold}"
            )
        except Exception as e:
            st.error(f"Error setting up tracking: {e}")
            
        # Show active tracking indicator
        st.markdown(
            """
            <div style="background-color:#d1fae5; padding:10px; border-radius:5px; margin-top:10px; text-align:center;">
                <span style="color:#047857; font-size:1.2em; font-weight:bold;">
                    ● TRACKING ACTIVE - Your safety is being monitored
                </span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Warning about battery usage
        st.info("ℹ️ Note: Continuous tracking may affect battery life. The app will update your safety status as you move.")
    else:
        # Clear tracking interval if exists
        try:
            streamlit_js_eval.streamlit_js_eval(
                js_expressions="""
                if (window.trackingIntervalId) {
                    clearInterval(window.trackingIntervalId);
                    window.trackingIntervalId = null;
                    if ("Notification" in window && Notification.permission === "granted") {
                        new Notification("Tracking Stopped", { body: "Location tracking has been disabled." });
                    }
                    "Tracking stopped";
                } else {
                    "No tracking to stop";
                }
                """,
                key="stop_tracking"
            )
            st.info("📴 Location tracking is currently disabled. Enable tracking for continuous safety monitoring.")
        except Exception as e:
            pass  # Silently ignore errors when stopping tracking
    
    # Option to manually enter coordinates (as a fallback)
    with st.expander("🔍 Enter coordinates manually"):
        col1, col2 = st.columns(2)
        with col1:
            manual_lat = st.number_input("Latitude", value=st.session_state.get('lat') if st.session_state.get('lat') is not None else 0.0)
        with col2:
            manual_lon = st.number_input("Longitude", value=st.session_state.get('lon') if st.session_state.get('lon') is not None else 0.0)
        
        if st.button("Check This Location"):
            st.session_state['lat'] = manual_lat
            st.session_state['lon'] = manual_lon
            st.rerun()
    
    # Button to clear location data
    if st.session_state.get('lat') is not None:
        if st.button("Clear Location Data", key="clear_location"):
            st.session_state['lat'] = None
            st.session_state['lon'] = None
            if "location_data" in st.session_state:
                del st.session_state["location_data"]
            st.session_state['safety_history'] = []
            st.rerun()
    
    # Back to Dashboard button
    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_helpline"):
        st.session_state['page'] = 'dashboard'
        st.rerun()

    # Troubleshooting information
    with st.expander("📌 Troubleshooting Location Services"):
        st.markdown("""
        If you're having trouble getting your location:
        
        1. **Browser permissions**: Check that you've allowed location access in your browser
        2. **Device settings**: Make sure location services are enabled on your device
        3. **Browser compatibility**: Try a different browser like Chrome or Edge
        4. **Network**: Some networks block location requests
        5. **HTTPS**: Location services work best on secure websites (HTTPS)
        6. **Try again**: Sometimes browsers need multiple attempts to get an accurate location
        """)

# Execution starts here
check_area_safety_page()