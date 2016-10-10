/***************************************************************************
   Copyright 2016 Ufora Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
****************************************************************************/
#pragma once

#include <Python.h>

#include <string>
#include <utility>


class PyAstUtil {
public:
    static std::pair<std::string, std::string> sourceFilenameAndText(PyObject*);
    static long startingSourceLine(PyObject*);

    /*
      These Next three functions (wich return PyObject*) return new references
      to objects, or NULL in the case of error conditions. All of them call
      PyObject_CallMethodObjArgs, so in the case of error conditions, they set an
      error string.
     */
    static PyObject* pyAstFromText(const std::string& fileText);
    static PyObject* pyAstFromText(PyObject* pyString);
    static PyObject* functionDefOrLambdaAtLineNumber(PyObject* obj, long sourceLine);
    static PyObject* classDefAtLineNumber(PyObject* obj, long sourceLine);
    static PyObject* withBlockAtLineNumber(PyObject* obj, long sourceLine);
    static PyObject* collectDataMembersSetInInit(PyObject* pyObject);

    static bool hasReturnInOuterScope(PyObject* pyAst);
    static bool hasYieldInOuterScope(PyObject* pyAst);

private:
    // singleton instance
    static PyAstUtil& _getInstance() {
        static PyAstUtil instance;
        return instance;
        }

    // implement, but keep private for singleton pattern
    PyAstUtil();
    // don't implement for these next two methods for the singleton pattern
    PyAstUtil(const PyAstUtil&);
    void operator=(const PyAstUtil&);

    void _initPyAstUtilModule();
    void _initGetSourceFilenameAndTextFun();
    void _initGetSourceLinesFun();
    void _initPyAstFromTextFun();
    void _initFunctionDefOrLambdaAtLineNumberFun();
    void _initClassDefAtLineNumberFun();

    // no checking is done on the argument here.
    // it MUST be a non-null PyString
    static PyObject* _pyAstFromText(PyObject* pyString);

    PyObject* mPyAstUtilModule;
    PyObject* mGetSourceFilenameAndTextFun;
    PyObject* mGetSourceLinesFun;
    PyObject* mPyAstFromTextFun;
    PyObject* mFunctionDefOrLambdaAtLineNumberFun;
    PyObject* mClassDefAtLineNumberFun;
};
