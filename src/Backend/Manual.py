import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import cv2
import signal
import time
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pymavlink import mavutil
from modules.mavlink_commands import *
from modules.latlon import *
from modules.automation import *
from modules.drone_status import drone_state
from modules.logger_config import *
from flask_socketio import SocketIO, emit



app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="http://localhost:5173")

# # Set the SocketIO instance for logging
# set_socketio_instance(socketio)

# Setup 
#if __name__ == '__main__':
#    setup_logging(socketio) 

@socketio.on('connect')
def handle_connect():
    logging.getLogger().status('Logger connected')

@socketio.on('disconnect')
def handle_disconnect():
    reason = request.args.get('reason', 'unknown')  # Retrieve the reason for disconnection
    logging.getLogger().status(f'Logger disconnected. Reason: {reason}')



CORS(app)


# Directories and File paths
parent_folder = "../../Data/Test"
IMAGE_DIRECTORY = parent_folder+"/images"
CROPPED_IMAGE_DIRECTORY = parent_folder+"/cropped"
DATA_FILE = '../../Data/details.txt'
csv_path = parent_folder+'/results.csv'
pickle_path = parent_folder+'/cam_wps.pickle'
geo_log_path = parent_folder+"/geo_log.txt"
geo_path = "./modules/geotag_on_UI_laptop.py"

# Global variables
global xco, yco, id, lats, longs, connection, process
global_count = 0
#connection = None
#is_connected = False
#the_connection = None
lats = ["null", "null", "null", "null", "null"]
longs = ["null", "null", "null", "null", "null"]

# Ensure directories exist
if not os.path.exists(CROPPED_IMAGE_DIRECTORY):
    os.makedirs(CROPPED_IMAGE_DIRECTORY, exist_ok=True)

if not os.path.exists(IMAGE_DIRECTORY):
    os.makedirs(IMAGE_DIRECTORY, exist_ok=True)

class ImageEventHandler(FileSystemEventHandler): # filesystemevent handlr a predefined library
    """Handles file system events for the image directory."""
    
    def on_created(self, event):
        if event.is_directory:
            return
        self.emit_image_update()

    def on_deleted(self, event):
        if event.is_directory:
            return
        self.emit_image_update()

    def on_modified(self, event):
        if event.is_directory:
            return
        self.emit_image_update()

    def emit_image_update(self):
        """Emit updated image URLs to connected clients."""
        images = os.listdir(IMAGE_DIRECTORY)
        socketio.emit('image_update', {'imageUrls': images})

def start_watching():
    """Start watching the image directory for changes."""
    event_handler = ImageEventHandler() # creates an instance of event handler
    observer = Observer() # Creates an empty observer object, ready to monitor directories.
    # now transfer the above instances so to the observer object pass this 
    # even_handler via schedule command to check on this IMAGE_DIRECTORY
    # Tells the observer which directory to watch and which event handler to use.
    observer.schedule(event_handler, IMAGE_DIRECTORY, recursive=False) 
    observer.start() # Starts the monitoring process so it begins reacting to file system changes.
    try:
        #Starts the function and enters the infinite while True loop.
        while True:
            #n each iteration, the program "sleeps" for 1 second (time.sleep(1)) 
            #to save CPU by preventing the loop from running endlessly and consuming unnecessary resources.
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt: # when pressed control c 
        observer.stop() # stops the program i mean observation
    observer.join()
    """
    The observer.stop() command tells the observer to stop observing (no more events will be handled).
    But, since the observer thread might still be busy processing events, we use observer.join(). 
    This ensures that the main program waits for the observer thread to finish any ongoing work before completely shutting down.
    """

def run_sync_script():
    # runs your sync_jetson.sh in the background using bash
    # goes to the shell script file and runs the command to start the process
    script_path = "../../sync_jetson.sh"
    global syncprocess
    try:
        # Creates a separate terminal-like environment to run the shell script command 
        syncprocess = subprocess.Popen(
            ["/bin/bash", script_path],
            stdout=subprocess.DEVNULL,# If there is output, discard it (don't show it)
            stderr=subprocess.DEVNULL,# If there is an error, discard it too
            preexec_fn=os.setsid  # Runs in a new process group (detached from the parent)
            # like a child class 
        )
        logging.info(f"Sync script started in the background with PID {process.pid}.")
        return syncprocess  # Store this in your app to terminate or track it later
    except Exception as e:
        logging.error("Unexpected error in sync script:\n" + str(e))
        return None

