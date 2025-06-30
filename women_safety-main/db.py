# db.py
# This file handles user authentication and database interactions using MongoDB.
# It should NOT import or directly interact with Streamlit's UI or session state.

import bcrypt # For secure password hashing
import pymongo # For MongoDB interaction
from pymongo import MongoClient, InsertOne, DeleteOne, ReplaceOne # Specific imports for clarity
from pymongo.errors import ConnectionFailure, OperationFailure, DuplicateKeyError
from bson.objectid import ObjectId # To handle MongoDB ObjectId
import streamlit as st # Used here only for accessing st.secrets
import os # Used to check for secrets file

# --- Configuration (Gets details from Streamlit Secrets) ---
def get_mongo_client():
    """Establishes and returns a MongoDB client connection using secrets."""
    # Check if secrets file exists and contains mongo config
    if not os.path.exists(".streamlit/secrets.toml"):
        print("DB: ERROR: .streamlit/secrets.toml not found. Cannot connect to MongoDB.")
        # Raise an error that app.py/pages can catch
        raise ConnectionFailure("MongoDB secrets file not found.")

    if "mongodb" not in st.secrets:
         print("DB: ERROR: '[mongodb]' section missing in .streamlit/secrets.toml")
         raise ConnectionFailure("MongoDB secrets section missing.")

    try:
        connection_string = st.secrets["mongodb"]["mongo_connection_string"]
        # Connect to MongoDB
        client = MongoClient(connection_string)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster') # Check if connection is successful
        print("DB: MongoDB connection successful!")
        return client
    except KeyError as e:
         print(f"DB: ERROR: Missing MongoDB secret: {e}. Check your .streamlit/secrets.toml")
         raise ConnectionFailure(f"MongoDB configuration error: Missing secret '{e}'.")
    except ConnectionFailure as e:
        print(f"DB: ERROR: Could not connect to MongoDB: {e}")
        # Re-raise the specific ConnectionFailure
        raise e
    except Exception as e:
        print(f"DB: An unexpected error occurred during MongoDB connection: {e}")
        # Re-raise as a generic exception
        raise e


def get_database():
    """Gets the specified database from the MongoDB client."""
    client = get_mongo_client()
    try:
        db_name = st.secrets["mongodb"]["mongo_database_name"]
        db = client[db_name]
        print(f"DB: Using database: {db_name}")
        return db
    except KeyError as e:
         print(f"DB: ERROR: Missing MongoDB database name secret: {e}. Check your .streamlit/secrets.toml")
         raise ConnectionFailure(f"MongoDB configuration error: Missing database name secret '{e}'.")
    except Exception as e:
        print(f"DB: An error occurred getting the database: {e}")
        raise e # Re-raise


# --- Collection Names ---
USERS_COLLECTION = "users"
CONTACTS_COLLECTION = "contacts"


# --- Database Initialization (MongoDB specific) ---
def init_db():
    """
    Ensures necessary collections exist and creates indexes in MongoDB.
    This function should be called once when the application starts or is set up.
    """
    print("DB: Checking/Initializing MongoDB collections and indexes.")
    db = None
    try:
        db = get_database()

        # Ensure 'users' collection exists and has a unique index on email
        if USERS_COLLECTION not in db.list_collection_names():
             print(f"DB: Creating '{USERS_COLLECTION}' collection.")
             db.create_collection(USERS_COLLECTION)

        # Create a unique index on the 'email' field in the users collection
        # This enforces unique emails and allows catching DuplicateKeyError
        if 'email_1' not in db[USERS_COLLECTION].index_information():
             print(f"DB: Creating unique index on '{USERS_COLLECTION}.email'.")
             db[USERS_COLLECTION].create_index("email", unique=True)

        # Ensure 'contacts' collection exists
        if CONTACTS_COLLECTION not in db.list_collection_names():
             print(f"DB: Creating '{CONTACTS_COLLECTION}' collection.")
             db.create_collection(CONTACTS_COLLECTION)

        # Create an index on user_id in the contacts collection for faster lookup
        if 'user_id_1' not in db[CONTACTS_COLLECTION].index_information():
             print(f"DB: Creating index on '{CONTACTS_COLLECTION}.user_id'.")
             db[CONTACTS_COLLECTION].create_index("user_id")

        print("DB: MongoDB initialization checked/completed.")

    except ConnectionFailure:
         print("DB: Initialization failed due to MongoDB connection issues.")
         # The connection error is already printed by get_database/get_mongo_client
         pass # Allow the ConnectionFailure to propagate if needed
    except Exception as e:
        print(f"DB Error during MongoDB initialization: {e}")
        # In a real app, you might want more specific error handling
        pass # Allow other exceptions to propagate if needed
    finally:
        # Client connection should ideally be managed outside, but for simplicity here
        # the client from get_database might need closing depending on implementation details
        # For MongoClient instances from get_mongo_client, they are reused implicitly by pymongo
        pass


# --- User Authentication Functions (Dynamic) ---

