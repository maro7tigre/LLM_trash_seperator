"""
Image processing utilities for Trash Analyzer
"""

import os
import cv2
import glob
import random
import shutil
from PIL import Image
import time
import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL import ImageTk
import threading
import urllib.request
import base64
from io import BytesIO

# Global camera object that persists throughout the application
_camera = None
_camera_lock = threading.Lock()
_camera_type = "webcam"  # Default camera type
_camera_ip = ""  # For ESP32 camera

# MARK: - Image Loading Functions
def load_image_from_path(path):
    """Load an image from a path and return BGR and RGB versions"""
    try:
        # Read image in BGR format (OpenCV default)
        img_data = cv2.imread(path)
        if img_data is None:
            return None
        
        # Convert BGR to RGB for display
        img_rgb = cv2.cvtColor(img_data, cv2.COLOR_BGR2RGB)
        
        # Get file name
        name = os.path.basename(path)
        
        # Return information dictionary
        return {
            'path': path,
            'name': name,
            'data': img_data,     # Original BGR format for OpenCV
            'display': img_rgb    # RGB format for display
        }
    except Exception as e:
        print(f"Error loading image {path}: {e}")
        return None

def load_image_from_base64(base64_str, filename="base64_image.jpg"):
    """Load an image from a base64 string and return BGR and RGB versions"""
    try:
        # Decode base64 to binary data
        if isinstance(base64_str, str):
            # Sometimes base64 strings can have header info, remove it if present
            if "base64," in base64_str:
                base64_str = base64_str.split("base64,")[1]
            img_data = base64.b64decode(base64_str)
        else:
            img_data = base64_str
            
        # Convert to numpy array
        nparr = np.frombuffer(img_data, np.uint8)
        
        # Decode the image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            print("Failed to decode base64 image")
            return None
        
        # Convert BGR to RGB for display
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Return information dictionary
        return {
            'path': None,  # No file path as it's from base64
            'name': filename,
            'data': img,       # Original BGR format for OpenCV
            'display': img_rgb # RGB format for display
        }
    except Exception as e:
        print(f"Error loading image from base64: {e}")
        return None

# MARK: - Camera Functions
def init_camera():
    """Initialize the camera once at application startup"""
    global _camera
    
    with _camera_lock:
        if _camera is None:
            try:
                # Try to initialize the camera with lower resolution first for faster startup
                _camera = cv2.VideoCapture(0)
                
                if _camera is not None and _camera.isOpened():
                    # Set to a reasonable default resolution - can be changed later if needed
                    _camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    _camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    
                    # Read a few frames to stabilize the camera
                    for _ in range(5):
                        _camera.read()
                    
                    print("Camera initialized successfully")
                else:
                    print("Failed to initialize camera")
                    _camera = None
            except Exception as e:
                print(f"Error initializing camera: {e}")
                _camera = None

def set_camera_source(camera_type, camera_id=0, ip_address=""):
    """
    Set the camera source
    
    Args:
        camera_type: Type of camera ("webcam" or "esp32")
        camera_id: Camera ID for webcam (default: 0)
        ip_address: IP address for ESP32 camera
        
    Returns:
        Boolean indicating success
    """
    global _camera, _camera_type, _camera_ip
    
    with _camera_lock:
        # Release existing camera if webcam type
        if _camera is not None and _camera_type == "webcam":
            _camera.release()
            _camera = None
        
        # Store camera settings
        _camera_type = camera_type
        
        if camera_type == "webcam":
            try:
                _camera = cv2.VideoCapture(int(camera_id))
                
                if _camera is not None and _camera.isOpened():
                    # Set to a reasonable default resolution
                    _camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    _camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    
                    # Read a few frames to stabilize the camera
                    for _ in range(5):
                        _camera.read()
                    
                    print(f"Webcam {camera_id} initialized successfully")
                    return True
                else:
                    print(f"Failed to initialize webcam {camera_id}")
                    return False
            except Exception as e:
                print(f"Error initializing webcam: {e}")
                return False
        
        elif camera_type == "esp32":
            # For ESP32, we store the IP address but don't create a VideoCapture object
            if not ip_address:
                print("IP address is required for ESP32 camera")
                return False
            
            # Validate the IP address format (basic check)
            if not ip_address.startswith("http"):
                # Add http:// prefix if missing
                ip_address = f"http://{ip_address}"
            
            # Store the IP address for later use
            _camera_ip = ip_address
            return True
        
        else:
            print(f"Unknown camera type: {camera_type}")
            return False
            
