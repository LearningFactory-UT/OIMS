import customtkinter as ctk
from tkinter import PhotoImage  # Import this to handle images
from customtkinter import CTkImage
from PIL import Image, ImageOps
from utils import ITEMS


# TODO: still not working, the images are displayed not as squares

def make_square_with_transparency(image):
    """
    Pad the given image with transparent pixels to make it square.
    """
    width, height = image.size
    # Determine the size of the new square side
    # new_side = max(width, height) * 2
    new_side = int(max(width, height) * 1.5)
    
    # Create a new transparent image with the determined square dimensions
    new_image = Image.new('RGBA', (new_side, new_side), (0, 0, 0, 0))
    
    # Calculate padding to add on the top and bottom or on the left and right
    top_bottom_padding = (new_side - height) // 2
    left_right_padding = (new_side - width) // 2
    
    # Paste the original image onto the transparent background
    new_image.paste(image, (left_right_padding, top_bottom_padding))
    
    return new_image

class Spinbox(ctk.CTkFrame):
    def __init__(self, master, value=0, scale_factor=1, image_path='', name=''):
        super().__init__(master=master)
        
        self.name = name
        self.font = ('Arial', 20)
        self.scale_factor = scale_factor

        if image_path == ITEMS['standard']['Board Screw']:
            self.item_set = 4
        elif image_path == ITEMS['standard']['Camera Screw']:
            self.item_set = 2
        elif image_path == ITEMS['standard']['Motor Screw']:
            self.item_set = 3
        else:
            self.item_set = 1


        self.configure(fg_color=("gray78", "gray28"))  # set frame color

        self.grid_columnconfigure((0, 1, 2), weight=1)
        #self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure((1, 2), weight=0)

        # Store the image path for realoading
        self.image_path = image_path 


        # make the image square
        self.original_image = make_square_with_transparency(Image.open(image_path))

        # print(self.original_image.size)

        self.image = CTkImage(self.original_image, size=(200, 200))
        self.image_label = ctk.CTkLabel(master=self, text='', image=self.image)
        self.image_label.grid(row=0, column=0, columnspan=3, padx=0, pady=0)  # Position it at the top

        self.item_label = ctk.CTkLabel(master=self, text=self.name)
        self.item_label.grid(row=1, column=0, columnspan=3, sticky='nsew')

        # Subtract button (left)
        self.subtract_button = ctk.CTkButton(self, text="-", command=self.subtract_button_callback, font=self.font, width=40 * self.scale_factor, height=40 * self.scale_factor)
        self.subtract_button.grid(row=2, column=0, columnspan=1, sticky='e', pady=10)#, padx=(10 * self.scale_factor, 5 * self.scale_factor), pady=(5 * self.scale_factor, 10 * self.scale_factor))

        self.value = value
        self.int_part = int(value)

        # Integer part display (center)
        self.int_text = ctk.StringVar()
        self.int_text.set(self.int_part)
        self.int_label = ctk.CTkLabel(master=self, textvariable=self.int_text, font=self.font)
        self.int_label.grid(row=2, column=1, sticky='nsew')  # Position adjusted to be between "+" and "-"
        
        # Add button (right)
        self.add_button = ctk.CTkButton(self, text="+", command=self.add_button_callback, font=self.font, width=40 * self.scale_factor, height=40 * self.scale_factor)
        self.add_button.grid(row=2, column=2, columnspan=1, sticky='w', pady=10)#, padx=(5 * self.scale_factor, 10 * self.scale_factor), pady=(5 * self.scale_factor, 10 * self.scale_factor))
    

    
    def get_value(self):
        value = self.int_part
        return value
    
    def add_button_callback(self):
        self.int_part += self.item_set
        self.int_text.set(self.int_part)

    def subtract_button_callback(self):
        self.int_part -= self.item_set
        if self.int_part < 0:
            self.int_part = 0
        self.int_text.set(self.int_part)

    def reset(self):
        self.int_part = 0

    def disable_spinbox(self):
        # Disable buttons
        self.subtract_button.configure(state="disabled")
        self.add_button.configure(state="disabled")
        
        # Convert image to grayscale
        gray_image = self._change_icon_color(self.original_image, new_color=(150,150,150))
        self.image = CTkImage(gray_image, size=(200,200))
        self.image_label.configure(image=self.image)
        self.image_label.image = self.image  # Keep a reference, prevent garbage-collected

    def enable_spinbox(self):
        # Enable buttons
        self.subtract_button.configure(state="normal")
        self.add_button.configure(state="normal")
        
        # Revert image back to original
        self.image = CTkImage(self.original_image, size=(200,200))
        self.image_label.configure(image=self.image)
        self.image_label.image = self.image

    def _change_icon_color(self, image, new_color):
        
        # Prepare a new image with the same size and 'RGBA' mode
        new_image = Image.new("RGBA", image.size)
        
        # Get the data of the original image
        data = image.getdata()
        
        # Create a new data list
        new_data = []
        
        # Change the color of non-transparent pixels
        for item in data:
            # item is a tuple (R, G, B, A)
            if item[3] != 0:  # if the pixel is not fully transparent
                new_data.append(new_color + (item[3],))  # Change color, preserve alpha
            else:
                new_data.append(item)  # Keep the transparent pixels unchanged
        
        # Update the image with the new data
        new_image.putdata(new_data)
        
        return new_image
            

        

