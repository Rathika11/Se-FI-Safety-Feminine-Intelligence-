import streamlit as st
import time
# import base64 # Removed base64 import as background image is removed
import os      # Keep os for path manipulation (e.g., loading CSVs)
import pandas as pd # Import pandas for reading CSV

# Import db module for contact management (MongoDB)
# Make sure your db.py file is in the same directory or accessible
try:
    import db
except ImportError:
    # Define dummy functions if db.py is not found
    class DummyDB:
        def get_contacts(self, user_id):
            print("Dummy db.get_contacts called. Please implement db.py.")
            st.warning("Database module (db.py) not found. Contact functionality disabled.")
            return []
        # Add other dummy db functions if needed by dashboard.py
        def get_user_by_email(self, email):
            print("Dummy db.get_user_by_email called.")
            return None # Assume user not found
        def verify_user(self, email, password):
            print("Dummy db.verify_user called.")
            return None # Assume login failed
        def add_contact(self, user_id, contact):
            print("Dummy db.add_contact called.")
            st.warning("Database module (db.py) not found. Cannot add contact.")
            return None # Indicate failure
        def update_contact(self, user_id, contact_id, contact):
            print("Dummy db.update_contact called.")
            st.warning("Database module (db.py) not found. Cannot update contact.")
            return False # Indicate failure
        def delete_contact(self, user_id, contact_id):
            print("Dummy db.delete_contact called.")
            st.warning("Database module (db.py) not found. Cannot delete contact.")
            return False # Indicate failure
        def register_user(self, user_data):
            print("Dummy db.register_user called.")
            st.warning("Database module (db.py) not found. Cannot register user.")
            return None # Indicate failure


    db = DummyDB()
    st.error("Database module (db.py) not found. Please ensure db.py is in the correct directory.")


# Import geopy for reverse geocoding and distance calculation
# you'll need to install this: pip install geopy
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderUnavailable # Import specific exceptions
    from geopy.distance import geodesic # Import geodesic for distance calculation
    _GEOPY_AVAILABLE = True
except ImportError:
    st.error("Geopy library not found. Please install it: pip install geopy")
    _GEOPY_AVAILABLE = False
    # Define dummy function if geopy is missing
    def get_address_from_coords(latitude, longitude):
        print("Dummy get_address_from_coords called. Geopy not available.")
        return {"error": "Geopy library not installed", "source": "Dummy Geopy"}
    # Define a dummy distance function
    def geodesic(coords1, coords2):
        print("Dummy geodesic distance called. Geopy not available.")
        # Return a dummy object with an infinite km attribute
        class DummyDistance:
            def __init__(self):
                self.km = float('inf')
        return DummyDistance()


# Import email_alert module (make sure email_alert.py exists and is configured)
try:
    from email_alert import send_alert_email
    _EMAIL_ALERT_AVAILABLE = True
except ImportError:
    # Define a dummy function if the actual module is not found
    def send_alert_email(contacts, location=None, video_link=None):
        print("Dummy send_alert_email function called. Please implement the actual email sending logic.")
        print(f"Dummy email details:")
        print(f"Contacts: {contacts}")
        # Use the email_body_string if available, otherwise fall back
        email_body = location.get('email_body_string', 'Location details not available.') if location else 'Location details not available.'
        print(f"Location Info (via email_body_string): {email_body[:200]}...") # Print first 200 chars
        st.error("Dummy email function used. No actual email sent. Check email_alert.py import.")

    st.error("Email alert module (email_alert.py) not found. Email alerts disabled.")
    _EMAIL_ALERT_AVAILABLE = False


# Import the streamlit-js-eval library directly into dashboard.py
# Need to install streamlit-js-eval: pip install streamlit-js-eval
try:
    import streamlit_js_eval
    _STREAMLIT_JS_EVAL_AVAILABLE = True
except ImportError:
    st.error("streamlit-js-eval library not found. Please install it: pip install streamlit-js-eval")
    # Define a dummy function/object if the library is missing
    class DummyJS:
        def streamlit_js_eval(self, js_expressions, want_output=False, key=None):
            st.warning("Dummy streamlit_js_eval used. Geolocation not available.")
            # Return a dummy error structure like the component would on failure
            # Need to put this in session state to mimic the component behavior
            if key:
                st.session_state[key] = {'error': 'streamlit-js-eval not installed', 'source': 'Dummy JS'}
            # Return None or similar if want_output is False
            if want_output:
                return {'error': 'streamlit-js-eval not installed', 'source': 'Dummy JS'}
            else:
                return None

    streamlit_js_eval = DummyJS()


# --- Location Key (Must be unique and used by streamlit-js-eval component) ---
# This key is used to store and retrieve the location result in st.session_state
_DASHBOARD_LOCATION_KEY = "dashboard_location_data_component_result"

# --- Session State Initialization (Dashboard Specific) ---
# Ensure these keys exist in session state (some initialized in app.py)
if 'user' not in st.session_state: st.session_state.user = None
if 'sos_triggered' not in st.session_state: st.session_state.sos_triggered = False # Not strictly needed here, but kept

# Add session state for the *actual* last known location data and source for display/email
if 'last_known_location_data' not in st.session_state: st.session_state.last_known_location_data = None # Raw lat/lon from browser
if 'last_known_location_source' not in st.session_state: st.session_state.last_known_location_source = "Not available (Initial)"

if 'address_details' not in st.session_state: st.session_state.address_details = None # Detailed address from geopy

# Add session state for the user's contacts list, loaded from DB on dashboard load
if 'dashboard_contacts_list' not in st.session_state: st.session_state.dashboard_contacts_list = []

# Add session state for a general processing flag to disable buttons while SOS sequence is active
if 'sos_button_processing' not in st.session_state: st.session_state.sos_button_processing = False

# Add session state for nearest services results
if 'nearest_hospitals' not in st.session_state: st.session_state.nearest_hospitals = None
if 'nearest_police_stations' not in st.session_state: st.session_state.nearest_police_stations = None


# Add placeholders for status and location display (defined at the top of the script)
# Define these outside the function so they persist across reruns
# and can be accessed globally if needed by other helper functions called from the main dashboard function
sos_status_placeholder = st.empty()
location_display_placeholder = st.empty()
nearest_services_placeholder = st.empty() # Placeholder for nearest services display


