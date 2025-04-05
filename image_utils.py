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

# Global camera object that persists throughout the application
_camera = None
_camera_lock = threading.Lock()

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

def get_camera():
    """Get the global camera object, initializing it if necessary"""
    global _camera
    
    with _camera_lock:
        if _camera is None or not _camera.isOpened():
            init_camera()
        return _camera

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
    # Get camera (initializes if needed)
    camera = get_camera()
    
    if camera is None or not camera.isOpened():
        status_var.set("Error: Could not open camera.")
        return False
    
    # Set preview active flag
    preview_active[0] = True
    
    # Start preview thread
    preview_thread = threading.Thread(
        target=update_camera_preview,
        args=(image_label, camera, preview_active, status_var),
        daemon=True
    )
    preview_thread.start()
    
    status_var.set("Camera active. Click 'Capture' to take a photo.")
    return True

def update_camera_preview(image_label, camera, preview_active, status_var):
    """
    Camera preview thread function - runs in a separate thread
    
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
    try:
        camera = get_camera()
        if camera is None or not camera.isOpened():
            return None
        
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Read a few frames to make sure we get a recent image
        for _ in range(3):
            ret, frame = camera.read()
            if not ret:
                return None
        
        # Generate a filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"camera_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        # Save the image
        cv2.imwrite(filepath, frame)
        
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
    try:
        camera = get_camera()
        if camera is None or not camera.isOpened():
            return None, None
        
        # Read the current frame
        ret, frame = camera.read()
        if not ret:
            return None, None
        
        # Convert to RGB for display
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame, img_rgb
        
    except Exception as e:
        print(f"Error getting frame: {e}")
        return None, None

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