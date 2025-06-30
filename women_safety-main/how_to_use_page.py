# how_to_use_page.py
import streamlit as st

def how_to_use_page():
    st.title("📖 How to Use")
    st.write("Instructions on how to use the Women Safety App.")
    st.info("How to use guide is not yet written. You can add detailed instructions here.")
    # Add detailed instructions here

    st.markdown("---") # Add a separator

    if st.button("⬅️ Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.experimental_rerun()