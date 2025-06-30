# developed_by_page.py
import streamlit as st

def developed_by_page():
    st.title("💡 Developed By")
    st.write("Information about the developer(s) goes here.")
    st.info("Developer information is not yet detailed.")
    # Add developer details, credits, etc. here

    st.markdown("---") # Add a separator

    if st.button("⬅️ Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.experimental_rerun()