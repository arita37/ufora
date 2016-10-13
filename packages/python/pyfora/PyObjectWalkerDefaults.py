#   Copyright 2016 Ufora Inc.
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
import ast

import pyfora.PureImplementationMappings as PureImplementationMappings


exclude_list = ["staticmethod", "property", "__inline_fora"]

def exclude_predicate_fun(node):
    return isinstance(node, ast.Call) and \
        isinstance(node.func, ast.Name) and \
        node.func.id == 'pureMapping'

mappings = PureImplementationMappings.PureImplementationMappings()

def terminal_value_filter(terminalValue):
    return not mappings.isOpaqueModule(terminalValue)
