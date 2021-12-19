# ------------------------------------------------------------------------------
# Project: legohdl
# Script: test.py
# Author: Chase Ruskin
# Description:
#   Runs tests to verify certain functions within legoHDL.
# ------------------------------------------------------------------------------

import os, shutil, time, sys
from datetime import datetime
from enum import Enum

from legohdl.apparatus import Apparatus as apt
from legohdl.workspace import Workspace
from legohdl.block import Block
from legohdl.vhdl import Vhdl
from legohdl.unit import Unit


# ------------------------------------------------------------------------------
# -- MAIN TESTING LAUNCH PAD
# ------------------------------------------------------------------------------
def main():
    #keep shorthand ready to override severity levels
    ts = Test.Severity

    #clean and create test input/output directories
    dirs = ['output/', 'input/']
    for d in dirs:
        if(os.path.exists(d)):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
        pass

    #load metadata
    apt.initialize()

    #setup fake workspace
    ws_path = './input/'
    ws = Workspace("testing-launch-pad", ws_path)

    #[!] create test object
    t = Test("unit-tests")

    #[!] run unit-tests --------------------------------------------------------

    #--- apparatus.py ---
    t.writeSection("APPARATUS.PY")
    #longest-word
    t.unit(t.run(apt.computeLongestWord, ['abc', 'a', 'abcd', 'abc']), \
        exp=len('abcd'))

    #sub-path
    p1 = "c:/users/chase/develop/"
    p2 = "C:\\\\Users\\\\Chase\\\\develop"
    t.unit(t.run(apt.isSubPath, p1, p2), \
        exp=False)

    #sub-path
    p1 = "c:/users/chase/develop/"
    p2 = "C:\\\\Users\\\\Chase\\\\develop/lvl1/"
    t.unit(t.run(apt.isSubPath, p1, p2), \
        exp=True)

    #sub-path
    p1 = "c:/users/chase/develop/hdl/"
    p2 = "C:\\\\Users\\\\Chase\\\\develop/lvl1/"
    t.unit(t.run(apt.isSubPath, p1, p2), \
        exp=False)

    #equal path
    p1 = "c:/users/chase/develop/"
    p2 = "C:\\\\Users\\\\Chase\\\\develop"
    t.unit(t.run(apt.isEqualPath, p1, p2), \
        exp=True)

    #equal path
    p1 = "c:/users/chase/develop/"
    p2 = "c:/users/chase/developp/"
    t.unit(t.run(apt.isEqualPath, p1, p2), \
        exp=False)

    #--- block.py ---
    t.writeSection("BLOCK.PY")
    b1 = Block(ws_path+'Block1/', ws)

    t.unit(t.run(b1.isValid), \
        exp=False)

    t.unit(t.run(b1.create, 'libraryA.Block1'), \
        exp=True)

    t.unit(t.run(b1.isValid), \
        exp=True)

    t.unit(t.run(b1.M), \
        exp='')

    t.unit(t.run(b1.L), \
        exp='libraryA')

    t.unit(t.run(b1.N), \
        exp='Block1')

    #--- vhdl.py ---
    t.writeSection("VHDL.PY")
    vhdl1 = Vhdl("./test/data/test1.vhd", block=b1)

    #get about
    exp = '''\
 File: test1.vhd
 Author: Chase Ruskin
 Description:
  Includes VHDL code to test against legoHDL functions. This initial comment block
  will also be tested to see if it is returned when getting an entity.
 Note:
  Code may be purposely written poorly to test the VHDL analysis in legoHDL.
'''
    t.unit(t.run(vhdl1.getAbout), \
        exp=exp)

    #decode package unit to test vhdl package inheritance
    sub_pkg = list(Unit.Bottle['libraryA']['inheritpkg'])[0]
    base_pkg = list(Unit.Bottle['libraryA']['genericpkg'])[0]
    t.unit(t.run(vhdl1.decode, sub_pkg), \
        sev=ts.OBSERVE)

    #verify that the generic package is identified as a required package for sub_pkg
    sub_req = sub_pkg.getReqs()[0]
    t.unit(t.run(t.isEqual, sub_req, base_pkg), \
        exp=True)


    # end unit tests -----------------------------------------------------------

    #clean test input directory
    dirs = ['input/']
    for d in dirs:
        if(os.path.exists(d)):
            shutil.rmtree(d, onerror=apt.rmReadOnly)
        pass

    #delete testing workspace
    del Workspace.Jar['testing-launch-pad']

    #[!] save file and report results
    t.summary()
    exit(t.hasFailure())


