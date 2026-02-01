from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# Use absolute paths for PythonAnywhere compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# How long before a driver is auto-removed?
TIMEOUT_INTERVAL = '45 minutes' 

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- CLEANUP ---
def cleanup_stale_drivers():
    conn = get_db_connection()
    try:
        conn.execute(f'''
            UPDATE driver_status 
            SET is_online = 0 
            WHERE is_online = 1 
            AND last_updated < datetime('now', '-{TIMEOUT_INTERVAL}')
        ''')
        conn.commit()
    except Exception as e:
        print(f"Cleanup Error: {e}")
    finally:
        conn.close()

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rider')
def rider_view():
    cleanup_stale_drivers()
    conn = get_db_connection()
    
    # FIX: strftime formats the date to dd/mm/yyyy HH:MM:SS
    drivers = conn.execute('''
        SELECT d.name, d.phone, d.vehicle_type, d.photo_url, s.location_name, 
               strftime('%d/%m/%Y %H:%M:%S', datetime(s.last_updated, '+5 hours', '+30 minutes')) as last_updated
        FROM drivers d
        JOIN driver_status s ON d.id = s.driver_id
        WHERE s.is_online = 1
        ORDER BY s.last_updated DESC
    ''').fetchall()
    conn.close()
    return render_template('rider.html', drivers=drivers)

@app.route('/driver')
def driver_menu():
    return render_template('driver_menu.html')

# --- DRIVER ROUTES ---
@app.route('/driver/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        vehicle = request.form['vehicle']
        location = request.form['location']
        photo = request.files.get('photo')
        
        photo_filename = 'default_driver.png'
        if photo and photo.filename != '':
            file_extension = os.path.splitext(photo.filename)[1]
            photo_filename = f"{phone}{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            photo.save(file_path)
            
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute('INSERT INTO drivers (name, phone, vehicle_type, photo_url) VALUES (?, ?, ?, ?)',
                         (name, phone, vehicle, photo_filename))
            new_driver_id = cur.lastrowid
            
            cur.execute('''
                INSERT INTO driver_status (driver_id, location_name, is_online, last_updated)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ''', (new_driver_id, location))
            
            conn.commit()
            return redirect(url_for('driver_menu'))
        except sqlite3.IntegrityError:
            return "Phone number already exists!"
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/driver/update', methods=('GET', 'POST'))
def update_location():
    if request.method == 'POST':
        phone = request.form['phone']
        location = request.form['location']
        conn = get_db_connection()
        driver = conn.execute('SELECT id FROM drivers WHERE phone = ?', (phone,)).fetchone()
        
        if driver:
            if location == "Offline":
                conn.execute('UPDATE driver_status SET is_online = 0 WHERE driver_id = ?', (driver['id'],))
                msg = "You are now Offline."
            else:
                conn.execute('''
                    INSERT OR REPLACE INTO driver_status (driver_id, location_name, is_online, last_updated)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ''', (driver['id'], location))
                msg = f"Location updated to {location}"
                
            conn.commit()
            conn.close()
            return render_template('update.html', success=msg)
        else:
            conn.close()
            return render_template('update.html', error="Phone number not found.")
            
    return render_template('update.html')

# --- ADMIN ROUTES ---
@app.route('/admin', methods=('GET', 'POST'))
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ? AND password = ?', 
                             (username, password)).fetchone()
        conn.close()
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dash'))
        else:
            return "Invalid Credentials"
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dash():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dash.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# --- API ROUTES ---

@app.route('/api/admin/all_drivers')
def get_all_drivers_admin():
    conn = get_db_connection()
    # FIX: Also formatted here for the Admin Panel
    drivers = conn.execute('''
        SELECT d.id as driver_id, d.name, d.phone, d.vehicle_type, d.photo_url, 
               s.location_name, s.is_online, 
               strftime('%d/%m/%Y %H:%M:%S', datetime(s.last_updated, '+5 hours', '+30 minutes')) as last_updated
        FROM drivers d
        JOIN driver_status s ON d.id = s.driver_id
        ORDER BY s.is_online DESC, s.last_updated DESC
    ''').fetchall()
    conn.close()
    data = [dict(row) for row in drivers]
    return jsonify(data)

@app.route('/api/driver/online/<int:driver_id>', methods=['POST'])
def force_online(driver_id):
    conn = get_db_connection()
    try:
        status = conn.execute('SELECT location_name FROM driver_status WHERE driver_id = ?', (driver_id,)).fetchone()
        loc = status['location_name'] if status and status['location_name'] else 'Main Gate'
        conn.execute('''
            INSERT OR REPLACE INTO driver_status (driver_id, location_name, is_online, last_updated)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ''', (driver_id, loc))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/driver/offline/<int:driver_id>', methods=['POST'])
