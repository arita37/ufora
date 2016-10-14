#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#!/usr/bin/python
"""
command-line interface to test the FORA runtime semantics

test.py 'module1.fora' 'module2.fora' ...

The tester takes a list of FORA module files on the command line.

members marked with metadata `test, or with tuple metadata (holding `test) are considered test cases.
"""

# TODO BUG anybody: when a module doesn't parse, test.py failes entirely rather than noting that the object itself fails
# TODO BUG anybody: The module parser has trouble finding other modules when test.py is not in the same directory as the .fora file being tested

#In order to control logging behavior, ufora.Native.Logging has to be
#triggered before FORA is imported. So, we set FORA to None,
#and all entrypoints are responsible for setting it when importing

import ufora.native.TCMalloc as TCMallocNative
import ufora.FORA.python.FORA as FORA
import ufora.native.FORA as ForaNative
import ufora.FORA.python.Runtime as Runtime
from ufora.FORA.python.ForaValue import FORAValue, FORAException
import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.FORA.python.ParseException as ParseException
import time
import os
import sys
import traceback
import logging
import ufora.config.Setup as Setup

testSymbol = ForaNative.makeSymbol("test")

def isTestCase(foraMemberMetadata):
    """
    given a module metadata `foraMemberMetadata`,
    return true if the member is a test case, or false otherwise.

    as described above, a test case is one in which the metadata is either `test, or
    is a tuple containing the value `test (among possibly other things)
    """
    if foraMemberMetadata is None:
        return False

    metaIVC = FORA.extractImplValContainer(foraMemberMetadata).getTupleMember("outer")

    if metaIVC is None:
        return False

    if metaIVC == testSymbol:
        return True

    if metaIVC.isTuple():
        for ix in range(len(metaIVC)):
            if metaIVC[ix] == testSymbol:
                return True

    return False

def extractModuleTestNames(foraModule):
    """
    get a a list of the module members which are test cases
    """

    moduleMembersAndMetadataDict = FORA.objectMembers(foraModule)

    tr = []

    for membername, memberMeta in moduleMembersAndMetadataDict.iteritems():
        if isTestCase(memberMeta):
            tr.append(membername)

    return tr

def sanitizeErrString(errString):
    """pack the error string into a single line of a few characters. include the beginning and end"""
    errString = errString.replace("\n", " ").replace("\t", " ")

    if len(errString) > 2500:
        errString = errString[:1250] + " ... " + errString[-1250:]
    return errString

def printTestResults(moduleName, testName, testResultWithTimes, verbose = False):
    failct = 0
    passct = 0

    result, timeElapsed = testResultWithTimes

    if result is not True:
        failct += 1

        print moduleName, ": ", testName,

        print time.strftime("%Y-%m-%d %H:%M:%S"), "--", "TEST FAILED:", moduleName, testName, ":",

        if isinstance(result, FORAException):
            print "throw", sanitizeErrString(str(result.foraVal))
        else:
            print result,
        print "is not True"

    else:
        passct += 1
        if verbose:
            print time.strftime("%Y-%m-%d %H:%M:%S"), "--", moduleName, testName, ": TEST SUCCEEDED in %2.4f" % timeElapsed, ". memory usage is ", TCMallocNative.getBytesUsed() / 1024 / 1024.0, " MB"

    return (passct, failct)

def executeFORATest(foraModule, moduleName, testname, verbose, testFunction):
    try:
        if verbose:
            print time.strftime("%Y-%m-%d %H:%M:%S"), "--", moduleName, testname, ": TEST STARTING"

        return testFunction(foraModule, moduleName, testname)


    except FORAException as e:
        return e

