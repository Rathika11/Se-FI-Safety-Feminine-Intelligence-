# email_alert.py
import smtplib
from email.mime.text import MIMEText
import streamlit as st # Used here only for accessing st.secrets and potentially st.error within the function
import os
import ssl
import time # Import time for timestamp
import firebase_admin
from firebase_admin import credentials, storage

firebase_app = None

def upload_video_to_firebase(local_video_path, video_filename):
    global firebase_app
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase_key.json")
            firebase_app = firebase_admin.initialize_app(cred, {
                'storageBucket': 'sos-alert-1bf56.appspot.com'  # ✅ Use your bucket name
            })

        bucket = storage.bucket()
        blob = bucket.blob(f"sos_videos/{video_filename}")
        blob.upload_from_filename(local_video_path)
        blob.make_public()

        print(f"✅ Uploaded video: {blob.public_url}")
        return blob.public_url

    except Exception as e:
        print(f"❌ Firebase upload error: {e}")
        return None

def send_alert_email(contacts, location=None, video_link=None):
    """
    Sends an SOS alert email to a list of contacts using SMTP.

    Reads email credentials from Streamlit secrets (.streamlit/secrets.toml).

    Args:
        contacts (list): A list of email addresses (strings).
        location (dict, optional): Dictionary containing location info.
                                    Expected structure:
                                    {'raw': {'latitude': ..., 'longitude': ..., 'accuracy': ..., 'source': ...},
                                     'detailed': {'full_address': ..., 'street': ..., 'city': ..., ...},
                                     'email_body_string': '...'}
                                    Defaults to None.
        video_link (str, optional): Link to the video evidence.
                                    Defaults to None.
    """
    print("Attempting to send real email via smtplib...")

    # --- Securely get email credentials from Streamlit secrets ---
    # Check if secrets are available (important for local testing without secrets file)
    # and if email section exists
    if not os.path.exists(".streamlit/secrets.toml"):
        print("WARNING: .streamlit/secrets.toml not found. Cannot send real emails.")
        # Use a placeholder to show message without disrupting flow significantly
        st.error("Email credentials not configured (.streamlit/secrets.toml missing). Cannot send real emails.")
        # Re-raise to be caught by dashboard's try/except block
        raise Exception("Email secrets file missing.")


    # Using st.secrets might trigger a rerun if the file changes, but accessing
    # non-existent keys will raise a KeyError.
    if "email" not in st.secrets:
         print("ERROR: '[email]' section missing in .streamlit/secrets.toml")
         st.error("Email configuration error: '[email]' section missing in secrets.toml.")
         raise Exception("Email secrets section missing.")

    try:
        # Access secrets - Streamlit makes these available via st.secrets
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"] # USE APP PASSWORD!
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = int(st.secrets["email"]["smtp_port"]) # Ensure port is integer
        # Add a check for empty credentials
        if not sender_email or not sender_password or not smtp_server or not smtp_port:
             raise ValueError("Empty value found in email secrets.")

    except KeyError as e:
        print(f"ERROR: Missing email secret: {e}. Check your .streamlit/secrets.toml")
        st.error(f"Email configuration error: Missing secret '{e}'. Cannot send real emails.")
        raise Exception(f"Missing email secret: {e}")
    except ValueError as e:
        print(f"ERROR: Invalid value in email secrets: {e}. Check your .streamlit/secrets.toml port number or empty values.")
        st.error(f"Email configuration error: Invalid value in secrets. {e}. Cannot send real emails.")
        raise Exception(f"Invalid value in email secrets: {e}")


    if not contacts:
        print("WARNING: No contacts provided to send email alert.")
        # No Streamlit message here, dashboard checks for contacts before calling this
        # Return True or None? Raising an error might be cleaner if contacts are empty.
        # But dashboard already handles the empty contacts case, so return silently?
        # Let's assume dashboard only calls this if contacts are > 0.
        pass # Continue if contacts list is received (even if it's empty, though dashboard guards)


    # --- Construct email body using the received location data structure ---
    body = "URGENT: SOS Alert! A user requires assistance.\n\n"

    if location is not None and isinstance(location, dict):
        raw_location = location.get('raw')
        detailed_address = location.get('detailed')
        prebuilt_body_string = location.get('email_body_string') # Get the string built in dashboard

        # Option 1: Use the pre-built body string from dashboard if available
        # This is the easiest way to ensure consistency with dashboard display
        if prebuilt_body_string:
             body = prebuilt_body_string
             print("Using pre-built email body string from dashboard.py") # Debug print
        # Option 2: Build the body here using the structured data
        else:
            print("Building email body in email_alert.py") # Debug print
            body = "URGENT: SOS Alert! A user requires assistance.\n\n" # Re-initialize body

            body += "Last Known Location:\n"

            # Prefer detailed address if available and not an error
            if detailed_address and not detailed_address.get('error'):
                 body += "  Address Details:\n"
                 if detailed_address.get('full_address'):
                     body += f"    Full Address: {detailed_address['full_address']}\n\n"
                 # Include specific components if available and not 'N/A'
                 if detailed_address.get('street') and detailed_address.get('street') != 'N/A':
                      body += f"    Street/Road: {detailed_address.get('street')}\n"
                 if detailed_address.get('city') and detailed_address.get('city') != 'N/A':
                      body += f"    City: {detailed_address.get('city')}\n"
                 if detailed_address.get('district') and detailed_address.get('district') != 'N/A':
                      body += f"    District: {detailed_address.get('district')}\n"
                 if detailed_address.get('state') and detailed_address.get('state') != 'N/A':
                      body += f"    State: {detailed_address.get('state')}\n"
                 if detailed_address.get('country') and detailed_address.get('country') != 'N/A':
                      body += f"    Country: {detailed_address.get('country')}\n"
                 # Add raw coordinates as supplementary info if available
                 if raw_location and not raw_location.get('error'):
                      lat = raw_location.get('latitude', 'N/A')
                      lon = raw_location.get('longitude', 'N/A')
                      acc = raw_location.get('accuracy', 'Unknown')
                      body += f"\n  Coordinates: Latitude {lat}, Longitude {lon} (Accuracy: {acc} m)\n"
                      # Add map link using raw coordinates
                      Maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                      body += f"  View on Map: {Maps_link}\n"
                 elif detailed_address.get('error'):
                      body += f"\nDetailed Address Lookup Error: {detailed_address['error']}\n" # Include Nominatim error
                 else:
                     body += "\nRaw coordinate data not available.\n"


            # Fallback to raw location if detailed address is not available or had an error
            elif raw_location and not raw_location.get('error'):
                 lat = raw_location.get('latitude', 'N/A')
                 lon = raw_location.get('longitude', 'N/A')
                 acc = raw_location.get('accuracy', 'Unknown')
                 src = raw_location.get('source', 'N/A')
                 body += f"  Source: {src}\n"
                 body += f"  Coordinates: Latitude {lat}, Longitude {lon} (Accuracy: {acc} m)\n"
                 # Add map link using raw coordinates
                 Maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                 body += f"  View on Map: {Maps_link}\n"
            # Handle cases where browser location had an error
            elif raw_location and raw_location.get('error'):
                 body += f"  Could not retrieve initial location details: {raw_location['error']}\n"
                 body += f"  Source: {raw_location.get('source', 'Error')}\n"
            else:
                body += "  Location data format is unexpected.\n"

    else:
        body += "Location information not available.\n"

    if video_link:
        body += f"\nVideo Evidence: {video_link}\n"

    body += "\nThis is an automated alert. Please respond if you are able."
    body += f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}" # Add local timestamp

    msg = MIMEText(body)
    msg['Subject'] = "URGENT: SOS ALERT!"
    msg['From'] = sender_email
    # 'To' header is typically just for display, actual recipients are passed to sendmail
    msg['To'] = ", ".join(contacts) # Join list of emails into a single string for 'To' header

    try:
        # Create a secure SSL context
        context = ssl.create_default_context()

        # Use SMTP_SSL for more reliable connection when using SSL ports like 465
        # Gmail and many providers expect SMTP_SSL on port 465
        if smtp_port == 465:
            print(f"Connecting to SMTP_SSL server {smtp_server}:{smtp_port}...")
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                print(f"Logging in as {sender_email}...")
                server.login(sender_email, sender_password)
                print(f"Sending email to {', '.join(contacts)}...")
                server.sendmail(sender_email, contacts, msg.as_string())
                print("✅ Email sent successfully.")
        # Use STARTTLS for ports like 587
        else:
            print(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                print("Starting TLS...")
                server.starttls(context=context) # Secure the connection
                print(f"Logging in as {sender_email}...")
                server.login(sender_email, sender_password) # Log in to the account
                print("Login successful.")
                print(f"Sending email to {', '.join(contacts)}...")
                server.sendmail(sender_email, contacts, msg.as_string())
                print("✅ Email sent successfully.")

        print(f"SUCCESS: SOS email process completed for {', '.join(contacts)}")
        return True

    except Exception as e:
        # Print the detailed error to the console/logs
        print(f"❌ Failed to send email using smtplib: {e}")
        # Re-raise the exception so dashboard.py can catch it and display an error message to the user
        raise e

def main():
    contacts = ["example1@gmail.com", "example2@gmail.com"]
    location = None  # or your real structure

if __name__ == "__main__":
    main()