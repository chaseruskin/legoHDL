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
        m1 = tk.PanedWindow(self._window, orient='horizontal', sashrelief=tk.RAISED)
        m1.pack(fill=tk.BOTH, expand=1)
        #configure size for both sections
        menu_width = int(self.getW()/4)
        field_width = self.getW() - menu_width

        #configure side menu
        items = tk.StringVar(value=['general','label','script','workspace','market'])
        self._menu_list = tk.Listbox(self._window, listvariable=items, selectmode='single')
        self._menu_list.pack(side=tk.LEFT)

        #configure actions when pressing a menu item
        self._menu_list.bind('<Double-1>', self.select)

        #configure field section
        self._fields = tk.Label(m1, text='general')

        #add to the pane
        m1.add(self._menu_list, minsize=menu_width)
        m1.add(self._fields, minsize=field_width, padx=-100, pady=-200)
        pass

    def select(self, event):
        '''
        Based on button click, select which section to present in the fields
        area of the window.
        '''
        i = self._menu_list.curselection()
        if i != ():
            sect = self._menu_list.get(i)  
            print('selected:',sect)
            self._fields.config(text=sect)
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