# --- Load Service Datasets ---
# Use st.cache_data to load the datasets only once
@st.cache_data
def load_service_data(hospital_csv_path, police_csv_path):
    """
    Loads hospital and police station data from CSV files.
    Includes checks for file existence, column validity, and data integrity.
    Returns two dataframes and any loading errors encountered.
    """
    hospital_df = None
    police_df = None
    load_errors = []

    # --- Load Hospital Data ---
    try:
        if not os.path.exists(hospital_csv_path):
            load_errors.append(f"Hospital CSV file not found: {os.path.basename(hospital_csv_path)}. Hospital data will not be available.")
        else:
            hospital_df = pd.read_csv(hospital_csv_path)
            print(f"Successfully loaded hospital data from {os.path.basename(hospital_csv_path)}. Shape: {hospital_df.shape}") # Debug

            # Define required columns for search and display (adjust 'id' if name column is different)
            required_hosp_cols_for_search = ['Latitude', 'Longitude', 'id'] # Assuming 'id' is used as name_col
            missing_hosp_cols_for_search = [col for col in required_hosp_cols_for_search if col not in hospital_df.columns]

            if missing_hosp_cols_for_search:
                load_errors.append(f"Hospital CSV ({os.path.basename(hospital_csv_path)}) missing essential columns for search: {', '.join(missing_hosp_cols_for_search)}. Hospital data will not be available for search.")
                hospital_df = None # Invalidate if essential coordinate/name columns are missing
            elif hospital_df.empty:
                load_errors.append(f"Hospital CSV file is empty after reading: {os.path.basename(hospital_csv_path)}. Hospital data will not be available.")
                hospital_df = None
            else:
                # Ensure lat/lon are numeric, drop rows with invalid coords and missing 'id'
                hospital_df['Latitude'] = pd.to_numeric(hospital_df['Latitude'], errors='coerce')
                hospital_df['Longitude'] = pd.to_numeric(hospital_df['Longitude'], errors='coerce')
                # Drop rows where lat or lon became NaN after coercion or 'id' is missing/empty string
                hospital_df.dropna(subset=['Latitude', 'Longitude', 'id'], inplace=True)
                # Also drop rows where 'id' might be an empty string after reading/dropna
                hospital_df = hospital_df[hospital_df['id'].astype(str).str.strip() != '']


                if hospital_df.empty:
                    load_errors.append(f"Hospital data became empty after cleaning invalid coordinates/names or missing names. Hospital data will not be available for search.")
                    hospital_df = None
                else:
                    print(f"Hospital data after cleaning: {hospital_df.shape}") # Debug
                    # Optional: Add checks for *other* expected columns if needed for display
                    # if 'City' not in hospital_df.columns:
                    #     load_errors.append(f"Hospital CSV missing 'City' column. Address details might be incomplete.")

    except pd.errors.EmptyDataError:
            load_errors.append(f"Hospital CSV file is empty: {os.path.basename(hospital_csv_path)}. Hospital data will not be available.")
            hospital_df = None
    except Exception as e:
        load_errors.append(f"Error loading hospital CSV ({os.path.basename(hospital_csv_path)}): {e}. Hospital data will not be available.")
        hospital_df = None

    # --- Load Police Station Data ---
    try:
        if not os.path.exists(police_csv_path):
            load_errors.append(f"Police Station CSV file not found: {os.path.basename(police_csv_path)}. Police station data will not be available.")
        else:
            police_df = pd.read_csv(police_csv_path)
            print(f"Successfully loaded police station data from {os.path.basename(police_csv_path)}. Shape: {police_df.shape}") # Debug

            # Define required columns for search and display
            required_police_cols_for_search = ['lat', 'lng', 'name']
            missing_police_cols_for_search = [col for col in required_police_cols_for_search if col not in police_df.columns]

            if missing_police_cols_for_search:
                load_errors.append(f"Police Station CSV ({os.path.basename(police_csv_path)}) missing essential columns for search: {', '.join(missing_police_cols_for_search)}. Police station data will not be available for search.")
                police_df = None # Invalidate if essential coordinate/name columns are missing
            elif police_df.empty:
                load_errors.append(f"Police Station CSV file is empty after reading: {os.path.basename(police_csv_path)}. Police station data will not be available.")
                police_df = None
            else:
                # Ensure lat/lng are numeric, drop rows with invalid coords and missing name
                police_df['lat'] = pd.to_numeric(police_df['lat'], errors='coerce')
                police_df['lng'] = pd.to_numeric(police_df['lng'], errors='coerce')
                # Drop rows where lat or lng became NaN after coercion OR 'name' is missing/empty string
                police_df.dropna(subset=['lat', 'lng', 'name'], inplace=True)
                # Also drop rows where 'name' might be an empty string after reading/dropna
                police_df = police_df[police_df['name'].astype(str).str.strip() != '']


                if police_df.empty:
                    load_errors.append(f"Police data became empty after cleaning invalid coordinates/names or missing names. Police station data will not be available for search.")
                    police_df = None
                else:
                    print(f"Police data after cleaning: {police_df.shape}") # Debug
                    # Optional: Add checks for *other* expected columns if needed for display
                    # if 'address' not in police_df.columns:
                    #     load_errors.append(f"Police Station CSV missing 'address' column. Address details might be incomplete.")


    except pd.errors.EmptyDataError:
            load_errors.append(f"Police Station CSV file is empty: {os.path.basename(police_csv_path)}. Police station data will not be available.")
            police_df = None
    except Exception as e:
        load_errors.append(f"Error loading police station CSV ({os.path.basename(police_csv_path)}): {e}. Police station data will not be available.")
        police_df = None


    # Display data loading errors immediately within this function's scope when called
    if load_errors:
        for error in load_errors:
            st.error(f"Data Loading Error: {error}")
            print(f"Logged Data Loading Error: {error}") # Also print to console


    # Return both dataframes
    return hospital_df, police_df

# --- Helper Function for Reverse Geocoding ---
# Only define and use if geopy is available
if _GEOPY_AVAILABLE:
    def get_address_from_coords(latitude, longitude):
        """
        Convert latitude and longitude to a detailed address using Nominatim.
        Returns a dictionary of address components or None/error dict on error.
        Includes basic input validation.
        """
        # Skip if latitude or longitude are None or clearly invalid
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            print("Invalid latitude or longitude type provided for geocoding.")
            return {"error": "Invalid coordinates type provided", "source": "Nominatim Prep Error"}
        if latitude is None or longitude is None: # Should be covered by type check but double-check
            print("None latitude or longitude provided for geocoding.")
            return {"error": "None coordinates provided", "source": "Nominatim Prep Error"}


        try:
            geolocator = Nominatim(user_agent="women_safety_app")
            print(f"Attempting reverse geocoding for {latitude}, {longitude} using Nominatim...") # Debug print
            # Use timeout for robustness
            location = geolocator.reverse((latitude, longitude), exactly_one=True, timeout=15) # Increased timeout slightly
            print(f"Nominatim raw response: {location.raw if location else 'None'}") # Debug print raw response

            if location and location.raw.get('address'):
                address = location.raw['address']
                address_details = {
                    'full_address': location.address,
                    'house_number': address.get('house_number', 'N/A'),
                    'building': address.get('building', 'N/A'),
                    'road': address.get('road', 'N/A'),
                    'street': address.get('street', address.get('road', 'N/A')), # Use road if street is missing
                    'neighbourhood': address.get('neighbourhood', 'N/A'),
                    'suburb': address.get('suburb', 'N/A'),
                    'city': address.get('city', address.get('town', address.get('village', 'N/A'))), # Handle variations
                    'district': address.get('district', address.get('county', 'N/A')), # Handle variations
                    'state': address.get('state', 'N/A'),
                    'postcode': address.get('postcode', 'N/A'),
                    'country': address.get('country', 'N/A'),
                    'source': 'Nominatim'
                }
                print(f"Successfully retrieved address details from Nominatim: {address_details}")
                return address_details
            else:
                print("No address details found for the coordinates using Nominatim.")
                return {"error": "No detailed address found for coordinates", "source": "Nominatim"}
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            print(f"Geocoding service error (timeout or unavailable): {e}")
            return {"error": f"Geocoding service error: {e}", "source": "Nominatim API Error"}
        except Exception as e:
            print(f"An unexpected error occurred during reverse geocoding: {e}")
            return {"error": f"Reverse geocoding failed: {e}", "source": "Nominatim Processing Error"}

# --- Helper Function to Find Nearest Services ---
# Only define and use if geopy is available
if _GEOPY_AVAILABLE:
    # Added radius_km parameter with a default of infinity
    def find_nearest_services(user_lat, user_lon, services_df, service_type='Service', name_col='Name', lat_col='Latitude', lon_col='Longitude', num_results=5, radius_km=10.0): # Default radius to 10 km
        """
        Finds the nearest services from a pandas DataFrame based on user coordinates.
        Can filter by a specified radius (km) or return the top N results.
        Assumes DataFrame has Latitude, Longitude, and Name columns (as specified by lat_col, lon_col, name_col).
        Returns a list of dictionaries for the nearest services, including distance,
        or an error/info dictionary.
        """
        nearest_list = []

        if services_df is None or services_df.empty:
            print(f"Warning: Service DataFrame ({service_type}) is empty or None.")
            return [{"info": f"No {service_type} data available to search."}]

        # Check if required columns actually exist in the dataframe before proceeding
        required_cols = [lat_col, lon_col, name_col]
        # Check if *all* required columns exist
        if not all(col in services_df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in services_df.columns]
            print(f"Error: Missing essential columns {missing} in {service_type} DataFrame for search.")
            return [{"error": f"Data for {service_type} is missing essential columns for search: {', '.join(missing)}."}]

        # Create user coordinates tuple
        user_coords = (user_lat, user_lon)

        # Calculate distances
        try:
            # Use .copy() to avoid SettingWithCopyWarning
            services_df_temp = services_df.copy()

            # Ensure coordinate columns are numeric before calculating distance
            services_df_temp[lat_col] = pd.to_numeric(services_df_temp[lat_col], errors='coerce')
            services_df_temp[lon_col] = pd.to_numeric(services_df_temp[lon_col], errors='coerce')

            services_df_temp['distance_km'] = services_df_temp.apply(
                lambda row: geodesic(user_coords, (row[lat_col], row[lon_col])).km if pd.notnull(row[lat_col]) and pd.notnull(row[lon_col]) else float('inf'),
                axis=1
            )

            # Filter out rows where distance calculation failed (coords were not valid numbers)
            filtered_services = services_df_temp[services_df_temp['distance_km'] != float('inf')]

            if filtered_services.empty:
                return [{"info": f"No {service_type} found in the dataset with valid coordinates."}]

            # --- Filter by radius if specified ---
            if radius_km is not None and radius_km != float('inf'):
                nearby_services = filtered_services[filtered_services['distance_km'] <= radius_km]
                sorted_services = nearby_services.sort_values(by='distance_km')

                if sorted_services.empty:
                    return [{"info": f"No {service_type} found within {radius_km} km based on available data."}]

                # Limit by num_results *after* filtering by radius if both are specified and valid
                if num_results is not None and num_results > 0:
                    services_to_return = sorted_services.head(num_results)
                else:
                    services_to_return = sorted_services # Return all within radius if num_results is not specified or invalid

            # --- Otherwise, return the top N results (fallback) ---
            else:
                sorted_services = filtered_services.sort_values(by='distance_km')
                # Use the num_results parameter here if radius is not used
                if num_results is not None and num_results > 0:
                    services_to_return = sorted_services.head(num_results)
                else:
                    services_to_return = sorted_services # Return all if neither radius nor num_results is specified/valid


            if services_to_return.empty:
                # This might happen if radius was tight or num_results was 0/None
                return [{"info": f"No {service_type} found matching search criteria (within radius or top N)."}]

            # Format results from services_to_return DataFrame
            for index, row in services_to_return.iterrows():
                # Attempt to get Address from common column names if 'Address' doesn't exist
                # Prioritize a column named 'address' or 'Address'
                address = row.get('address', row.get('Address', row.get('Location', 'N/A Address')))

                nearest_list.append({
                    'Type': service_type,
                    'Name': row.get(name_col, f'Unknown {service_type}'), # Use get with default
                    'Latitude': row.get(lat_col, 'N/A'),
                    'Longitude': row.get(lon_col, 'N/A'),
                    'Distance (km)': round(row['distance_km'], 2), # Round distance
                    'Address': address
                })

            if not nearest_list and not services_to_return.empty:
                # If nearest_list is empty after formatting (e.g. name_col issues)
                return [{"info": f"Found locations within radius/top N, but could not format details for {service_type} (missing name column?)."}]


        except Exception as e:
            print(f"Error finding nearest {service_type} services: {e}")
            return [{"error": f"Error finding nearest {service_type}: {e}"}]

        return nearest_list

