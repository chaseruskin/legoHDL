################################################################################
#   Project: legohdl
#   Script: gui.py
#   Author: Chase Ruskin
#   Description:
#       This script contains the class describing the settings GUI framework
#   and behavior for interacting, modifying, and saving settings.
################################################################################

import logging as log
import os
from .apparatus import Apparatus as apt
import webbrowser

import_success = True
try:
    import tkinter as tk
    from tkinter.ttk import *
    from tkinter import messagebox
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
        file_path = os.path.realpath(__file__)
        head,_ = os.path.split(file_path)
        img = tk.Image("photo", file=head+'/data/icon.gif')
        self._window.tk.call('wm','iconphoto', self._window._w, img)
        #set the window size
        self._width,self._height = 800,600
        self._window.geometry(str(self.getW())+"x"+str(self.getH()))
        #constrain the window size
        self._window.wm_resizable(False, False)
        self._window.title("legoHDL settings")
        #center the window
        self._window = self.center(self._window)

        self.initFrames()
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

    def initFrames(self):
        #divide window into 2 sections
        #configure size for both sections
        menu_width = int(self.getW()/6)
        field_width = self.getW() - menu_width
        bar_height = int(self.getH()/10)
        field_height = self.getH() - bar_height

        #create the 3 main divisions
        menu_frame = tk.PanedWindow(self._window, width=menu_width, height=self.getH())
        self._field_frame = tk.LabelFrame(self._window, width=field_width, height=field_height, relief=tk.RAISED, padx=20, pady=20)
        bar_frame = tk.Frame(self._window, width=field_width, height=bar_height, relief=tk.SUNKEN)
        #don't resize frames to fit content
        bar_frame.grid_propagate(0)
        self._field_frame.grid_propagate(0)

        #layout all of the frames
        self._window.grid_rowconfigure(1, weight=1)
        self._window.grid_columnconfigure(0, weight=1)

        menu_frame.grid(row=1, sticky='w')
        bar_frame.grid(row=2, sticky='nsew')
        self._field_frame.grid(row=1, sticky='nse')
        self._field_frame.grid_columnconfigure(0, weight=1)
        
        # --- menu pane ---
        #configure side menu
        items = tk.StringVar(value=list(apt.SETTINGS.keys()))
        self._menu_list = tk.Listbox(self._window, listvariable=items, selectmode='single', relief=tk.RIDGE)
        #configure actions when pressing a menu item
        self._menu_list.bind('<Double-1>', self.select)
        #add to the pane
        menu_frame.add(self._menu_list)

        # --- variables for various widgets ---
        self._act_ws = tk.StringVar(value=apt.SETTINGS['general']['active-workspace'])
        self._mult_dev = tk.IntVar(value=int(apt.SETTINGS['general']['multi-develop']))
        self._ovlp_rec = tk.IntVar(value=int(apt.SETTINGS['general']['overlap-recursive']))
        self._tgl_labels = tk.IntVar(value=1)
        self._ref_rate = tk.IntVar(value=int(apt.SETTINGS['general']['refresh-rate']))

        # --- field frame ---
        #configure field frame widgets
        self._field_title = tk.Label(self._field_frame, text='general')
        self._cur_widgets = []
        self.load('general')

        # --- bar frame ---
        #configure bar frame widgets
        btn_save = tk.Button(bar_frame, text='apply', command=self.save, relief=tk.RAISED)
        btn_cancel = tk.Button(bar_frame, text='cancel', command=self._window.quit, relief=tk.RAISED)
        btn_help = tk.Button(bar_frame, text='help', command=self.openDocs, relief=tk.RAISED)

        #map buttons on bar frame
        btn_help.pack(side=tk.RIGHT, padx=20, pady=16)
        btn_cancel.pack(side=tk.RIGHT, padx=0, pady=16)
        btn_save.pack(side=tk.RIGHT, padx=20, pady=16)
        pass

    def clrFieldFrame(self):
        for widgets in self._field_frame.winfo_children():
            widgets.destroy()

    def save(self):
        log.info("Settings saved.")
        pass

    def openDocs(self):
        webbrowser.open(apt.DOCUMENTATION_URL)

    def select(self, event):
        '''
        Based on button click, select which section to present in the fields
        area of the window.
        '''
        i = self._menu_list.curselection()
        if i != ():
            sect = self._menu_list.get(i)  
            self.load(section=sect)
        pass

    def load(self, section):
        #print('Loading',section+'...')
        #clear all widgets from the frame
        self.clrFieldFrame()
        #re-write section title widget
        self._field_frame.config(text=section)

        def display_fields(field_map, i=0):
            for field,value in field_map.items():
                #skip profiles field
                if(field == 'profiles'):
                    continue
                #create widgets
                widg = tk.Label(self._field_frame, text=field)
                widg.grid(row=i, column=0, padx=10, pady=10)
                
                if(isinstance(value, str) or value == None):
                    #special case for 'active-workspace'
                    if(field == 'active-workspace'):
                        entry = tk.ttk.Combobox(self._field_frame, textvariable=self._act_ws, values=list(apt.SETTINGS['workspace'].keys()))
                        #print(entry.get())
                    else:
                        entry = tk.Entry(self._field_frame, width=40)
                        if(value == None):
                            value = ''
                        entry.insert(tk.END, str(value))
                    entry.grid(row=i, column=2, columnspan=2, padx=10, pady=10, sticky='e')
 
                elif(isinstance(value, bool)):
                    if(field == 'overlap-recursive'):
                        ToggleSwitch(self._field_frame, 'on', 'off', row=i, col=1, state_var=self._ovlp_rec)
                    elif(field == 'multi-develop'):
                        ToggleSwitch(self._field_frame, 'on', 'off', row=i, col=1, state_var=self._mult_dev)

                elif(isinstance(value, int)):
                    #refresh-rate
                    wheel = tk.ttk.Spinbox(self._field_frame, from_=-1, to=1440, textvariable=self._ref_rate, wrap=True)
                    wheel.grid(row=i, column=2, columnspan=2, padx=10, pady=10, sticky='e')
                i += 1
                if(isinstance(value,dict)):
                    #print(value)
                    i = display_fields(value, i)
            return i

        if(section == 'general'):
            #map widgets
            display_fields(apt.SETTINGS[section])
            pass
        elif(section == 'label'):
           
            def loadShallowTable(event=None):
                #clear all records
                tb.clearRecords()
                #load labels from shallow list
                for key,val in apt.SETTINGS['label']['shallow'].items():
                    tb.insertRecord([key,val])

            def loadRecursiveTable(event=None):
                #clear all records
                tb.clearRecords()
                #load labels from recursive list
                for key,val in apt.SETTINGS['label']['recursive'].items():
                    tb.insertRecord([key,val])
            
            ToggleSwitch(self._field_frame, 'shallow', 'recursive', row=0, col=0, state_var=self._tgl_labels, offCmd=loadRecursiveTable, onCmd=loadShallowTable)
            #create the table object
            tb = Table(self._field_frame, 'Name (@)', 'File extension', row=1, col=0)
            tb.mapPeripherals(self._field_frame)

            #load the table elements from the settings
            loadShallowTable()
            
            pass
        elif(section == 'script'):
            #create the table object
            tb = Table(self._field_frame, 'alias', 'command', row=0, col=0)
            tb.mapPeripherals(self._field_frame)
            #load the table elements from the settings
            for key,val in apt.SETTINGS['script'].items():
                tb.insertRecord([key,val])
            pass
        elif(section == 'workspace'):
           
            #create the table object
            tb = Table(self._field_frame, 'name', 'path', 'markets', row=0, col=0)
            tb.mapPeripherals(self._field_frame)
            #load the table elements from the settings
            for key,val in apt.SETTINGS['workspace'].items():
                fields = [key]+list(val.values())
                #convert any lists to strings seperated by commas
                for ii in range(len(fields)):
                    if isinstance(fields[ii], list):
                        str_list = ''
                        for f in fields[ii]:
                            str_list = str_list + str(f) + ','
                        fields[ii] = str_list

                tb.insertRecord(fields)
            pass
        elif(section == 'market'):
            #create the table object
            tb = Table(self._field_frame, 'name', 'remote connection', row=0, col=0)
            tb.mapPeripherals(self._field_frame)
            #load the table elements from the settings
            for key,val in apt.SETTINGS['market'].items():
                tb.insertRecord([key,val])
            pass

    def center(self, win):
        '''
        Center the tkinter window. Returns the modified tkinter object.
        '''
        #hide window
        win.attributes('-alpha', 0.0)
        #update information regarding window size and screen size
        win.update_idletasks()
        s_height,s_width = win.winfo_screenheight(),win.winfo_screenwidth()
        width,height = win.winfo_width(),win.winfo_height()
        #compute the left corner point for the window to be center
        center_x = int((s_width/2) - (width/2))
        centery_y = int((s_height/2) - (height/2))
        #set size and position
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


