# helpline_numbers_page.py
import streamlit as st

def helpline_numbers_page():
    st.title("🎧 Women Safety Helpline Numbers (India)")

    st.write("Below is a list of important helpline numbers. Clicking these numbers will attempt to initiate a **standard phone call** using your device's default phone application.")
    st.info("On some devices or operating systems (like Windows), you might be asked to choose an application to handle the call. Please select your device's **default phone dialer** (e.g., 'Phone', 'Phone Link', 'Dialer') from the list, not messaging apps like WhatsApp or Skype, to make a standard call.")


    # List of prominent women safety helpline numbers in India
    # This list can be expanded or modified. Aiming for around 20 as requested.
    # Numbers are kept as strings.
    helpline_numbers = [
        {"name": "All India Women Helpline (Domestic Abuse)", "number": "181"}, # Pan-India
        {"name": "Police (Emergency)", "number": "100"},
        {"name": "Fire Services (Emergency)", "number": "101"}, # Useful in various emergencies
        {"name": "Ambulance (Emergency)", "number": "102"}, # Medical emergencies
        {"name": "Centralized Accident & Trauma Services (CATS, Delhi)", "number": "1099"}, # Delhi specific ambulance/trauma
        {"name": "National Commission for Women (NCW)", "number": "011-26942369"}, # General contact, check NCW website for specific helplines if available
        {"name": "National Human Rights Commission (NHRC)", "number": "14433"}, # Toll-free, general human rights
        {"name": "CHILDLINE India", "number": "1098"}, # For children in distress (often related to women's safety)
        {"name": "AASRA (Suicide Prevention & Counseling)", "number": "022-27546669"}, # Mumbai based, but offers counseling
        {"name": "SAATH (Suicide Prevention)", "number": "079-26305545"}, # Ahmedabad based
        {"name": "Sneha (Suicide Prevention)", "number": "044-24640050"}, # Chennai based
        {"name": "Vandrevala Foundation (Mental Health & Crisis Support)", "number": "1860-2662-345"}, # Pan-India
        {"name": "Connecting... (Suicide Prevention)", "number": "020-24470270"}, # Pune based
        {"name": "Arunodaya Deseret Eye Hospital (ADEH) - Counseling", "number": "080-26682500"}, # Bangalore based
        {"name": "Prerana (Trafficking)", "number": "022-23098843"}, # Mumbai based
        {"name": "ActionAid India", "number": "011-49144000"}, # General contact, may direct to relevant help
        {"name": "SEWA (Self-Employed Women's Association)", "number": "079-27540647"}, # Supports women workers, may offer related help
        {"name": "Sakhi One Stop Centres", "number": "181"}, # Integrated support for women affected by violence (same as general helpline but specific service)
        {"name": "Cyber Crime Helpline", "number": "155260"}, # For cyber crimes, including online harassment
        {"name": "Shakti Vahini (Anti-Human Trafficking)", "number": "011-42244224"}, # Delhi based, works nationally
        # Added a couple more common emergency numbers to get closer to 20
        {"name": "Railways Security Helpline", "number": "182"}, # For safety on trains/stations
        {"name": "Anti-Poison (Medical Emergency)", "number": "1066"} # Medical emergencies related to poisoning
    ]

    st.markdown("---")

    # Display numbers with clickable links
    # Use columns for a slightly cleaner layout
    num_columns = 2
    cols = st.columns(num_columns)

    for i, item in enumerate(helpline_numbers):
        col_index = i % num_columns
        with cols[col_index]:
            st.markdown(f"**{item['name']}**")
            # Use tel: link for clickable phone numbers
            # Clean the number by removing spaces and hyphens for the tel: link
            # tel: links are quite flexible, but removing non-digit characters is safest
            cleaned_number = item['number'].replace(" ", "").replace("-", "")
            # Prepending '+' is good practice for international numbers, but not strictly necessary for domestic ones
            # Let's keep it simple and just use the cleaned number for tel:
            tel_link = f"tel:{cleaned_number}"

            st.markdown(f"<a href='{tel_link}'>{item['number']}</a>", unsafe_allow_html=True)
            st.markdown("---") # Small separator between items


    st.markdown("---")

    # Button to go back to dashboard
    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_helpline"): # Added a unique key
        st.session_state.page = 'dashboard'
        st.rerun()

# For testing this specific page in isolation:
# if __name__ == "__main__":
#     # Ensure session state is initialized for testing
#     if 'page' not in st.session_state:
#         st.session_state.page = 'helpline_numbers_page' # Set a default page for isolated testing
#     helpline_numbers_page()
