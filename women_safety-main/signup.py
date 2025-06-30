# signup.py
import streamlit as st
import base64
import os
import re # Import regex for email format validation

# Assuming db.py exists and has a create_user function that hashes passwords
# Make sure your db.py file is in the same directory or accessible in your project
try:
    from db import create_user
except ImportError:
    # Define a dummy create_user function if db.py is not found
    def create_user(name, email, password):
        print("Dummy create_user function called. Please implement your database logic in db.py.")
        print(f"Dummy user creation attempt: Name={name}, Email={email}, Password={password}")
        # Dummy logic: Always succeed for demonstration
        print("Dummy user creation successful.")
        return True # Simulate success for dummy

    st.warning("Could not import db.py. Using a dummy database function for signup.")


# Function to read and encode the image file to base64
# This function needs to be in signup.py as well
def add_bg_from_local(image_file):
    """
    Function to read and encode the file to base64.
    This allows us to embed the image directly in the CSS.
    """
    try:
        with open(image_file, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        # Assuming the image is JPEG, adjust if using PNG or other formats
        return f"data:image/jpeg;base64,{encoded_string}"
    except FileNotFoundError:
        # Print the exact path that was not found
        print(f"Background image file not found: {image_file}")
        return None
    except Exception as e:
        print(f"Error encoding background image: {e}")
        return None


def signup_page():
    """Renders the signup page UI and handles signup logic."""
    st.title("🔒 Create New Account")

    # --- Add Custom CSS for Background Image and Box Styling ---
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to image file - ADJUSTED FILENAME HERE
    # Assuming the image file is 'login-page.jpg' inside the 'assets' folder
    image_path = os.path.join(current_dir, "assets", "imgae.jpg") # Corrected filename

    bg_img_css = "" # Initialize empty string for background CSS

    # Generate base64 encoded image and build the CSS rule
    bg_img_data = add_bg_from_local(image_path)

    if bg_img_data:
        bg_img_css = f"""
        .stApp {{
            background-image: url("{bg_img_data}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        """
    else:
         # This warning will appear if the image file is not found or encoding fails
         st.warning(f"Unable to load background image from {image_path}. Using fallback background color.")
         # Fallback background color if image loading fails
         bg_img_css = """
         .stApp {
             background-color: #f0f2f6; /* Light grey fallback */
         }
         """

    # Combine all custom CSS rules
    custom_css = f"""
    <style>
    /* Background Image or Fallback Color */
    {bg_img_css}

    /* Optional: Add a semi-transparent overlay to make text more readable */
    .stApp::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(255, 255, 255, 0.5); /* White overlay with 50% opacity */
        z-index: -1; /* Place the overlay behind the content */
    }}

    /* Custom CSS for the input fields */
    div[data-testid="stTextInput"] {{
        max-width: 250px; /* Reduced width for text boxes */
    }}
    </style>
    """

    st.markdown(custom_css, unsafe_allow_html=True)
    # --- End Custom CSS ---

    # Use columns to align form left
    col1, col2, col3 = st.columns([1, 3, 6])

    with col2: # Place form in the left column
        st.subheader("Signup Details")

        # Use keys for input widgets to maintain state correctly across reruns
        new_name = st.text_input("Full Name", key="signup_name_input")
        new_email = st.text_input("Enter Email", key="signup_email_input")
        new_password = st.text_input("Create Password", type="password", key="signup_password_input")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password_input")


        # Placeholder for displaying status messages (success, warning, error)
        status_message = st.empty()

        if st.button("Sign Up", key="signup_button"):
            # Clear previous messages
            status_message.empty()

            # --- Validation ---
            if not new_name or not new_email or not new_password or not confirm_password:
                status_message.warning("Please fill in all fields.")
            elif new_password != confirm_password:
                status_message.error("Passwords do not match.")
            elif len(new_password) < 6: # Basic password length check
                 status_message.warning("Password must be at least 6 characters long.")
            elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", new_email): # More robust email format check
                 status_message.warning("Please enter a valid email address format.")
            else:
                # --- Call Database Function to Create User ---
                # This now calls the dynamic create_user function in db.py
                try:
                    # create_user now returns True on success, False if email exists, or None on DB error
                    user_created_status = create_user(new_name, new_email, new_password)

                    if user_created_status is True:
                        status_message.success("Account created successfully! You can now log in.")
                        # Navigate to login page after successful signup
                        st.session_state.page = 'login'
                        st.rerun() # Trigger immediate navigation

                    elif user_created_status is False:
                        # create_user returns False if email already exists
                        status_message.error("Failed to create account. This email might already be registered.")

                    elif user_created_status is None:
                         # create_user returns None on DB error
                         status_message.error("An error occurred while creating the account. Please try again.")


                except Exception as e:
                    # Catch any unexpected errors during the database call (unlikely with explicit None return)
                    status_message.error(f"An unexpected error occurred during signup. Please try again. (Error: {e})")
                    print(f"Signup DB Call Error: {e}") # Print error to console for debugging


        st.markdown("---") # Separator

        # Button to go back to login page
        if st.button("⬅️ Back to Login", key="back_to_login_button"):
            st.session_state.page = 'login' # Set page state to 'login'
            st.rerun() # Trigger immediate navigation

# Note: This script assumes it's part of a larger Streamlit application
# that manages page navigation using st.session_state.page.
# The main app.py would typically call signup_page() when st.session_state.page is 'signup'.

# Example usage if running this script directly for testing (usually not needed in a multi-page app)
# if __name__ == "__main__":
#     # Initialize page state if running directly
#     if 'page' not in st.session_state:
#         st.session_state.page = 'signup' # Start on signup page

#     # Simple page routing for direct testing
#     if st.session_state.page == 'signup':
#         signup_page()
#     elif st.session_state.page == 'login':
#          st.write("This is the Login page (placeholder)")
#          if st.button("Go to Signup"):
#              st.session_state.page = 'signup'
#              st.rerun()