def testModuleStr(modulePath, verbose, delay, testFilter, testFunction):
    """parse text in moduleText into a FORA module and execute tests within"""
    try:
        foraModule = FORA.importModule(modulePath)
    except ParseException.ParseException as parseException:
        print "Failed to import module %s: %s" % (modulePath, parseException)
        return (0, 1)

    moduleName = os.path.split(modulePath)[-1]
    testNames = extractModuleTestNames(foraModule)

    allPassed = 0
    allFailed = 0

    for testName in testNames:
        if testFilter is None or testFilter(modulePath, testName):
            time.sleep(delay)

            t0 = time.time()
            testResults = []

            testResultWithTimes = (executeFORATest(foraModule, moduleName, testName, verbose, testFunction), time.time() - t0)

            passed, failed = printTestResults(
                moduleName,
                testName,
                testResultWithTimes,
                verbose
                )

            allPassed += passed
            allFailed += failed

    return (allPassed, allFailed)

def executeForaCode(module, moduleName, testName):
    return getattr(module, testName)

def makeJovt(*args):
    return ForaNative.JOVListToJOVT(list(args))

def symbolJov(sym):
    return ForaNative.parseStringToJOV("`" + sym)

def dumpReasonerSummary(moduleName, testName, reasoner, frame):
    allFrames = set()
    unknownWithStacks = []

    def checkFrame(frame, curStack=()):
        if frame in allFrames:
            return
        allFrames.add(frame)
        if len(frame.unknownApplyNodes()) > 0:
            unknownWithStacks.append({'frame':frame,'stack':curStack})

        for subframe in reasoner.subframesFor(frame).values():
            checkFrame(subframe, curStack + (frame,))

    checkFrame(frame)

    reachableFrames = len(allFrames)
    allFrameCount = reasoner.totalFrameCount()
    badApplyNodes = 0

    def replaceWhitespace(s):
        s = s.replace('\t',' ').replace('\n',' ')
        while True:
            s2 = s.replace('  ', ' ')
            if s == s2:
                return s
            s = s2


    for frameAndStack in unknownWithStacks:
        frame = frameAndStack['frame']
        stack = frameAndStack['stack']
        badApplyNodes += len(frame.unknownApplyNodes())
        print "Found ", len(frame.unknownApplyNodes()), " in "
        for f in stack + (frame,):
            print "\t", replaceWhitespace(f.graph().graphName + " " + str(f.entryJOVs()))

    if badApplyNodes:
        print "%s.%s reaching %s of %s frames with %s bad nodes." % (moduleName, testName, reachableFrames, allFrameCount, badApplyNodes)


reasoner = [None]
compiler = [None]
def reasonAboutForaCode(module, moduleName, testName):
    if reasoner[0] is None:
        runtime = Runtime.getMainRuntime()
        axioms = runtime.getAxioms()
        compiler[0] = runtime.getTypedForaCompiler()
        instructionGraph = runtime.getInstructionGraph()
        reasoner[0] = ForaNative.SimpleForwardReasoner(compiler[0], instructionGraph, axioms)

    moduleJOV = ForaNative.JudgmentOnValue.Constant(module.implVal_)

    t0 = time.time()
    frame = reasoner[0].reasonAboutApply(makeJovt(moduleJOV, symbolJov("Member"), symbolJov(testName)))
    print "reasoning ", moduleName + "." + testName, " took ", time.time() - t0

    dumpReasonerSummary(moduleName, testName, reasoner[0], frame)

    return True

def test(verbose = False, testFilter=None, reasoning=False):
    """use all .fora files in this directory to generate a single unit test.

    returns 1 on failure, 0 on success

    testFilter - a function from modulename and testname to a bool indicating whether to test
    """
    numPassed = 0
    numFailed = 0

    curdir = os.path.split(__file__)[0]
    t0 = time.time()

    for f in sorted(os.listdir(curdir)):
        if f.endswith(".fora"):
            passed, failed = testModuleStr(
                os.path.join(curdir, f),
                verbose,
                0.0,
                testFilter,
                executeForaCode if not reasoning else reasonAboutForaCode
                )

            numPassed += passed
            numFailed += failed

    print "FORA SEMANTIC TESTS EXECUTED. %d passed, %d failed." % (numPassed, numFailed),
    print " in ", time.time() - t0

    time.sleep(.5)

    if numFailed > 0:
        return 1
    return 0

