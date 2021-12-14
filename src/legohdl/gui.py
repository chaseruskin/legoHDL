# ------------------------------------------------------------------------------
# Project: legohdl
# Script: gui.py
# Author: Chase Ruskin
# Description:
#   This script contains the class describing the settings GUI framework
#   and behavior for interacting, modifying, and saving settings.
# ------------------------------------------------------------------------------

import os, webbrowser
import logging as log
from .apparatus import Apparatus as apt

import_success = True
try:
    import tkinter as tk
    from tkinter.ttk import *
    from tkinter import messagebox
    from tkinter import font
except ModuleNotFoundError:
    import_success = False


class GUI:


    COMMENTS = {
        'active-workspace' : "The current workspace set.",

        'editor' : "The command to call your preferred text editor.",

        'author' : "Your name.",

        'refresh-rate' : 
"How often to synchronize vendors with their remote every day. Set to -1 to refresh on every call. \
Max value is 1440 (every minute). Evenly divides the refresh points throughout the 24-hour day. \
This automates the 'refresh' command.",

        'template' : 
"The path to copy a template folder when making a new block. If an empty assignment, \
it will use the built-in template folder.",

        'multi-develop' : 
"When enabled, it will reference blocks found in the workspace path over blocks found in the cache. \
This is ideal for simulataneously working on interconnected blocks. When done, be sure to \
release the blocks as new versions so any changes are set in stone (default is disabled).",

        'overlap-global' : 
"When enabled, on export the labels to be gathered can be the same file even if from the same project \
across different versions (overlapping). If disabled, it will not write multiple labels for the same \
file, even across different block versions (default is disabled).",

        'mixed-language' :
"When enabled, units will be able to be identified as instantiated regardless what language it was \
written in (VHDL or Verilog). When disabled, determining what component is instantiated is filtered \
to only search through units written in the original language.",

        'label:local' : 
"User-defined groupings of filetypes to be collected and written to the blueprint file on export. \
Labels help bridge a custom workflow with the user's backend tool. Local labels are only searched \
for in the current block. An @ symbol will be automatically prepended to the label in the blueprint file.\n\n\
Special default labels for *.vhd and *.vhdl are @VHDL-LIB, @VHDL-SRC, @VHDL-SIM, @VHDL-SIM-TOP, @VHDL-SRC-TOP, and for *.v and *.sv are @VLOG-LIB, @VLOG-SRC, \
@VLOG-SIM, @VLOG-SIM-TOP, @VLOG-SRC-TOP.",

        'label:global' : 
"User-defined groupings of filetypes to be collected and written to the blueprint file on export. \
Labels help bridge a custom workflow with the user's backend tool. Global labels are searched \
for in every dependent block. An @ symbol will be automatically prepended to the label in the blueprint file.\n\n\
Special default labels for *.vhd and *.vhdl are @VHDL-LIB, @VHDL-SRC, @VHDL-SIM, @VHDL-SIM-TOP, @VHDL-SRC-TOP, and for *.v and *.sv are @VLOG-LIB, @VLOG-SRC, \
@VLOG-SIM, @VLOG-SIM-TOP, @VLOG-SRC-TOP.",

        'plugin' : 
"User-defined aliases to execute plugins (scripts/programs). The command field is what will be executed \
as-if through the terminal. Enter the alias to legoHDL during the build command prepended with a + symbol. \
Use plugins to read a block's exported blueprint file and perform custom actions on the collected data.",

        'workspace' : 
"User-defined spaces for working with blocks. Blocks must appear in the workspace's path to be \
recognized as downloaded. Multiple vendors can be configured to one workspace and vendors can \
be shared across workspaces. Block downloads and installations in one workspace are separate from \
those of another workspace. List multiple vendors by separating values with a comma (,).",

        'vendor' : 
"The list of available vendors to be connected to workspaces. A vendor allows blocks to be visible \
from remote repositories and downloaded/installed across machines. If a vendor is not configured \
to a remote repository, its remote connection is empty. Vendors identified by remote connection cannot \
be renamed. Vendors have a .vndr file at the root of their directory.",

        'profiles' : 
"A list of profiles to import settings, templates, and/or plugins. Add a template by creating a template/ folder \
at the root of a profile. Add plugins into a plugins/ folder to be available for import. Add a legohdl.cfg file to configure \
settings that will be merged in when importing that profile. A profile directory is indicated by having a .prfl file.",
    }


    def __init__(self):
        '''
        Create a Tkinter object.
        '''
        if(import_success == False):
            log.error("Failed to open GUI for settings (unable to find tkinter).")
            return None

        #create dictionary to store tk variables
        self._tk_vars = dict()

        #create root window
        self._window = tk.Tk()
        #add icon
        img = tk.Image("photo", file=apt.getProgramPath()+'/data/icon.gif')
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
        items = tk.StringVar(value=list(list(apt.SETTINGS.keys()) + ['profiles']))
        self._menu_list = tk.Listbox(self._window, listvariable=items, selectmode='single', relief=tk.RIDGE)
        #configure actions when pressing a menu item
        self._menu_list.bind('<Double-1>', self.select)
        #add to the pane
        menu_frame.add(self._menu_list)

        # --- field frame ---
        #configure field frame widgets
        self.loadFields('general')

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
        '''
        Transfers all GUI-related fields/data into legohdl.cfg file and apt.SETTINGS
        variable. Saves only affect the current field frame window variables/settings.
        '''
        #transfer all gui fields/data into legohdl.cfg
        for key,sect in self._tk_vars.items():
            for name,field in sect.items():
                # --- ACTIVE-WORKSPACE ---
                #save active-workspace if its a valid workspace available
                if(name == 'active-workspace' and field.get() in apt.SETTINGS['workspace'].keys()):
                    apt.SETTINGS[key][name] = field.get()
                    pass
                # --- REFRESH-RATE ---
                #save refresh-rate only if its an integer being returned
                elif(name == 'refresh-rate'):
                    try:
                        apt.SETTINGS[key][name] = field.get()
                    except:
                        #do not save getting an error on field.get() (NaN)
                        pass
                    pass
                # --- PLUG-INS and MARKETS ---
                elif(key == 'plugin' or key == 'vendor'):
                    #load records directly from table for plugins
                    self._tk_vars[key] = {}
                    for record in self._tb.getAllValues():
                        self._tk_vars[key][record[0]] = record[1]
                    #copy dictionary back to settings
                    apt.SETTINGS[key] = self._tk_vars[key].copy()
                    pass
                # --- PROFILES ---
                elif(name == 'profiles'):
                    #load records directly from table for profiles
                    self._tk_vars[name][name] = []
                    for record in self._tb.getAllValues():
                        self._tk_vars[name][name] += [record[0]]
                    #copy list back to settings
                    apt.SETTINGS['general'][name] = self._tk_vars[name][name].copy()

                    pass
                # --- LABELS ----
                elif(key == 'label'):
                    #load records directly from table for global (tgl_label == 0)
                    if(self._tgl_labels.get() == 0):
                        self._tk_vars[key]['global'] = {}
                        for record in self._tb.getAllValues():
                            self._tk_vars[key]['global'][record[0].upper()] = record[1]
                    #load records directly from table for local (tgl_label == 1)
                    else:
                        self._tk_vars[key]['local'] = {}
                        for record in self._tb.getAllValues():
                            self._tk_vars[key]['local'][record[0].upper()] = record[1]
                    #copy dictionaries back to settings
                    apt.SETTINGS[key]['local'] = self._tk_vars[key]['local'].copy()
                    apt.SETTINGS[key]['global'] = self._tk_vars[key]['global'].copy()
                    pass
                # --- WORKSPACES ---
                elif(key == 'workspace'):
                    #load records directly from table
                    self._tk_vars[key] = {}
                    apt.SETTINGS[key] = {}
                    for record in self._tb.getAllValues():
                        #properly formart vendor list
                        mkts = []
                        for m in list(record[2].split(',')):
                            if(m != ''):
                                mkts += [m]
                        #store the inner workspace dictionaries
                        self._tk_vars[key][record[0]] = {'path' : record[1], 'vendor' : mkts}
                        #copy dictionary back to settings
                        apt.SETTINGS[key][record[0]] = self._tk_vars[key][record[0]].copy()
                    pass
                # --- OTHERS/SIMPLE STRING VARIABLES ---
                elif(isinstance(field, dict) == False):
                    e = field.get()
                    if(isinstance(e, str)):
                        #split to identify any paths and ENV_NAME
                        words = e.split()
                        for i in range(len(words)):
                            if(os.path.exists(os.path.expandvars(os.path.expanduser(words[i])))):
                                words[i] = apt.fs(words[i])
                        #regroup into one string
                        e = ''
                        for c in words:
                            e = e + c + ' '
                        e.strip()
                    field.set(e)
                    apt.SETTINGS[key][name] = e
                # --- ? ---
                else:
                    log.error("A saving error has occurred.")
        #write back to legohdl.cfg
        apt.save()
        #inform the user
        log.info("Settings saved successfully.")
        pass


    def openDocs(self):
        '''
        Open the documentation website in default browser.
        '''
        webbrowser.open(apt.DOCUMENTATION_URL)


    def select(self, event):
        '''
        Based on button click, select which section to present in the fields
        area of the window.
        '''
        i = self._menu_list.curselection()
        if i != ():
            sect = self._menu_list.get(i)  
            self.loadFields(section=sect)
        pass


    def loadFields(self, section):
        ft = font.nametofont("TkSmallCaptionFont")
        comment_font = ft
        wrap_len = 500
        #print('Loading',section+'...')
        #clear all widgets from the frame
        self.clrFieldFrame()
        self._comments = tk.Label(self._field_frame, text='', font=comment_font, wraplength=wrap_len, justify="left")
        #clear tk vars dictionary
        self._tk_vars = {section : {}}
        #re-write section title widget
        self._field_frame.config(text=section)        
        # always start label section with local labels begin displayed
        self._tgl_labels = tk.IntVar(value=1)

        # [!] load in legohdl.cfg variables

        def display_fields(field_map, i=0):
            '''
            Configure and map the appropiate widgets for the general settings
            section.
            '''
            for field,value in field_map.items():
                #skip profiles field
                if(field == 'profiles'):
                    continue
                
                #create widgets
                pady = 1
                padx = 20
                field_name_pos = 'w'
                field_value_pos = 'e'
                widg = tk.Label(self._field_frame, text=field)
                widg.grid(row=i, column=0, padx=padx, pady=pady, sticky=field_name_pos)
                
                if(isinstance(value, str) or value == None):
                    self._tk_vars[section][field] = tk.StringVar(value=apt.SETTINGS[section][field])
                    
                    #special case for 'active-workspace'
                    if(field == 'active-workspace'):
                        entry = tk.ttk.Combobox(self._field_frame, textvariable=self._tk_vars[section][field], values=list(apt.SETTINGS['workspace'].keys()))
                    else:
                        entry = tk.Entry(self._field_frame, width=40, textvariable=self._tk_vars[section][field])

                    entry.grid(row=i, column=2, columnspan=10, padx=padx, pady=pady, sticky=field_value_pos)
                    pass
                elif(isinstance(value, bool)):
                    self._tk_vars[section][field] = tk.BooleanVar(value=apt.SETTINGS[section][field])
                    
                    if(field == 'overlap-global'):
                        ToggleSwitch(self._field_frame, 'on', 'off', row=i, col=1, state_var=self._tk_vars[section][field], padx=padx, pady=pady)
                    elif(field == 'multi-develop'):
                        ToggleSwitch(self._field_frame, 'on', 'off', row=i, col=1, state_var=self._tk_vars[section][field], padx=padx, pady=pady)
                    elif(field == 'mixed-language'):
                        ToggleSwitch(self._field_frame, 'on', 'off', row=i, col=1, state_var=self._tk_vars[section][field], padx=padx, pady=pady)
                    pass
                elif(isinstance(value, int)):
                    self._tk_vars[section][field] = tk.IntVar(value=apt.SETTINGS[section][field])
                    
                    if(field == 'refresh-rate'):
                        wheel = tk.ttk.Spinbox(self._field_frame, from_=-1, to=1440, textvariable=self._tk_vars[section][field], wrap=True)
                        wheel.grid(row=i, column=2, columnspan=10, padx=padx, pady=pady, sticky=field_value_pos)
                    pass
                i += 1
                self._comments = tk.Label(self._field_frame, font=comment_font, text=self.COMMENTS[field], wraplength=wrap_len, justify="left")
                self._comments.grid(row=i, column=0, columnspan=10, padx=padx, pady=pady, sticky=field_name_pos)
                i += 1
            pass
        i = 0 
        if(section == 'general'):
            #map widgets
            display_fields(apt.SETTINGS[section])
            i = -1 #disable because we print comments in method
        elif(section == 'label'):
            #store 1-level dicionaries
            self._tk_vars[section]['local'] = apt.SETTINGS[section]['local'].copy()
           
            def loadLocalTable(event=None):
                #store global table
                #print(self._tb.getAllValues())
                self._tk_vars[section]['global'] = {}
                for record in self._tb.getAllValues():
                    self._tk_vars[section]['global'][record[0]] = record[1]
                #clear all records
                self._tb.clearRecords()
                #load labels from local list
                for key,val in self._tk_vars[section]['local'].items():
                    self._tb.insertRecord([key,val])
                self._comments.configure(text=self.COMMENTS[section+':local'])
                pass

            def loadGlobalTable(event=None):
                #store local label
                #print(self._tb.getAllValues())
                self._tk_vars[section]['local'] = {}
                for record in self._tb.getAllValues():
                    self._tk_vars[section]['local'][record[0]] = record[1]
                #clear all records
                self._tb.clearRecords()
                #load labels from global list
                for key,val in self._tk_vars[section]['global'].items():
                    self._tb.insertRecord([key,val])
                self._comments.configure(text=self.COMMENTS[section+':global'])
                pass
            
            ToggleSwitch(self._field_frame, 'local', 'global', row=0, col=0, state_var=self._tgl_labels, offCmd=loadGlobalTable, onCmd=loadLocalTable)
            #create the table object
            self._tb = Table(self._field_frame, 'Name (@)', 'File extension', row=1, col=0)
            i = self._tb.mapPeripherals(self._field_frame)

            #load the table elements from the settings
            loadLocalTable()
            self._tk_vars[section]['global'] = apt.SETTINGS[section]['global'].copy()
            self._comments.grid(row=i, column=0, columnspan=10, padx=10, pady=2, sticky='w')
            i = -1
            pass
        elif(section == 'plugin'):
            self._tk_vars[section] = apt.SETTINGS[section].copy()
            #create the table object
            self._tb = Table(self._field_frame, 'alias', 'command', row=0, col=0)
            i = self._tb.mapPeripherals(self._field_frame)
            #load the table elements from the settings
            for key,val in self._tk_vars[section].items():
                self._tb.insertRecord([key,val])
            pass
        elif(section == 'workspace'):
            self._tk_vars[section] = apt.SETTINGS[section].copy()
            #create the table object
            self._tb = Table(self._field_frame, 'name', 'path', 'vendors', row=0, col=0, rules=Table.workspaceRules)
            i = self._tb.mapPeripherals(self._field_frame)
            #load the table elements from the settings
            for key,val in self._tk_vars[section].items():
                fields = [key]+list(val.values())
                #convert any lists to strings seperated by commas
                for ii in range(len(fields)):
                    if isinstance(fields[ii], list):
                        str_list = ''
                        for f in fields[ii]:
                            str_list = str_list + str(f) + ','
                        fields[ii] = str_list

                self._tb.insertRecord(fields)
            pass
        elif(section == 'vendor'):
            self._tk_vars[section] = apt.SETTINGS[section].copy()
            #create the table object
            self._tb = Table(self._field_frame, 'name', 'remote connection', row=0, col=0, rules=Table.vendorRules)
            i = self._tb.mapPeripherals(self._field_frame)
            #load the table elements from the settings
            for key,val in self._tk_vars[section].items():
                self._tb.insertRecord([key,val])
            pass
        elif(section == 'profiles'):
            #copy in profile list from settings
            self._tk_vars[section][section] = apt.SETTINGS['general']['profiles'].copy()
            #create the table object
            self._tb = Table(self._field_frame, 'name', row=0, col=0, rules=None)
            #only '+' and '-' are available for profiles
            i = self._tb.mapPeripherals(self._field_frame, editable=False, openCmd=self._tb.openProfile)
            #load the table elements from the settings
            for item in self._tk_vars[section][section]:
                self._tb.insertRecord([item])

        if(i >= 0 and section in self.COMMENTS):
            self._comments.configure(text=self.COMMENTS[section])
            self._comments.grid(row=i, column=0, columnspan=10, padx=10, pady=2, sticky='w')

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


    def __init__(self, tk_frame, *headers, row=0, col=0, rules=None):
        '''
        Create an editable tkinter treeview object as a table containing records.
        '''
         #create a new frame for the plugins table
        tb_frame = tk.Frame(tk_frame)
        tb_frame.grid(row=row, column=col, sticky='nsew')
        self._initial_row = row
        #store the method in a variable that handles extra conditions for saving valid records
        self._rules = rules
        #tk.Label to print status of current command if necessary
        self._status = None

        scroll_y = tk.Scrollbar(tb_frame)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = tk.Scrollbar(tb_frame, orient='horizontal')
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self._tv = tk.ttk.Treeview(tb_frame, column=tuple(headers), show='headings', xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set, selectmode='browse')
        self._tv.pack(fill='both', expand=1)

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
        self._tv.insert(parent='', index=index, iid=self.assignID(), text='', values=tuple(data))
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


    def getAllValues(self):
        '''
        Returns a list of data values for each index from the table.
        '''
        records = []
        for i in self._tv.get_children():
            records += [self.getValues(i)]
        return records


    def mapPeripherals(self, field_frame, editable=True, openCmd=None):
        '''
        Creates surrounding supportive widgets for a data table.
        
        Parameters
        ---
        field_frame : master frame where the table is inputted
        editable : boolean to determine if 'update' and 'edit' buttons exist
        openCmd : method to set an 'open' button (no button if 'None')
        '''
        #create frame for buttons to go into
        button_frame = tk.Frame(field_frame)

        button_frame.grid(row=self._initial_row+2, column=0, sticky='ew', pady=2)
        #addition button
        button = tk.Button(button_frame, text=' + ', command=self.handleAppend)
        button.pack(side=tk.LEFT, anchor='w', padx=2)

        if(editable):
            #update button
            button = tk.Button(button_frame, text='update', command=self.handleUpdate)
            button.pack(side=tk.LEFT, anchor='w',padx=2)
            #edit button
            button = tk.Button(button_frame, text='edit', command=self.handleEdit)
            button.pack(side=tk.LEFT, anchor='w', padx=2)

        #delete button
        button = tk.Button(button_frame, text=' - ', command=self.handleRemove)
        button.pack(side=tk.LEFT, anchor='w', padx=2)

        if(openCmd != None):
            #open button
            button = tk.Button(button_frame, text='open', command=openCmd)
            button.pack(side=tk.LEFT, anchor='w',padx=2)

        self._status = tk.Label(button_frame, text='')
        self._status.pack(side=tk.RIGHT, anchor='e', padx=2)
        #divide up the entries among the frame width
        #text entries for editing
        entry_frame = tk.Frame(field_frame)
        entry_frame.grid(row=self._initial_row+1, column=0, sticky='ew')
        for ii in range(len(self.getHeaders())):
            if(ii == 0):
                self._entries.append(tk.Entry(entry_frame, text='', width=12))
                self._entries[-1].pack(side=tk.LEFT, fill='both')
            else:
                self._entries.append(tk.Entry(entry_frame, text=''))
                self._entries[-1].pack(side=tk.LEFT, fill='both', expand=1)

        #return the next availble row for the field_frame
        return self._initial_row+3


    def openProfile(self):
        sel = self._tv.focus()
        if(sel == ''): return
        #grab the data available at the selected table element
        data = self.getValues(sel)
        if(apt.SETTINGS['general']['editor'] != ''):
            try:
                apt.execute(apt.SETTINGS['general']['editor'], apt.getProfiles()[data[0]])
            except KeyError:
                tk.messagebox.showerror(title='Nonexistent Profile', message='Make sure to click apply to save settings.')
        pass


    def getAllRows(self, col, lower=True):
        '''
        This method returns a list of all the elements for a specific column.
        '''
        elements = []
        for it in (self._tv.get_children()):
            val = str(self.getValues(it)[col])
            val = val.lower() if(lower) else val
            elements += [val]
        return elements


    @classmethod
    def vendorRules(cls, self, data, new):
        '''
        Extra rules for adding/updating a vendor record.

        Parameters
        ---
        self : table object instance using this method
        data : list of the new record
        new  : boolean if the record is trying to be appended (True) or inserted
        '''
        rename_atmpt = False
        duplicate_remote = False
        valid_remote = True

        #cannot rename a vendor
        if(new == False):
            rename_atmpt = (data[0].lower() not in self.getAllRows(col=0, lower=True))
            if(data[1] != ''):
                data[1] = apt.fs(data[1])  
                valid_remote = apt.isValidURL(data[1])

        #cannot have duplicate remote connections
        if(new == True and data[1] != ''):
            data[1] = apt.fs(data[1])
            duplicate_remote = (data[1].lower() in self.getAllRows(col=1, lower=True))
            #try to link to remote
            if(duplicate_remote == False):
                valid_remote = apt.isValidURL(data[1])
           
        if(valid_remote == False):
            tk.messagebox.showerror(title='Invalid Remote', message='This git remote repository does not exist.')
        elif(rename_atmpt):
            tk.messagebox.showerror(title='Failed Rename', message='A vendor cannot be renamed.')
        elif(duplicate_remote):
            tk.messagebox.showerror(title='Duplicate Remote', message='This vendor is already configured.')

        return (not rename_atmpt) and (not duplicate_remote) and valid_remote


    @classmethod
    def workspaceRules(cls, self, data, new):
        '''
        Extra rules for adding/updating a workspace record.

        Parameters
        ---
        self : table object instance using this method
        data : list of the new record
        new  : boolean if the record is trying to be appended (True) or inserted
        '''
        #must have a path
        valid_path = data[1] != ''
        rename_atmpt = False
        
        #cannot rename a workspace
        if(new == False):
            rename_atmpt = (data[0].lower() not in self.getAllRows(col=0, lower=True))
        
        if(valid_path == False):
            tk.messagebox.showerror(title='Invalid Path', message='A workspace cannot have an empty path.')
        elif(rename_atmpt):
            tk.messagebox.showerror(title='Failed Rename', message='A workspace cannot be renamed.')
        #print('workspace rules')
        return valid_path and (not rename_atmpt)


    def validEntry(self, data, new):
        data = list(data)
        all_blank = True
        duplicate = False
        extra_valid = True
        #ensure the data has some fields completed
        for d in data:
            if(d != ''):
                all_blank = False
                break
        #ensure the data is not a duplicate key
        if(new == True):
            col = 0
            elements = self.getAllRows(col=col, lower=True)
            duplicate = elements.count(data[col].lower())
        
        #define table data rules
        if(self._rules != None):
            extra_valid = self._rules(self, data, new)

        if(extra_valid == False):
            pass
        elif(all_blank):
            tk.messagebox.showerror(title='Empty Record', message='Cannot add an empty record.')
        elif(duplicate):
            tk.messagebox.showerror(title='Duplicate Key', message='A record already has that key.')
        return (not all_blank) and (not duplicate) and extra_valid


    def handleUpdate(self):
        #get what record is selected
        sel = self._tv.focus()
        if(sel == ''): return

        #get the fields from the entry boxes
        data = []
        for ii in range(len(self.getEntries())):
            #replace ENV_NAME with correct path
            e = str(self.getEntries()[ii].get())
            if(e.count(apt.ENV_NAME)):
                e = e.replace(apt.ENV_NAME, apt.HIDDEN)
            if(os.path.exists(os.path.expanduser(e))):
                e = apt.fs(e)
            data += [e]

        #define rules for updating data fields
        if(self.validEntry(data, new=False)):
            #cannot reconfigure a vendor's remote connection if it already is established
            if(self._rules != self.vendorRules or self.getValues(sel)[1] == ''):
                #now plug into selected space
                self.replaceRecord(data, index=sel)
                self.clearEntries()
            else:
                tk.messagebox.showerror(title='Vendor Configured', message='This vendor\'s remote configuration is locked.')
        pass


    def handleAppend(self):
        #get the fields from the entry boxes
        data = []
        for ii in range(len(self.getEntries())):
            e = str(self.getEntries()[ii].get())
            if(e.count(apt.ENV_NAME)):
                e = e.replace(apt.ENV_NAME, apt.HIDDEN)
            if(os.path.exists(os.path.expanduser(e))):
                e = apt.fs(e)
            data += [e]

        if(self.validEntry(data, new=True)):
            #now add to new space at end
            self.insertRecord(data)
            self.clearEntries()
        pass


    def handleRemove(self):
        sel = self._tv.focus()
        if(sel == ''): return
        #delete the selected record
        self.removeRecord(int(sel))
        pass


    def handleEdit(self):
        sel = self._tv.focus()
        if(sel == ''): return
        #grab the data available at the selected table element
        data = self.getValues(sel)
        #clear any old values from entry boxes
        self.clearEntries()
        #ensure it is able to be edited (only for vendors)
        if(self._rules != self.vendorRules or data[1] == ''):
            #load the values into the entry boxes
            for ii in range(len(data)):
                self.getEntries()[ii].insert(0,str(data[ii]))
        else:
            tk.messagebox.showerror(title='Invalid Edit', message='This vendor cannot be edited.')
        pass


    def getTreeview(self):
        return self._tv


    pass


class ToggleSwitch:


    def __init__(self, tk_frame, on_txt, off_txt, row, col, state_var, onCmd=None, offCmd=None, padx=0, pady=0):
        self._state = state_var

        #create a new frame
        swt_frame = tk.Frame(tk_frame)
        swt_frame.grid(row=row, column=col, columnspan=10, sticky='ew', padx=padx, pady=pady)
        
        # radio buttons toggle between global table and local table  
        btn_on = tk.Radiobutton(swt_frame, indicatoron=0, text=on_txt, variable=state_var, value=1, width=8, command=onCmd)
        btn_off = tk.Radiobutton(swt_frame, indicatoron=0, text=off_txt, variable=state_var, value=0, width=8, command=offCmd)
        btn_off.pack(side=tk.RIGHT)
        btn_on.pack(side=tk.RIGHT)
        pass


    def getState(self):
        return self._state.get()


    pass