def test_esp32_connection(ip_address):
    """
    Test connection to an ESP32 camera
    
    Args:
        ip_address: IP address of the ESP32 camera
        
    Returns:
        Boolean indicating success
    """
    try:
        # Validate the IP address format (basic check)
        if not ip_address.startswith("http"):
            # Add http:// prefix if missing
            ip_address = f"http://{ip_address}"
            
        # Try to access the root page first
        response = urllib.request.urlopen(f"{ip_address}/")
        if response.getcode() != 200:
            print(f"Failed to connect to ESP32 at {ip_address}")
            return False
            
        # If URL ends with slash, append the image path
        if ip_address.endswith("/"):
            test_url = f"{ip_address}cam-lo.jpg"
        else:
            test_url = f"{ip_address}/cam-lo.jpg"
        
        # Try to open the URL
        img_resp = urllib.request.urlopen(test_url)
        imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        im = cv2.imdecode(imgnp, -1)
        
        if im is not None:
            print(f"ESP32 camera at {ip_address} connected successfully")
            return True
        else:
            print(f"Connected to {ip_address} but couldn't decode image")
            return False
    except Exception as e:
        print(f"Error connecting to ESP32 camera at {ip_address}: {e}")
        return False

def get_camera():
    """Get the global camera object, initializing it if necessary"""
    global _camera
    
    with _camera_lock:
        if _camera_type == "webcam":
            if _camera is None or not _camera.isOpened():
                init_camera()
            return _camera
        else:
            # For ESP32, we don't return a camera object
            return None

def release_camera():
    """Release the camera resources"""
    global _camera
    
    with _camera_lock:
        if _camera is not None:
            _camera.release()
            _camera = None
            print("Camera released")

def start_camera_preview(image_label, status_var, preview_active):
    """
    Start camera preview thread
    
    Args:
        image_label: Tkinter label widget to display camera preview
        status_var: Tkinter StringVar for status updates
        preview_active: List with boolean flag to control preview loop
        
    Returns:
        Boolean indicating success
    """
    global _camera_type, _camera_ip
    
    # Set preview active flag
    preview_active[0] = True
    
    if _camera_type == "webcam":
        # Get camera (initializes if needed)
        camera = get_camera()
        
        if camera is None or not camera.isOpened():
            status_var.set("Error: Could not open webcam.")
            return False
        
        # Start preview thread for webcam
        preview_thread = threading.Thread(
            target=update_camera_preview,
            args=(image_label, camera, preview_active, status_var),
            daemon=True
        )
        preview_thread.start()
    
    elif _camera_type == "esp32":
        if not _camera_ip:
            status_var.set("Error: ESP32 camera IP not set.")
            return False
        
        # Start preview thread for ESP32 camera
        preview_thread = threading.Thread(
            target=update_esp32_preview,
            args=(image_label, _camera_ip, preview_active, status_var),
            daemon=True
        )
        preview_thread.start()
    
    else:
        status_var.set(f"Error: Unknown camera type '{_camera_type}'.")
        return False
    
    status_var.set(f"Camera active ({_camera_type}). Click 'Capture' to take a photo.")
    return True

def update_camera_preview(image_label, camera, preview_active, status_var):
    """
    Camera preview thread function for webcam - runs in a separate thread
    
    Args:
        image_label: Tkinter label widget
        camera: OpenCV VideoCapture object
        preview_active: List with boolean flag to control preview loop
        status_var: Tkinter StringVar for status updates
    """
    last_update = time.time()
    frame_delay = 1.0 / 30  # Target 30 FPS
    
    while preview_active[0]:
        try:
            # Throttle updates to target frame rate
            current_time = time.time()
            if current_time - last_update < frame_delay:
                time.sleep(0.001)  # Short sleep to reduce CPU usage
                continue
                
            last_update = current_time
            
            # Read frame from camera
            ret, frame = camera.read()
            if not ret:
                # Camera disconnected or error
                image_label.after(0, lambda: status_var.set("Camera error: Failed to read frame"))
                break
            
            # Convert to RGB for tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame for display (keeping aspect ratio)
            height, width = frame_rgb.shape[:2]
            max_height = 400
            max_width = 500
            
            if height > max_height or width > max_width:
                scale = min(max_height / height, max_width / width)
                new_height, new_width = int(height * scale), int(width * scale)
                frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
            
            # Convert to PhotoImage and update label in main thread
            img_pil = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)
            
            # Update UI in the main thread
            image_label.after(0, lambda img=img_tk: update_label(image_label, img))
        
        except Exception as e:
            # Handle errors gracefully
            image_label.after(0, lambda: status_var.set(f"Camera error: {str(e)}"))
            break