def force_offline(driver_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE driver_status SET is_online = 0 WHERE driver_id = ?', (driver_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/driver/delete/<int:driver_id>', methods=['POST'])
def delete_driver(driver_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM driver_status WHERE driver_id = ?', (driver_id,))
        conn.execute('DELETE FROM drivers WHERE id = ?', (driver_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/driver/edit/<int:driver_id>', methods=['POST'])
def edit_driver(driver_id):
    data = request.json
    new_name = data.get('name')
    new_phone = data.get('phone')
    new_vehicle = data.get('vehicle')
    new_location = data.get('location')
    
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT id FROM drivers WHERE phone = ? AND id != ?', (new_phone, driver_id)).fetchone()
        if existing:
            return jsonify({"success": False, "error": "Phone number already in use."})

        conn.execute('UPDATE drivers SET name = ?, phone = ?, vehicle_type = ? WHERE id = ?', (new_name, new_phone, new_vehicle, driver_id))

        current_status = conn.execute('SELECT is_online FROM driver_status WHERE driver_id = ?', (driver_id,)).fetchone()
        is_online = current_status['is_online'] if current_status else 0

        conn.execute('''
            INSERT OR REPLACE INTO driver_status (driver_id, location_name, is_online, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (driver_id, new_location, is_online))

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/get_driver_photo')
def get_driver_photo():
    phone = request.args.get('phone')
    conn = get_db_connection()
    driver = conn.execute('SELECT photo_url FROM drivers WHERE phone = ?', (phone,)).fetchone()
    conn.close()
    if driver and driver['photo_url']:
        return jsonify({'photo_url': driver['photo_url']})
    else:
        return jsonify({'photo_url': 'default_driver.png'})


@app.route('/sms_webhook', methods=['POST'])
def sms_webhook():
    # 1. Capture the raw message (keep original case for Names)
    if request.is_json:
        data = request.json
        phone = data.get('phone')
        raw_msg = data.get('msg', '').strip()
    else:
        phone = request.form.get('From') or request.form.get('phone')
        raw_msg = request.form.get('Body') or request.form.get('msg') or ''
        raw_msg = raw_msg.strip()

    if phone: 
        phone = phone.replace('+91', '').replace(' ', '')
    
    # Create an UPPERCASE version for command checking
    cmd_msg = raw_msg.upper()
    print(f"DEBUG: SMS from {phone}: {raw_msg}")

    conn = get_db_connection()
    try:
        # Check if driver exists
        driver = conn.execute('SELECT id, name FROM drivers WHERE phone = ?', (phone,)).fetchone()
        response_text = ""
        
        if driver:
            # --- EXISTING DRIVER LOGIC ---
            if cmd_msg.startswith("ON "):
                # Extract location from the original message to keep casing nice (optional)
                # Or just use the upper case one. Let's use UPPER for standard locations.
                loc = cmd_msg[3:].strip() 
                conn.execute('''
                    INSERT OR REPLACE INTO driver_status (driver_id, location_name, is_online, last_updated) 
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ''', (driver['id'], loc))
                conn.commit()
                response_text = f"Location updated to {loc}"
                
            elif cmd_msg == "OFF":
                conn.execute('UPDATE driver_status SET is_online = 0 WHERE driver_id = ?', (driver['id'],))
                conn.commit()
                response_text = "You are now offline. Bye!"
            
            else:
                response_text = f"Hello {driver['name']}. Send 'ON [Location]' or 'OFF'."

        else:
            # --- NEW REGISTRATION LOGIC ---
            if cmd_msg.startswith("REGISTER "):
                # Expected format: "REGISTER Rohit Auto"
                parts = raw_msg.split(' ') # Split by space
                
                # We need at least 3 parts: Command, Name, Vehicle
                if len(parts) >= 3:
                    # Vehicle is usually the last word
                    vehicle = parts[-1]
                    # Name is everything in between
                    name = " ".join(parts[1:-1])
                    
                    # 1. Create Driver (Default Photo)
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO drivers (name, phone, vehicle_type, photo_url) 
                        VALUES (?, ?, ?, ?)
                    ''', (name, phone, vehicle, 'default_driver.png'))
                    new_id = cur.lastrowid
                    
                    # 2. Set them Online immediately (Default: Main Gate)
                    cur.execute('''
                        INSERT INTO driver_status (driver_id, location_name, is_online, last_updated)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (new_id, 'Main Gate'))
                    
                    conn.commit()
                    response_text = f"Welcome {name}! Registered successfully. You are online at Main Gate."
                else:
                    response_text = "Error. Format: REGISTER [Name] [Vehicle]"
            else:
                response_text = "Not registered. Send 'REGISTER [Name] [Vehicle]' to join."

    except Exception as e:
        response_text = f"System Error: {str(e)}"
        print(response_text)
    finally:
        conn.close()
    
    return jsonify({"status": "success", "reply": response_text})

if __name__ == '__main__':
    app.run(debug=True, port=5000)