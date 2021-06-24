#   teardown.py is ran to properly clean a user's local machine from all
#   legoHDL footprints. It is in essence the 'uninstall' file. It
#   will attempt to remove from both install options.
import os, sys, shutil

print('---BEGINNING UNINSTALLATION---')

program_name='legoHDL'
working_dir=os.path.expanduser('~/.'+program_name+'/')

print('Removing '+working_dir+' working directory...')
shutil.rmtree(working_dir, ignore_errors=True)


print('Option: 0')

print('Checking for symbolic link file...')
try:
    os.remove('/usr/local/bin/'+program_name)
    print('Removed symbolic link file from /usr/local/bin/')
except:
    print('No symbolic link file detected in /usr/local/bin/')


print("Option: 1")

shell=os.environ['SHELL']
shell=shell[shell.rfind('/')+1:]
rc=os.path.expanduser('~/.'+shell+'rc')

data=list()
with open(rc, 'r') as config:
    data = config.readlines()
config.close()

print("Checking if alias exists...")
alias_exists = False
for line in data:
    if (line.find('alias '+program_name) != -1):
        alias_exists = True
        data.remove(line)
        print('Removed alias from '+rc)

if(not alias_exists):
    print('No alias detected in '+rc)

with open(rc, 'w') as config:
    config.writelines(data)

print('---UNINSTALLATION COMPLETE---')