def update_esp32_preview(image_label, ip_address, preview_active, status_var):
    """
    Camera preview thread function for ESP32 camera - runs in a separate thread
    
    Args:
        image_label: Tkinter label widget
        ip_address: ESP32 camera IP address
        preview_active: List with boolean flag to control preview loop
        status_var: Tkinter StringVar for status updates
    """
    last_update = time.time()
    frame_delay = 1.0 / 10  # Target 10 FPS (ESP32 cameras are usually slower)
    
    # Format the URL correctly
    if ip_address.endswith("/"):
        url = f"{ip_address}cam-lo.jpg"
    else:
        url = f"{ip_address}/cam-lo.jpg"
        
    while preview_active[0]:
        try:
            # Throttle updates to target frame rate
            current_time = time.time()
            if current_time - last_update < frame_delay:
                time.sleep(0.01)  # Short sleep to reduce CPU usage
                continue
                
            last_update = current_time
            
            # Read frame from ESP32 camera
            img_resp = urllib.request.urlopen(url)
            imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
            frame = cv2.imdecode(imgnp, -1)
            
            if frame is None:
                # Camera disconnected or error
                image_label.after(0, lambda: status_var.set("ESP32 camera error: Failed to decode frame"))
                time.sleep(1)  # Wait longer on error
                continue
            
            # Convert to RGB for tkinter if needed
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                # Already RGB or grayscale
                frame_rgb = frame
            
            # Resize frame for display (keeping aspect ratio)
            height, width = frame_rgb.shape[:2]
            max_height = 400
            max_width = 500
            
            if height > max_height or width > max_width:
                scale = min(max_height / height, max_width / width)
                new_height, new_width = int(height * scale), int(width * scale)
                frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
            
            # Convert to PhotoImage and update label in main thread
            img_pil = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)
            
            # Update UI in the main thread
            image_label.after(0, lambda img=img_tk: update_label(image_label, img))
        
        except Exception as e:
            # Handle errors gracefully
            image_label.after(0, lambda: status_var.set(f"ESP32 camera error: {str(e)}"))
            time.sleep(1)  # Wait longer on error

def update_label(label, image):
    """Update label with new image (called in main thread)"""
    label.config(image=image)
    label.image = image  # Keep a reference to prevent garbage collection

def capture_image_embedded(save_dir="."):
    """
    Capture an image from the active camera
    
    Args:
        save_dir: Directory to save the captured image
        
    Returns:
        Image info dictionary or None if failed
    """
    global _camera_type, _camera_ip
    
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate a filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"camera_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        # Capture based on camera type
        if _camera_type == "webcam":
            camera = get_camera()
            if camera is None or not camera.isOpened():
                return None
            
            # Read a few frames to make sure we get a recent image
            for _ in range(3):
                ret, frame = camera.read()
                if not ret:
                    return None
            
            # Save the image
            cv2.imwrite(filepath, frame)
            
        elif _camera_type == "esp32":
            if not _camera_ip:
                return None
                
            # Format the URL
            if _camera_ip.endswith("/"):
                url = f"{_camera_ip}cam-lo.jpg"
            else:
                url = f"{_camera_ip}/cam-lo.jpg"
            
            # Capture from ESP32
            img_resp = urllib.request.urlopen(url)
            imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
            frame = cv2.imdecode(imgnp, -1)
            
            if frame is None:
                return None
                
            # Save the image
            cv2.imwrite(filepath, frame)
        
        else:
            return None
        
        # Create image info dictionary
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return {
            'path': filepath,
            'name': filename,
            'data': frame,       # Original BGR format for OpenCV
            'display': img_rgb   # RGB format for display
        }
        
    except Exception as e:
        print(f"Error capturing image: {e}")
        return None