# --- Helper Function to Send Email Alert (Defined within dashboard.py scope) ---
# This function is called *after* location data is processed and available
# Only define and use if email_alert is available
if _EMAIL_ALERT_AVAILABLE:
    def send_sos_email_alert():
        global sos_status_placeholder  # Need to access global placeholder

        print(f"\n--- Preparing Email Alert ---")  # Debug print

        user_name = st.session_state.user.get('name', 'User')
        user_email = st.session_state.user.get('email', 'N/A User')
        # Use the data exactly as it was retrieved/processed
        location_data = st.session_state.get('last_known_location_data')
        address_details = st.session_state.get('address_details') # Get detailed address
        nearest_hospitals = st.session_state.get('nearest_hospitals') # Get nearest services
        nearest_police_stations = st.session_state.get('nearest_police_stations') # Get nearest services


        contacts_to_notify = st.session_state.get('dashboard_contacts_list', [])
        # Filter for valid email addresses
        contact_emails = [contact['email'] for contact in contacts_to_notify
                            if isinstance(contact, dict) and 'email' in contact and contact['email'] and "@" in str(contact['email'])]

        if not contact_emails:
            print("Warning: Email sending skipped because contacts list is empty after processing.")
            sos_status_placeholder.warning("No valid email contacts found for sending.")
            # Clear processing flag immediately if no contacts to notify
            st.session_state.sos_button_processing = False
            st.session_state.last_known_location_source = "SOS Failed (No email contacts)"
            return

        print(f"Notifying contacts: {contact_emails}")

        body = f"URGENT: SOS Alert from {user_name} ({user_email})!\n\n"
        body += "Please check on them immediately.\n\n"

        # --- Building Email Body based on available data ---
        body += "--- Last Known Location Details ---\n"
        if location_data is not None and isinstance(location_data, dict):
            # Check for error FIRST from browser geolocation
            if 'error' in location_data:
                body += f"Could not retrieve initial location details: {location_data['error']}\n"
                body += f"Source: {location_data.get('source', 'Browser Geolocation Error')}\n"
            # Then check for valid coordinates if no error
            elif 'latitude' in location_data and 'longitude' in location_data:
                lat = location_data['latitude']
                lon = location_data['longitude']
                acc = location_data.get('accuracy', 'Unknown')
                src = location_data.get('source', 'N/A')
                body += f"Source: {src}\n"
                body += f"Coordinates: Latitude {lat}, Longitude {lon}\n"
                body += f"Accuracy: {acc} meters\n"
                # Use the modern Google Maps URL format
                Maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                body += f"View Location on Map: {Maps_link}\n"

                # Add detailed address information if available from Nominatim
                body += "\nAddress Details (if available):\n"
                if address_details:
                    if address_details.get('error'):
                        body += f"  Address Lookup Error: {address_details['error']}\n"
                    elif address_details.get('info'): # Handle info messages from geocoding failure
                        body += f"  Address Lookup Info: {address_details['info']}\n"
                    elif address_details.get('full_address'):
                        body += f"  Full Address: {address_details['full_address']}\n"
                        # Add specific components if available and not 'N/A'
                        if address_details.get('street') and address_details['street'] != 'N/A': body += f"  Street/Road: {address_details['street']}\n"
                        if address_details.get('house_number') and address_details['house_number'] != 'N/A': body += f"  House/Building: {address_details['house_number']}\n"
                        if address_details.get('neighbourhood') and address_details['neighbourhood'] != 'N/A': body += f"  Neighborhood: {address_details['neighbourhood']}\n"
                        if address_details.get('suburb') and address_details.get('suburb') != 'N/A': body += f"  Suburb: {address_details.get('suburb')}\n"
                        if address_details.get('city') and address_details.get('city') != 'N/A': body += f"  City: {address_details.get('city')}\n"
                        if address_details.get('district') and address_details.get('district') != 'N/A': body += f"  District: {address_details.get('district')}\n"
                        if address_details.get('state') and address_details.get('state') != 'N/A': body += f"  State: {address_details.get('state')}\n"
                        if address_details.get('postcode') and address_details.get('postcode') != 'N/A': body += f"  Postal Code: {address_details.get('postcode')}\n"
                        if address_details.get('country') and address_details.get('country') != 'N/A': body += f"  Country: {address_details.get('country')}\n"
                    else:
                        body += "  Detailed address information could not be parsed.\n"
                else:
                    body += "  Detailed address information not available.\n" # Case where address_details is None or empty


            else: # Handle unexpected location_data format
                body += "Location data available but format is unexpected.\n"
        else: # This else is for the outer if location_data is None or not a dict
            body += "Location information not available.\n"
        body += "---------------------------------------\n\n"


        # --- Add Nearest Services Details to Email Body ---
        body += "--- Nearest Emergency Services (if available) ---\n"
        services_added = False

        # Hospitals
        if isinstance(nearest_hospitals, list) and nearest_hospitals:
            # Check if it's an error/info message or actual results
            if nearest_hospitals[0].get('error'):
                body += f"Nearest Hospitals: {nearest_hospitals[0]['error']}\n"
                services_added = True
            elif nearest_hospitals[0].get('info'):
                body += f"Nearest Hospitals: {nearest_hospitals[0]['info']}\n"
                services_added = True
            else: # Actual list of services
                body += "Nearest Hospitals:\n"
                for hosp in nearest_hospitals:
                    hosp_name = hosp.get('Name', 'Unknown Hospital')
                    hosp_dist = hosp.get('Distance (km)', 'N/A')
                    hosp_addr = hosp.get('Address', 'N/A')
                    hosp_lat = hosp.get('Latitude')
                    hosp_lon = hosp.get('Longitude')

                    item_line = f"- {hosp_name} ({hosp_dist} km)"
                    if hosp_addr != 'N/A': item_line += f", Address: {hosp_addr}"
                    if hosp_lat is not None and hosp_lon is not None:
                        hosp_map_link = f"https://www.google.com/maps/search/?api=1&query={hosp_lat},{hosp_lon}"
                        item_line += f" [Map: {hosp_map_link}]"
                    body += item_line + "\n"
                services_added = True

        # Police Stations
        if isinstance(nearest_police_stations, list) and nearest_police_stations:
            if nearest_police_stations[0].get('error'):
                body += f"Nearest Police Stations: {nearest_police_stations[0]['error']}\n"
                services_added = True
            elif nearest_police_stations[0].get('info'):
                body += f"Nearest Police Stations: {nearest_police_stations[0]['info']}\n"
                services_added = True
            else: # Actual list of services
                body += "Nearest Police Stations:\n"
                for station in nearest_police_stations:
                    police_name = station.get('Name', 'Unknown Police Station')
                    police_dist = station.get('Distance (km)', 'N/A')
                    police_addr = station.get('Address', 'N/A')
                    police_lat = station.get('Latitude') # Get raw lat/lon
                    police_lon = station.get('Longitude') # Get raw lat/lon

                    item_line = f"- {police_name} ({police_dist} km)"
                    if police_addr != 'N/A': item_line += f", Address: {police_addr}"
                    if police_lat is not None and police_lon is not None:
                        police_map_link = f"https://www.google.com/maps/search/?api=1&query={police_lat},{police_lon}"
                        item_line += f" [Map: {police_map_link}]"
                    body += item_line + "\n"
                services_added = True

        if not services_added:
            body += "No nearest emergency service data available.\n"

        body += "-------------------------------------------\n\n"


        body += "This is an automated alert from the Women Safety App."
        body += f"\nTimestamp (IST): {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"

        email_subject = f"EMERGENCY ALERT from {user_name}!"

        try:
            print("Attempting to send email via send_alert_email function...")
            # Call the function from the imported email_alert module
            # Pass the raw location data, detailed address, and the full body string
            send_alert_email(
                contacts=contact_emails,
                location={'raw': location_data, 'detailed': address_details, 'email_body_string': body},
                video_link=None # Assuming no video link is used in this flow
            )
            print("Email sending function called successfully.")
            # Display success message after the attempt
            sos_status_placeholder.success("SOS alert email sent to your trusted contacts.")

        except Exception as e:
            # Catch any exceptions during email sending (e.g., SMTP errors)
            print(f"Email Sending Failed: {e}")
            sos_status_placeholder.error(f"Failed to send SOS email alert: {e}")

        finally:
            # Clear general processing flag regardless of email success/failure
            print("Dashboard: Email sending finished, clearing processing flag.")
            st.session_state.sos_button_processing = False

