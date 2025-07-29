import os
import asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from pathlib import Path
import json
import csv
import logging
import folium

UPLOAD_FOLDER = "/home/aseel/data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
AI_IMAGE_DIR = "/home/aseel/data/crops"
AI_CSV_PATH = "/home/aseel/data/inference.csv"
app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set your React frontend URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = []

# ROS2 Node Setup
rclpy.init()
ros_node = rclpy.create_node('server_node')
publisher = ros_node.create_publisher(String, '/planning/generate_pattern', 10)
mission_publisher = ros_node.create_publisher(String, '/mission_commands', 10)

# This will queue up incoming ROS messages to send to React
ros_message_queue = asyncio.Queue()
ai_csv_data = {}

# Function to load AI CSV data
def load_ai_csv():
    """
    Loads AI data from the specified CSV file into the global cache,
    using the new column names provided by the user.
    """
    global ai_csv_data
    ai_csv_data = {} # Clear existing data
    if not os.path.exists(AI_CSV_PATH):
        print(f"AI CSV file not found at {AI_CSV_PATH}. Skipping data load.")
        return

    try:
        with open(AI_CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Use 'Crop Name' as the key for the dictionary
                if 'Crop Name' in row:
                    crop_name = row['Crop Name']
                    ai_csv_data[crop_name] = {
                        "Name": crop_name,
                        "Center": row.get("Pixel Center X Y", ""),
                        "Latitude": row.get("Latitude", ""),
                        "Longitude": row.get("Longitude", ""),
                        "Confidence": row.get("Confidence", ""),
                        "Timestamp": row.get("Timestamp", ""),
                    }
        print(f"AI CSV data loaded successfully. Cached {len(ai_csv_data)} entries.")
    except Exception as e:
        print(f"Error loading AI CSV: {str(e)}")

# Load data on startup
load_ai_csv()

@app.post("/upload-kml")
async def upload_kml(kmlFiles: list[UploadFile] = File(...)):
    uploaded_file_names = []

    for file in kmlFiles:
        # Save the file with its original filename
        file_location = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())
        uploaded_file_names.append(file.filename) # Append the actual filename

    return JSONResponse({
        "message": "Files uploaded successfully.",
        "uploadedFileNames": uploaded_file_names # Return the list of actual filenames
    })


@app.post("/generate_waypoint")
async def generate_waypoint(payload: dict):
    # Get the filename from the payload sent by the frontend
    filename_from_frontend = payload.get("filename")
    custom_params = payload.get("params", {})

    if not filename_from_frontend:
        return JSONResponse(status_code=400, content={"error": "Filename not provided"})

    # Construct the full path using the filename received from the frontend
    kml_path = os.path.join(UPLOAD_FOLDER, filename_from_frontend)

    # Check if the file actually exists on the server
    if not os.path.exists(kml_path):
        return JSONResponse(status_code=404, content={"error": f"KML file '{filename_from_frontend}' not found on server."})

    default_params = {
        "kml_file": kml_path, # Use the full path to the specific KML file
        "line_spacing": 20,
        "flight_altitude": 30,
        "flight_velocity": 4.0,
        "fence_buffer": 5,
        "optimize_angle": True,
        "angle": 90
    }

    default_params.update(custom_params)

    msg = String()
    msg.data = json.dumps(default_params)
    publisher.publish(msg)

    return {"status": "published", "message": "Parameters merged and sent."}
    
    
@app.post("/send_mission_command")
async def send_mission_command(payload: dict):
    """
    NEW ENDPOINT: Sends a mission command (e.g., "mission_start") to the ROS2 system.
    This command is intended to be picked up by the MissionCommander node.
    """
    command = payload.get("command")

    if not command:
        return JSONResponse(status_code=400, content={"error": "Command not provided in payload."})

    # Create a ROS2 String message with the command
    msg = String()
    msg.data = command
    
    try:
        # Publish the command to the /mission_commands topic
        mission_publisher.publish(msg)
        print(f"Published mission command: '{command}' to /mission_commands topic.")
        return JSONResponse({"status": "success", "message": f"Command '{command}' sent to ROS2."})
    except Exception as e:
        print(f"Error publishing mission command: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to send command '{command}' to ROS2."})


@app.get('/ai-images')
async def ai_all_images():
    """
    Get all AI processed images.
    Returns a list of image filenames available in the AI_IMAGE_DIR.
    """
    try:
        # List all files in the AI_IMAGE_DIR that are actual files
        images = [f for f in os.listdir(AI_IMAGE_DIR) if os.path.isfile(os.path.join(AI_IMAGE_DIR, f))]
        print(f"Found AI images: {images}")
        return JSONResponse({'imageUrls': images})
    except Exception as e:
        print(f"Error getting AI images: {str(e)}") # Using print for consistency with existing code
        return JSONResponse({'imageUrls': []}, status_code=500)

@app.get('/ai-images/{filename}')
async def get_ai_image(filename: str):
    """
    Serve a specific AI processed image.
    Returns the image file from AI_IMAGE_DIR.
    """
    file_path = os.path.join(AI_IMAGE_DIR, filename)
    try:
        # Check if the file exists and is indeed a file
        if os.path.isfile(file_path):
            print(f"Serving AI image: {file_path}")
            return FileResponse(file_path)
        else:
            print(f"AI image not found: {file_path}")
            return JSONResponse({'error': 'Image not found'}, status_code=404)
    except Exception as e:
        print(f"Error serving AI image {filename}: {str(e)}") # Using print for consistency
        return JSONResponse({'error': 'Internal server error'}, status_code=500)


