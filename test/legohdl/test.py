# ------------------------------------------------------------------------------
# Project: legohdl
# Script: test.py
# Author: Chase Ruskin
# Description:
#   Runs tests to verify certain functions within legoHDL.
# ------------------------------------------------------------------------------

import os, shutil, time
from datetime import datetime
from enum import Enum

from legohdl.apparatus import Apparatus as apt

# ------------------------------------------------------------------------------
# -- MAIN TESTING LAUNCH PAD
# ------------------------------------------------------------------------------
def main():
    ts = Test.Severity

    #clean and create test output directory
    if(os.path.exists("output/")):
        shutil.rmtree("output/")
    os.makedirs("output/", exist_ok=True)

    #run unit tests
    t = Test("unit-tests")

    t.unit(t.run(incBy1, input=1423), \
        exp=1424)

    t.unit(t.run(incBy1, input=10), \
        exp=11)

    t.unit(t.run(incBy1, 1), \
        exp=3, sev=ts.FAILURE)

    t.unit(t.run(apt.computeLongestWord, ['abc', 'a', 'abcd', 'abc']), \
        exp=len('abcd'))

    t.summary()

    exit(t.hasFailure())


# ------------------------------------------------------------------------------
# -- TEST CLASS
# ------------------------------------------------------------------------------
class Test:
    '''The Test class. Creates a tracker to track all types of tests performed. 
    Outputs a log file with a report.'''

    class Severity(Enum):
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
            name (str): the name of the test
        '''
        self._name = name
        #create logfile
        self._log = open(Test.OUTPUT+self._name+".log", 'w')

        #create header
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

        self.writeSection("TESTS")
        pass


    def hasFailure(self):
        '''Return (bool) if >= 1 failure has been logged.'''
        return (self._failures >= 1)


    def writeSection(self, title, details=""):
        '''
        Begin a new section in the logfile

        Parameters:
        '''
        self.log(Test.DIVIDER)
        self.log(title+'\n')
        self.log(Test.DIVIDER)
        self.log(details)
        if(len(details)):
            self.log(Test.DIVIDER)


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
        if(Test.DEBUG):
            print(txt,end='')
        self._log.write(txt)
        pass


    def unit(self, got, exp, sev=Severity.ERROR, report=''):
        '''
        Perform a unit test.
        
        Parameters:
            about (str): what is the test being performed
            funct (any): the values returned from the function
            exp (any): the values expected to return
            sev (Test.Severity): level of importance
            report (str): message to write when test fails
        Returns:
            NonE
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

        if(got != exp):
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

    
    def run(self, funct, *args, **kwargs):
        '''Run the inputted function with the arguments provided.'''

        self._funct = funct.__name__
        self._t0 = time.time()
        return funct(*args, **kwargs)


    def timestamp(self, t_delta):
        '''Returns intial data for a logfile line.'''

        return "CASE "+str(self._testcases)+":\tELAPSED: "+str(t_delta)+'\t'

    pass


# example function to test
def incBy1(input):
    '''Returns input + 1.''' 

    return int(input)+1


# ------------------------------------------------------------------------------
# -- ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main()