def get_user(email, password):
    """
    Retrieves a user from the database by email and verifies the password.
    Returns the user dictionary {id, name, email} if credentials are valid, None otherwise.
    """
    print(f"DB: Attempting login for email: {email}")
    db = None
    try:
        db = get_database()
        users_collection = db[USERS_COLLECTION]

        # Find the user document by email
        user_document = users_collection.find_one({'email': email})

        if user_document:
            # User found, now verify password hash
            stored_password_hash = user_document['password_hash']

            # Verify the provided password against the stored hash
            # bcrypt.checkpw takes bytes, so encode the plain password and the stored hash
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
                print(f"DB: Login successful for email: {email}")
                # Return user data as a dictionary, converting ObjectId to string
                return {"id": str(user_document['_id']), "name": user_document['name'], "email": user_document['email']}
            else:
                print(f"DB: Password verification failed for email: {email}")
                return None # Password doesn't match
        else:
            print(f"DB: User not found with email: {email}")
            return None # User not found

    except ConnectionFailure:
        print("DB: get_user failed due to MongoDB connection issues.")
        # Allow the exception to propagate to be caught by the calling page
        raise
    except Exception as e:
        print(f"DB Error during get_user: {e}")
        # Raise a generic exception or handle specifically
        raise e


def create_user(name, email, password):
    """
    Creates a new user in the database.
    Returns True on success, False if email already exists, or None on DB error.
    """
    print(f"DB: Attempting to create user: Name: {name}, Email: {email}")
    db = None
    try:
        db = get_database()
        users_collection = db[USERS_COLLECTION]

        # Hash the password securely
        # bcrypt.gensalt() generates a salt, bcrypt.hashpw() hashes the password with the salt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        print(f"DB: Hashed password for {email}")

        # Create the user document
        user_document = {
            "name": name,
            "email": email,
            "password_hash": password_hash
        }

        # Insert the new user document
        # This will raise DuplicateKeyError if email is not unique and index is active
        insert_result = users_collection.insert_one(user_document)

        print(f"DB: User created successfully with ID: {insert_result.inserted_id}")
        return True # Indicate success

    except DuplicateKeyError:
         # This specifically catches the case where email is UNIQUE and already exists
         print(f"DB: User creation failed (DuplicateKeyError) - email already exists: {email}")
         return False # Indicate that email is taken
    except ConnectionFailure:
        print("DB: create_user failed due to MongoDB connection issues.")
        # Allow the exception to propagate
        raise
    except Exception as e:
        print(f"DB Error during create_user: {e}")
        # Raise a generic exception or handle specifically
        raise e

# --- Contact Management Functions (Dynamic using MongoDB) ---
# These functions now link contacts to a user_id (which is the string ObjectId from MongoDB)

def save_contact(user_id, name, phone, email):
    """
    Saves a contact for a specific user in the database.
    Returns True on success, False on failure.
    """
    print(f"DB: Saving contact for User ID {user_id}: Name: {name}, Email: {email}")
    db = None
    try:
        db = get_database()
        contacts_collection = db[CONTACTS_COLLECTION]

        # Create the contact document, storing user_id as a string
        contact_document = {
            "user_id": user_id, # Store the user's ObjectId as a string
            "name": name,
            "phone": phone,
            "email": email
        }

        # Insert the new contact document
        insert_result = contacts_collection.insert_one(contact_document)
        print(f"DB: Contact saved successfully with ID: {insert_result.inserted_id}")
        return True

    except ConnectionFailure:
        print("DB: save_contact failed due to MongoDB connection issues.")
        raise
    except Exception as e:
        print(f"DB Error during save_contact: {e}")
        return False # Indicate a database error


def get_contacts(user_id):
    """
    Retrieves contacts for a user from the database.
    Returns a list of contact dictionaries [{ '_id': ObjectId(...), 'name': '...', ... }, ...]
    (Note: _id will be ObjectId, user_id is string)
    """
    print(f"DB: Getting contacts for User ID: {user_id}")
    db = None
    contacts_list = []
    try:
        db = get_database()
        contacts_collection = db[CONTACTS_COLLECTION]

        # Find contact documents filtering by user_id (which is stored as a string)
        # Use a cursor and convert documents to dictionaries if needed, although pymongo results are dict-like
        for contact_document in contacts_collection.find({"user_id": user_id}):
            # You can optionally convert _id to string here if needed by the calling code
            # contact_document['_id'] = str(contact_document['_id'])
            contacts_list.append(contact_document)


        print(f"DB: Retrieved {len(contacts_list)} contacts for User ID {user_id}.")
        return contacts_list

    except ConnectionFailure:
        print("DB: get_contacts failed due to MongoDB connection issues.")
        raise
    except Exception as e:
        print(f"DB Error during get_contacts: {e}")
        return [] # Return empty list on error


def delete_contact(contact_id):
    """
    Deletes a contact by its ID from the database.
    Returns True on success, False if not found, or None on DB error.
    """
    print(f"DB: Deleting contact ID: {contact_id}")
    db = None
    try:
        db = get_database()
        contacts_collection = db[CONTACTS_COLLECTION]

        # Delete the contact by its ObjectId
        # Ensure contact_id passed in is a valid ObjectId string
        object_id_to_delete = ObjectId(contact_id)

        delete_result = contacts_collection.delete_one({'_id': object_id_to_delete})

        # Check if a document was deleted
        if delete_result.deleted_count > 0:
            print(f"DB: Contact ID {contact_id} deleted successfully.")
            return True
        else:
            print(f"DB: Contact ID {contact_id} not found for deletion.")
            return False # Contact ID not found

    except ConnectionFailure:
        print("DB: delete_contact failed due to MongoDB connection issues.")
        raise
    except Exception as e:
        print(f"DB Error during delete_contact: {e}")
        # Raise a generic exception or return None
        raise e


# --- Call init_db() once when the module is first imported ---
# This ensures the database connection is checked and collections/indexes are handled.
# Note: In a multi-threaded environment (like Streamlit can use), MongoClient should be
# created carefully or reused. This simple approach works but might need refinement
# for high concurrency if not relying on pymongo's internal pooling.
init_db()