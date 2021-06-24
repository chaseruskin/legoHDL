#   setup.py is ran first to properly configure a new user's local machine for
#   legoHDL to properly function. It is in essence the 'install' file. It
#   supports two types of installations.
import os, sys

INSTALL_OPTION=0

print('---BEGINNING INSTALLATION---')

for i,arg in enumerate(sys.argv):
    if(i == 0):
        continue
    if(i == 1 and (int(arg) == 1 or int(arg) == 0)):
        INSTALL_OPTION = int(arg)
    else:
        exit('ERROR- Invalid arguments. Setup failed.')
    pass

master_script='manager.py'
program_name='legoHDL'
working_dir=os.path.expanduser('~/.'+program_name+'/')
try:
    os.makedirs(working_dir+'packages/')
except:
    pass
path=os.path.realpath(__file__)
path=path[:path.rfind('/')+1]

#   The first method (preferred) will turn the main python script into an 
#   executable file and then symbolically store it in /usr/local/bin/.
if(INSTALL_OPTION == 0):
    print('Option: 0')

    print('Creating executable script...')
    os.system("chmod +x "+path+master_script)
    try:
        os.makedirs('/usr/local/bin/') # attempt to create directory if DNE
    except:
        pass

    if(os.path.isfile("/usr/local/bin/"+program_name)):
        print('Symbolic link already exists for '+program_name)
    else:
        print('Creating symbolic link located in /usr/local/bin/ to executable script...')
        os.system("ln -s "+path+master_script+" /usr/local/bin/"+program_name)
    pass


#   The second method will open your terminal's rc file and append an alias
#   to it that allows python to execute the main python script and pass in any args.
if(INSTALL_OPTION == 1):
    print("Option: 1")

    shell=os.environ['SHELL']
    shell=shell[shell.rfind('/')+1:]
    rc=os.path.expanduser('~/.'+shell+'rc')
    
    print("Checking if alias already exists...")
    already_exists=False
    with open(rc, 'r') as config:
        already_exists = (config.read().find('alias '+program_name) > -1)
    config.close()

    if (not already_exists):
        print("Appending alias to "+rc+"...")
        with open(rc, 'a') as config:
            alias='\nalias '+program_name+'=\"python3 \''+path+master_script+'\' $*\"'
            config.write(alias)
        config.close()
    else:
        print("Alias already exists in "+rc)
    pass

print('---INSTALLATION COMPLETE---')