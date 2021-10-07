################################################################################
#   Project: legohdl
#   Script: gui.py
#   Author: Chase Ruskin
#   Description:
#       This script contains the class describing the settings GUI framework
#   and behavior for interacting, modifying, and saving settings.
################################################################################

import logging as log


import_success = True
try:
    import tkinter as tk
    from tkinter.messagebox import showinfo
except ModuleNotFoundError:
    import_success = False

class GUI:

    def __init__(self):
        '''
        Create a Tkinter object.
        '''
        if(import_success == False):
            log.error("Failed to open GUI for settings (unable to find tkinter).")
            return None
        
        self._window = tk.Tk()
        #add icon
        img = tk.Image("photo", file='./docs/legohdl_icon.gif')
        self._window.tk.call('wm','iconphoto', self._window._w, img)
        #set the window size
        self._width,self._height = 800,600
        self._window.geometry(str(self.getW())+"x"+str(self.getH()))
        #constrain the window size
        self._window.wm_resizable(False, False)
        self._window.title("legoHDL settings")
        #center the window
        self._window = self.center(self._window)

        self.initPanes()
        #enter main loop
        try:
            self._window.mainloop()
        except KeyboardInterrupt:
            log.info("Exiting GUI...")
        pass

    def getW(self):
        return self._width

    def getH(self):
        return self._height

    def initPanes(self):
        #divide window into 2 sections
        #m1 = tk.PanedWindow(self._window, orient='horizontal', sashrelief=tk.RAISED)
        #configure size for both sections
        menu_width = int(self.getW()/4)
        field_width = self.getW() - menu_width
        bar_height = int(self.getH()/10)
        field_height = self.getH() - bar_height
        field_bg = '#CCCCCC'

        #create the main divisions
        menu_frame = tk.PanedWindow(self._window, width=menu_width, height=self.getH())
        field_frame = tk.Frame(self._window, bg=field_bg, width=field_width, height=field_height,relief=tk.RAISED)
        bar_frame = tk.Frame(self._window, width=field_width, height=bar_height)
        # don't resize frames to fit content
        bar_frame.grid_propagate(0)
        field_frame.grid_propagate(0)

        #layout all of the frames
        self._window.grid_rowconfigure(1, weight=1)
        self._window.grid_columnconfigure(0, weight=1)

        menu_frame.grid(row=1, sticky='w')
        field_frame.grid(row=1, sticky='nse')
        bar_frame.grid(row=2, sticky='nsew')
    
        # --- menu pane ---
        #configure side menu
        items = tk.StringVar(value=['general','label','script','workspace','market'])
        self._menu_list = tk.Listbox(self._window, listvariable=items, selectmode='single')
        #configure actions when pressing a menu item
        self._menu_list.bind('<Double-1>', self.select)
        #add to the pane
        menu_frame.add(self._menu_list)

        # --- field frame ---
        #configure field frame widgets
        self._field_title = tk.Label(field_frame, text='general', bg=field_bg)
        entry = tk.Entry(field_frame, background='white')
        addition = tk.Button(field_frame, text='+', relief=tk.RAISED, bg=field_bg)

        #place on field frame
        self._field_title.place(x=self.offsetW(0.45,field_width))
        entry.place(x=self.offsetW(0.1,field_width), y=self.offsetH(0.3,field_height))
        addition.place(x=self.offsetW(0.8,field_width), y=self.offsetH(0.3,field_height))

        # --- bar frame ---
        #configure bar frame widgets
        btn_save = tk.Button(bar_frame, text='apply', command=self.save, relief=tk.RAISED)
        btn_cancel = tk.Button(bar_frame, text='cancel', command=self._window.quit, relief=tk.RAISED)

        #place on bar frame
        btn_save.place(x=self.offsetW(-0.3),y=self.offsetH(0.2, bar_height))
        btn_cancel.place(x=self.offsetW(-0.18),y=self.offsetH(0.2, bar_height))
        pass

    def offsetW(self, f, w=None):
        if(w == None):
            w = self.getW()
        if(f < 0):
            return w+int(w*f)
        else:
            return int(w*f)

    def offsetH(self, f, h=None):
        if(h == None):
            h = self.getH()
        if(f < 0):
            return h-int(h*f)
        else:
            return int(h*f)

    def save(self):
        log.info("Settings saved.")
        pass

    def select(self, event):
        '''
        Based on button click, select which section to present in the fields
        area of the window.
        '''
        #print(event)
        i = self._menu_list.curselection()
        if i != ():
            sect = self._menu_list.get(i)  
            print('selected:',sect)
            self._field_title.config(text=sect)
            self.load(section=sect)
        #sample of using showinfo
        #showinfo(title='info',message='selected')
        pass

    def load(self, section):
        print('Loading',section+'...')
        if(section == 'general'):

            pass
        elif(section == 'label'):

            pass
        elif(section == 'script'):

            pass
        elif(section == 'workspace'):

            pass
        elif(section == 'market'):
            
            pass

    def center(self, win):
        '''
        Center the tkinter window. Returns the modified tkinter object.
        '''
        #hide window
        win.attributes('-alpha', 0.0)
        
        #update information regarding window size and screen size
        win.update_idletasks()
        s_height = win.winfo_screenheight()
        s_width = win.winfo_screenwidth()
        width = win.winfo_width()
        height = win.winfo_height()
        #compute the left corner point for the window to be center
        center_x = int((s_width/2) - (width/2))
        centery_y = int((s_height/2) - (height/2))

        win.geometry(str(width)+"x"+str(height)+"+"+str(center_x)+"+"+str(centery_y))

        #reveal window
        win.deiconify()
        win.update_idletasks()
        win.attributes('-alpha', 1.0)
        return win

    
    def initialized(self):
        '''
        Return true if the GUI object has a tkinter object.
        '''
        return hasattr(self, "_window")
    pass