# --- Helper function to handle button actions (page navigation) ---
def handle_dashboard_action(action):
    """Handles navigation and state cleanup when leaving the dashboard."""
    # Reset SOS trigger state and clear related data when navigating away
    st.session_state.sos_triggered = False
    st.session_state.last_known_location_data = None  # Clear location data (raw)
    st.session_state.last_known_location_source = "Not available (Navigated away)"  # Clear source
    st.session_state.sos_button_processing = False  # Reset general processing flag
    st.session_state.dashboard_contacts_list = []  # Clear contacts list on navigation
    st.session_state.address_details = None  # Clear address details from Nominatim

    # Clear nearest services results when navigating away
    st.session_state.nearest_hospitals = None
    st.session_state.nearest_police_stations = None

    # Also clear the component result key from session state just in case
    if _DASHBOARD_LOCATION_KEY in st.session_state:
        del st.session_state[_DASHBOARD_LOCATION_KEY]

    # Clear the location display, status messages, and nearest services on the dashboard (best effort)
    global sos_status_placeholder, location_display_placeholder, nearest_services_placeholder
    sos_status_placeholder.empty()
    location_display_placeholder.empty()
    nearest_services_placeholder.empty()

    # Set the new page state and rerun
    if action == "logout":
        # Clear session state relevant to a logged-in user
        keys_to_clear = ['page', 'user', 'sos_triggered', 'sos_pending_location',
                         'last_known_location_data', 'last_known_location',
                         'last_known_location_source', 'sos_button_processing',
                         'dashboard_contacts_list', 'user_contacts', 'address_details',
                         'nearest_hospitals', 'nearest_police_stations', _DASHBOARD_LOCATION_KEY] # Include component key
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()  # Trigger immediate navigation
    elif action in st.session_state.get('pages', {}): # Check if the action corresponds to a registered page
        st.session_state.page = action
        st.rerun()
    else:
        st.warning(f"Navigation attempted for unknown action: {action}")

