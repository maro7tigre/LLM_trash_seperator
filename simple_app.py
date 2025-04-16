import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk
from io import BytesIO
import time

class ESP32CamClient:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32-CAM Client")
        self.root.geometry("680x550")
        self.root.resizable(True, True)
        
        # ESP32 IP address input
        frame_top = ttk.Frame(root, padding="10")
        frame_top.pack(fill=tk.X)
        
        ttk.Label(frame_top, text="ESP32-CAM IP:").pack(side=tk.LEFT)
        self.ip_entry = ttk.Entry(frame_top, width=15)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        self.ip_entry.insert(0, "192.168.1.") # Default prefix
        
        self.connect_btn = ttk.Button(frame_top, text="Connect", command=self.test_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.capture_btn = ttk.Button(frame_top, text="Capture Image", command=self.capture_image, state=tk.DISABLED)
        self.capture_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Enter ESP32-CAM IP address and click Connect")
        self.status_label = ttk.Label(root, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(pady=5)
        
        # Image display area
        self.image_frame = ttk.Frame(root, padding="10")
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas with a border
        self.canvas = tk.Canvas(self.image_frame, bg="lightgray", highlightthickness=1, 
                               highlightbackground="darkgray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Image placeholder
        self.display_placeholder()
        
        # ESP32 URL
        self.esp32_url = None
        
    def display_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(320, 240, text="Image will appear here", font=("Arial", 14))
        
    def test_connection(self):
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
                self.capture_btn.config(state=tk.NORMAL)
            else:
                self.status_var.set(f"Error: Received status code {response.status_code}")
                self.capture_btn.config(state=tk.DISABLED)
                
        except requests.exceptions.RequestException as e:
            self.status_var.set(f"Connection failed: {str(e)}")
            self.capture_btn.config(state=tk.DISABLED)
            
    def capture_image(self):
        if not self.esp32_url:
            messagebox.showerror("Error", "No ESP32-CAM connected")
            return
            
        self.status_var.set("Capturing image... (please wait)")
        self.capture_btn.config(state=tk.DISABLED)
        self.root.update()
        
        try:
            # Use a longer timeout and stream the response
            start_time = time.time()
            response = requests.get(f"{self.esp32_url}/capture", timeout=20, stream=True)
            
            if response.status_code == 200:
                # Display the image
                img_data = BytesIO()
                
                # Stream content in chunks to avoid timeout issues
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        img_data.write(chunk)
                
                img_data.seek(0)
                
                try:
                    pil_img = Image.open(img_data)
                    
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
                    
                    elapsed = time.time() - start_time
                    self.status_var.set(f"Image captured successfully ({img_width}x{img_height}, {img_data.getbuffer().nbytes} bytes, {elapsed:.1f}s)")
                except Exception as e:
                    self.status_var.set(f"Error processing image: {str(e)}")
            else:
                self.status_var.set(f"Error: Received status code {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.status_var.set(f"Image capture failed: {str(e)}")
            
        finally:
            self.capture_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32CamClient(root)
    root.mainloop()