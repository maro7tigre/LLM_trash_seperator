import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from PIL import Image, ImageTk
from io import BytesIO
import time
import base64
import json
import threading

class ESP32CamClient:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32-CAM Trash Classification Viewer")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # ESP32 IP address input
        frame_top = ttk.Frame(root, padding="10")
        frame_top.pack(fill=tk.X)
        
        ttk.Label(frame_top, text="ESP32-CAM IP:").pack(side=tk.LEFT)
        self.ip_entry = ttk.Entry(frame_top, width=15)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        self.ip_entry.insert(0, "192.168.100.228") # Default prefix
        
        self.connect_btn = ttk.Button(frame_top, text="Connect", command=self.connect_and_monitor)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Enter ESP32-CAM IP address and click Connect")
        self.status_label = ttk.Label(root, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(pady=5)
        
        # Main display area with two panes
        self.main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left pane for JSON
        self.text_frame = ttk.LabelFrame(self.main_pane, text="JSON Data")
        self.main_pane.add(self.text_frame, weight=1)
        
        # Right pane for image
        self.image_frame = ttk.LabelFrame(self.main_pane, text="Image Preview")
        self.main_pane.add(self.image_frame, weight=1)
        
        # Text area with scrollbar for JSON content
        self.text_area = scrolledtext.ScrolledText(self.text_frame, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for image display
        self.canvas = tk.Canvas(self.image_frame, bg="lightgray", highlightthickness=1, 
                               highlightbackground="darkgray")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image placeholder
        self.display_placeholder()
        
        # ESP32 URL and monitoring
        self.esp32_url = None
        self.monitoring = False
        self.monitor_thread = None
        self.last_json = None
        
    def display_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(self.canvas.winfo_width()//2 or 200, 
                               self.canvas.winfo_height()//2 or 150, 
                               text="Image will appear here", font=("Arial", 14))
        
    def connect_and_monitor(self):
        """Connect to ESP32 and start monitoring for new images"""
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please enter the ESP32-CAM IP address")
            return
            
        self.esp32_url = f"http://{ip}"
        self.status_var.set(f"Connecting to {self.esp32_url}...")
        self.root.update()
        
        try:
            # Try to connect to the ESP32-CAM with increased timeout
            response = requests.get(self.esp32_url, timeout=5)
            
            if response.status_code == 200:
                self.status_var.set(f"Connected to ESP32-CAM at {ip}")
                
                # Start monitoring thread
                self.start_monitoring()
            else:
                self.status_var.set(f"Error: Received status code {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.status_var.set(f"Connection failed: {str(e)}")
    
    def start_monitoring(self):
        """Start a thread to monitor for new JSON data"""
        if not self.monitoring and self.esp32_url:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_esp32)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.status_var.set("Monitoring ESP32-CAM for new images...")
    
    def monitor_esp32(self):
        """Continuously check for new images"""
        while self.monitoring:
            try:
                # Request the latest photo
                response = requests.get(f"{self.esp32_url}/photo", timeout=5)
                
                if response.status_code == 200:
                    # Get the JSON content
                    json_text = response.text
                    
                    # Compare with the last received JSON
                    if json_text != self.last_json:
                        self.last_json = json_text
                        
                        # Use the main thread to update the UI
                        self.root.after(0, lambda: self.update_ui(json_text))
                
            except requests.exceptions.RequestException:
                # Just skip this iteration if there's an error
                pass
                
            # Check every 1 second
            time.sleep(1)
    
    def update_ui(self, json_text):
        """Update the UI with new JSON data"""
        # Update the text area
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, json_text)
        
        # Extract and display the image
        self.extract_image_from_json(json_text)
        
        # Update status
        self.status_var.set("New image received")
    
    def extract_image_from_json(self, json_text=None):
        """Extract Base64 image from JSON and display it"""
        if json_text is None:
            # Get the JSON text from text area
            json_text = self.text_area.get(1.0, tk.END).strip()
            
        if not json_text:
            self.status_var.set("No JSON data to process")
            return
            
        try:
            # Parse the JSON
            json_data = json.loads(json_text)
            
            # Extract Base64 data
            if "contents" in json_data and len(json_data["contents"]) > 0:
                parts = json_data["contents"][0]["parts"]
                base64_data = None
                text_prompt = None
                
                # Find the part with inline_data and text
                for part in parts:
                    if "inline_data" in part:
                        base64_data = part["inline_data"]["data"]
                    elif "text" in part:
                        text_prompt = part["text"]
                
                if base64_data:
                    # Decode Base64 to binary
                    img_data = base64.b64decode(base64_data)
                    
                    # Load as image
                    img_file = BytesIO(img_data)
                    pil_img = Image.open(img_file)
                    
                    # Display the image
                    self.display_image(pil_img)
                    
                    self.status_var.set(f"Image extracted. Prompt: {text_prompt}")
                else:
                    self.status_var.set("No Base64 image data found in JSON")
                    self.display_placeholder()
            else:
                self.status_var.set("Invalid JSON structure: no contents array found")
                self.display_placeholder()
            
        except json.JSONDecodeError as e:
            self.status_var.set(f"Error parsing JSON: {str(e)}")
            self.display_placeholder()
        except Exception as e:
            self.status_var.set(f"Error extracting image: {str(e)}")
            self.display_placeholder()
    
    def display_image(self, pil_img):
        # Get current canvas dimensions
        self.root.update_idletasks()  # Make sure dimensions are updated
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Calculate resize ratio
        img_width, img_height = pil_img.size
        ratio = min(canvas_width/max(1, img_width), canvas_height/max(1, img_height))
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        # Resize while preserving aspect ratio
        if ratio < 1:  # Only resize if image is larger than canvas
            pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to Tkinter format
        self.photo = ImageTk.PhotoImage(pil_img)
        
        # Display in canvas
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, image=self.photo, anchor=tk.CENTER)

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32CamClient(root)
    root.mainloop()