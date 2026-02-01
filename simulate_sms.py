import requests
import time

SERVER_URL = "http://127.0.0.1:5000/sms_webhook"

def send_sms(phone_number, message):
    """
    Simulates sending an SMS by POSTing data to the Flask server.
    """
    payload = {
        "phone": phone_number,
        "msg": message
    }
    
    try:
        print(f" Phone ({phone_number}) sending SMS: '{message}'...")
        
        response = requests.post(SERVER_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f" Server Reply: {data.get('status', 'Unknown')}")
            if 'reply' in data:
                print(f" Return SMS: {data['reply']}")
        else:
            print(f" Error: Server returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(" Error: Could not connect. Is the Flask server running?")

# --- THE INTERACTIVE LOOP ---
if __name__ == "__main__":
    print("\n========================================")
    print("       IITK SMS SIMULATOR 2.0      ")
    print("========================================")
    print("1. Make sure 'python app.py' is running.")
    print("2. Enter a phone number below.")
    print("----------------------------------------")
    
    while True:
        phone = input("\n Enter Driver Phone Number: ")
        if not phone: break
        
        print("\n--- Available Commands ---")
        print("1. NEW USER:   REGISTER [Name] [Vehicle]")
        print("   Ex: REGISTER Rohit Auto")
        print("   Ex: REGISTER Sunil E-Rick")
        print("--------------------------")
        print("2. UPDATE LOC: ON [Location Name]")
        print("   Ex: ON Main Gate")
        print("   Ex: ON Hall 1")
        print("   Ex: ON Old Shopping Complex")
        print("   Ex: ON Health Centre")
        print("   Ex: ON New SAC")
        print("--------------------------")
        print("3. GO OFFLINE: OFF")
        print("--------------------------")
        
        msg = input("📝 Enter SMS Message: ")
        
        send_sms(phone, msg)
        time.sleep(1)