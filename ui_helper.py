"""
UI helper functions for Trash Analyzer
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from PIL import Image, ImageTk
import cv2

# MARK: - UI Creation Helpers
def create_prompt_section(parent, default_prompt):
    """Create prompt input section"""
    prompt_frame = ttk.LabelFrame(parent, text="Prompt")
    prompt_frame.pack(fill=tk.X, pady=(0, 10))
    
    prompt_text = scrolledtext.ScrolledText(
        prompt_frame, 
        height=3, 
        wrap=tk.WORD
    )
    prompt_text.pack(fill=tk.X, padx=5, pady=5)
    prompt_text.insert(tk.END, default_prompt)
    
    return prompt_text

def create_image_list_panel(parent, callbacks):
    """Create the left panel with image list and controls"""
    left_panel = ttk.LabelFrame(parent, text="Images")
    left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    
    # Image control buttons
    buttons_frame = ttk.Frame(left_panel)
    buttons_frame.pack(fill=tk.X, padx=5, pady=5)
    
    ttk.Button(
        buttons_frame, 
        text="Upload Images", 
        command=callbacks['upload']
    ).pack(side=tk.LEFT, padx=2)
    
    ttk.Button(
        buttons_frame, 
        text="Toggle Camera", 
        command=callbacks['camera']
    ).pack(side=tk.LEFT, padx=2)
    
    ttk.Button(
        buttons_frame, 
        text="Random Images", 
        command=callbacks['random']
    ).pack(side=tk.LEFT, padx=2)
    
    ttk.Button(
        buttons_frame, 
        text="Clear Images", 
        command=callbacks['clear']
    ).pack(side=tk.LEFT, padx=2)
    
    # Listbox for images
    list_frame = ttk.Frame(left_panel)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    file_listbox = tk.Listbox(
        list_frame,
        selectmode=tk.SINGLE,
        exportselection=0
    )
    
    list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
    file_listbox.config(yscrollcommand=list_scrollbar.set)
    list_scrollbar.config(command=file_listbox.yview)
    
    file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Bind selection event
    file_listbox.bind('<<ListboxSelect>>', callbacks['select'])
    
    return file_listbox

def create_camera_controls_panel(parent, camera_callbacks):
    """Create camera control panel with dropdown and IP input"""
    # Main container for camera controls
    camera_frame = ttk.Frame(parent)
    
    # Camera source selection
    camera_source_frame = ttk.Frame(camera_frame)
    camera_source_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 2))
    
    ttk.Label(camera_source_frame, text="Camera:").pack(side=tk.LEFT)
    
    # Camera selection dropdown
    camera_var = tk.StringVar(value="Webcam (0)")
    camera_dropdown = ttk.Combobox(
        camera_source_frame,
        textvariable=camera_var,
        values=["Webcam (0)", "Webcam (1)", "Webcam (2)", "ESP32 Camera"],
        width=15,
        state="readonly"
    )
    camera_dropdown.pack(side=tk.LEFT, padx=5)
    
    # IP address frame for ESP32 camera (initially hidden)
    ip_frame = ttk.Frame(camera_frame)
    ttk.Label(ip_frame, text="IP Address:").pack(side=tk.LEFT, padx=(0, 5))
    ip_entry = ttk.Entry(ip_frame, width=20)
    ip_entry.pack(side=tk.LEFT)
    ip_entry.insert(0, "192.168.137.6")  # Default IP
    
    # Connect/Disconnect button
    connect_var = tk.StringVar(value="Connect")
    connect_btn = ttk.Button(
        ip_frame, 
        textvariable=connect_var,
        command=lambda: camera_callbacks['connect_esp32'](camera_var.get(), ip_entry.get(), connect_var)
    )
    connect_btn.pack(side=tk.LEFT, padx=5)
    
    # Camera action buttons
    button_frame = ttk.Frame(camera_frame)
    button_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
    
    capture_btn = ttk.Button(
        button_frame,
        text="Capture Photo",
        command=camera_callbacks['capture']
    )
    capture_btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    analyze_live_btn = ttk.Button(
        button_frame,
        text="Analyze Live Feed",
        command=camera_callbacks['analyze_live']
    )
    analyze_live_btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    stop_camera_btn = ttk.Button(
        button_frame,
        text="Stop Camera",
        command=camera_callbacks['stop']
    )
    stop_camera_btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    # Function to handle camera type changes
    def on_camera_change(*args):
        camera_type = camera_var.get()
        if camera_type == "ESP32 Camera":
            ip_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
            # Reset connect button when switching to ESP32
            connect_var.set("Connect")
        else:
            ip_frame.pack_forget()
            # Automatically connect to webcam
            camera_id = camera_type.split("(")[1].split(")")[0]
            camera_callbacks['connect_webcam'](camera_type, camera_id)
    
    # Bind dropdown change event
    camera_var.trace_add("write", on_camera_change)
    
    return {
        'frame': camera_frame,
        'camera_var': camera_var,
        'ip_entry': ip_entry,
        'capture_btn': capture_btn,
        'analyze_live_btn': analyze_live_btn, 
        'stop_btn': stop_camera_btn,
        'connect_btn': connect_btn,
        'connect_var': connect_var
    }

def create_config_section(parent, providers, models, analyze_callback):
    """Create the configuration section"""
    config_frame = ttk.LabelFrame(parent, text="API Configuration")
    config_frame.pack(fill=tk.BOTH, expand=True)
    
    # Provider selection
    provider_var = tk.StringVar()
    model_var = tk.StringVar()
    temperature = tk.DoubleVar(value=0.7)
    max_length = tk.IntVar(value=100)
    
    # Provider selection
    ttk.Label(config_frame, text="Provider:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    provider_combo = ttk.Combobox(
        config_frame,
        textvariable=provider_var,
        values=providers,
        state="readonly"
    )
    provider_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
    
    # Model selection
    ttk.Label(config_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    model_combo = ttk.Combobox(
        config_frame,
        textvariable=model_var,
        values=models,
        state="readonly"
    )
    model_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
    
    # Temperature slider
    ttk.Label(config_frame, text="Temperature:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
    temp_slider = ttk.Scale(
        config_frame,
        from_=0.1,
        to=1.0,
        orient=tk.HORIZONTAL,
        variable=temperature,
        length=200
    )
    temp_slider.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
    
    # Temperature value label
    temp_value_label = ttk.Label(config_frame, text="0.7")
    temp_value_label.grid(row=2, column=2, padx=5)
    
    # Update temperature label when slider moves
    def update_temp_label(*args):
        temp_value_label.configure(text=f"{temperature.get():.1f}")
    
    temperature.trace_add("write", update_temp_label)
    
    # Max length slider
    ttk.Label(config_frame, text="Max Tokens:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    length_slider = ttk.Scale(
        config_frame,
        from_=1,
        to=500,
        orient=tk.HORIZONTAL,
        variable=max_length,
        length=200
    )
    length_slider.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
    
    # Length value label
    length_value_label = ttk.Label(config_frame, text="100")
    length_value_label.grid(row=3, column=2, padx=5)
    
    # Update length label when slider moves
    def update_length_label(*args):
        length_value_label.configure(text=f"{max_length.get()}")
    
    max_length.trace_add("write", update_length_label)
    
    # Analyze button
    analyze_button = ttk.Button(
        config_frame,
        text="Analyze Image",
        command=analyze_callback
    )
    analyze_button.grid(row=4, column=0, columnspan=3, pady=10)
    
    # Status label
    status_var = tk.StringVar(value="Ready")
    status_label = ttk.Label(config_frame, textvariable=status_var, wraplength=250)
    status_label.grid(row=5, column=0, columnspan=3, pady=5)
    
    return {
        'provider_var': provider_var,
        'model_var': model_var,
        'temperature': temperature,
        'max_length': max_length,
        'analyze_button': analyze_button,
        'status_var': status_var,
        'provider_combo': provider_combo,
        'model_combo': model_combo
    }

def create_results_section(parent):
    """Create the results section"""
    results_frame = ttk.LabelFrame(parent, text="Analysis Results")
    results_frame.pack(fill=tk.BOTH, expand=True)
    
    results_text = scrolledtext.ScrolledText(
        results_frame,
        wrap=tk.WORD,
        height=10,
        font=("TkDefaultFont", 24, "bold"),
        state=tk.DISABLED
    )
    results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    return results_text

# MARK: - Display Functions
def display_image(image_label, img_rgb):
    """Display an image on a label widget"""
    if img_rgb is None:
        image_label.config(image='')
        return
    
    # Resize image for display while maintaining aspect ratio
    height, width = img_rgb.shape[:2]
    max_height = 400
    max_width = 500
    
    # Calculate new dimensions
    if height > max_height or width > max_width:
        scale = min(max_height / height, max_width / width)
        new_height, new_width = int(height * scale), int(width * scale)
        img_rgb = cv2.resize(img_rgb, (new_width, new_height))
    
    # Convert to PhotoImage
    img_pil = Image.fromarray(img_rgb)
    img_tk = ImageTk.PhotoImage(image=img_pil)
    
    # Update label
    image_label.config(image=img_tk)
    image_label.image = img_tk  # Keep a reference to prevent garbage collection

def update_results(results_text, text):
    """Update the results text widget"""
    results_text.config(state=tk.NORMAL)
    results_text.delete(1.0, tk.END)
    results_text.insert(tk.END, text)
    
    # Configure tags for bold and larger text
    results_text.tag_configure("bold_large", font=("TkDefaultFont", 24, "bold"))
    
    # Apply the tag to all text
    results_text.tag_add("bold_large", "1.0", tk.END)
    
    results_text.config(state=tk.DISABLED)

# MARK: - Dialog Functions
def get_image_paths_from_dialog():
    """Show file dialog and return selected image paths"""
    return filedialog.askopenfilenames(
        title="Select Images",
        filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.bmp"),
            ("All files", "*.*")
        ]
    )