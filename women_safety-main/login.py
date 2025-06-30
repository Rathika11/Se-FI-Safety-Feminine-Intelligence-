import streamlit as st
import base64
import os
# Assuming db.py exists and has a get_user function
try:
    from db import get_user
except ImportError:
    # Define a dummy get_user function if db.py is not found
    def get_user(email, password):
        print("Dummy get_user function called. Please implement your database logic in db.py.")
        # Dummy logic: Allow login with specific credentials for testing
        if email == "test@example.com" and password == "password123":
            print("Dummy login successful for test@example.com")
            # Return a dummy user dictionary
            return {"id": "dummy_user_123", "name": "Test User", "email": "test@example.com"}
        else:
            print("Dummy login failed")
            return None
    st.warning("Could not import db.py. Using a dummy database function for login.")


def add_bg_from_local(image_file):
    """
    Function to read and encode the file to base64.
    This allows us to embed the image directly in the CSS.
    """
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpeg;base64,{encoded_string}"


def login_page():
    """Renders the login page UI and handles login logic."""
    st.title("SEFI")

    # --- Add Custom CSS for Background Image and Text Input Width ---
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Path to image file - adjust the path as needed
        image_path = os.path.join(current_dir, "assets", "imgae.jpg")
        
        # Generate base64 encoded image
        bg_img = add_bg_from_local(image_path)
        
        # Apply background image using CSS with base64 encoded image
        # And add CSS to reduce text input width
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("{bg_img}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            
            .stApp::before {{
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(255, 255, 255, 0.5);
                z-index: -1;
            }}
            
            /* Custom CSS for reducing text input width */
            div[data-testid="stTextInput"] {{
                max-width: 250px;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except Exception as e:
        st.warning(f"Unable to load background image: {e}")
        # Fallback styling without background image but still with reduced text input width
        st.markdown(
            """
            <style>
            .stApp {
                background-color: #f0f2f6;
            }
            
            /* Custom CSS for reducing text input width */
            div[data-testid="stTextInput"] {
                max-width: 250px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    # Use columns for better layout to center the form
    col1, col2, col3 = st.columns([1,2,1])

    with col2: # Content within the middle column
        st.subheader("User Login")
        # Added keys to input widgets for consistent state management across reruns
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        # Added a placeholder for status messages (success/error/warning)
        login_status = st.empty()

        # Login button
        if st.button("Login", key="login_button"):
            # Clear previous status messages when button is clicked
            login_status.empty()
            # Check if fields are empty
            if not email or not password:
                 login_status.warning("Please enter both email and password.")
            else:
                # Call the get_user function from db.py to authenticate
                # This function should return user data (e.g., a dict) if successful, None otherwise
                user = get_user(email, password)
                if user:
                    # If login is successful
                    login_status.success("Login successful! Redirecting...")
                    # Store user info in session state for access across pages
                    st.session_state.user = user
                    # Set the page state to 'dashboard'
                    st.session_state.page = 'dashboard'
                    # Trigger an immediate rerun to navigate to the dashboard
                    st.rerun()
                else:
                    # If login fails
                    login_status.error("Invalid credentials") # Show error message

        st.markdown("---") # Separator line

        st.markdown("Don't have an account?")
        # Button to navigate to the signup page
        if st.button("Go to Signup", key="goto_signup_button"):
            # Set the page state to 'signup'
            st.session_state.page = 'signup'
            # Trigger an immediate rerun to navigate to the signup page
            st.rerun()


# If running directly for testing
if __name__ == "__main__":
    # Initialize page state if running directly
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

    # Simple page routing for direct testing
    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'dashboard':
        st.write("This is the Dashboard (placeholder)")
        if st.button("Logout"):
            st.session_state.page = 'login'
            st.rerun()
    elif st.session_state.page == 'signup':
        st.write("This is the Signup page (placeholder)")
        if st.button("Go to Login"):
            st.session_state.page = 'login'
            st.rerun()