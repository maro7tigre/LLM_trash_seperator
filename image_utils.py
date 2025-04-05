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
def capture_image_from_camera(save_dir="."):
    """
    Capture an image using the camera
    
    Args:
        save_dir: Directory to save the captured image
        
    Returns:
        Image info dictionary or None if failed
    """
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Initialize camera (0 is usually the default camera)
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return None
        
        # Set camera properties (optional)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Countdown timer
        countdown = 3
        while countdown > 0:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                cap.release()
                return None
            
            # Display countdown
            cv2.putText(
                frame, 
                f"Capturing in {countdown}...", 
                (50, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 0, 255), 
                2
            )
            
            cv2.imshow("Camera Capture", frame)
            
            # Wait for 1 second
            start_time = time.time()
            while time.time() - start_time < 1:
                if cv2.waitKey(1) & 0xFF == 27:  # ESC key to cancel
                    cap.release()
                    cv2.destroyAllWindows()
                    return None
            
            countdown -= 1
        
        # Capture the image
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            cap.release()
            cv2.destroyAllWindows()
            return None
        
        # Display "CAPTURED" message
        cv2.putText(
            frame, 
            "CAPTURED!", 
            (50, 70), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1, 
            (0, 255, 0), 
            2
        )
        
        cv2.imshow("Camera Capture", frame)
        cv2.waitKey(1000)  # Display for 1 second
        
        # Release camera and close window
        cap.release()
        cv2.destroyAllWindows()
        
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
        if 'cap' in locals() and cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        return None

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