def get_current_frame():
    """
    Get the current frame from the camera without saving
    
    Returns:
        Tuple of (BGR image, RGB image) or (None, None) if failed
    """
    global _camera_type, _camera_ip
    
    try:
        if _camera_type == "webcam":
            camera = get_camera()
            if camera is None or not camera.isOpened():
                return None, None
            
            # Read the current frame
            ret, frame = camera.read()
            if not ret:
                return None, None
                
        elif _camera_type == "esp32":
            if not _camera_ip:
                return None, None
                
            # Format the URL
            if _camera_ip.endswith("/"):
                url = f"{_camera_ip}cam-lo.jpg"
            else:
                url = f"{_camera_ip}/cam-lo.jpg"
            
            # Capture from ESP32
            img_resp = urllib.request.urlopen(url)
            imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
            frame = cv2.imdecode(imgnp, -1)
            
            if frame is None:
                return None, None
        
        else:
            return None, None
        
        # Convert to RGB for display
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame, img_rgb
        
    except Exception as e:
        print(f"Error getting frame: {e}")
        return None, None

def save_base64_as_image(base64_str, save_path):
    """
    Save a base64 string as an image file
    
    Args:
        base64_str: Base64 encoded image string
        save_path: Path to save the image file
        
    Returns:
        Boolean indicating success
    """
    try:
        # Decode base64 to binary
        if "base64," in base64_str:
            # Remove data URL header if present
            base64_str = base64_str.split("base64,")[1]
            
        image_data = base64.b64decode(base64_str)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Write binary data to file
        with open(save_path, "wb") as f:
            f.write(image_data)
            
        return True
    except Exception as e:
        print(f"Error saving base64 as image: {e}")
        return False

# MARK: - Random Image Functions
def get_random_images(max_count=20):
    """Get random images from datasets directory"""
    # Define common image search paths
    search_paths = [
        os.path.join('.', 'complete_dataset'),
        os.path.join('.', 'complete_dataset', 'complete_dataset'),
    ]
    
    # Find all image files
    image_files = []
    for base_path in search_paths:
        if os.path.exists(base_path):
            for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
                pattern = os.path.join(base_path, '**', ext)
                image_files.extend(glob.glob(pattern, recursive=True))
    
    if not image_files:
        return []
    
    # Select random images
    if len(image_files) > max_count:
        selected_images = random.sample(image_files, max_count)
    else:
        selected_images = image_files
    
    return selected_images

# MARK: - Image Preparation for APIs
def prepare_image_for_api(img_data, provider, max_size=None):
    """
    Prepare image for different API providers with optional resizing
    
    Args:
        img_data: Image data in CV2 format (BGR)
        provider: Provider name ('gemini', 'openai')
        max_size: Maximum dimension (width or height) in pixels. If provided,
                  image will be resized to fit within this limit while
                  maintaining aspect ratio.
        
    Returns:
        Processed image in the format required by the provider
    """
    # Convert BGR to RGB (OpenCV uses BGR by default)
    import cv2
    img_rgb = cv2.cvtColor(img_data, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL image
    from PIL import Image
    pil_image = Image.fromarray(img_rgb)
    
    # Resize image if max_size is provided
    if max_size is not None and isinstance(max_size, int) and max_size > 0:
        # Get current dimensions
        width, height = pil_image.size
        
        # Check if resizing is needed
        if width > max_size or height > max_size:
            # Determine which dimension is larger
            if width >= height:
                # Width is larger or equal, scale based on width
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                # Height is larger, scale based on height
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            # Resize the image
            pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
    
    # Format by provider
    provider = provider.lower()
    
    # For Gemini API - Return PIL image directly
    if provider == 'gemini':
        return pil_image
    
    # For OpenAI API - Return base64-encoded image
    elif provider == 'openai':
        import base64
        from io import BytesIO
        
        # Compress and convert to JPEG for efficient encoding
        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG", quality=90)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Default - return PIL image
    return pil_image