@app.post('/reload-ai-data')
async def reload_ai_data():
    """Reload AI CSV data"""
    try:
        load_ai_csv()
        return JSONResponse({'status': 'success', 'message': 'AI data reloaded'}, status_code=200)
    except Exception as e:
        print(f"Error reloading AI data: {str(e)}")
        return JSONResponse({'status': 'error', 'message': str(e)}, status_code=500)
@app.get('/get-image-info/{image_name}')
async def get_fresh_image_info(image_name: str):
    """
    Get fresh image info from CSV, returning only specified fields.
    """
    try:
        if not os.path.exists(AI_CSV_PATH):
            print(f"AI CSV file not found at {AI_CSV_PATH} for image info.")
            return JSONResponse({}, status_code=404)

        with open(AI_CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Crop Name') == image_name:
                    # Construct a new dictionary with only the desired fields
                    filtered_info = {
                        "Name": row.get("Crop Name", ""),
                        "Center": row.get("Pixel Center X Y", ""),
                        "Latitude": row.get("Latitude", ""),
                        "Longitude": row.get("Longitude", ""),
                        "Confidence": row.get("Confidence", ""),
                        "Timestamp": row.get("Timestamp", ""),
                        "Yaw": row.get("Yaw", "") # Include Yaw if it's still desired
                    }
                    return JSONResponse(filtered_info)
        print(f"Image info not found for {image_name} in CSV.")
        return JSONResponse({}) # Return empty JSON if not found
    except Exception as e:
        print(f"Error getting fresh image info for {image_name}: {str(e)}")
        return JSONResponse({}, status_code=500)

@app.get('/get-info/{image_name}')
async def get_ai_info(image_name: str):
    """Get AI info from cached data"""
    try:
        info = ai_csv_data.get(image_name, {})
        if not info:
            print(f"AI info not found in cache for {image_name}.")
        return JSONResponse(info)
    except Exception as e:
        print(f"Error getting AI info from cache for {image_name}: {str(e)}")
        return JSONResponse({}, status_code=500)


@app.get('/get-all-ai-info')
async def get_all_ai_info():
    """
    Returns all cached AI data from the CSV.
    """
    try:
        return JSONResponse(list(ai_csv_data.values()))
    except Exception as e:
        print(f"Error getting all AI info: {str(e)}")
        return JSONResponse([], status_code=500)


@app.get('/ai-map') # Modified endpoint to generate map dynamically
async def ai_map():
    """
    Dynamically generates and serves an HTML map with AI detection markers using Folium.
    """
    try:
        # Default map center if no data is available
        map_center = [0, 0]
        initial_zoom = 2
        
        # Get all AI data from cache
        all_detections = list(ai_csv_data.values())
        
        # If there's data, try to set the map center to the first detection
        if all_detections:
            first_detection = all_detections[0]
            lat = float(first_detection.get("Latitude", 0))
            lon = float(first_detection.get("Longitude", 0))
            if -90 <= lat <= 90 and -180 <= lon <= 180: # Validate coordinates
                map_center = [lat, lon]
                initial_zoom = 10 # Zoom in if we have a specific location

        # Create a Folium map object
        m = folium.Map(location=map_center, zoom_start=initial_zoom, tiles="OpenStreetMap")

        # Add markers for each detection
        for detection in all_detections:
            lat = float(detection.get("Latitude", 0))
            lon = float(detection.get("Longitude", 0))
            
            if -90 <= lat <= 90 and -180 <= lon <= 180: # Validate coordinates
                # Create popup content
                popup_html = f"""
                <strong>Name:</strong> {detection.get("Name", "N/A")}<br>
                <strong>Class:</strong> {detection.get("Class", "N/A")}<br>
                <strong>Confidence:</strong> {detection.get("Confidence", "N/A")}<br>
                <strong>Timestamp:</strong> {detection.get("Timestamp", "N/A")}<br>
                <strong>Lat:</strong> {lat:.4f}, <strong>Lon:</strong> {lon:.4f}<br>
                <strong>Center:</strong> {detection.get("Center", "N/A")}<br>
                <strong>Yaw:</strong> {detection.get("Yaw", "N/A")}
                """
                
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=detection.get("Name", "Detection")
                ).add_to(m)

        # Convert the Folium map to an HTML string
        map_html = m._repr_html_()
        
        # Return the HTML response
        return HTMLResponse(content=map_html, status_code=200)

    except Exception as e:
        print(f"Error generating AI map: {str(e)}")
        return JSONResponse({'error': f'Failed to generate map: {str(e)}'}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print("Client connected.")

    try:
        while True:
            # Wait for ROS2 message to forward
            message = await ros_message_queue.get()
            await websocket.send_text(f"📨 ROS2: {message}")
    except WebSocketDisconnect:
        print("Client disconnected.")
        clients.remove(websocket)


# ROS2 subscription callback
def ros_callback(msg):
    asyncio.run_coroutine_threadsafe(ros_message_queue.put(msg.data), asyncio.get_event_loop())

# Create subscription in separate thread
def ros_spin():
    subscription = ros_node.create_subscription(
        String,
        'ros_to_react_topic',
        ros_callback,
        10
    )
    rclpy.spin(ros_node)

import threading
threading.Thread(target=ros_spin, daemon=True).start()

