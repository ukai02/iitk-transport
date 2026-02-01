# IITK Transport - Smart Auto-Rickshaw Management System

A full-stack web application designed to digitize campus transport at IIT Kanpur. It bridges the gap between students (smartphone users) and auto drivers (feature phone users).

## Key Features
* **Hybrid Connectivity:** Drivers update their location via **SMS** (simulated) using basic feature phones.
* **Live Rider Dashboard:** Students see real-time driver locations on a map.
* **Admin Control:** Full CRUD capabilities (Register, Edit, Delete, Mark Offline).
* **Auto-Cleanup:** System automatically marks drivers offline if they are inactive for 45 minutes.
* **Simulation Script:** Includes `simulate_sms.py` to test the SMS gateway functionality without physical hardware.

## Tech Stack
* **Backend:** Python (Flask)
* **Database:** SQLite (File-based, lightweight)
* **Frontend:** HTML5, CSS3, JavaScript 

## How to Run Locally
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Start the server:
    ```bash
    python app.py
    ```
3.  Open `http://127.0.0.1:5000` in your browser.
4.  **To Simulate SMS:** Open a second terminal and run:
    ```bash
    python simulate_sms.py
    ```

## Admin Credentials
1. Username:
   ```bash
   admin
   ```
2. Password:
   ```bash
   admin123
   ```