# --- Main Dashboard Rendering Function ---
def dashboard():
    global sos_status_placeholder, location_display_placeholder, nearest_services_placeholder # Access global placeholders

    # --- Custom CSS for enhanced UI (Inspired by provided images) ---
    st.markdown("""
    <style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    /* Define Keyframes for Background Animation */
    @keyframes gradient-animation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Main App Container Styling */
    body {
        font-family: 'Poppins', sans-serif !important;
        color: #333333; /* Default dark text for light backgrounds */
    }

    .stApp {
        /* Light Lavender/Purple Animated Gradient Background */
        background: linear-gradient(180deg, #EDE7F6, #D1C4E9, #B39DDB, #9575CD);
        background-size: 200% 200%;
        animation: gradient-animation 25s ease infinite;
    }

    /* Main Content Area Background */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.9); /* Frosted glass effect */
        padding: 25px;
        border-radius: 12px; /* Moderately rounded corners */
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        margin-top: -40px; /* Adjust as needed */
        color: #333333; /* Dark text for content */
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif !important;
        color: #6A1B9A; /* Darker Purple for headers */
        text-shadow: none; /* Remove previous shadow if background is light */
        margin-bottom: 0.7rem;
        padding-bottom: 0.2rem;
        position: relative;
    }
    h1 {
        color: #4A148C; /* Even darker for main title */
        text-align: center;
        margin-bottom: 1.5rem;
    }
    /* Custom header underline effect for h2, h3, h4 */
    h2::after, h3::after, h4::after {
        content: '';
        position: absolute;
        left: 0;
        bottom: -2px;
        width: 40px;
        height: 3px;
        background-color: #9C27B0; /* Medium Purple */
        border-radius: 2px;
    }
     h1::after { content: none; }


    /* Separators */
    hr {
        border-top: 1px solid rgba(156, 39, 176, 0.3); /* Lighter purple */
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }

    /* General Button Styling (Navigation buttons) */
    div[data-testid="stButton"] > button {
        font-family: 'Poppins', sans-serif !important;
        width: 100%;
        margin-bottom: 10px;
        padding: 12px 18px;
        border-radius: 8px; /* Rounded rectangle */
        border: 1px solid #D1C4E9; /* Light lavender border */
        background-color: #FFFFFF; /* White background */
        color: #5E35B1; /* Deep purple text */
        font-size: 15px;
        font-weight: 600;
        transition: all 0.25s ease;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        text-transform: none; /* Normal case for better readability */
        box-shadow: 0 2px 5px rgba(0,0,0,0.08);
    }
    div[data-testid="stButton"] > button:hover {
        box-shadow: 0 4px 10px rgba(94, 53, 177, 0.2);
        transform: translateY(-2px);
        background-color: #F3E5F5; /* Very light purple tint on hover */
        border-color: #B39DDB;
        color: #4527A0;
    }
    div[data-testid="stButton"] > button:active {
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transform: translateY(0);
        background-color: #EDE7F6;
    }

    /* SOS Button Styling - Kept distinct and prominent */
    .sos-button-container div[data-testid="stButton"] > button {
        font-family: 'Poppins', sans-serif !important;
        background: linear-gradient(90deg, #FF5252, #D32F2F); /* Bright to Dark Red */
        color: white;
        border: none;
        font-weight: 700;
        font-size: 17px;
        padding: 18px 30px;
        margin-top: 25px;
        margin-bottom: 20px;
        box-shadow: 0 5px 20px rgba(255, 82, 82, 0.7);
        border-radius: 30px; /* Pill shape for SOS */
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }
    .sos-button-container div[data-testid="stButton"] > button:hover {
        background: linear-gradient(90deg, #D32F2F, #FF5252);
        box-shadow: 0 8px 25px rgba(255, 82, 82, 0.9);
        transform: translateY(-3px);
    }
    .sos-button-container div[data-testid="stButton"] > button:active {
        background: linear-gradient(90deg, #C62828, #E53935);
        box-shadow: 0 2px 10px rgba(255, 82, 82, 0.5);
        transform: translateY(0);
    }

    /* Columns Gap */
    div[data-testid="stHorizontalBlock"] {
        gap: 20px;
    }

    /* Alert Boxes - Keeping existing high-contrast styling */
    div[data-testid="stAlert"] {
        margin-bottom: 18px;
        padding: 18px;
        border-radius: 8px;
        border-left: 8px solid;
        opacity: 0.98;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-size: 15px;
        font-family: 'Roboto', sans-serif !important;
    }
    div[data-testid="stAlert"] > div > div > div > p { font-family: 'Roboto', sans-serif !important; font-weight: 400 !important; }

    div[data-testid="stAlert"].stError { background-color: #FFEBEE; color: #B71C1C; border-color: #E57373; }
    div[data-testid="stAlert"].stError > div > div > div > p { color: #B71C1C !important; }
    div[data-testid="stAlert"].stWarning { background-color: #FFF8E1; color: #F57F17; border-color: #FFB300; }
    div[data-testid="stAlert"].stWarning > div > div > div > p { color: #F57F17 !important; }
    div[data-testid="stAlert"].stSuccess { background-color: #E8F5E9; color: #2E7D32; border-color: #81C784; }
    div[data-testid="stAlert"].stSuccess > div > div > div > p { color: #2E7D32 !important; }
    div[data-testid="stAlert"].stInfo { background-color: #E3F2FD; color: #1565C0; border-color: #64B5F6; }
    div[data-testid="stAlert"].stInfo > div > div > div > p { color: #1565C0 !important; }


    /* Location Details & Nearest Services Boxes */
    .location-details, .nearest-services {
        margin-top: 20px;
        padding: 20px;
        background-color: rgba(255, 255, 255, 0.8); /* Light, slightly transparent */
        border-radius: 10px;
        color: #333333; /* Dark text */
        box-shadow: 0 3px 10px rgba(0,0,0,0.07);
        font-family: 'Roboto', sans-serif;
        font-size: 15px;
    }
    .location-details { border-left: 5px solid #9C27B0; } /* Plum */
    .nearest-services { border-left: 5px solid #7E57C2; } /* Deep Purple */

    .location-details p, .location-details div[data-testid="stVerticalBlock"] > div > div > p,
    .nearest-services p, .nearest-services li, .nearest-services div[data-testid="stVerticalBlock"] > div > div > p {
        color: #333333 !important;
        font-family: 'Roboto', sans-serif !important;
        font-weight: 400 !important;
        font-size: 15px;
    }

    .location-details .streamlit-expander {
        background-color: rgba(237, 231, 246, 0.7); /* Lighter purple tint */
        border-radius: 8px;
        margin-top: 10px;
        padding: 5px 12px;
    }
    .location-details .streamlit-expander span p {
        color: #5E35B1 !important;
        font-weight: 600 !important;
        font-family: 'Poppins', sans-serif !important;
    }

    .nearest-services h4 {
        color: #7E57C2; /* Match border accent */
        margin-bottom: 8px;
        padding-left: 0; /* remove extra padding for h4 in this box */
    }
     .nearest-services h4::after { content: none; } /* remove underline for h4 in this box */

    .nearest-services ul { list-style: none; padding: 0; }
    .nearest-services li {
        background-color: rgba(237, 231, 246, 0.5); /* Subtle purple tint */
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 6px;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    .nearest-services li strong { color: #6A1B9A; font-weight: 600; } /* Dark Purple for service name */
    .nearest-services li a {
        color: #7E57C2 !important; /* Deep Purple link */
        text-decoration: none;
        font-weight: 600;
    }
    .nearest-services li a:hover { text-decoration: underline; }

    /* Specificity for general text and headers inside the main content block */
    .st-emotion-cache-z5f06i > div > div > div > div > p,
    .st-emotion-cache-z5f06i div[data-testid="stHorizontalBlock"] > div > div > div > div > p {
        color: #333333 !important;
        font-family: 'Roboto', sans-serif !important;
    }
    .st-emotion-cache-z5f06i h1, .st-emotion-cache-z5f06i h2, .st-emotion-cache-z5f06i h3,
    .st-emotion-cache-z5f06i h4, .st-emotion-cache-z5f06i h5, .st-emotion-cache-z5f06i h6 {
        font-family: 'Poppins', sans-serif !important;
        color: #6A1B9A !important;
    }
    .st-emotion-cache-z5f06i h1 { color: #4A148C !important; }


    /* Responsive Adjustments */
    @media (max-width: 768px) {
        .main .block-container { padding: 20px; margin-top: -20px;}
        div[data-testid="stButton"] > button { padding: 10px 15px; font-size: 14px; }
        .sos-button-container div[data-testid="stButton"] > button { padding: 15px 25px; font-size: 16px; }
        div[data-testid="stAlert"] { padding: 12px; font-size: 14px; border-left-width: 6px;}
        .location-details, .nearest-services { padding: 15px; }
        .nearest-services li { padding: 10px; font-size: 14px; }
        h2::after, h3::after, h4::after { width: 35px; height: 2px; }
    }
    @media (max-width: 480px) {
        .main .block-container { padding: 15px; border-radius: 10px; margin-top: -10px;}
        h1 { font-size: 1.8em; }
        div[data-testid="stButton"] > button { padding: 9px 12px; font-size: 13px; gap: 6px;}
        .sos-button-container div[data-testid="stButton"] > button { padding: 12px 20px; font-size: 15px; }
        div[data-testid="stAlert"] { padding: 10px; font-size: 13px; border-left-width: 5px;}
        .location-details, .nearest-services { padding: 12px; border-radius: 8px;}
        .nearest-services li { padding: 8px; font-size: 13px; }
        h2::after, h3::after, h4::after { width: 30px; }
    }

    </style>
    """, unsafe_allow_html=True)
    # --- End Custom CSS ---


    st.title("🛡️ Women Safety Dashboard")

    # Ensure user is logged in
    if st.session_state.user is None:  # Check the user object directly
        st.warning("You need to be logged in to access the dashboard.")
        # Clear relevant state on logout/not logged in
        handle_dashboard_action('login') # Use the helper to clean state and navigate
        return # Stop execution

    # Using st.write inside the main content block implicitly styles it
    st.write(f"Welcome, {st.session_state.user.get('name', 'User')}!")

    # --- Load Contacts on Dashboard Page Load ---
    # This loads the contacts list from the DB for the logged-in user
    # This list is used by the SOS button and passed to the email function
    # Reload every time dashboard renders for simplicity
    user_id = st.session_state.user.get('id')
    if user_id is None:
        st.error("User ID not found in session state. Cannot load contacts.")
        st.session_state.dashboard_contacts_list = []
    else:
        try:
            # Ensure db is not the DummyDB before attempting to get contacts
            if not isinstance(db, type) or db.__name__ != 'DummyDB':
                contacts_from_db = db.get_contacts(user_id)
                if not isinstance(contacts_from_db, list):
                    print(f"Warning: db.get_contacts did not return a list. Received: {contacts_from_db}")
                    contacts_from_db = [] # Ensure it's a list
            else:
                # If using DummyDB, it prints a warning inside get_contacts
                contacts_from_db = db.get_contacts(user_id) # Call dummy function

            st.session_state.dashboard_contacts_list = contacts_from_db
            print(f"Dashboard: Loaded {len(contacts_from_db)} contacts from DB for user {user_id}.")  # Debug print
        except Exception as e:
            print(f"Dashboard: Error loading contacts from DB: {e}")  # Debug print
            st.error(f"Failed to load emergency contacts: {e}")
            st.session_state.dashboard_contacts_list = []


    # --- Load Service Data (Hospitals and Police Stations) ---
    # Define the paths to the CSV files. It's best to use relative paths if possible,
    # or ensure absolute paths are correct for the environment where the app runs.
    # Using the user-provided absolute paths:
    hospital_csv_path = r"C:\Users\dhivy\Downloads\women_safety_app_complete\Hospitals In India (Anonymized).csv"
    police_csv_path = r"C:\Users\dhivy\Downloads\women_safety_app_complete\indian_police_stations_10000.csv"

    # Load data using the cached function - Returns dataframes and logs errors
    hospital_df, police_df = load_service_data(hospital_csv_path, police_csv_path)


    # --- Page Navigation Buttons ---
    # Define the dashboard items with labels, icons (emojis), and action keys
    dashboard_items = [
        {"label": "Manage Contacts", "icon": "👪", "action": "add_contacts_page"}, # Renamed for clarity
        {"label": "Helpline Numbers", "icon": "🎧", "action": "helpline_numbers_page"},
        {"label": "Emergency Triggers", "icon": "📱", "action": "triggers_page"}, # Renamed for clarity
        {"label": "Check Area Safety", "icon": "🛰️", "action": "check_area_safety_page"},  # NEW - Uncommented
        {"label": "Crime Analysis", "icon": "📊", "action": "crime_analysis_page"},  # NEW
        {"label": "How to Use", "icon": "📖", "action": "how_to_use_page"},
        {"label": "Developed By", "icon": "💡", "action": "developed_by_page"},
        {"label": "Logout", "icon": "➡️", "action": "logout"},
    ]

    st.subheader("App Sections:")

    # Create a 2-column layout for the grid
    cols = st.columns(2) # Creates 2 equal-width columns

    available_pages = st.session_state.get('pages', {}) # Get the dictionary of available pages from app.py

    for i, item in enumerate(dashboard_items):
        col_index = i % 2
        with cols[col_index]:
            button_label = f"{item['icon']} {item['label']}"
            # Check if the action is 'logout' or if the action key exists in the available_pages dict
            if item['action'] == "logout" or item['action'] in available_pages:
                # Use a unique key for each button
                if st.button(button_label, key=f"button_{item['action']}"):
                    handle_dashboard_action(item['action'])
            else:
                # Display a disabled button for pages not yet linked in app.py
                st.button(f"{button_label} (Page Not Configured)", key=f"button_{item['action']}_unlinked", disabled=True)


    st.markdown("---")  # Separator


    # --- Location and SOS Logic ---
    # This section handles the SOS button click, triggering location retrieval,
    # geocoding, finding nearest services, and sending email.

    # --- Step 2: Process Location Result from Component ---
    # This block runs on any rerun triggered by the js_eval component returning a result.
    # It checks if the specific key used by the component exists in session state.
    # Ensure this check happens *before* the SOS button click logic below.
    if st.session_state.get('sos_button_processing', False) and _DASHBOARD_LOCATION_KEY in st.session_state:
        print(f"Dashboard: Component result key '{_DASHBOARD_LOCATION_KEY}' found in session state.")  # Debug print
        # Retrieve the result
        location_result = st.session_state[_DASHBOARD_LOCATION_KEY]
        # Consume the key immediately after finding the result to avoid reprocessing on subsequent reruns
        del st.session_state[_DASHBOARD_LOCATION_KEY]
        print(f"Dashboard: Result key '{_DASHBOARD_LOCATION_KEY}' deleted from session state.")  # Debug print


        # Store the result in the session state variable used for display and email
        st.session_state.last_known_location_data = location_result
        st.session_state.last_known_location = location_result # Update old implementation variable


        # --- Process the location result ---
        # Check if the result is valid location data (dict with lat/lon) or an error
        # Note: Display logic below also checks for valid data before rendering the styled block
        if st.session_state.last_known_location_data is not None and isinstance(st.session_state.last_known_location_data, dict):
            # Check for error FIRST from browser geolocation
            if 'error' in st.session_state.last_known_location_data:
                error_msg = st.session_state.last_known_location_data['error']
                error_source = st.session_state.last_known_location_data.get('source', 'Error')
                sos_status_placeholder.error(f"Location error: {error_msg} (Source: {error_source})")
                st.session_state.last_known_location_source = error_source
                print("Dashboard: Location error feedback displayed.")
                st.session_state.sos_button_processing = False # Processing finished due to location error
                # Clear nearest services results and address details on location failure
                st.session_state.nearest_hospitals = None
                st.session_state.nearest_police_stations = None
                st.session_state.address_details = None
                # Do NOT send email if location failed
                return # Stop further processing (geocoding/email/services) if location failed

            # If no error, check for valid coordinates
            elif 'latitude' in st.session_state.last_known_location_data and 'longitude' in st.session_state.last_known_location_data:
                # Keep the initial success message or update it as processing continues
                # sos_status_placeholder.success("Location retrieved successfully from browser.") # This will be updated by later steps
                st.session_state.last_known_location_source = st.session_state.last_known_location_data.get('source', 'Browser Geolocation')
                print("Dashboard: Location success feedback displayed.")

                lat = st.session_state.last_known_location_data['latitude']
                lon = st.session_state.last_known_location_data['longitude']

                # --- Attempt Reverse Geocoding ---
                # Only attempt geocoding if geopy is available
                if _GEOPY_AVAILABLE:
                    sos_status_placeholder.info("Fetching address details...")
                    print("Dashboard: Coordinates available, attempting reverse geocoding with Nominatim.")
                    address_details = get_address_from_coords(lat, lon)
                    st.session_state.address_details = address_details

                    if address_details and not address_details.get('error'):
                        # Handle info messages from geocoding failure
                        if address_details.get('info'):
                            # sos_status_placeholder.warning(f"Address Info: {address_details['info']}") # Keep the email status
                            st.session_state.last_known_location_source = "Browser Geolocation (Nominatim Info)"
                            print(f"Dashboard: Address info: {address_details['info']}")
                        else: # Successful detailed address
                            # sos_status_placeholder.success("Address details retrieved successfully.") # Keep the email status
                            # Update source to reflect successful geocoding if applicable
                            st.session_state.last_known_location_source = "Combined (Browser+Nominatim)"
                            print("Dashboard: Address details retrieved.")
                    elif address_details and address_details.get('error'):
                        # Keep previous status message, add a warning
                        # sos_status_placeholder.warning(f"Could not retrieve detailed address: {address_details['error']}") # Keep the email status
                        # Keep source as Browser if Nominatim failed
                        st.session_state.last_known_location_source = "Browser Geolocation (Nominatim Error)"
                        print(f"Dashboard: Address details failed: {address_details['error']}")
                    else: # address_details is None or empty dict without 'error' or 'info'
                        # sos_status_placeholder.warning("Could not retrieve detailed address information.") # Keep the email status
                        # Keep source as Browser if Nominatim returned no data
                        st.session_state.last_known_location_source = "Browser Geolocation (No Nominatim Data)"
                        print("Dashboard: Address details not found.")
                else:
                    # Geopy warning is already displayed at the top if missing
                    st.session_state.address_details = {"info": "Geopy not available. Cannot fetch address details."}
                    st.session_state.last_known_location_source = "Browser Geolocation (Geopy Missing)"
                    print("Dashboard: Geopy not available for address details.")


                # --- Find Nearest Services (After Location & Geocoding Attempt) ---
                # We have valid lat/lon here, attempt to find nearest services if data and geopy are available
                print("Dashboard: Attempting to find nearest services.")
                # Only check if Geopy is available AND at least one DataFrame loaded successfully
                if _GEOPY_AVAILABLE and (hospital_df is not None or police_df is not None):
                    sos_status_placeholder.info("Finding nearest emergency services...") # Update status

                    # Only attempt to find hospitals if hospital_df loaded and has required columns
                    if hospital_df is not None:
                        st.session_state.nearest_hospitals = find_nearest_services(
                            lat, lon, hospital_df, service_type='Hospital',
                            name_col='id', lat_col='Latitude', lon_col='Longitude',
                            num_results=5, radius_km=10.0 # Use default 10km radius
                        )
                        print(f"Dashboard: Nearest hospitals search result: {st.session_state.nearest_hospitals}")
                    else: # hospital_df was None after loading/cleaning
                        st.session_state.nearest_hospitals = [{"info": "Hospital data not available for search."}] # Indicate data not available

                    # Only attempt to find police stations if police_df loaded and has required columns
                    if police_df is not None:
                        st.session_state.nearest_police_stations = find_nearest_services(
                            lat, lon, police_df, service_type='Police Station',
                            name_col='name', lat_col='lat', lon_col='lng',
                            num_results=5, radius_km=10.0 # Use default 10km radius
                        )
                        print(f"Dashboard: Nearest police stations search result: {st.session_state.nearest_police_stations}")
                    else: # police_df was None after loading/cleaning
                        st.session_state.nearest_police_stations = [{"info": "Police station data not available for search."}] # Indicate data not available

                elif _GEOPY_AVAILABLE: # Geopy available, but neither DataFrame loaded
                    sos_status_placeholder.warning("Service data not loaded. Cannot find nearest services.")
                    st.session_state.nearest_hospitals = [{"info": "Service data not loaded."}]
                    st.session_state.nearest_police_stations = [{"info": "Service data not loaded."}]
                    print("Dashboard: Service data not available for nearest search.")


                elif not _GEOPY_AVAILABLE: # Geopy not available at all
                    sos_status_placeholder.warning("Geopy not available. Cannot find nearest services.")
                    st.session_state.nearest_hospitals = [{"info": "Geopy not available. Cannot find nearest services."}]
                    st.session_state.nearest_police_stations = [{"info": "Geopy not available. Cannot find nearest services."}]
                    print("Dashboard: Geopy not available for nearest search.")


                # --- Attempt to Send Email Alert (After Location, Geocoding, Services Search) ---
                # Email is sent if the email module is available, regardless of geocoding or service search success/failure,
                # as long as browser location data was successfully retrieved.
                if _EMAIL_ALERT_AVAILABLE:
                    print("Dashboard: Browser location successfully processed, proceeding to send email.")
                    sos_status_placeholder.info("Sending email alert...") # Update status
                    # The send_sos_email_alert function will use the data already in session state
                    send_sos_email_alert() # Call the helper function to send the email
                    print("Dashboard: Email sending function called. Processing flag will be cleared in its finally block.")
                else:
                    print("Dashboard: Email sending skipped - email_alert module not available.")
                    sos_status_placeholder.warning("Email alerts disabled (email_alert.py not found). No email sent.")
                    st.session_state.sos_button_processing = False # Clear processing flag if email module is missing
                    st.session_state.last_known_location_source += " (Email Disabled)"


            else: # Location data is a dict but doesn't have lat/lon or error keys - unexpected format
                sos_status_placeholder.warning("Could not retrieve location (unexpected format).")
                st.session_state.last_known_location_source = "Unknown (Result format error)"
                print("Dashboard: Location unexpected format warning displayed.")
                st.session_state.sos_button_processing = False # Processing finished due to location format error
                # Clear nearest services results on location failure
                st.session_state.nearest_hospitals = None
                st.session_state.nearest_police_stations = None
                st.session_state.address_details = None # Also clear address details
                # Do NOT send email if location format is bad
                return # Stop execution here

        # Execution continues after this block...
        # The general processing flag st.session_state.sos_button_processing is cleared
        # either in the send_sos_email_alert's finally block or immediately if email is skipped.


    # --- Step 3: Display Current Location Status (Conditional Rendering) ---
    # This section displays the location data stored in session state (`last_known_location_data`)
    # It runs on every rerun to update the display based on session state
    # Use the placeholder defined globally

    # Always clear the placeholder before potentially writing to it on this rerun
    location_display_placeholder.empty()

    current_location_data = st.session_state.get('last_known_location_data')
    address_details = st.session_state.get('address_details')

    # --- Conditional Rendering of Location Details Block ---
    # ONLY display this section if valid location data exists (not None, is dict, and no 'error' key)
    if current_location_data is not None and isinstance(current_location_data, dict) and 'error' not in current_location_data:
        print("Dashboard: Valid location data found. Displaying location details section.") # Debug print

        # Use the placeholder to write the section header and separator
        # All content written within this 'with' block will go into the placeholder
        with location_display_placeholder.container():
            st.markdown("---") # Separator
            st.subheader("Last Known Location:")
            # Apply the custom CSS class by wrapping content in a div
            st.markdown('<div class="location-details">', unsafe_allow_html=True)

            # Display the location source
            src = st.session_state.get('last_known_location_source', 'N/A')
            st.markdown(f"**Source:** {src}")

            # Display coordinates and map link
            lat = current_location_data['latitude']
            lon = current_location_data['longitude']
            acc = current_location_data.get('accuracy', 'Unknown')
            st.write(f"Coordinates: Latitude {lat}, Longitude {lon} (Accuracy: {acc} m)")
            # Use modern Google Maps URL format
            Maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            st.markdown(f"[View Location on Google Maps]({Maps_link})")

            # Display detailed address information if available
            if address_details:
                # Check if address_details has data beyond just an error or info message
                if not address_details.get('error') and not address_details.get('info'):
                    with st.expander("📍 Detailed Address Information", expanded=True):
                        if address_details.get('full_address'):
                            st.markdown(f"**Full Address:** {address_details['full_address']}")
                            st.markdown("---") # Separator within expander
                            col1, col2 = st.columns(2)
                            with col1:
                                if address_details.get('street') and address_details.get('street') != 'N/A': st.markdown(f"**Street/Road:** {address_details.get('street')}")
                                if address_details.get('house_number') and address_details.get('house_number') != 'N/A': st.markdown(f"**House/Building Number:** {address_details.get('house_number')}")
                                if address_details.get('neighbourhood') and address_details.get('neighbourhood') != 'N/A': st.markdown(f"**Neighborhood:** {address_details.get('neighbourhood')}")
                                if address_details.get('suburb') and address_details.get('suburb') != 'N/A': st.markdown(f"**Suburb:** {address_details.get('suburb')}")
                                if address_details.get('city') and address_details.get('city') != 'N/A': st.markdown(f"**City:** {address_details.get('city')}")
                            with col2:
                                if address_details.get('district') and address_details.get('district') != 'N/A': st.markdown(f"**District:** {address_details.get('district')}")
                                if address_details.get('state') and address_details.get('state') != 'N/A': st.markdown(f"**State:** {address_details.get('state')}")
                                if address_details.get('postcode') and address_details.get('postcode') != 'N/A': st.markdown(f"**Postal Code:** {address_details.get('postcode')}")
                                if address_details.get('country') and address_details.get('country') != 'N/A': st.markdown(f"**Country:** {address_details.get('country')}")
                        else: # address_details exists but doesn't have full_address
                            st.info("Detailed address information could not be parsed.")
                elif address_details.get('error'):
                    st.error(f"Could not get detailed address: {address_details['error']}")
                elif address_details.get('info'):
                    st.info(address_details['info'])


            # This else correctly matches the inner if address_details: check
            else:
                st.info("Detailed address information not available.")

            # Close the custom CSS div
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Display message if location data is NOT available or is an error state ---
    else:
        # This message appears initially or if location retrieval failed
        print("Dashboard: Location data not available or error state. Displaying info/error message in placeholder.") # Debug print
        # Use the placeholder to display the section header and separator
        with location_display_placeholder.container():
            st.markdown("---") # Separator
            st.subheader("Last Known Location:")
            # Check specifically if there was an error returned
            if current_location_data is not None and isinstance(current_location_data, dict) and 'error' in current_location_data:
                error_msg = current_location_data['error']
                error_source = current_location_data.get('source', 'Error')
                st.error(f"Could not get location: {error_msg} (Source: {error_source})")
            else:
                # Display the general "not available" message
                st.info(f"Location data not available. Source: {st.session_state.get('last_known_location_source', 'Not available (Initial)')}")


    # --- Display Nearest Services (Conditional Rendering) ---
    # This block runs on every rerun if nearest services data is available in session state
    nearest_hospitals = st.session_state.get('nearest_hospitals')
    nearest_police_stations = st.session_state.get('nearest_police_stations')

    # Always clear the placeholder before potentially writing to it on this rerun
    nearest_services_placeholder.empty()

    # Only display the nearest services section if *either* hospital or police data is available (even if it's just an info/error message)
    if nearest_hospitals is not None or nearest_police_stations is not None:
        print("Dashboard: Nearest services data available. Displaying services section.") # Debug print

        # Use the placeholder for the section header, separator, and the styled div content
        with nearest_services_placeholder.container():
            st.markdown("---") # Separator
            st.subheader("Nearest Emergency Services:")

            # Apply the custom CSS class by wrapping content in a div
            st.markdown('<div class="nearest-services">', unsafe_allow_html=True) # Apply custom CSS class

            # Display Hospitals if data is available
            if nearest_hospitals is not None:
                st.markdown("<h4>🏥 Nearest Hospitals:</h4>", unsafe_allow_html=True)
                # Check for specific content types (error, info, or actual list)
                if isinstance(nearest_hospitals, list) and nearest_hospitals and nearest_hospitals[0].get('error'):
                    st.error(f"Could not find nearest hospitals: {nearest_hospitals[0]['error']}")
                elif isinstance(nearest_hospitals, list) and nearest_hospitals and nearest_hospitals[0].get('info'):
                    st.info(nearest_hospitals[0]['info'])
                elif isinstance(nearest_hospitals, list) and nearest_hospitals: # Actual results list
                    st.markdown("<ul>", unsafe_allow_html=True)
                    for hospital in nearest_hospitals:
                        # Use .get() for safety with potentially missing keys
                        name = hospital.get('Name', 'Unknown Hospital')
                        distance = hospital.get('Distance (km)', 'N/A')
                        address = hospital.get('Address', 'N/A Address')
                        lat = hospital.get('Latitude') # Get raw lat/lon
                        lon = hospital.get('Longitude') # Get raw lat/lon

                        item_html = f"<li><strong>{name}</strong> ({distance} km)"
                        if address != 'N/A Address':
                            item_html += f"<br>Address: {address}"
                        if lat is not None and lon is not None:
                            # Use modern Google Maps URL format for the service location
                            service_map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                            item_html += f" [<a href='{service_map_link}' target='_blank'>View on Map</a>]"
                        item_html += "</li>"
                        st.markdown(item_html, unsafe_allow_html=True)
                    st.markdown("</ul>", unsafe_allow_html=True)
                else: # Should not happen if nearest_hospitals is not None, but as a fallback
                    st.info("No nearby hospitals found or data not available.")


            # Display Police Stations if data is available
            if nearest_police_stations is not None:
                st.markdown("<h4>🚓 Nearest Police Stations:</h4>", unsafe_allow_html=True)
                if isinstance(nearest_police_stations, list) and nearest_police_stations and nearest_police_stations[0].get('error'):
                    st.error(f"Could not find nearest police stations: {nearest_police_stations[0]['error']}")
                elif isinstance(nearest_police_stations, list) and nearest_police_stations and nearest_police_stations[0].get('info'):
                    st.info(nearest_police_stations[0]['info'])
                elif isinstance(nearest_police_stations, list) and nearest_police_stations: # Actual results list
                    st.markdown("<ul>", unsafe_allow_html=True)
                    for station in nearest_police_stations:
                        # Use .get() for safety with potentially missing keys
                        name = station.get('Name', 'Unknown Police Station')
                        distance = station.get('Distance (km)', 'N/A')
                        address = station.get('Address', 'N/A Address')
                        lat = station.get('Latitude') # Get raw lat/lon
                        lon = station.get('Longitude') # Get raw lat/lon

                        item_html = f"<li><strong>{name}</strong> ({distance} km)"
                        if address != 'N/A Address':
                            item_html += f"<br>Address: {address}"
                        if lat is not None and lon is not None:
                            # Use modern Google Maps URL format for the service location
                            service_map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                            item_html += f" [<a href='{service_map_link}' target='_blank'>View on Map</a>]"
                        item_html += "</li>"
                        # CORRECTED INDENTATION HERE
                        st.markdown(item_html, unsafe_allow_html=True) # <--- Corrected line 1505
                    st.markdown("</ul>", unsafe_allow_html=True)
                else: # Should not happen if nearest_police_stations is not None, but as a fallback
                    st.info("No nearby police stations found or data not available.")

            # Close the custom CSS div
            st.markdown('</div>', unsafe_allow_html=True)

    # If both are None initially, display the placeholder message outside the styled div
    elif nearest_hospitals is None and nearest_police_stations is None:
        print("Dashboard: Nearest services data not available. Displaying initial message.") # Debug print
        # Use the placeholder for the section header and separator
        with nearest_services_placeholder.container():
            st.markdown("---") # Separator
            st.subheader("Nearest Emergency Services:")
            # Display the initial info message
            st.info("Nearest emergency services will appear here after your location is retrieved.")


    # --- Step 1: SOS Alert Button ---
    # This button initiates the SOS process
    # Use st.error for the header as requested, styled by CSS alerts
    st.error("🚨 Emergency SOS Alert:") # This will be styled by the .stAlert.stError rule if not overridden
                                      # For a simple text header, use st.subheader or st.markdown with custom class
    # Wrap the button in a custom div for SOS-specific styling
    st.markdown('<div class="sos-button-container">', unsafe_allow_html=True)

    # Check if any processing is ongoing (waiting for location or email sending)
    is_processing_any = st.session_state.get('sos_button_processing', False)

    # Button is disabled while processing or if streamlit-js-eval is not available
    button_disabled = is_processing_any or not _STREAMLIT_JS_EVAL_AVAILABLE

    # Display status messages based on the processing state and library availability
    if is_processing_any:
        # The specific status message will be set by the processing logic (e.g., "Getting location...", "Fetching address...", "Sending email...")
        pass # Keep the status placeholder as is, it's updated elsewhere
    elif not _STREAMLIT_JS_EVAL_AVAILABLE:
        st.error("Cannot activate SOS button: streamlit-js-eval library not installed.")
    elif not _EMAIL_ALERT_AVAILABLE and _STREAMLIT_JS_EVAL_AVAILABLE:
        sos_status_placeholder.warning("Email alerts disabled (email_alert.py not found). Location will be retrieved but email won't be sent.")
    elif not st.session_state.get('dashboard_contacts_list') and _EMAIL_ALERT_AVAILABLE and _STREAMLIT_JS_EVAL_AVAILABLE:
        sos_status_placeholder.warning("No valid email contacts added. Location will be retrieved but email alert will be skipped.")
    else:
        # Clear status placeholder if not processing and no persistent warnings/errors need display
        # The placeholders are global and persist. Messages written to them will stay
        # until the placeholder is written to again or cleared explicitly.
        # The processing logic writes specific messages. If not processing, no new message is written here,
        # so the last message in the placeholder remains. This is generally desired behavior.
        pass # Do nothing, placeholder retains last message


    # The actual SOS button
    button_clicked = st.button("🔴 TAP FOR SOS ALERT 🔴", key="button_sos_alert", disabled=button_disabled)

    # Only execute the button click logic if the button was clicked AND we are not already processing AND js_eval is available
    if button_clicked and not is_processing_any and _STREAMLIT_JS_EVAL_AVAILABLE:
        print("\n--- SOS Button Clicked ---")

        # Set processing flag immediately to disable the button and show status
        st.session_state.sos_button_processing = True
        st.session_state.sos_triggered = True  # Mark SOS as triggered

        # Clear previous results/data when starting a new request
        st.session_state.last_known_location_data = None
        st.session_state.address_details = None # Clear address details
        st.session_state.nearest_hospitals = None # Clear previous nearest services
        st.session_state.nearest_police_stations = None # Clear previous nearest services
        st.session_state.last_known_location_source = "Requesting location..."

        # Clear previous display elements immediately using the placeholders
        # This ensures the old location/services blocks disappear instantly on button click
        location_display_placeholder.empty()
        nearest_services_placeholder.empty()
        # Display initial status message for the SOS sequence
        sos_status_placeholder.info("Initiating SOS sequence: Getting location...")

        # Get necessary data (User ID, Contacts)
        user_id = st.session_state.user.get('id')
        if user_id is None:
            sos_status_placeholder.error("User ID missing. Cannot trigger SOS.")
            st.session_state.sos_button_processing = False # Reset flag on failure
            st.session_state.last_known_location_source = "SOS Failed (User ID missing)"
            return # Stop execution

        # Get contacts list loaded at the start of dashboard()
        user_contacts_list = st.session_state.get('dashboard_contacts_list', [])

        valid_email_contacts_exist = any(isinstance(contact, dict) and 'email' in contact and contact['email'] and "@" in str(contact['email']) for contact in user_contacts_list)

        # Check if email alert is possible BEFORE triggering location
        if not _EMAIL_ALERT_AVAILABLE:
            sos_status_placeholder.warning("Email alerts disabled (email_alert.py not found). Location will be retrieved but no email will be sent.")
            # Processing continues to get location if js_eval is available
        elif not valid_email_contacts_exist:
            sos_status_placeholder.warning("No valid email contacts added. Location will be retrieved but email alert will be skipped.")
            # Processing continues to get location if js_eval is available
        else:
            # Contacts found AND email module available, indicate that email will follow
            # Keep the info message about getting location, the email step message comes later after location is known
            # sos_status_placeholder.info("Initiating SOS sequence: Getting location and preparing email...")
            pass # Let the "Getting location..." message stand

        # --- Trigger the streamlit-js-eval component request for location directly ---
        # The result will appear in st.session_state[_DASHBOARD_LOCATION_KEY] on a subsequent rerun.
        try:
            print(f"Dashboard: Attempting to render component with key: '{_DASHBOARD_LOCATION_KEY}'.") # Debug print
            # This call renders the component and triggers a rerun when the browser responds.
            # Use the simplified JS to request current position once.
            streamlit_js_eval.streamlit_js_eval(js_expressions="""
                        new Promise((resolve) => {
                            if (!navigator.geolocation) {
                                resolve({error: "Geolocation not supported by browser", source: "Browser API"});
                                return;
                            }
                            navigator.geolocation.getCurrentPosition(
                                (position) => { resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude, accuracy: position.coords.accuracy, source: "Browser Geolocation" }); },
                                (error) => {
                                    let errorMsg = "Unknown browser geolocation error";
                                    if (error.code === 1) errorMsg = "Permission denied";
                                    if (error.code === 2) errorMsg = "Position unavailable";
                                    if (error.code === 3) errorMsg = "Timeout";
                                    resolve({error: errorMsg, code: error.code, source: "Browser Geolocation Error"});
                                }
                            );
                        });
                        """,
                        want_output=True, # We need the location data back
                        key=_DASHBOARD_LOCATION_KEY # Use the specific key to store the result
                    )
            print(f"Dashboard: Component rendered directly with key: '{_DASHBOARD_LOCATION_KEY}'. Location request initiated.") # Debug print
            # The processing flag st.session_state.sos_button_processing remains True until the location result is processed and email is sent (or skipped).

        except Exception as e:
            # Catch errors specifically during the rendering of the JS component
            print(f"Dashboard: Error rendering JS location component directly: {e}") # Debug print
            sos_status_placeholder.error(f"Location component failed to load or execute: {e}")
            st.session_state.sos_button_processing = False # Reset flag on component failure
            st.session_state.last_known_location_source = "SOS Failed (Component Load Error)"
            # Clear nearest services results on failure
            st.session_state.nearest_hospitals = None
            st.session_state.nearest_police_stations = None
            st.session_state.address_details = None # Also clear address details
            # Do NOT send email if location component failed
            return # Stop execution here


    # Close the custom div for the SOS button styling
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---") # Separator

    st.info("Disclaimer: This application is a supplementary safety tool. It relies on network connectivity and browser geolocation, which may not always be accurate or available. Always prioritize contacting emergency services directly in case of an emergency.")


# --- Run the dashboard function when the page is 'dashboard' ---
# (Assuming this script is called by an app.py that manages pages)
# This part is typically handled in your main app.py file, which would check
# st.session_state.page and call dashboard() if it's 'dashboard'.
# if st.session_state.get('page') == 'dashboard':
#     dashboard()