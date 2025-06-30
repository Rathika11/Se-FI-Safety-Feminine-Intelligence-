import streamlit as st
import streamlit_js_eval

st.title("Simplified JS Eval Test")

st.write("Testing if streamlit-js-eval is working properly")

# Display session state for debugging
st.subheader("Current Session State")
st.write("Keys in session state:", list(st.session_state.keys()))

# Simple test that doesn't rely on promises
st.subheader("Basic Test")
test_result = streamlit_js_eval.streamlit_js_eval(
    js_expressions="1 + 1",
    want_output=True,
    key="basic_test"
)

st.write("JavaScript evaluation initiated. Check if session state updates.")

# Check if result is in session state
if "basic_test" in st.session_state:
    st.success(f"Basic test result: {st.session_state['basic_test']}")
    st.write("streamlit-js-eval is working correctly!")
    # Remove key from session state
    del st.session_state["basic_test"]
else:
    st.warning("Waiting for result to appear in session state...")
    st.write("Try refreshing the page if this message persists.")

# Button to test location
st.subheader("Location Test")
st.write("Click the button below to test geolocation")

if st.button("Test Location"):
    st.info("Requesting location...")
    
    # Try to get location - wrapped in try/except to avoid errors
    try:
        streamlit_js_eval.streamlit_js_eval(
            js_expressions="""
            new Promise((resolve) => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            resolve({
                                success: true,
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude
                            });
                        },
                        function(error) {
                            resolve({
                                success: false,
                                errorMessage: error.message,
                                errorCode: error.code
                            });
                        }
                    );
                } else {
                    resolve({
                        success: false,
                        errorMessage: "Geolocation not supported"
                    });
                }
            });
            """,
            want_output=True,
            key="location_test"
        )
        st.success("Location request sent to browser")
    except Exception as e:
        st.error(f"Error running JavaScript: {e}")

# Check if location result is available
if "location_test" in st.session_state:
    location_result = st.session_state["location_test"]
    st.write("Raw location result:", location_result)
    
    # Handle the result based on its type
    if location_result is None:
        st.warning("Result is None. This might indicate a problem with streamlit-js-eval")
    elif isinstance(location_result, dict):
        if location_result.get("success") == True:
            st.success("Location successfully retrieved!")
            st.write(f"Latitude: {location_result.get('latitude')}")
            st.write(f"Longitude: {location_result.get('longitude')}")
            
            # Show on map
            try:
                map_data = {
                    "lat": [location_result.get("latitude")],
                    "lon": [location_result.get("longitude")]
                }
                st.map(map_data)
            except Exception as e:
                st.error(f"Error displaying map: {e}")
        else:
            st.error(f"Error getting location: {location_result.get('errorMessage', 'Unknown error')}")
    else:
        st.warning(f"Unexpected result type: {type(location_result)}")
    
    # Button to clear result
    if st.button("Clear Result"):
        del st.session_state["location_test"]
        st.experimental_rerun()

# Show troubleshooting info
st.subheader("Troubleshooting")
st.markdown("""
If you're having issues:

1. Make sure location is enabled in your browser
2. Try running this in Chrome or Edge
3. Be patient - location requests can take time
""")

# Extra information for debugging
st.divider()
st.subheader("Technical Information")
st.code(f"""
Python version: {st.__version__}
streamlit-js-eval version: {streamlit_js_eval.__version__}
""")