def stop_sync_script():
    #cleanly stops that background process.
    if syncprocess:
        os.killpg(os.getpgid(syncprocess.pid), signal.SIGTERM) # this is to kill the entire thing

        # login the info 
        logging.getLogger().status("Sync stopped successfully.")
        logging.info(f"Sync script with PID {syncprocess.pid} terminated.")

def crop_image(image_path, x, y):
    global global_count, xco, yco
    image = cv2.imread(image_path)

    xco = int(x)
    yco = int(y)

    height, width, _ = image.shape
    crop_size = 100

    # max size for the cropped image 

    x_start = max(xco - crop_size, 0)
    x_end = min(xco + crop_size, width)
    y_start = max(yco - crop_size, 0)
    y_end = min(yco + crop_size, height)

    crop = image[y_start:y_end, x_start:x_end]

    
    logging.getLogger().status(f'Received coordinates: x={xco}, y={yco}')
    logging.getLogger().status('Cropping Image...')
    cropped_image_filename = f'cropped_image_{global_count}.png'
    cropped_image_path = os.path.join(
        CROPPED_IMAGE_DIRECTORY, cropped_image_filename)
    cv2.imwrite(cropped_image_path, crop)

    global_count += 1 # counts to update the file number in the name

    return cropped_image_filename


def run_python_file(file_path):#Starts running a Python script in the background and logs its output to a file (geo_log_path).
    # Open the output file in append mode to preserve existing content 
    with open(geo_log_path, "a") as f:
        # Start the subprocess with stderr redirected to a pipe
        process = subprocess.Popen(["python", file_path], stdout=f)
    return process

def stop_python_file():#Stops that running script and then stops the sync process (stop_sync_script()).
    global process
    try:
        # pid gets the process id 
        os.kill(process.pid, signal.SIGTERM)  # Send SIGTERM signal to the process

        """
        SIGTERM	Please terminate nicely	Signal Terminate
        SIGKILL	Die immediately 
        SIGINT	Ctrl + C from terminal
        
        """

        logging.getLogger().status("Python file stopped successfully.")
        time.sleep(5)
        stop_sync_script()

    except ProcessLookupError:
        logging.getLogger().status("Process not found. It may have already stopped.")


@app.route('/all-images', methods=['GET']) # get all the images as paths
def all_images():
    with os.scandir(IMAGE_DIRECTORY) as entries:
        # Filter to include only files (skip directories) and sort by name if desired
        images = [entry.name for entry in entries if entry.is_file()]
        images.sort()
    return jsonify({'imageUrls': images})

"""
📬 What are methods in routes?

When someone comes to the café (your server), they can do different actions:
Action	Real World	Programming	Meaning
Ask for something	"Can I see the menu?"	GET	Just want info
Give something	"Here's my order."	POST	Sending you data
Update something	"I changed my mind!"	PUT	Modify data
Delete something	"Cancel my order!"	DELETE	Remove data
"""
"""
🔁 Think of APIs like Delivery Guys 🚚

Imagine:

    Frontend = Hungry Customer 😋

    Backend/API = Zomato Delivery Guy 🛵

    Database / Files = Kitchen 👨‍🍳
"""

@app.route('/images/<filename>', methods=['GET']) # displays a single image when mentioned the path
def get_image(filename):
    return send_from_directory(IMAGE_DIRECTORY, filename)

# “Whenever someone visits this route (URL), and uses this method (GET/POST), here’s the function you should run.”
@app.route('/crop-image', methods=['POST']) # recieves the the coordinates and crops nad send a url 
def crop_image_endpoint():
    data = request.json
    image_url = data['imageUrl']
    x = int(data['x'])
    y = int(data['y'])

    image_path = os.path.join(IMAGE_DIRECTORY, image_url)
    cropped_image_filename = crop_image(image_path, x, y)
    cropped_image_url = f'http://127.0.0.1:9080/cropped-images/{cropped_image_filename}'

    return jsonify({'croppedImageUrl': cropped_image_url})


