# add_contacts_page.py
import streamlit as st
import re # Import regex for basic email validation

# Import db functions (which are now using MongoDB)
from db import save_contact, get_contacts, delete_contact

def add_contacts_page():
    """Renders the Add Contacts page UI and handles contact management using the database."""
    st.title("👪 Add Emergency Contacts")

    # Ensure user is logged in to see this page content
    if 'user' not in st.session_state or st.session_state.user is None:
         st.warning("Please log in to manage contacts.")
         if st.button("Go to Login", key="contacts_goto_login"):
              st.session_state.page = 'login'
              st.rerun()
         return # Stop rendering the rest of the page

    st.write("Add contacts who will receive the SOS alert email.")
    # Get the current user's ID from session state (should be the MongoDB ObjectId string)
    user_id = st.session_state.user.get('id')
    if user_id is None:
         st.error("User ID not found in session state. Cannot manage contacts. Please try logging out and back in.")
         return

    # Input fields for a new contact
    with st.form(key='contact_form', clear_on_submit=True):
        st.subheader("Add New Contact")
        contact_name = st.text_input("Name", key="new_contact_name")
        contact_phone = st.text_input("Phone Number (Optional)", key="new_contact_phone")
        contact_email = st.text_input("Email Address", key="new_contact_email")
        submit_button = st.form_submit_button("Add Contact")

        # Placeholder for status messages within the form
        form_status = st.empty()

        if submit_button:
            # Clear previous form status messages
            form_status.empty()

            if not contact_name or not contact_email:
                form_status.warning("Please enter at least a valid name and email.")
            elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", contact_email): # Email validation
                form_status.warning("Please enter a valid email address format.")
            else:
                # --- Call Database function to save contact (MongoDB) ---
                try:
                    # Save the contact for the logged-in user using the DB function
                    if save_contact(user_id, contact_name, contact_phone, contact_email):
                        form_status.success(f"Contact '{contact_name}' added.")
                        # After adding to DB, rerun to refresh the displayed list below
                        st.rerun()
                    else:
                        # Handle potential errors from save_contact (e.g., DB error, though save_contact currently returns True/False)
                        form_status.error("Failed to add contact.")
                except Exception as e:
                    # Catch errors during DB call (e.g. MongoDB connection failure)
                    form_status.error(f"An error occurred while adding contact: {e}")
                    print(f"Add Contact DB Call Error: {e}")

    st.markdown("---")
    st.subheader("Your Emergency Contacts:")

    # --- Call Database function to get contacts (MongoDB) ---
    # Retrieve contacts for the logged-in user every time the page loads
    current_contacts_from_db = []
    try:
         current_contacts_from_db = get_contacts(user_id) # Get contacts from DB
    except Exception as e:
         st.error(f"Error retrieving contacts: {e}")
         print(f"Get Contacts DB Error: {e}")
         # Continue with empty list if DB call failed

    # Display current contacts from the list returned by the database function
    if current_contacts_from_db:
        # Display contacts in a table (converting ObjectId to string for display)
        contact_data_for_table = [
            {"Name": c.get('name', 'N/A'), "Email": c.get('email', 'N/A'), "Phone": c.get('phone', 'N/A')}
            for c in current_contacts_from_db
        ]
        st.table(contact_data_for_table)

        # Option to remove contacts
        st.markdown("---")
        st.subheader("Remove Contacts:")

        # Store complete contact information with _id in session state for easier access
        # This is more reliable than trying to parse IDs from display strings
        if 'contact_id_map' not in st.session_state:
            st.session_state.contact_id_map = {}
            
        # Clear previous mappings to avoid stale data
        st.session_state.contact_id_map = {}
        
        # Create simple display options and map them to contact IDs in session state
        contact_display_options = []
        
        for c in current_contacts_from_db:
            if c.get('_id') is not None:
                # Create a display string (name and email)
                display_string = f"{c.get('name', 'N/A')} <{c.get('email', 'N/A')}>"
                # Store the relationship between display string and MongoDB _id
                st.session_state.contact_id_map[display_string] = str(c.get('_id'))
                contact_display_options.append(display_string)

        # Only show the selector if we have valid contacts
        if contact_display_options:
            contact_to_remove_display = st.selectbox(
                "Select a contact to remove:",
                options=contact_display_options,
                index=None,  # Start with no selection
                placeholder="Select a contact...",
                key="remove_contact_select"
            )

            remove_status = st.empty()  # Placeholder for remove status

            if st.button("Remove Selected Contact", key="remove_contact_button"):
                remove_status.empty()
                if contact_to_remove_display:
                    # Get the contact ID directly from our session state mapping
                    contact_id = st.session_state.contact_id_map.get(contact_to_remove_display)
                    
                    if contact_id:
                        try:
                            # Pass the MongoDB _id string to the delete function
                            if delete_contact(contact_id):
                                remove_status.success(f"Contact removed: {contact_to_remove_display}")
                                st.rerun()  # Refresh the page
                            else:
                                remove_status.error("Failed to delete contact. Contact might not exist or DB error.")
                        except Exception as e:
                            remove_status.error(f"An error occurred while deleting contact: {e}")
                            print(f"Delete Contact DB Call Error: {e}")
                    else:
                        remove_status.warning("Could not find contact ID for removal. Please try again.")
                else:
                    remove_status.warning("Please select a contact to remove.")
        else:
            st.info("No valid contacts available for removal.")
    else:
        st.info("No contacts added yet. Add contacts using the form above.")

    st.markdown("---")
    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_contacts"):
        st.session_state.page = 'dashboard'
        st.rerun()
