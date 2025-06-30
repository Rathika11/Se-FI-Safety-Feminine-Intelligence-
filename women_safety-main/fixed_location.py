import streamlit as st
import streamlit_js_eval

st.title("🌍 Live Location Tracker")

# Check if streamlit-js-eval is working
st.write("Checking if streamlit-js-eval is available...")
try:
    version = streamlit_js_eval.__version__
    st.success(f"streamlit-js-eval v{version} is installed correctly!")
except:
    st.error("Could not detect streamlit-js-eval version")

# Display session state for debugging
with st.expander("Debug Information"):
    st.write("Current session state keys:", list(st.session_state.keys()))

# Location request
st.subheader("Your Location")

col1, col2 = st.columns([1, 3])
with col1:
    get_location = st.button("📍 Get My Location")

if get_location:
    with st.spinner("Requesting location from your browser..."):
        try:
            # Use a simple JS expression to get location
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
                        }
                    );
                });
                """,
                want_output=True,
                key="location_data"
            )
            st.success("Location request sent!")
        except Exception as e:
            st.error(f"Error running location request: {e}")

# Process location data if available
if "location_data" in st.session_state:
    location = st.session_state["location_data"]
    
    # Make sure location is not None
    if location is None:
        st.warning("Browser returned no location data. Please try again.")
    else:
        st.write("Raw location data:", location)
        
        # Check if it's a dictionary with location data
        if isinstance(location, dict):
            if "error" in location:
                st.error(f"Location error: {location['error']}")
                st.info("Please make sure you've allowed location access in your browser.")
            elif "latitude" in location and "longitude" in location:
                # Display location
                st.success("Location successfully retrieved!")
                
                # Format location data
                st.markdown(f"""
                ### 📍 Your Current Location:
                - **Latitude:** {location['latitude']}
                - **Longitude:** {location['longitude']} 
                - **Accuracy:** {location.get('accuracy', 'Unknown')} meters
                """)
                
                # Display map
                try:
                    st.map({
                        "lat": [location["latitude"]],
                        "lon": [location["longitude"]]
                    })
                except Exception as e:
                    st.error(f"Error displaying map: {e}")
        else:
            st.warning(f"Unexpected location data format: {type(location)}")
    
    # Option to clear location
    if st.button("Clear Location Data"):
        del st.session_state["location_data"]
        st.experimental_rerun()

# Manual location input as fallback
st.divider()
st.subheader("Manual Location Input")
st.write("If automatic location doesn't work, you can enter coordinates manually:")

col1, col2 = st.columns(2)
with col1:
    manual_lat = st.number_input("Latitude", value=0.0)
with col2:
    manual_lon = st.number_input("Longitude", value=0.0)

if st.button("Show Manual Location"):
    st.map({
        "lat": [manual_lat],
        "lon": [manual_lon]
    })

# Help information
st.divider()
st.subheader("Troubleshooting")
st.markdown("""
If you're having trouble getting your location:

1. **Browser permissions**: Check that you've allowed location access in your browser
2. **Device settings**: Make sure location services are enabled on your device
3. **Browser compatibility**: Try a different browser like Chrome or Edge
4. **Network**: Some networks block location requests
5. **HTTPS**: Location services work best on secure websites (HTTPS)
""")