class Table:

    def __init__(self, tk_frame, *headers, row=0, col=0):
        '''
        Create an editable tkinter treeview object as a table containing records.
        '''
         #create a new frame for the scripts table
        tb_frame = tk.Frame(tk_frame)
        tb_frame.grid(row=row, column=col, columnspan=10, sticky='nsew')
        self._initial_row = row

        scroll_y = tk.Scrollbar(tb_frame)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = tk.Scrollbar(tb_frame, orient='horizontal')
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self._tv = tk.ttk.Treeview(tb_frame, column=tuple(headers), show='headings', xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set, selectmode='browse')
        self._tv.pack(fill='both', expand=1)

        self._tv.tag_configure('gray', background='#dddddd')

        scroll_y.config(command=self._tv.yview)
        scroll_x.config(command=self._tv.xview)

        #define columns
        self._tv.column("#0", width=0, stretch=tk.NO)
        for h in headers:
            if(h == headers[0]):
                self._tv.column(h, width=0, anchor='w')
            else:
                self._tv.column(h, anchor='w')

        #create headings
        self._tv.heading("#0", text="", anchor='center')
        
        for h in headers:
            self._tv.heading(h, text=h, anchor='w')

        self._headers = headers
        self._entries = []
        self._size = 0
        self._id_tracker = 0
        pass

    def getSize(self):
        return self._size

    def getHeaders(self):
        return self._headers

    def getEntries(self):
        return self._entries

    def assignID(self):
        #always increment id so every table element is unique
        self._id_tracker += 1
        return self._id_tracker

    def insertRecord(self, data, index=-1):
        '''
        Inserts a new record at specified index. Default is the appended to end
        of table.
        '''
        if(index == -1):
            index = self.getSize()
        tag = 'white' if(self.getSize() % 2 == 0) else 'gray'
        self._tv.insert(parent='', index=index, iid=self.assignID(), text='', values=tuple(data), tag=tag)
        self._size += 1
        pass

    def replaceRecord(self, data, index):
        self._tv.item(index, text='', values=tuple(data))

    def removeRecord(self, index=-1):
        '''
        Removes a record from the specified index. Default is the last record.
        Also returns the popped value if successful.
        '''
        popped_val = None
        if(index == -1):
            index = self.getSize()-1
        if(self.getSize() > 0):
            popped_val = self.getValues(index)
            self._tv.delete(index)
            self._size -= 1
        return popped_val

    def clearRecords(self):
        self._tv.delete(*self._tv.get_children())
        self._size = 0

    def clearEntries(self):
        #clear any old values from entry boxes
        for ii in range(len(self.getEntries())):
            self.getEntries()[ii].delete(0,tk.END)

    def getValues(self, index):
        '''
        Returns the data values at the specified index from the table.
        '''
        fields = []
        for value in self._tv.item(index)['values']:
            fields += [value]
        return fields

    def mapPeripherals(self, field_frame, editable=True):
        #create frame for buttons to go into
        button_frame = tk.Frame(field_frame)

        button_frame.grid(row=self._initial_row+1, column=0, sticky='ew')
        #addition button
        button = tk.Button(button_frame, text='+', command=self.handleAppend)
        button.pack(side=tk.LEFT, anchor='w')

        if(editable):
            #update button
            button = tk.Button(button_frame, text='update', command=self.handleUpdate)
            button.pack(side=tk.LEFT, anchor='w')
            #edit button
            button = tk.Button(button_frame, text='edit', command=self.handleEdit)
            button.pack(side=tk.LEFT, anchor='w')

        #delete button
        button = tk.Button(button_frame, text='-', command=self.handleRemove)
        button.pack(side=tk.LEFT, anchor='w')
        #divide up the entries among the frame width
        #text entries for editing
        entry_frame = tk.Frame(field_frame)
        entry_frame.grid(row=self._initial_row+2, column=0, sticky='ew')
        for ii in range(len(self.getHeaders())):
            if(ii == 0):
                self._entries.append(tk.Entry(entry_frame, text='', width=20))
                self._entries[-1].pack(side=tk.LEFT, fill='both')
            else:
                self._entries.append(tk.Entry(entry_frame, text=''))
                self._entries[-1].pack(side=tk.LEFT, fill='both', expand=1)

        #return the next availble row for the field_frame
        return self._initial_row+3


    def validEntry(self, data):
        # :todo: define table data rules
        return True

    def handleUpdate(self):
        #get what record is selected
        sel = self._tv.focus()
        if(sel == ''): return

        #get the fields from the entry boxes
        data = []
        for ii in range(len(self.getEntries())):
            data += [self.getEntries()[ii].get()]

        # :todo: define rules for updating data fields
        if(self.validEntry(data)):
            #now plug into selected space
            self.replaceRecord(data, index=sel)
            self.clearEntries()
        else:
            tk.messagebox.showerror(title='Invalid Entry', message='go gators')
        pass

    def handleAppend(self):
        #get the fields from the entry boxes
        data = []
        for ii in range(len(self.getEntries())):
            data += [self.getEntries()[ii].get()]

        if(self.validEntry(data)):
            #now add to new space at end
            self.insertRecord(data)
            self.clearEntries()
        pass

    def handleRemove(self):
        sel = self._tv.focus()
        if(sel == ''): return
        #delete the selected record
        self.removeRecord(int(sel))
        #now reapply the toggle colors
        i = 0
        for it in list(self._tv.get_children()):
            tag = 'white' if (i % 2 == 0) else 'gray'
            self._tv.item(it, tag=tag)
            i += 1
        pass

    def handleEdit(self):
        sel = self._tv.focus()
        if(sel == ''): return
        #grab the data available at the selected table element
        data = self.getValues(sel)
        #clear any old values from entry boxes
        self.clearEntries()
        #load the values into the entry boxes
        for ii in range(len(data)):
            self.getEntries()[ii].insert(0,str(data[ii]))
        pass

    def getTreeview(self):
        return self._tv

    pass


class ToggleSwitch:

    def __init__(self, tk_frame, on_txt, off_txt, row, col, state_var, onCmd=None, offCmd=None,):
        self._state = state_var

        #create a new frame
        swt_frame = tk.Frame(tk_frame)
        swt_frame.grid(row=row, column=col, columnspan=10, sticky='ew')
        
        # radio buttons toggle between recursive table and shallow table  
        btn_on = tk.Radiobutton(swt_frame, indicatoron=0, text=on_txt, variable=state_var, value=1, width=8, command=onCmd)
        btn_off = tk.Radiobutton(swt_frame, indicatoron=0, text=off_txt, variable=state_var, value=0, width=8, command=offCmd)
        btn_off.pack(side=tk.RIGHT)
        btn_on.pack(side=tk.RIGHT)
        pass

    def getState(self):
        return self._state.get()

    pass