@app.route('/cropped-images/<filename>', methods=['GET']) # displays the crop when entered its path
def get_cropped_image(filename):
    return send_from_directory(CROPPED_IMAGE_DIRECTORY, filename)


@app.route('/save-details', methods=['POST']) #recieves the cropped image lat lon id coordinates shapecolor and stores the details
def save_details():
    global xco, yco, id, lats, longs
    try:
        data = request.json
        image_url = data.get('selectedImageUrl')
        image_name = data.get('selectedImageUrl', '').split('/')[-1]
        cropped_name = data.get('croppedImageUrl', '').split('/')[-1]
        shape = data.get('shape', '')
        colour = data.get('colour', '')
        id = data.get('id', '')
        logging.getLogger().status(id)
        label = data.get('label', '')

        logging.getLogger().status(f"Received data: {image_name}, {shape}, {colour}, {id}, {label}")
        logging.getLogger().status("Saving Details...")
        # print(xco, yco, flush=True)
        lats, longs = lat_long_calculation(csv_path, image_url, image_name, xco, yco, id)
        latz, longz = lats[id-1], longs[id-1]
        # Write to file
        with open(DATA_FILE, 'a') as f:
            f.write(f'{image_name}: Lat={latz}, Long={longz}, id={id}, Label={label}\n')
            f.flush()
        logging.getLogger().status("Saved Succesfully.")
        return jsonify({'message': 'Details saved successfully', 'latitude': latz, 'longitude': longz}), 200
    except Exception as e:
        # print(f"Error saving details: {str(e)}", file=sys.stderr)
        logging.getLogger().status(f"Error saving detailsP: {str(e)}")
        return jsonify({'message': f'Failed to save details: {str(e)}'}), 500

"""
# Endpoint for connecting to the drone
@app.route('/toggle-connection', methods=['POST'])
def connectDrone():
    global connection, is_connected
    connection, is_connected = toggle_connection()  # Capture the connection

    if is_connected: 
        logging.getLogger().status("Connection Successfull...") # Check if connection is valid
        return jsonify({'message': 'Connected to the drone',
                        'system': connection.target_system,
                        'component': connection.target_component}), 200
    else:
        logging.getLogger().status(f"Failed to connect to the drone")  # Print the error message
        return jsonify({'message': 'Failed to connect to the drone'}), 500
"""
@app.route('/toggle-connection', methods=['POST'])
def connectDrone():
    global connection, is_connected
    connection, is_connected = toggle_connection()

    if is_connected:
        logging.getLogger().status("Connection Successfull...")
        print(f"Returning 200 with system={connection.target_system}, component={connection.target_component}")
        return jsonify({
            'message': 'Connected to the drone',
            'system': connection.target_system,
            'component': connection.target_component
        }), 200
    else:
        print("Returning 500 - could not connect.")
        return jsonify({'message': 'Failed to connect to the drone'}), 500
        
@app.route('/drone-status', methods=['GET'])
def get_drone_status():
    from modules.mavlink_commands import is_connected
    return jsonify({'is_connected': is_connected})


