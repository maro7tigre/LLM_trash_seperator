"""
Main Application Class for Trash Analyzer
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import cv2
import time
import requests
import json
import base64
from datetime import datetime

# Import helpers
import ui_helper
import model_helper
import image_utils

# MARK: - Main Application Class
class TrashAnalyzerApp:
    def __init__(self, root):
        """Initialize the main application"""
        self.root = root
        self.root.title("Trash Analyzer")
        self.root.geometry("1000x800")
        
        # Initialize variables
        self.images = []  # List of {path, name, data, display}
        self.current_image_index = -1
        
        # Camera variables
        self.camera_active = False
        self.preview_active = [False]  # Using a list to make it mutable for reference
        self.current_camera_type = "Webcam (0)"
        self.esp32_connected = False
        self.connection_thread = None
        
        # ESP32 Subscription variables
        self.esp32_subscription_active = False
        self.esp32_subscription_ip = ""
        self.esp32_polling_thread = None
        self.esp32_poll_stop = False
        
        # Initialize camera at startup
        image_utils.init_camera()
        
        # Create required directories if they don't exist
        os.makedirs("esp32_images", exist_ok=True)
        os.makedirs("esp32_base64", exist_ok=True)  # New directory for base64 data
        
        # Get available providers and models
        self.providers = model_helper.get_available_providers()
        if not self.providers:
            # Default to Gemini if no API keys are found
            self.providers = ['Gemini']
        
        # Default model lists
        if self.providers:
            self.models = model_helper.get_models_for_provider(self.providers[0])
        else:
            self.models = []
        
        # Create UI layout
        self._create_ui()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def _create_ui(self):
        """Create the UI layout"""
        # Main container
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top frame for prompt
        self.prompt_text = ui_helper.create_prompt_section(
            main_frame, 
            "I want a short answer for which trash type do you see in the image [cardboard, glass, metal, paper, plastic or other]"
        )
        
        # Middle frame (two panels side by side)
        middle_frame = tk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left panel - Image list
        left_panel = ui_helper.create_image_list_panel(
            middle_frame,
            {
                'upload': self.open_images,
                'camera': self.toggle_camera,
                'random': self.get_random_images,
                'clear': self.clear_images,
                'select': self.on_file_select,
                'subscribe_esp32': self.toggle_esp32_subscription  # New callback
            }
        )
        
        self.file_listbox = left_panel['listbox']
        self.esp32_sub_var = left_panel['esp32_sub_var']
        self.esp32_ip_entry = left_panel['esp32_ip_entry']
        
        # Right panel - Image display and camera controls
        right_panel = ttk.LabelFrame(middle_frame, text="Selected Image / Camera Preview")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Image display
        self.image_label = ttk.Label(right_panel)
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Camera controls - initially hidden
        self.camera_controls = ui_helper.create_camera_controls_panel(
            right_panel,
            {
                'connect_webcam': self.connect_webcam,
                'connect_esp32': self.connect_esp32,
                'capture': self.capture_from_camera,
                'analyze_live': self.analyze_live_camera,
                'stop': self.stop_camera
            }
        )
        
        # Bottom frame - Configuration and results
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, pady=(0, 5))
        
        # Split bottom frame into left (config) and right (results)
        bottom_left = tk.Frame(bottom_frame)
        bottom_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        bottom_right = tk.Frame(bottom_frame)
        bottom_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Configuration section
        self.config_widgets = ui_helper.create_config_section(
            bottom_left,
            self.providers,
            self.models,
            self.analyze_image
        )
        
        # Set provider change handler
        self.config_widgets['provider_combo'].bind(
            "<<ComboboxSelected>>", 
            self.on_provider_change
        )
        
        # Set initial values
        if self.providers:
            self.config_widgets['provider_var'].set(self.providers[0])
        if self.models:
            self.config_widgets['model_var'].set(self.models[0])
        
        # Results section
        self.results_text = ui_helper.create_results_section(bottom_right)
    
    # MARK: - Event Handlers
    def on_provider_change(self, event):
        """Handle provider selection change"""
        provider = self.config_widgets['provider_var'].get()
        if provider:
            # Update models for the selected provider
            models = model_helper.get_models_for_provider(provider)
            
            # Update combobox values
            self.config_widgets['model_combo']['values'] = models
            
            # Set default model
            if models:
                self.config_widgets['model_var'].set(models[0])
    
    def on_file_select(self, event):
        """Handle image selection from listbox"""
        # If camera is active, stop it first
        if self.camera_active:
            self.stop_camera()
        
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if 0 <= index < len(self.images):
            self.current_image_index = index
            self._display_current_image()
    
    def on_close(self):
        """Handle window close event"""
        # Stop ESP32 subscription if running
        if self.esp32_subscription_active:
            self.stop_esp32_subscription()
            
        # Stop camera if running
        if self.camera_active:
            self.stop_camera()
        
        # Cancel connection thread if running
        if self.connection_thread and self.connection_thread.is_alive():
            # We can't directly cancel threads in Python,
            # but we can set a flag for the thread to check
            self.esp32_connected = False
            
            # Wait briefly for thread to finish
            self.connection_thread.join(0.5)
        
        # Release camera resources
        image_utils.release_camera()
        
        # Close the window
        self.root.destroy()
    
    # MARK: - ESP32 Subscription Functions
    def toggle_esp32_subscription(self):
        """Toggle ESP32 subscription on/off"""
        if self.esp32_subscription_active:
            self.stop_esp32_subscription()
        else:
            self.start_esp32_subscription()
    
    def start_esp32_subscription(self):
        """Start subscribing to an ESP32 camera for new images"""
        ip_address = self.esp32_ip_entry.get().strip()
        
        if not ip_address:
            messagebox.showwarning("Invalid IP", "Please enter a valid ESP32 IP address")
            return
        
        # Format the IP address
        if not ip_address.startswith("http"):
            ip_address = f"http://{ip_address}"
        
        # Test connection first
        try:
            response = requests.get(f"{ip_address}/", timeout=5)
            if response.status_code != 200:
                messagebox.showwarning("Connection Error", f"Could not connect to ESP32 at {ip_address}")
                return
        except Exception as e:
            messagebox.showwarning("Connection Error", f"Error connecting to ESP32: {str(e)}")
            return
        
        # Set subscription variables
        self.esp32_subscription_ip = ip_address
        self.esp32_subscription_active = True
        self.esp32_poll_stop = False
        
        # Update UI
        self.esp32_sub_var.set("Unsubscribe")
        self.esp32_ip_entry.config(state="disabled")
        self.config_widgets['status_var'].set(f"Subscribed to ESP32 at {ip_address}")
        
        # Start polling thread
        self.esp32_polling_thread = threading.Thread(
            target=self.poll_esp32_for_images,
            daemon=True
        )
        self.esp32_polling_thread.start()
    
    def stop_esp32_subscription(self):
        """Stop subscribing to ESP32 camera"""
        # Set flag to stop polling thread
        self.esp32_poll_stop = True
        
        # Wait for thread to terminate
        if self.esp32_polling_thread and self.esp32_polling_thread.is_alive():
            self.esp32_polling_thread.join(1.0)
        
        # Reset variables
        self.esp32_subscription_active = False
        self.esp32_polling_thread = None
        
        # Update UI
        self.esp32_sub_var.set("Subscribe to ESP32")
        self.esp32_ip_entry.config(state="normal")
        self.config_widgets['status_var'].set("ESP32 subscription stopped")
    
    def poll_esp32_for_images(self):
        """Poll ESP32 for new images in a separate thread"""
        poll_interval = 2  # seconds
        
        while not self.esp32_poll_stop:
            try:
                # Check if a new image is available
                response = requests.get(f"{self.esp32_subscription_ip}/check", timeout=5)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    if data.get("newImage", False):
                        # Download the base64 data
                        self.download_base64_from_esp32()
                        
                        # Reset the new image flag on ESP32
                        requests.get(f"{self.esp32_subscription_ip}/reset", timeout=5)
            except Exception as e:
                print(f"Error polling ESP32: {str(e)}")
            
            # Sleep for poll interval
            for _ in range(poll_interval * 10):  # Allow for more responsive termination
                if self.esp32_poll_stop:
                    break
                time.sleep(0.1)
    
    def download_base64_from_esp32(self):
        """Download base64 data from the ESP32 camera"""
        try:
            # Download the base64 data
            response = requests.get(f"{self.esp32_subscription_ip}/base64", timeout=10)
            if response.status_code != 200:
                print(f"Error downloading base64: status code {response.status_code}")
                return
            
            # Get the base64 string
            base64_data = response.text
            
            # Create a timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save the base64 data to file
            base64_filename = f"esp32_base64_{timestamp}.txt"
            base64_filepath = os.path.join("esp32_base64", base64_filename)
            
            with open(base64_filepath, "w") as f:
                f.write(base64_data)
            
            # Convert base64 to image and save
            try:
                # Decode base64 data
                image_data = base64.b64decode(base64_data)
                
                # Save as image file
                image_filename = f"esp32_{timestamp}.jpg"
                image_filepath = os.path.join("esp32_images", image_filename)
                
                with open(image_filepath, "wb") as f:
                    f.write(image_data)
                
                # Add to image list (in main thread)
                self.root.after(0, lambda: self.add_esp32_image_to_list(image_filepath, image_filename))
                
            except Exception as e:
                print(f"Error converting base64 to image: {str(e)}")
            
        except Exception as e:
            print(f"Error downloading base64 from ESP32: {str(e)}")
    
    def add_esp32_image_to_list(self, filepath, filename):
        """Add a downloaded ESP32 image to the image list (called in main thread)"""
        # Load the image
        image_info = image_utils.load_image_from_path(filepath)
        if not image_info:
            return
        
        # Add to our list
        self.images.append(image_info)
        
        # Add to listbox
        self.file_listbox.insert(tk.END, filename)
        
        # Select this image if no other is selected
        if self.current_image_index < 0:
            index = len(self.images) - 1
            self.file_listbox.selection_set(index)
            self.current_image_index = index
            self._display_current_image()
        
        # Update status
        self.config_widgets['status_var'].set(f"New ESP32 image received: {filename}")
    
    # MARK: - Camera Functions
    def connect_webcam(self, camera_type, camera_id):
        """
        Connect to a webcam
        
        Args:
            camera_type: Type of camera (e.g., "Webcam (0)")
            camera_id: Camera ID (e.g., "0")
        """
        # Disable dropdown during connection
        self.camera_controls['camera_var'].configure(state="disabled")
        
        # Update status
        self.config_widgets['status_var'].set(f"Connecting to {camera_type}...")
        self.root.update()
        
        # Set camera source
        success = image_utils.set_camera_source("webcam", camera_id=int(camera_id))
        
        # Re-enable dropdown
        self.camera_controls['camera_var'].configure(state="readonly")
        
        if success:
            self.config_widgets['status_var'].set(f"Connected to {camera_type}")
            self.current_camera_type = camera_type
            
            # If camera was active, restart it
            if self.camera_active:
                self.start_camera()
        else:
            self.config_widgets['status_var'].set(f"Failed to connect to {camera_type}")
    
    def connect_esp32(self, camera_type, ip_address, connect_var):
        """
        Connect or disconnect ESP32 camera in a separate thread
        
        Args:
            camera_type: Type of camera ("ESP32 Camera")
            ip_address: IP address of the ESP32 camera
            connect_var: StringVar for the connect button text
        """
        # Check if we're already connected - if so, disconnect
        if self.esp32_connected:
            # Disconnect
            self.esp32_connected = False
            connect_var.set("Connect")
            
            # Stop the camera if it was active
            if self.camera_active:
                self.stop_camera()
                
            self.config_widgets['status_var'].set("ESP32 camera disconnected")
            return
        
        # Validate IP address input
        if not ip_address:
            messagebox.showwarning("Invalid IP", "Please enter a valid IP address")
            return
        
        # Disable controls during connection
        self.camera_controls['connect_btn'].configure(state="disabled")
        self.camera_controls['ip_entry'].configure(state="disabled")
        
        # Update status
        self.config_widgets['status_var'].set("Connecting to ESP32 camera...")
        self.root.update()
        
        # Connect in a separate thread
        def connection_thread():
            # Set up basic camera configuration
            success = image_utils.set_camera_source("esp32", ip_address=ip_address)
            
            if not success:
                # Enable controls
                self.root.after(0, lambda: self.camera_controls['connect_btn'].configure(state="normal"))
                self.root.after(0, lambda: self.camera_controls['ip_entry'].configure(state="normal"))
                self.root.after(0, lambda: self.config_widgets['status_var'].set("Failed to set up ESP32 camera"))
                return
            
            # Test connection
            success = image_utils.test_esp32_connection(ip_address)
            
            # Update UI based on result (in main thread)
            if success:
                self.root.after(0, lambda: self._on_esp32_connect_success(connect_var))
            else:
                self.root.after(0, lambda: self._on_esp32_connect_failure())
        
        # Start connection thread
        self.connection_thread = threading.Thread(target=connection_thread, daemon=True)
        self.connection_thread.start()
    
    def _on_esp32_connect_success(self, connect_var):
        """Handle successful ESP32 camera connection"""
        # Enable controls
        self.camera_controls['connect_btn'].configure(state="normal")
        self.camera_controls['ip_entry'].configure(state="normal")
        
        # Update connection state
        self.esp32_connected = True
        connect_var.set("Disconnect")
        self.current_camera_type = "ESP32 Camera"
        
        # Update status
        self.config_widgets['status_var'].set("ESP32 camera connected successfully")
        
        # If camera was active, restart it
        if self.camera_active:
            self.start_camera()
    
    def _on_esp32_connect_failure(self):
        """Handle failed ESP32 camera connection"""
        # Enable controls
        self.camera_controls['connect_btn'].configure(state="normal")
        self.camera_controls['ip_entry'].configure(state="normal")
        
        # Update connection state
        self.esp32_connected = False
        
        # Update status
        self.config_widgets['status_var'].set("Failed to connect to ESP32 camera")
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.camera_active:
            self.stop_camera()
        else:
            self.start_camera()
    
    def start_camera(self):
        """Start camera preview"""
        # If camera is already active, do nothing
        if self.camera_active:
            return
        
        # Special check for ESP32 camera
        if self.camera_controls['camera_var'].get() == "ESP32 Camera" and not self.esp32_connected:
            self.config_widgets['status_var'].set("ESP32 camera not connected. Please connect first.")
            return
        
        # Clear the current image display
        self.image_label.config(image='')
        
        # Update status
        self.config_widgets['status_var'].set("Starting camera...")
        self.root.update()
        
        # Show camera controls
        self.camera_controls['frame'].pack(fill=tk.X, padx=5, pady=5)
        
        # Start camera preview
        success = image_utils.start_camera_preview(
            self.image_label,
            self.config_widgets['status_var'],
            self.preview_active
        )
        
        if not success:
            self.config_widgets['status_var'].set("Failed to start camera")
            self.camera_controls['frame'].pack_forget()
            return
        
        # Update state
        self.camera_active = True
    
    def stop_camera(self):
        """Stop camera preview"""
        # If camera is not active, do nothing
        if not self.camera_active:
            return
        
        # Stop preview loop
        self.preview_active[0] = False
        
        # Give time for preview thread to stop
        time.sleep(0.1)
        
        # Hide camera controls
        self.camera_controls['frame'].pack_forget()
        
        # Update state
        self.camera_active = False
        
        # Clear display
        self.image_label.config(image='')
        
        # Display current image if available
        if self.current_image_index >= 0:
            self._display_current_image()
        
        # Update status
        self.config_widgets['status_var'].set("Camera stopped")
    
    def capture_from_camera(self):
        """Capture image from camera preview"""
        if not self.camera_active:
            return
        
        # Create captured_images folder if it doesn't exist
        captures_dir = os.path.join(".", "captured_images")
        
        # Capture the image
        image_info = image_utils.capture_image_embedded(captures_dir)
        
        if not image_info:
            self.config_widgets['status_var'].set("Failed to capture image")
            return
        
        # Stop camera preview
        self.stop_camera()
        
        # Clear existing images if this is the first one
        if not self.images:
            self.clear_images(ask=False)
        
        # Add to our list
        self.images.append(image_info)
        
        # Add to listbox
        self.file_listbox.insert(tk.END, image_info['name'])
        
        # Select this image
        index = len(self.images) - 1
        self.file_listbox.selection_set(index)
        self.current_image_index = index
        self._display_current_image()
        
        # Update status
        self.config_widgets['status_var'].set("Image captured from camera")
    
    def analyze_live_camera(self):
        """Analyze the current live camera feed"""
        if not self.camera_active:
            return
        
        # Get the current frame from the camera
        frame, frame_rgb = image_utils.get_current_frame()
        
        if frame is None:
            self.config_widgets['status_var'].set("Failed to get frame from camera")
            return
            
        # Create a temporary image info
        temp_image = {
            'path': None,
            'name': 'live_camera',
            'data': frame,
            'display': frame_rgb
        }
        
        # Run analysis on this frame
        self._run_analysis_on_image(temp_image)
    
    # MARK: - Image Management
    def open_images(self):
        """Open image files from dialog"""
        # If camera is active, stop it first
        if self.camera_active:
            self.stop_camera()
            
        file_paths = ui_helper.get_image_paths_from_dialog()
        if not file_paths:
            return
        
        # Clear existing images
        self.clear_images(ask=False)
        
        # Load selected images
        count = 0
        for path in file_paths:
            image_info = image_utils.load_image_from_path(path)
            if image_info:
                # Add to our list
                self.images.append(image_info)
                
                # Add to listbox
                self.file_listbox.insert(tk.END, image_info['name'])
                
                count += 1
        
        # Select first image if available
        if count > 0:
            self.file_listbox.selection_set(0)
            self.current_image_index = 0
            self._display_current_image()
        
        # Update status
        self.config_widgets['status_var'].set(f"Loaded {count} images")
    
    def get_random_images(self):
        """Get random images from datasets directory"""
        # If camera is active, stop it first
        if self.camera_active:
            self.stop_camera()
            
        # Get random image paths
        image_paths = image_utils.get_random_images()
        
        if not image_paths:
            messagebox.showwarning(
                "No Images Found", 
                "No images found in the datasets directories. Please upload images manually."
            )
            return
        
        # Clear existing images
        self.clear_images(ask=False)
        
        # Load selected images
        count = 0
        for path in image_paths:
            image_info = image_utils.load_image_from_path(path)
            if image_info:
                # Add to our list
                self.images.append(image_info)
                
                # Add to listbox
                self.file_listbox.insert(tk.END, image_info['name'])
                
                count += 1
        
        # Select first image if available
        if count > 0:
            self.file_listbox.selection_set(0)
            self.current_image_index = 0
            self._display_current_image()
        
        # Update status
        self.config_widgets['status_var'].set(f"Loaded {count} random images")
    
    def clear_images(self, ask=True):
        """Clear all loaded images"""
        # If camera is active, stop it first
        if self.camera_active:
            self.stop_camera()
            
        if ask and self.images:
            if not messagebox.askyesno("Clear Images", "Really clear all images?"):
                return
        
        # Clear image data
        self.images = []
        self.current_image_index = -1
        
        # Clear UI
        self.file_listbox.delete(0, tk.END)
        self.image_label.config(image='')
        ui_helper.update_results(self.results_text, "")
        
        # Update status
        self.config_widgets['status_var'].set("All images cleared")
    
    def _display_current_image(self):
        """Display the currently selected image"""
        if self.current_image_index < 0 or self.current_image_index >= len(self.images):
            return
        
        # Get image data
        img_rgb = self.images[self.current_image_index]['display']
        
        # Display image
        ui_helper.display_image(self.image_label, img_rgb)
    
    # MARK: - Image Analysis
    def analyze_image(self):
        """Analyze the currently selected image"""
        if self.current_image_index < 0:
            # No image selected
            if self.camera_active:
                # If camera is active, analyze the live feed
                self.analyze_live_camera()
                return
            else:
                messagebox.showwarning("No Image", "Please select an image first.")
                return
        
        # Get current image from list
        current_image = self.images[self.current_image_index]
        
        # Run analysis
        self._run_analysis_on_image(current_image)
    
    def _run_analysis_on_image(self, image_info):
        """Run analysis on the specified image"""
        # Get prompt
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("No Prompt", "Please enter a prompt.")
            return
        
        # Get parameters
        temperature = self.config_widgets['temperature'].get()
        max_tokens = self.config_widgets['max_length'].get()
        provider = self.config_widgets['provider_var'].get()
        model_name = self.config_widgets['model_var'].get()
        
        if not provider or not model_name:
            messagebox.showwarning("No Model", "Please select a provider and model.")
            return
        
        # Disable analyze button during processing
        self.config_widgets['analyze_button'].config(state=tk.DISABLED)
        if self.camera_active:
            self.camera_controls['analyze_live_btn'].config(state=tk.DISABLED)
        
        self.config_widgets['status_var'].set("Analyzing image...")
        
        # Clear results
        ui_helper.update_results(self.results_text, "")
        
        # Run analysis in background thread
        def analysis_thread():
            try:
                # Call model helper to analyze image
                result = model_helper.analyze_image(
                    provider, 
                    model_name, 
                    prompt, 
                    image_info['data'],
                    temperature,
                    max_tokens
                )
                
                # Update UI with results
                self.root.after(0, lambda: ui_helper.update_results(self.results_text, result))
                self.root.after(0, lambda: self.config_widgets['status_var'].set("Analysis complete"))
            
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: ui_helper.update_results(self.results_text, f"ERROR: {error_msg}"))
                self.root.after(0, lambda: self.config_widgets['status_var'].set("Error during analysis"))
            
            finally:
                # Enable buttons again
                self.root.after(0, lambda: self.config_widgets['analyze_button'].config(state=tk.NORMAL))
                if self.camera_active:
                    self.root.after(0, lambda: self.camera_controls['analyze_live_btn'].config(state=tk.NORMAL))
        
        # Start thread
        threading.Thread(target=analysis_thread, daemon=True).start()