# ------------------------------------------------------------------------------
# -- TEST CLASS
# ------------------------------------------------------------------------------
class Test:
    '''
    The Test class. Creates a tracker to track all types of tests performed. 
    Outputs a log file with a report.
    '''

    class Severity(Enum):
        DEBUG    = -1
        OBSERVE  = 0
        WARNING  = 1
        ERROR    = 2
        FAILURE  = 3
        CRITICAL = 4
        pass

    #track number of testcases created
    TotalCount = 0

    #class container to store all tests
    Suite = []

    #folder to store test results
    OUTPUT = 'output/'

    #file characters to separate sections
    DIVIDER = '-'*80+'\n'

    #boolean to determine if to print log lines to console as well
    DEBUG = True


    def __init__(self, name):
        '''
        Creates a test object.

        Parameters:
            name (str): the test log file name
        Returns:
            None
        '''
        self._name = name
        #create logfile
        self._log = open(Test.OUTPUT+self._name+".log", 'w')

        #create HEADER log section
        txt = "FILE: "+self._name+".log\n"
        txt = txt + "TIME: "+str(datetime.now())+"\n"
        self.writeSection("HEADER", txt)

        #track number of test cases
        self._testcases = 0
        #track number of failures
        self._failures = 0

        #increment number of test cases
        Test.TotalCount += 1
        #add to class container
        Test.Suite += [self]

        #begin TESTS log section
        self.writeSection("TESTS")
        pass


    def hasFailure(self):
        '''Return (bool) if >= 1 failure has been logged.'''
        return (self._failures >= 1)


    def writeSection(self, title, details=""):
        '''
        Begin a new section in the logfile

        Parameters:
            title (str): section header
            details (str): optional extra text to add
        Returns:
            None
        '''
        self.log(Test.DIVIDER)
        self.log(title+'\n')
        self.log(Test.DIVIDER)
        self.log(details)
        if(len(details)):
            self.log(Test.DIVIDER)
        pass


    def summary(self):
        '''Write the log file summary stats section.'''

        self._log.write(Test.DIVIDER)
        txt = ''
        txt = txt = "TESTS         | "+str(self._testcases)+"\n"
        txt = txt + "FAILS         | "+str(self._failures)+"\n"
        txt = txt + "SUCCESS RATE  | "+str(((self._testcases-self._failures)/self._testcases)*100)+" %\n"
        self.writeSection("SUMMARY", txt)
        pass

    
    def log(self, txt):
        '''Write to logfile and may also print to console the logfile line.'''

        if(Test.DEBUG):
            print(txt,end='')
        self._log.write(txt)
        pass


    def unit(self, got, exp=None, sev=Severity.ERROR, report=''):
        '''
        Perform a unit test.
        
        Parameters:
            about (str): what is the test being performed
            funct (any): the values returned from the function
            exp (any): the values expected to return
            sev (Test.Severity): level of importance
            report (str): message to write when test fails
        Returns:
            None
        '''
        #stop timer
        t1 = time.time()
        #calculate time the function took
        delta = t1-self._t0
        delta = (str)(round(delta*1000, 4))+ " ms"

        self._testcases += 1
        self.log(self.timestamp(delta))

        name = '  "'+self._funct+'"'

        #assign default report
        if(report == ''):
            report = "EXPECTS: " + str(exp) + " " + "RECIEVED: " + str(got)
        #add tab
        report = ' -- ' + report
        #add extra tab to align with others
        if(sev != Test.Severity.CRITICAL):
            name = '\t' + name

        #only print output
        if(sev == Test.Severity.DEBUG):
            self.log(str(sev.name)+name+'\n')
            self.log(str(got))
        elif(got != exp):
            #count as a failure if worse than WARNING
            if(sev.value > 1):
                self._failures += 1
            #print message to log file
            self.log(str(sev.name)+name+report)
        else:
            self.log("SUCCESS"+name)
            pass
        
        self.log("\n")
        pass


    def isEqual(self, lhs, rhs):
        '''Return (bool) for lhs == rhs.'''
        return lhs == rhs

    
    def run(self, funct, *args, **kwargs):
        '''Start a timer and execute 'funct'. Returns the result.'''

        self._funct = funct.__name__
        self._t0 = time.time()
        return funct(*args, **kwargs)


    def timestamp(self, t_delta):
        '''Returns intial data for a logfile line.'''

        return "# "+str(self._testcases)+":\tELAPSED: "+str(t_delta)+'\t'

    pass


# ------------------------------------------------------------------------------
# -- ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main()