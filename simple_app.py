import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from PIL import Image, ImageTk
from io import BytesIO
import time
import base64

class ESP32CamClient:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32-CAM Base64 Client")
        self.root.geometry("1000x600")
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
        
        self.capture_base64_btn = ttk.Button(frame_top, text="Capture Image", command=self.capture_base64, state=tk.DISABLED)
        self.capture_base64_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Enter ESP32-CAM IP address and click Connect")
        self.status_label = ttk.Label(root, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(pady=5)
        
        # Main display area with two panes
        self.main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left pane for text/Base64
        self.text_frame = ttk.LabelFrame(self.main_pane, text="Base64 Text")
        self.main_pane.add(self.text_frame, weight=1)
        
        # Right pane for image
        self.image_frame = ttk.LabelFrame(self.main_pane, text="Image Preview")
        self.main_pane.add(self.image_frame, weight=1)
        
        # Text area with scrollbar for Base64 content
        self.text_area = scrolledtext.ScrolledText(self.text_frame, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for image display
        self.canvas = tk.Canvas(self.image_frame, bg="lightgray", highlightthickness=1, 
                               highlightbackground="darkgray")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add decode button below text area
        self.decode_btn = ttk.Button(self.text_frame, text="Decode from Text", 
                                    command=self.decode_base64, state=tk.DISABLED)
        self.decode_btn.pack(pady=5)
        
        # Image placeholder
        self.display_placeholder()
        
        # ESP32 URL
        self.esp32_url = None
        
    def display_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(self.canvas.winfo_width()//2 or 200, 
                               self.canvas.winfo_height()//2 or 150, 
                               text="Image will appear here", font=("Arial", 14))
        
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
                self.capture_base64_btn.config(state=tk.NORMAL)
            else:
                self.status_var.set(f"Error: Received status code {response.status_code}")
                self.capture_base64_btn.config(state=tk.DISABLED)
                
        except requests.exceptions.RequestException as e:
            self.status_var.set(f"Connection failed: {str(e)}")
            self.capture_base64_btn.config(state=tk.DISABLED)
    
    def capture_base64(self):
        if not self.esp32_url:
            messagebox.showerror("Error", "No ESP32-CAM connected")
            return
            
        self.status_var.set("Capturing image... (please wait)")
        self.capture_base64_btn.config(state=tk.DISABLED)
        self.root.update()
        
        try:
            # Use a longer timeout and stream the response
            start_time = time.time()
            response = requests.get(f"{self.esp32_url}/base64", timeout=20)
            
            if response.status_code == 200:
                # Get the Base64 text content
                base64_text = response.text
                
                # Display the Base64 text
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, base64_text)
                
                # Enable decode button
                self.decode_btn.config(state=tk.NORMAL)
                
                # Automatically decode and display the image
                self.decode_base64(base64_text)
                
                elapsed = time.time() - start_time
                self.status_var.set(f"Image captured successfully ({len(base64_text)} chars, {elapsed:.1f}s)")
            else:
                self.status_var.set(f"Error: Received status code {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.status_var.set(f"Image capture failed: {str(e)}")
            
        finally:
            self.capture_base64_btn.config(state=tk.NORMAL)
    
    def decode_base64(self, base64_text=None):
        # If no text provided, get it from text area
        if base64_text is None:
            base64_text = self.text_area.get(1.0, tk.END).strip()
            
        if not base64_text:
            self.status_var.set("No Base64 text to decode")
            return
            
        try:
            # Decode Base64 to binary
            img_data = base64.b64decode(base64_text)
            
            # Load as image
            img_file = BytesIO(img_data)
            pil_img = Image.open(img_file)
            
            # Display the image
            self.display_image(pil_img)
            
            self.status_var.set(f"Base64 decoded successfully to {pil_img.width}x{pil_img.height} image")
            
        except Exception as e:
            self.status_var.set(f"Error decoding Base64: {str(e)}")
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