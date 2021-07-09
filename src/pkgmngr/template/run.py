import os,sys
#example script demonstrating the easy handling of recipe file
VER='08'

#run a command in os-terminal
def execute(*args):
    cmd = 'cd build; '
    for x in args:
        cmd = cmd + x + ' '
    print(cmd,end='')
    os.system(cmd)

#parse file path to return name of file (VHDL entity name)
def unitName(file):
    s = file.rfind('/')
    d = file.rfind('.')
    return file[s+1:d]
    pass

def main():
    global VER
    recipe = open("./build/recipe", 'r')
    #clean build dir
    for f in os.listdir("./build"):
        if f.count(".cf"):
            os.remove("./build/"+f)
    #parse recipe file and analyze units
    tb_path = ''
    for x in recipe.readlines():
        spce1 = x.find(' ')
        spce2 = x.rfind(' ')
        lib = x[spce1+1:spce2]
        path = x[spce2+1:]
        if(lib != ''):
            execute("ghdl -a","--std="+VER,"--work="+lib,path)
        if(lib == '' and x.count("SRC")):
            execute("ghdl -a","--std="+VER,path)
        if(lib == '' and x.count("TB")):
            tb_path = path
    #determine target from command line args
    target = ''
    for i,arg in enumerate(sys.argv):
        if(i == 0):
            continue
        else:
            target = arg
    if(target == 'sim'):
        execute("ghdl -a -g","--std="+VER,"-fsynopsys",tb_path) 
        execute("ghdl -r","--std="+VER,"-fsynopsys",unitName(tb_path),"--vcd=./wf.vcd")
    print()


if __name__ == "__main__":
    main()