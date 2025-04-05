"""
Main Application Class for Trash Analyzer
"""

import os
import tkinter as tk
from tkinter import messagebox
import threading

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
        self.file_listbox = ui_helper.create_image_list_panel(
            middle_frame,
            {
                'upload': self.open_images,
                'camera': self.capture_from_camera,
                'random': self.get_random_images,
                'clear': self.clear_images,
                'select': self.on_file_select
            }
        )
        
        # Right panel - Image display
        self.image_label = ui_helper.create_image_display_panel(middle_frame)
        
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
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if 0 <= index < len(self.images):
            self.current_image_index = index
            self._display_current_image()
    
    # MARK: - Image Management
    def open_images(self):
        """Open image files from dialog"""
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
    
    def capture_from_camera(self):
        """Capture image from camera"""
        # Create captured_images folder if it doesn't exist
        captures_dir = os.path.join(".", "captured_images")
        
        # Display status
        self.config_widgets['status_var'].set("Opening camera...")
        self.root.update()
        
        # Capture the image
        image_info = image_utils.capture_image_from_camera(captures_dir)
        
        if not image_info:
            self.config_widgets['status_var'].set("Camera capture failed or cancelled")
            return
        
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
    
    def get_random_images(self):
        """Get random images from datasets directory"""
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
        """Analyze the current image using selected model"""
        if self.current_image_index < 0:
            messagebox.showwarning("No Image", "Please select an image first.")
            return
        
        # Get current image
        current_image = self.images[self.current_image_index]
        
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
            
        # For backward compatibility, if Gemini is selected, use the direct approach from the original code
        if provider == 'Gemini':
            self._analyze_with_gemini(
                prompt, 
                current_image, 
                model_name, 
                temperature, 
                max_tokens
            )
        else:
            # Use the generic approach for other providers
            # Disable analyze button during processing
            self.config_widgets['analyze_button'].config(state=tk.DISABLED)
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
                        current_image['data'],
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
                    # Enable button again
                    self.root.after(0, lambda: self.config_widgets['analyze_button'].config(state=tk.NORMAL))
            
            # Start thread
            threading.Thread(target=analysis_thread, daemon=True).start()
    
    def _analyze_with_gemini(self, prompt, current_image, model_name, temperature, max_tokens):
        """
        Analyze image using Gemini API directly - uses the same approach as the original code
        This ensures compatibility with the original implementation
        """
        # Disable analyze button during processing
        self.config_widgets['analyze_button'].config(state=tk.DISABLED)
        self.config_widgets['status_var'].set("Analyzing image...")
        
        # Clear results
        ui_helper.update_results(self.results_text, "")
        
        # Run analysis in background thread
        def analysis_thread():
            try:
                # Import required libraries
                import google.generativeai as genai
                from PIL import Image
                import cv2
                from credentials import get_api_key
                
                # Get API key - using original approach
                api_key = get_api_key()
                
                # Configure the API
                genai.configure(api_key=api_key)
                
                # Prepare image for API - exactly as in original code
                img_rgb = cv2.cvtColor(current_image['data'], cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(img_rgb)
                
                # Create the model with generation config - exactly as in original code
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                        "top_p": 0.95,
                        "top_k": 64
                    }
                )
                
                # Generate content using the model with PIL image directly - exactly as in original code
                response = model.generate_content([prompt, pil_image])
                
                # Process response - exactly as in original code
                result_text = response.text if hasattr(response, 'text') else str(response)
                self.root.after(0, lambda: ui_helper.update_results(self.results_text, result_text))
                self.root.after(0, lambda: self.config_widgets['status_var'].set("Analysis complete"))
            
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: ui_helper.update_results(self.results_text, f"ERROR: {error_msg}"))
                self.root.after(0, lambda: self.config_widgets['status_var'].set("Error during analysis"))
            
            finally:
                # Enable button again
                self.root.after(0, lambda: self.config_widgets['analyze_button'].config(state=tk.NORMAL))
        
        # Start thread
        threading.Thread(target=analysis_thread, daemon=True).start()