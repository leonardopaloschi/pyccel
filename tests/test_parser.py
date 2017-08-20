# coding: utf-8

"""
.. todo:
    - no need to declare a variable, if it is defined by assignment. ex: 'x=1'
    means that x is of type double. this must be done automatically.
"""

from pyccel.parser  import PyccelParser, get_by_name
from pyccel.syntax import ( \
                           # statements
                           DeclarationStmt, \
                           DelStmt, \
                           PassStmt, \
                           AssignStmt, \
                           IfStmt, ForStmt)

# ... creates an instance of Pyccel parser
pyccel = PyccelParser()
# ...

# ...
def test_Assign(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "double  a,b" + "\n"
    stmts += "x=1"       + "\n"
    stmts += "y=2*3+1"   + "\n"
    stmts += "x=a"       + "\n"
    stmts += "y=2*a+b"   + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            if isinstance(stmt, DeclarationStmt):
                print "declared variable : ", stmt.variables
            if isinstance(stmt, AssignStmt):
                print "lhs : ", stmt.lhs, "     rhs: ", stmt.rhs.expr
    # ...

    return ast
# ...

# ...
def test_Declare(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "double x,y" + "\n"
    stmts += "double z"   + "\n"
    stmts += "int  n"   + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            if isinstance(stmt, DeclarationStmt):
                print stmt.variables
    # ...

    return ast
# ...

# ...
def test_Del(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "double b" + "\n"
    stmts += "del b"   + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            print stmt.expr
    # ...

    return ast
# ...

# ...
def test_Flow(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "raise"    + "\n"
    stmts += "break"    + "\n"
    stmts += "continue" + "\n"
    stmts += "return True"   + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            print type(stmt)
    # ...

    return ast
# ...

# ...
def test_For(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "for i in range(0,10):" + "\n"
    stmts += "indent"                + "\n"
    stmts += "x=1;"                  + "\n"
    stmts += "y=x+1"                 + "\n"
    stmts += "dedent"                + "\n"

#    stmts += "for j in range(a,b):" + "\n"
#    stmts += "x=1"                + "\n"
#    stmts += "end"                   + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            if isinstance(stmt, DeclarationStmt):
                print "declared variable : ", stmt.variables
            if isinstance(stmt, ForStmt):
                print stmt.expr
    # ...

    return ast
# ...

# ...
def test_FunctionDef(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
#    stmts += "def f(x,y):"   + "\n"
#    stmts += "indent"        + "\n"
#    stmts += "z = x+y"       + "\n"
#    stmts += "dedent"        + "\n"

    stmts += "def f(x,y):"   + "\n"
    stmts += "indent"        + "\n"
    stmts += "z = x+y;"       + "\n"
    stmts += "return z"        + "\n"
    stmts += "dedent"        + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            print type(stmt)
            e = stmt.expr
    # ...

    return ast
# ...

# ... TODO for the moment, intructions must be splitted by ";"
#          => \n is not recognized
def test_If(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "double  a,b" + "\n"
    stmts += "if a==1:"  + "\n"
    stmts += "indent"                + "\n"
    stmts += "b=a+1;"    + "\n"
#    stmts += "b=a+1; a=b+a"   + "\n"
#    stmts += ";"   + "\n"
    stmts += "a=b*a"     + "\n"
    stmts += "dedent"                + "\n"
    stmts += "else:"     + "\n"
    stmts += "indent"                + "\n"
    stmts += "a=b*a"     + "\n"
    stmts += "dedent"                + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            if isinstance(stmt, DeclarationStmt):
                print "declared variable : ", stmt.variables
            if isinstance(stmt, AssignStmt):
                print "lhs : ", stmt.lhs, "     rhs: ", stmt.rhs.expr
            if isinstance(stmt, IfStmt):
#                print "body_true : ", stmt.body_true, "     body_false: ", stmt.body_false
                print stmt.expr
    # ...

    return ast
# ...

# ...
def test_Import(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "from numpy import zeros" + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            print type(stmt)
            print stmt.dotted_name.names, stmt.import_as_names.names
    # ...

    return ast
# ...

# ...
def test_Numpy(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "x1 = zeros(shape=3)"          + "\n"
    stmts += "y = x1[1]"                    + "\n"
#    stmts += "x2 = zeroslike(x1)"     + "\n"
#    stmts += "x3 = ones(3)"           + "\n"
#    stmts += "x4 = linspace(0,1,100)" + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            print type(stmt)
    # ...

    return ast
# ...

# ...
def test_Pass(verbose=False):
    # ... parse the Pyccel code
    stmts  = ""
    stmts += "pass" + "\n"

    ast = pyccel.parse(stmts)

    if verbose:
        for stmt in ast.statements:
            print type(stmt)
    # ...

    return ast
# ...

######################################
if __name__ == "__main__":
#    test_Assign(verbose=True)
#    test_Declare(verbose=True)
#    test_Del(verbose=True)
#    test_Flow(verbose=True)
#    test_For(verbose=True)
#    test_FunctionDef(verbose=True)
#    test_If(verbose=True)
#    test_Import(verbose=True)
    test_Numpy(verbose=True)
#    test_Pass(verbose=True)