@app.route('/arm-disarm', methods=['POST'])  # Get the action ('arm' or 'disarm')
def armdisarm():
    data = request.get_json()
    action = data.get('action') 

    try:
        if action == 'arm':
            msgs = arm()  # Call the arm function
        elif action == 'disarm':
            msgs = disarm()  # Call the disarm function
        else:
            raise ValueError('Invalid action')

        return jsonify({'status': 'success', 'message': msgs}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/change-mode', methods=['POST']) # helps in chnaging the mode 
def change_mode():
    try:
        mode = request.json.get('mode')

        if mode == 'auto':
            msgs = auto()  # Call auto mode function
        elif mode == 'guided':
            msgs = guided()  # Call guided mode function
        elif mode == 'loiter':
            msgs = loiter()  # Call loiter mode function
        elif mode == 'stabilize':
            msgs = stabilize()
        else:
            return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400

        return jsonify({'status': 'success', 'message': msgs}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/takeoff', methods=['POST'])
def takeoffdrone():
    response = takeoffcommand()
    return response

@app.route('/RTL', methods=['POST'])
def rtl():
    response = rtlcommand()
    return response

@app.route('/drop', methods=['POST'])
def dropPkg(): 
    # Call the drop functions
    for i in range(4):
        drop(i+1)
        time.sleep(3)
    return "Drop command executed", 200  # Respond with a success message

@app.route('/lock-servo', methods=['POST'])
def lockservo():
    # Call the drop function
    lock(7)
    time.sleep(3)
    lock(8)
    return "Drop command executed", 200  # Respond with a success message


@app.route('/rtl', methods=['GET'])
def rtl_command():
    try:
        # Call the rtl function
        result = rtl()
        return jsonify({"status": "success", "message": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/start_geotagg', methods=['POST'])
def start_geotagg():
    target_waypoint2 = 15
    geotag_waypoint = 3
    global process

    
    logging.getLogger().status(f"Waiting for drone to reach waypoint {geotag_waypoint}")

    while True:
            # Wait for a message
            msg = connection.recv_match(type='MISSION_ITEM_REACHED', blocking=True)
            # mission item reached is the msg sent by the drone via mavlink
            logging.getLogger().status(f"Waypoint {msg.seq} reached.")
                # logging.getLogger().status(f"Waypoint reached.")
                # logging.getLogger().status(f"Waypoint : {msg.seq}")
            # msg.seq is the id if the way point it reached
            if msg.seq == geotag_waypoint:
                process = run_python_file(geo_path)  # This will run even if run_sync_script fails
                global msgs
                msgs = "started geotagg"
                logging.getLogger().status("Started geotagg")  # Log this information
                time.sleep(10)
                logging.getLogger().status("Running sync script...")
                run_sync_script()
                # Check if it's the target waypoint
            elif msg.seq == target_waypoint2:
                    guided()
                    stop_python_file()
                    time.sleep(100)
                    stop_sync_script()
                    # guided()
                    break

@app.route('/start_geotaggG', methods=['POST'])#Starts geotagging immediately (manual/shortcut version).
def start_geotaggG():
    global process
    process = run_python_file(geo_path)  # This will run even if run_sync_script fails
    global msgs
    msgs = "started geotagg"
    logging.getLogger().status("Started geotagg")  # Log this information
    time.sleep(10)
    logging.getLogger().status("Running sync script...")
    run_sync_script()
    return "", 204

@app.route('/stop_geotagg', methods=['POST'])
def stop_geotagg():
    stop_python_file()
    global msgs
    msgs="stopped geotagg"
    logging.info("stopped geotagg")
    return "", 204

"""
Takes in a target ID,
➡️ Looks up its latitude and longitude,
➡️ Sends the drone there using that info.
"""
@app.route('/reposition', methods=['POST'])
def repos():
    data = request.get_json()  # Extract the JSON payload which was made via the frontend
    if not data or 'id' not in data:
        return jsonify({"error": "Missing 'id' in request body"}), 400

    tno = data['id']  # Rename 'id' to 'tno'
    print(tno, flush=True)

    global connection
    # logging.getLogger().status("Moving towards target...", flush=True)
    global msg
    target_no = 0
    msg = "Target number bottle is dropping on: %s" % str(target_no)

    try:
        lati = lats[tno - 1]
        longi = longs[tno - 1]
        automation(lati, longi, tno, connection)
    except IndexError:
        return jsonify({"error": f"Invalid 'tno': {tno}"}), 400

    return "", 204

@app.route('/auto-repo', methods=['POST'])
def autorepos():

    initial_waypoint = True
    target_waypoint = 5
    global connection
    # logging.getLogger().status("Moving towards target...", flush=True)
    global msg
    target_no = 0
    msg = "Target number bottle is dropping on: %s" % str(target_no) # Replace with your desired waypoint sequence number
    for target in range(1,5):
        lati = lats[target - 1]
        longi = longs[target - 1]
        automation(lati, longi, target, connection)

        while True:
            # Wait for a message
            msg = connection.recv_match(type='MISSION_ITEM_REACHED', blocking=True)
            if msg:
                logging.getLogger().status(f"Waypoint reached.")
                # logging.getLogger().status(f"Waypoint : {msg.seq}")
                
                # Check if it's the target waypoint
                if msg.seq == target_waypoint:
                    break

                

######################################################################################################################################
                                                        #AI#
######################################################################################################################################

# AI Integration Code - Add this to Manual.py
# Place this code after the existing imports and before the existing routes

import csv

# AI-specific configurations
AI_BASE = "/home/dishita/Desktop/SHITTT!!!/AI"
AI_CSV_PATH = os.path.join(AI_BASE, "results.csv")
AI_IMAGE_DIR = os.path.join(AI_BASE, "crops_dir")

# AI Global variables
ai_csv_data = {}

def load_ai_csv():
    """Load AI CSV data into memory"""
    global ai_csv_data
    try:
        with open(AI_CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                crop_name = row['crop_name']
                ai_csv_data[crop_name] = {
                    "crop_name": crop_name,
                    "lat": row.get("lat", ""),
                    "lon": row.get("lon", ""),
                    "class": row.get("class", ""),
                    "pxl_center": row.get("pxl_center_x_y", ""),
                    "crop_path": row.get("crop_path", "")
                }
        logging.getLogger().status("AI CSV data loaded successfully")
    except Exception as e:
        logging.getLogger().status(f"Error loading AI CSV: {str(e)}")

# AI Routes - No conflicts with existing routes

@app.route('/ai-images', methods=['GET'])
def ai_all_images():
    """Get all AI processed images"""
    try:
        images = [f for f in os.listdir(AI_IMAGE_DIR) if os.path.isfile(os.path.join(AI_IMAGE_DIR, f))]
        return jsonify({'imageUrls': images})
    except Exception as e:
        logging.getLogger().status(f"Error getting AI images: {str(e)}")
        return jsonify({'imageUrls': []}), 500

@app.route('/ai-images/<filename>', methods=['GET'])
def get_ai_image(filename):
    """Serve AI processed images"""
    try:
        return send_from_directory(AI_IMAGE_DIR, filename)
    except Exception as e:
        logging.getLogger().status(f"Error serving AI image {filename}: {str(e)}")
        return jsonify({'error': 'Image not found'}), 404

@app.route('/get-image-info/<image_name>', methods=['GET'])
def get_fresh_image_info(image_name):
    """Get fresh image info from CSV"""
    try:
        with open(AI_CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['crop_name'] == image_name:
                    return jsonify(row)
        return jsonify({})
    except Exception as e:
        logging.getLogger().status(f"Error getting fresh image info: {str(e)}")
        return jsonify({}), 500

@app.route('/get-info/<image_name>', methods=['GET'])
def get_ai_info(image_name):
    """Get AI info from cached data"""
    try:
        info = ai_csv_data.get(image_name, {})
        return jsonify(info)
    except Exception as e:
        logging.getLogger().status(f"Error getting AI info: {str(e)}")
        return jsonify({}), 500

@app.route('/ai-map', methods=['GET'])
def ai_map():
    """Serve the AI map HTML file"""
    try:
        return send_from_directory(AI_BASE, "combined_output_with_class.html")
    except Exception as e:
        logging.getLogger().status(f"Error serving AI map: {str(e)}")
        return jsonify({'error': 'Map not found'}), 404

@app.route('/run-ai-script', methods=['POST'])
def run_ai_script():
    """Run the AI processing script"""
    try:
        import subprocess
        result = subprocess.run(["/home/edhitha/gdino/autogeo/ai_run.sh"], capture_output=True, text=True)
        output = result.stdout or result.stderr
        logging.getLogger().status(f"AI script executed: {output}")
        
        # Reload CSV data after running the script
        load_ai_csv()
        
        return jsonify({'status': 'success', 'output': output}), 200
    except Exception as e:
        logging.getLogger().status(f"Error running AI script: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/reload-ai-data', methods=['POST'])
def reload_ai_data():
    """Reload AI CSV data"""
    try:
        load_ai_csv()
        return jsonify({'status': 'success', 'message': 'AI data reloaded'}), 200
    except Exception as e:
        logging.getLogger().status(f"Error reloading AI data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500




#if __name__ == '__main__':
#    socketio.start_background_task(target=start_watching)
#    socketio.run(app, debug=False, port=9080, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    setup_logging(socketio) 
    load_ai_csv()  # Add this line
    socketio.start_background_task(target=start_watching)
    socketio.run(app, debug=False, port=9080, allow_unsafe_werkzeug=True)