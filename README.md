# 🚨 SeFI – Safety Feminine Intelligence

> An AI-powered women’s safety system built to empower and protect women across India with real-time alerts, safety predictions, and emergency support.

---

## 🌟 Overview

**SeFI** (Safety Feminine Intelligence) is a smart and intuitive AI-based safety platform developed to provide women with reliable, real-time security information during emergencies or daily commutes. By analyzing 1L+ crime records with ML models, it predicts location-based safety risks and assists with instant SOS alerts and local emergency services.

---

## 🔥 Key Features

- 🆘 **SOS Emergency Alerts**  
  Instantly sends an email with your live location, full address, and timestamp to pre-set trusted contacts.

- 📍 **Live Safety Risk Detection**  
  Real-time AI-powered classification of your area as *safe* or *unsafe* based on crime patterns.

- 📊 **Crime Data Visualization**  
  Interactive dashboards with district-wise crime trends (starting from Tamil Nadu) using 1L+ records.

- 🚑 **Nearby Police & Hospital Finder**  
  Automatically maps and displays nearby emergency services for immediate support.

- 📞 **Emergency Helpline Access**  
  One-click access to verified helpline numbers including 100, 181, and 1091 across India.

---

## 🧠 Machine Learning Model

- **Model:** XGBoost Classifier  
- **Input:** Latitude, longitude, location metadata  
- **Output:** Safety status prediction (*Safe* / *Unsafe*)  
- **Tools:** Pandas, Scikit-learn, Geolocation Intelligence, Matplotlib

---

## 🛠 Tech Stack

| Category       | Technologies Used                             |
|----------------|------------------------------------------------|
| **Frontend**   | React.js, Streamlit                           |
| **Backend**    | Python, Flask                                 |
| **AI/ML**      | XGBoost, Pandas, NumPy                        |
| **APIs**       | Google Maps API, SMTP (Email), Geolocation API |
| **Data**       | 1,00,000+ crime records, hospital & police locations, emergency contacts |

---

## 📂 Folder Structure

SeFI-Project/
│
├── streamlit_app/ # Streamlit dashboard code
├── react_frontend/ # React.js frontend (if applicable)
├── flask_backend/ # Flask backend APIs
├── model/ # Trained ML model and notebooks
├── data/ # Crime dataset, hospitals, helplines
├── utils/ # Helper functions and logic
└── README.md # Project description


---

## 🚀 Getting Started

# Step 1: Clone the repository
git clone https://github.com/Rathika11/sefi-safety-system.git
cd sefi-safety-system

# Step 2: Install dependencies
pip install -r requirements.txt

# Step 3: Run the Streamlit app
streamlit run streamlit_app/main.py

# Now open the dashboard in your browser, test safety predictions, and simulate SOS alerts.
----


##📈 Future Enhancements
Mobile app version with geofence alerts

Multilingual support (Hindi, Tamil, Telugu, etc.)

Chatbot integration for live help

Integration with state crime databases for live feeds

❤️ Built With Purpose
SeFI is built with the mission to empower every woman in India to feel safe, informed, and protected—through the power of AI, open data, and real-time intelligence.

