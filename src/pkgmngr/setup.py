#   setup.py is ran first to configure a new user's local machine for
#   legoHDL to properly function. It is in essence the 'install' file. It
#   supports two types of installations.
import os, sys, stat, shutil, git, yaml

INSTALL_OPTION=0

settings = dict()
with open("./settings.yml", "r") as file:
    settings = yaml.load(file, Loader=yaml.FullLoader)

print('---BEGINNING INSTALLATION---')

for i,arg in enumerate(sys.argv):
    if(i == 0):
        continue
    if(i == 1 and (int(arg) == 1 or int(arg) == 0)):
        INSTALL_OPTION = int(arg)
    else:
        exit('ERROR- Invalid arguments. Setup failed.')
    pass

master_script='/manager.py'
program_name='legohdl'

remote=settings['remote']
working_dir=os.path.expanduser(settings['local'])+'/'
hidden_dir=os.path.expanduser("~/."+program_name+"/")

print('Initializing working directory... '+working_dir)
os.makedirs(working_dir, exist_ok=True)

print('Initializing configuration directory... '+hidden_dir)
os.makedirs(hidden_dir, exist_ok=True)

open(hidden_dir+"mapping.toml", 'w').write("[libraries]").close()


print('Setting up package registry... ',end='')
#check the remote registry if package appears there
if(not os.path.isfile(hidden_dir+"registry/db.txt")):
    os.makedirs(hidden_dir+"registry/", exist_ok=True)
    open(hidden_dir+"registry/db.txt", 'w').close()
    print('success')
    pass
else:
    print('skipped')

print('Setting up cache folder... ',end='')
os.makedirs(hidden_dir+"cache", exist_ok=True)
print('success')

print('Setting up libraries folder... ',end='')
os.makedirs(hidden_dir+"lib", exist_ok=True)
print('success')

path=os.path.realpath(__file__) #note for release: path <- working_dir
path=path[:path.rfind('/')+1]
try:
    pass
    #shutil.copytree(path, hidden_dir+program_name)
    #shutil.move(path, working_dir) #note for release: use this command
except:
    pass


#   The first method (preferred) will turn the main python script into an 
#   executable file and then symbolically store it in /usr/local/bin/.
if(INSTALL_OPTION == 0):
    print('Option: 0')

    print('Creating executable script...')
    st = os.stat(path+master_script)
    os.chmod(path+master_script, st.st_mode | stat.S_IXUSR | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    try:
        os.makedirs('/usr/local/bin/') # attempt to create directory if DNE
    except:
        pass

    if(os.path.isfile("/usr/local/bin/"+program_name)):
        print('Symbolic link already exists for '+program_name)
    else:
        print('Creating symbolic link file located in /usr/local/bin/ to executable script...')
        os.symlink(path+master_script, "/usr/local/bin/"+program_name)
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