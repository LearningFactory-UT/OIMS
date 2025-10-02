import customtkinter as ctk

class ScrollableLabelButtonFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, detail_command=None, delivered_command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.detail_command = detail_command
        self.delivered_command = delivered_command
        self.radiobutton_variable = ctk.StringVar()
        self.order_dict = {}
        # self.order_id_list = []
        # self.button_list = []

    def add_item(self, order_id, label_text, image=None):
        small_font = ctk.CTkFont(size=20)
        # label_text: StringVar
        label = ctk.CTkLabel(self, textvariable=label_text, image=image, compound="left", padx=5, anchor="w", font=small_font)
        if self.detail_command is not None:
            detail_button = ctk.CTkButton(self, text="Details", width=50, height=24, font=small_font)
            detail_button.configure(command=lambda: self.detail_command(order_id))
            detail_button.grid(row=len(self.order_dict), column=2, pady=(0, 10), padx=5)
        else:
            detail_button = None

        if self.delivered_command is not None:
            delivered_button = ctk.CTkButton(self, text="Delivered", width=50, height=24, font=small_font)
            delivered_button.configure(command=lambda: self.delivered_command(order_id))
            delivered_button.grid(row=len(self.order_dict), column=1, pady=(0, 10), padx=5)
        else:
            delivered_button = None

        label.grid(row=len(self.order_dict), column=0, pady=(0, 10), sticky="w")
        self.order_dict[order_id] = {
            'label': label,
            'detail_button': detail_button,
            'delivered_button': delivered_button,
            'row': len(self.order_dict)
        }


    def remove_item(self, order_id):
        if order_id in self.order_dict:
            removed_row = self.order_dict[order_id]['row']

            # Remove the widgets associated with the order_id
            self.order_dict[order_id]['label'].grid_forget()
            self.order_dict[order_id]['detail_button'].grid_forget()
            if self.order_dict[order_id]['delivered_button']:
                self.order_dict[order_id]['delivered_button'].grid_forget()

            # Remove the item from the dictionary
            self.order_dict.pop(order_id)

            # Update the row numbers of the subsequent items
            for key, value in self.order_dict.items():
                if value['row'] > removed_row:
                    new_row = value['row'] - 1
                    value['label'].grid(row=new_row, column=0, pady=(0, 10), sticky="w")
                    value['detail_button'].grid(row=new_row, column=2, pady=(0, 10), padx=5)
                    if value['delivered_button']:
                        value['delivered_button'].grid(row=new_row, column=1, pady=(0, 10), padx=5)
                    value['row'] = new_row