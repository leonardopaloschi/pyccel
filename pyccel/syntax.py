# coding: utf-8
import numpy as np
from numpy import ndarray
from numpy import asarray

from ast import literal_eval

from sympy.core.containers import Tuple
from sympy import Symbol, sympify, Integer, Float, Add, Mul
from sympy import true, false,pi
from sympy.tensor import Idx, Indexed, IndexedBase
from sympy.core.basic import Basic
from sympy.core.relational import Eq, Ne, Lt, Le, Gt, Ge
from sympy.core.power import Pow
from sympy.core.function import Function
from sympy import preorder_traversal
from sympy import (Abs,sqrt,sin,cos,exp,log,csc, cos, \
                   sec, tan, cot, asin, acsc, acos, asec, atan,\
                   acot, atan2,factorial)

from pyccel.types.ast import DataType
from pyccel.types.ast import (For, Assign, Declare, Variable, \
                              datatype, While, NativeFloat, \
                              EqualityStmt, NotequalStmt, \
                              Argument, InArgument, InOutArgument, \
                              MultiAssign, OutArgument, Result, \
                              FunctionDef, Import, Print, \
                              Comment, AnnotatedComment, \
                              IndexedVariable, Slice, If, \
                              ThreadID, ThreadsNumber, \
                              Rational, NumpyZeros, NumpyLinspace, \
                              Stencil,ceil,Break, \
                              NumpyOnes, NumpyArray, LEN, Dot, Min, Max,SIGN,IndexedElement,\
                              GOrEq,LOrEq,Lthan,Gter)

DEBUG = False
#DEBUG = True

# TODO: 1. check that every stmt is well implementing
#          the local_vars and stmt_vars properties.

__all__ = ["Pyccel", \
           "Expression", "Term", "Operand", \
           "FactorSigned", "FactorUnary", "FactorBinary", \
           # statements
           "AssignStmt", "MultiAssignStmt", "DeclarationStmt", \
           # compound stmts
           "ForStmt", "IfStmt", "SuiteStmt", \
           # Flow statements
           "FlowStmt", "BreakStmt", "ContinueStmt", \
           "RaiseStmt", "YieldStmt", "ReturnStmt", \
           "DelStmt", "PassStmt", "FunctionDefStmt", \
           "ImportFromStmt", \
           "ConstructorStmt", \
           "CommentStmt", \
           "EvalStmt", \
           # Multi-threading
           "ThreadStmt", \
           "StencilStmt", \
           # python standard library statements
           "PythonPrintStmt", \
           # Test
           "Test", "OrTest", "AndTest", "NotTest", "Comparison", \
           # Trailers
           "ArgList", \
           "Trailer", "TrailerArgList", "TrailerSubscriptList", \
           "TrailerSlice", "TrailerSliceRight", "TrailerSliceLeft"
           ]


# Global variable namespace
namespace    = {}
stack        = {}
settings     = {}
variables    = {}
declarations = {}

namespace["True"]  = true
namespace["False"] = false
namespace["pi"]    = pi

# ... builtin types
builtin_types  = ['int', 'float', 'double', 'complex']
# ...

# ... builtin functions
builtin_funcs_math_un = ['abs', 'sqrt', 'exp', 'log', \
                         'cos', 'sin', 'tan', 'cot', \
                         'asin', 'acsc', 'acos', \
                         'asec', 'atan', 'acot', \
                         'atan2','csc', 'sec', 'ceil' \
                        ]
builtin_funcs_math_bin = ['dot']
builtin_funcs_math = builtin_funcs_math_un + \
                     builtin_funcs_math_bin

builtin_funcs  = ['zeros', 'ones', 'array']
builtin_funcs += builtin_funcs_math
# ...

# TODO add kwargs
def builtin_function(name, args, lhs=None):
    """
    User friendly interface for builtin function calls.

    name: str
        name of the function
    args: list
        list of arguments
    lhs: str
        name of the variable to assign to
    """
    # ...
    def get_arguments():
        # TODO appropriate default type
        dtype = 'float'
        allocatable = True
        shape = []
        for i in args:
            if isinstance(i, DataType):
                dtype = i
            elif isinstance(i, Tuple):
                shape = [j for j in i]
            else:
                # TODO further check
                shape.append(i)
        rank = len(shape)
        if rank == 1:
            shape = shape[0]

        d_var = {}
        d_var['datatype'] = dtype
        d_var['allocatable'] = allocatable
        d_var['shape'] = shape
        d_var['rank'] = rank

        return d_var
    # ...

    # ...
    def get_arguments_array():
        # TODO appropriate default type
        dtype = 'float'
        allocatable = True
        for i in args:
            if isinstance(i, DataType):
                dtype = i
            elif isinstance(i, Tuple):
                arr = [j for j in i]
            else:
                raise TypeError("Expecting a Tuple or DataType.")
        arr = asarray(arr)
        shape = arr.shape
        rank = len(shape)

        d_var = {}
        d_var['datatype'] = dtype
        d_var['allocatable'] = allocatable
        d_var['shape'] = shape
        d_var['rank'] = rank

        return d_var, arr
    # ...

    # ...
    if name == "zeros":
        if not lhs:
            raise ValueError("Expecting a lhs.")
        d_var = get_arguments()
        insert_variable(lhs, **d_var)
        return NumpyZeros(lhs, d_var['shape'])
    elif name == "ones":
        if not lhs:
            raise ValueError("Expecting a lhs.")
        d_var = get_arguments()
        insert_variable(lhs, **d_var)
        return NumpyOnes(lhs, d_var['shape'])
    elif name == "array":
        if not lhs:
            raise ValueError("Expecting a lhs.")
        d_var, arr = get_arguments_array()
        insert_variable(lhs, **d_var)
        return NumpyArray(lhs, arr, d_var['shape'])
    elif name == "dot":
        if lhs is None:
            return Dot(*args)
        else:
            d_var = {}
            # TODO get dtype from args
            d_var['datatype'] = 'float'
            insert_variable(lhs, **d_var)
            expr = Dot(*args)
            return Assign(Symbol(lhs), expr)
    elif name in builtin_funcs_math_un:
        func = eval(name)
        if lhs is None:
            return func(*args)
        else:
            d_var = {}
            # TODO get dtype from args
            d_var['datatype'] = 'float'
            insert_variable(lhs, **d_var)
            expr = func(*args)
            return Assign(Symbol(lhs), expr)
    else:
        raise ValueError("Expecting a builtin function.")
    # ...

def Check_type(var_name,expr):
    datatype='int'
    rank=0
    allocatable=False
    shape=[]
    s=[]
    def pre(expr):

        if(type(expr)==Indexed) or type(expr)==IndexedElement:
            element=list([expr.args[i] for i in range(0,len(expr.args))])
            s.append(element)
            return


        elif len(expr.args)==0:
            s.append(expr)
        for arg in expr.args:
            pre(arg)

    pre(expr.expr)
    if isinstance(expr,Expression):
        for i in s:
            if isinstance(i,list):
                if isinstance(i[0],IndexedVariable)and isinstance(variables[str(i[0])].dtype,NativeFloat):
                         datatype='float'
                if  variables[str(i[0])].allocatable:
                    allocatable=True
                import numpy as np
                anySlice=[isinstance(i[j],Slice) for j in range(1,len(i))]
                SliceIndex=np.where(anySlice)[0]
                temp1=variables[str(i[0])].shape
                for j in SliceIndex:
                    slice_start=i[j+1].start
                    slice_end=i[j+1].end
                    if i[j+1].start==None:
                        slice_start=0
                    if i[j+1].end==None:
                        if isinstance(temp1,(list,tuple)):
                            slice_end=temp1[j]
                        else:
                            slice_end=temp1
                    i[j+1]=Slice(slice_start,slice_end)

                    if not variables[str(i[0])].shape==None:

                            if isinstance(temp1,(tuple,list)):
                                rank=len(temp1)
                                if all(i[k+1].start>=0 and i[k+1].end<=temp1[k] for k in SliceIndex):
                                   shape.append(tuple([i[k+1].end-i[k+1].start for k in SliceIndex]))
                                else:
                                    raise TypeError('dimension mismatch')
                            elif isinstance(temp1,int):
                                if i[1].start>=0 and i[1].end<=temp1:
                                    shape.append(i[1].end-i[1].start)
                                else:
                                    raise TypeError('dimension mismatch')
                            else:
                                raise TypeError('shape must be an int or a tuple of int')
                    else:
                         raise TypeError('variable doesnt have a shape')
            elif isinstance(i,Symbol):

                if isinstance(variables[str(i)].dtype,NativeFloat):
                    datatype='float'
                if  variables[str(i)].allocatable:
                    allocatable=True
                if not variables[str(i)].shape==None:
                    shape.append(variables[str(i)].shape)
            elif i.is_real and not i.is_integer:
                    datatype='float'
    name=sympify(var_name)
    if len(shape)>0:
        if all(x==shape[0] for x in shape):
            shape=shape[0]

            if isinstance(shape,(tuple,list)):
                s=[]
                for i in shape:
                    try:
                        s.append(int(i))
                    except:
                        s.append(i)

                shape=tuple(s)
                rank=len(shape)
            elif isinstance(shape,int):
                rank=1
            elif isinstance(shape,Symbol) or isinstance(shape,Integer) :
                if shape.is_integer:
                    rank=1
                    shape=int(shape)
        else:
            raise TypeError('shape are not equal')

    else:
        shape=None

    return {'datatype':datatype,'name':name , 'rank':rank, 'allocatable':allocatable,'shape':shape}

def insert_variable(var_name, \
                    datatype=None, \
                    rank=None, \
                    allocatable=None, \
                    shape=None, \
                    is_argument=False, \
                    var=None):
    """
    Inserts a variable as a symbol into the namespace. Appends also its
    declaration and the corresponding variable.

    var_name: str
        variable name

    datatype: str
        datatype variable attribut. One among {'int', 'float', 'complex'}

    allocatable: bool
        if True then the variable needs memory allocation.

    rank: int
        if rank > 0, then the variable is an array

    shape: int or list of int
        shape of the array.

    is_argument: bool
        if the variable is a function argument.

    var: pyccel.types.ast.Variable
        if attributs are not given, then var must be provided.
    """
    if type(var_name) in [int, float]:
        return

    if DEBUG:
        print ">>> trying to insert : ", var_name
        txt = '    datatype={0}, rank={1}, allocatable={2}, shape={3}, is_argument={4}'\
                .format(datatype, rank, allocatable, shape, is_argument)
        print txt

    if var_name in namespace:
        var = variables[var_name]
        if datatype is None:
            datatype = var.dtype
        if rank is None:
            rank = var.rank
        if allocatable is None:
            allocatable = var.allocatable
        if shape is None:
            shape = var.shape
        if isinstance(var, InArgument):
            is_argument = True
    else:
        if datatype is None:
            datatype = 'float'
        if rank is None:
            rank = 0
        if allocatable is None:
            allocatable = False

    is_integer = (datatype == 'int')

    # we first create a sympy symbol
    s = Symbol(var_name, integer=is_integer)

    # we create a variable (for annotation)
    if not is_argument:
        var = Variable(datatype, s, \
                       rank=rank, \
                       allocatable=allocatable, \
                       shape=shape)
    else:
        var = InArgument(datatype, s, \
                         rank=rank, \
                         allocatable=allocatable, \
                         shape=shape)

    # we create a declaration for code generation
    dec = Declare(datatype, var)

    if var_name in namespace:
        namespace.pop(var_name)
        variables.pop(var_name)
        declarations.pop(var_name)

    namespace[var_name]    = s
    variables[var_name]    = var
    declarations[var_name] = dec

# ...
# TODO: refactoring
def do_arg(a):
    if isinstance(a, str):
        arg = Symbol(a, integer=True)
    elif isinstance(a, (Integer, Float)):
        arg = a
    elif isinstance(a, Expression):
        arg = a.expr
        if isinstance(arg, Symbol):
            arg = Symbol(arg.name, integer=True)
        else:
            arg = convert_to_integer_expression(arg)
    else:
        raise Exception('Wrong instance in do_arg')

    return arg
# ...

# ...
def is_integer_expression(expr):
    """
    Determines if an expression is an integer expression.
    We check if there is an integer Symbol.

    expr: sympy.expression
        a sympy expression
    """
    for arg in preorder_traversal(expr):
        if isinstance(arg, Symbol):
            if arg.is_integer:
                return True
    return False
# ...

# ...
def convert_to_integer_expression(expr):
    """
    converts an expression to an integer expression.
    this function replaces the float numbers like 1.0 to 1

    expr: sympy.expression
        a sympy expression
    """
    numbers = []
    for arg in preorder_traversal(expr):
        if isinstance(arg, Float):
            numbers.append(arg)
    e = expr
    for n in numbers:
        e = e.subs(n, int(n))
    return e
# ...

# ...
def is_Float(s):
    """
    returns True if the string s is a float number.

    s: str, int, float
        a string or a number
    """
    try:
        float(s)
        return True
    except:
        return False
# ...

# ...
def convert_numpy_type(dtype):
    """
    convert a numpy type to standard python type that are understood by the
    syntax.

    dtype: int, float, complex
        a numpy datatype
    """
    # TODO improve, numpy dtypes are int64, float64, ...
    if dtype == int:
        datatype = 'int'
    elif dtype == float:
        datatype = 'float'
    elif dtype == complex:
        datatype = 'complex'
    else:
        raise TypeError('Expecting int, float or complex for numpy dtype.')
    return datatype
# ...

# ...
class Pyccel(object):
    """Class for Pyccel syntax."""

    def __init__(self, **kwargs):
        """
        Constructor for Pyccel.

        Parameters
        ==========
        statements : list
            list of parsed statements.
        """
        self.statements = kwargs.pop('statements', [])

        # ... reset global variables
        namespace    = {}
        stack        = {}
        settings     = {}
        variables    = {}
        declarations = {}

        namespace["True"]  = true
        namespace["False"] = false
        namespace["pi"]    = pi
        # ...

    @property
    def declarations(self):
        """
        Returns the list of all declarations using objects from pyccel.types.ast
        """
        d = {}
        for key,dec in declarations.items():
            if not(isinstance(dec, Argument)):
                d[key] = dec
        return d

class BasicStmt(object):
    """
    Base class for all objects in Pyccel.
    """

    def __init__(self, **kwargs):
        """
        Constructor for the base class.

        Conventions:

        1) Every extension class must provide the properties stmt_vars and
        local_vars
        2) stmt_vars describes the list of all variables that are
        created by the statement.
        3) local_vars describes the list of all local variables to the
        statement, like the index of a For statement.
        4) Every extension must implement the update function. This function is
        called to prepare for the applied property (for example the expr
        property.)

        Parameters
        ==========
        statements : list
            list of statements from pyccel.types.ast
        """
        self.statements = []

    @property
    def declarations(self):
        """
        Returns all declarations related to the current statement by looking
        into the global dictionary declarations. the filter is given by
        stmt_vars and local_vars, which must be provided by every extension of
        the base class.
        """
        return [declarations[v] for v in self.stmt_vars + self.local_vars]

    @property
    def local_vars(self):
        """must be defined by the statement."""
        return []

    @property
    def stmt_vars(self):
        """must be defined by the statement."""
        return []

    def update(self):
        pass

class ConstructorStmt(BasicStmt):
    """
    Class representing a Constructor statement.

    Constructors are used to mimic static typing in Python.
    """
    def __init__(self, **kwargs):
        """
        Constructor for the Constructor statement class.

        Parameters
        ==========
        lhs: str
            variable to construct
        constructor: str
            a builtin constructor
        """
        self.lhs         = kwargs.pop('lhs')
        self.constructor = kwargs.pop('constructor')

        super(ConstructorStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the Constructor statement by inserting the lhs variable in the
        global dictionaries.
        """
        var_name    = str(self.lhs)
        constructor = str(self.constructor)
        # TODO improve
        if constructor in ["array_1", "array_2", "array_3"]:
            if constructor == "array_2":
                rank = 2
                datatype = 'float'
            elif constructor == "array_3":
                rank = 3
                datatype = 'float'
            else:
                rank = 1
                datatype = 'float'
        else:
            rank     = 0
            datatype = constructor
        insert_variable(var_name, datatype=datatype, rank=rank)
        return Comment("")

class DeclarationStmt(BasicStmt):
    """Class representing a declaration statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the declaration statement.

        Parameters
        ==========
        variables_names: list of str
            list of variable names.
        datatype: str
            datatype of the declared variables.
        """
        self.variables_name = kwargs.pop('variables')
        self.datatype = kwargs.pop('datatype')

        raise Exception("Need to be updated! not used anymore.")

        super(DeclarationStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the declaration statement. This property will return a list of
        declarations statements.
        """
        datatype = str(self.datatype)
        decs = []
        # TODO depending on additional options from the grammar
        for var in self.variables:
            dec = InArgument(datatype, var.expr)
            decs.append(Declare(datatype, dec))

        self.update()

        return decs

# TODO: improve by creating the corresponding object in pyccel.types.ast
class DelStmt(BasicStmt):
    """Class representing a delete statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the Delete statement class.

        Parameters
        ==========
        variables: list of str
            variables to delete
        """
        self.variables = kwargs.pop('variables')

        super(DelStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the Delete statement by returning a pyccel.types.ast object
        """
        lines = []
        for var in self.variables:
            if var in namespace:
                namespace.pop(var)
            elif var in stack:
                stack.pop(var)
            else:
                raise Exception('Unknown variable "{}" at position {}'
                                .format(var, self._tx_position))

            line = "del " + str(var)
            lines.append(line)

        self.update()

        return lines

# TODO: improve by creating the corresponding object in pyccel.types.ast
class PassStmt(BasicStmt):
    """Class representing a Pass statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the Pass statement class.

        Parameters
        ==========
        label: str
            label must be equal to 'pass'
        """
        self.label = kwargs.pop('label')

        super(PassStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the Delete statement by returning a pyccel.types.ast object
        """
        self.update()

        return self.label

#class ElifStmt(BasicStmt):
#    """Class representing an Elif statement."""
#
#    def __init__(self, **kwargs):
#        """
#        Constructor for the Elif statement class.
#        This class does not have the expr property,
#        since it is used inside the IfStmt
#
#        Parameters
#        ==========
#        body: list
#            statements tree as given by the textX, for the true block (if)
#        test: Test
#            represents the condition for the Elif statement.
#        """
#        self.body = kwargs.pop('body')
#        self.test = kwargs.pop('test')
#
#        super(ElifStmt, self).__init__(**kwargs)
#
#    @property
#    def stmt_vars(self):
#        """Returns the statement variables."""
#        ls = []
#        for stmt in self.body.stmts:
#            ls += stmt.local_vars
#            ls += stmt.stmt_vars
#        return ls

# TODO: improve by allowing for the elif statements
class IfStmt(BasicStmt):
    """Class representing an If statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the If statement class.

        Parameters
        ==========
        body_true: list
            statements tree as given by the textX, for the true block (if)
        body_false: list
            statements tree as given by the textX, for the false block (else)
        body_elif: list
            statements tree as given by the textX, for the elif blocks
        test: Test
            represents the condition for the If statement.
        """
        self.body_true  = kwargs.pop('body_true')
        self.body_false = kwargs.pop('body_false', None)
        self.body_elif  = kwargs.pop('body_elif',  None)
        self.test       = kwargs.pop('test')

        super(IfStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """Returns the statement variables."""
        ls = []
        for stmt in self.body_true.stmts:
            ls += stmt.local_vars
            ls += stmt.stmt_vars
        if not self.body_false==None:
            for stmt in self.body_false.stmts:
                ls += stmt.local_vars
                ls += stmt.stmt_vars
        if not self.body_elif==None:
            for elif_block in self.body_elif:
                for stmt in elif_block.body.stmts:
                    ls += stmt.local_vars
                    ls += stmt.stmt_vars
        return ls

    @property
    def expr(self):
        """
        Process the If statement by returning a pyccel.types.ast object
        """
        self.update()

        args = [(self.test.expr, self.body_true.expr)]

        if not self.body_elif==None:
            for elif_block in self.body_elif:
                args.append((elif_block.test.expr, elif_block.body.expr))

        if not self.body_false==None:
            args.append((True, self.body_false.expr))

        return If(*args)

class AssignStmt(BasicStmt):
    """Class representing an assign statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the Assign statement.

        Parameters
        ==========
        lhs: str
            variable to assign to
        rhs: Expression
            expression to assign to the lhs
        trailer: Trailer
            a trailer is used for a function call or Array indexing.
        """
        self.lhs     = kwargs.pop('lhs')
        self.rhs     = kwargs.pop('rhs')
        self.trailer = kwargs.pop('trailer', None)

        super(AssignStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """Statement variables."""
        return [self.lhs]

    def update(self):
        """
        Update before processing the Assign statement
        """
        # TODO default type?
        datatype = 'float'
#        datatype = 'int'
        if isinstance(self.rhs, Expression):
            expr = self.rhs
            symbols = set([])
            if isinstance(expr, Basic):
                symbols = expr.free_symbols

            for s in symbols:
                if s.name in namespace:
                    if s.is_integer:
                        datatype = 'int'
                        break
                    elif s.is_Boolean:
                        datatype = 'bool'
                        break

        var_name = self.lhs
        if not(var_name in namespace):
#            if DEBUG:
            if True:
                print("> Found new variable " + var_name)

            # TODO check if var is a return value
            rank = 0
            d_var=Check_type(self.lhs,self.rhs)
            insert_variable(var_name,rank=d_var['rank'],
                            datatype=d_var['datatype'],
                            allocatable=d_var['allocatable'],
                            shape=d_var['shape'])


    @property
    def expr(self):
        """
        Process the Assign statement by returning a pyccel.types.ast object
        """
        if isinstance(self.rhs, Expression):
            rhs = self.rhs.expr

            if isinstance(rhs, Function):
                name = str(type(rhs).__name__)
                if name in builtin_funcs:
                    args = rhs.args
                    return builtin_function(name, args, lhs=self.lhs)
                else:
                    name = str(type(rhs).__name__)
                    F = namespace[name]
                    f_expr = F.expr
                    results = f_expr.results
                    result = results[0]
                    insert_variable(self.lhs, \
                                    datatype=result.dtype, \
                                    allocatable=result.allocatable, \
                                    shape=result.shape, \
                                    rank=result.rank)
        else:
            rhs = sympify(self.rhs)

        if self.trailer is None:
            l = sympify(self.lhs)
        else:
            args = self.trailer.expr
            l = IndexedVariable(str(self.lhs))[args]

        l = Assign(l, rhs)

        self.update()
        return l

class MultiAssignStmt(BasicStmt):
    """
    Class representing multiple assignments.
    In fortran, this correspondans to the call of a subroutine.
    """
    def __init__(self, **kwargs):
        """
        Constructor for the multi Assign statement.

        Parameters
        ==========
        lhs: list of str
            variables to assign to
        name: str
            function/subroutine name
        trailer: Trailer
            a trailer is used for a function call or Array indexing.
        """
        self.lhs     = kwargs.pop('lhs')
        self.name    = kwargs.pop('name')
        self.trailer = kwargs.pop('trailer', None)

        super(MultiAssignStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """Statement variables."""
        return self.lhs

    def update(self):
        """
        Update before processing the MultiAssign statement
        """
        datatype = 'float'
        name = str(self.name)
        if not(name in namespace):
            raise Exception('Undefined function/subroutine {}'.format(name))
        else:
            F = namespace[name]
            if not(isinstance(F, FunctionDefStmt)):
                raise Exception('Expecting a {0} for {1}'.format(type(F), name))

        for var_name in self.lhs:
            if not(var_name in namespace):
                if DEBUG:
                    print("> Found new variable " + var_name)

                # TODO get info from FunctionDefStmt
                rank = 0
                insert_variable(var_name, datatype=datatype, rank=rank)

    @property
    def expr(self):
        """
        Process the MultiAssign statement by returning a pyccel.types.ast object
        """
        self.update()
        lhs = self.lhs
        rhs = self.name
        if not(self.trailer is None):
            args = self.trailer.expr
        else:
            raise Exception('Expecting a trailer')

        return MultiAssign(lhs, rhs, args)

class ForStmt(BasicStmt):
    """Class representing a For statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the For statement.

        Parameters
        ==========
        iterable: str
            the iterable variable
        start: str
            start index
        end: str
            end index
        step: str
            step for the iterable. if not given, 1 will be used.
        body: list
            a list of statements for the body of the For statement.
        """
        self.iterable = kwargs.pop('iterable')
        self.start    = kwargs.pop('start')
        self.end      = kwargs.pop('end')
        self.step     = kwargs.pop('step', None)
        self.body     = kwargs.pop('body')

        super(ForStmt, self).__init__(**kwargs)

    @property
    def local_vars(self):
        """Local variables of the For statement."""
        return [self.iterable]

    @property
    def stmt_vars(self):
        """Statement variables."""
        ls = []
        for stmt in self.body.stmts:
            ls += stmt.local_vars
            ls += stmt.stmt_vars
        return ls

    def update(self):
        """
        Update before processing the statement
        """
        # check that start and end were declared, if they are symbols
        insert_variable(self.iterable, datatype='int')

    @property
    def expr(self):
        """
        Process the For statement by returning a pyccel.types.ast object
        """
        i = Symbol(self.iterable, integer=True)

        if self.start in namespace:
            b = namespace[self.start]
        else:
            b = do_arg(self.start)

        if self.end in namespace:
            e = namespace[self.end]
        else:
            e = do_arg(self.end)

        if self.step is None:
            s = 1
        else:
            if self.step in namespace:
                s = namespace[self.step]
            else:
                s = do_arg(self.step)

        self.update()

        body = self.body.expr

        return For(i, (b,e,s), body)

class WhileStmt(BasicStmt):
    """Class representing a While statement."""

    def __init__(self, **kwargs):
        """
        Constructor for the While statement.

        Parameters
        ==========
        test: Test
            a test expression
        body: list
            a list of statements for the body of the While statement.
        """
        self.test = kwargs.pop('test')
        self.body = kwargs.pop('body')

        super(WhileStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """Statement variables."""
        ls = []
        for stmt in self.body.stmts:
            ls += stmt.local_vars
            ls += stmt.stmt_vars
        return ls

    @property
    def expr(self):
        """
        Process the While statement by returning a pyccel.types.ast object
        """
        test = self.test.expr

        self.update()

        body = self.body.expr

        return While(test, body)

class ExpressionElement(object):
    """Class representing an element of an expression."""
    def __init__(self, **kwargs):
        """
        Constructor for the ExpessionElement class.

        Parameters
        ==========
        parent: Expression
            parent Expression
        op:
            attribut in the Expression (see the grammar)
        """
        # textX will pass in parent attribute used for parent-child
        # relationships. We can use it if we want to.
        self.parent = kwargs.get('parent', None)

        # We have 'op' attribute in all grammar rules
        self.op = kwargs['op']

        super(ExpressionElement, self).__init__()

class FactorSigned(ExpressionElement, BasicStmt):
    """Class representing a signed factor."""

    def __init__(self, **kwargs):
        """
        Constructor for a signed factor.

        Parameters
        ==========
        sign: str
            one among {'+', '-'}
        trailer: Trailer
            a trailer is used for a function call or Array indexing.
        """
        self.sign    = kwargs.pop('sign', '+')
        self.trailer = kwargs.pop('trailer', None)

        super(FactorSigned, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the signed factor, by returning a sympy expression
        """
        if DEBUG:
            print "> FactorSigned "
        expr = self.op.expr

        if self.trailer is None:
            return -expr if self.sign == '-' else expr
        else:
            args = self.trailer.expr
            if self.trailer.args:
                ls = []
                for i in args:
                    if isinstance(i, (list, tuple)):
                        ls.append(Tuple(*i))
                    else:
                        ls.append(i)
                args = ls
                name = str(expr)
                if name in builtin_funcs_math:
                    expr = builtin_function(name, args)
                else:
                    expr = Function(str(expr))(*args)
            elif self.trailer.subs:
                expr = IndexedVariable(str(expr))[args]
            return -expr if self.sign == '-' else expr

class FactorUnary(ExpressionElement, BasicStmt):
    """Class representing a unary factor."""

    def __init__(self, **kwargs):
        """
        Constructor for an unary factor.

        Parameters
        ==========
        name: str
            the unary operator
        trailer: Trailer
            a trailer is used for a function call or Array indexing.
        """
        self.name    = kwargs['name']
        self.trailer = kwargs.pop('trailer', None)

        super(FactorUnary, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the unary factor, by returning a sympy expression
        """
        if DEBUG:
            print "> FactorUnary "

        expr = self.op.expr
        rhs=expr

        if self.name=='len':
            import ast
            try:
                rhs=ast.literal_eval(expr)
            except:
                rhs=expr
            return LEN(rhs)
        elif self.name=='sign':
            return SIGN(rhs)
        elif self.name=='factorial':
            return factorial(rhs)
        else:
            raise Exeption('function note supported')

        if self.trailer is None:
            return expr
        else:
            args = self.trailer.expr
            if self.trailer.args:
                expr = Function(str(expr))(*args)
            elif self.trailer.subs:
                expr = IndexedVariable(str(expr))[args]
            return expr

# TODO: add trailer?
class FactorBinary(ExpressionElement):
    """Class representing a binary factor."""

    def __init__(self, **kwargs):
        """
        Constructor for a binary factor.

        Parameters
        ==========
        name: str
            name of the applied binary operator
        """
        self.name = kwargs['name']

        super(FactorBinary, self).__init__(**kwargs)

    @property
    def expr(self):
        if DEBUG:
            print "> FactorBinary "

        expr_l = self.op[0].expr
        expr_r = self.op[1].expr

        if self.name == "pow":
            return Pow(expr_l, expr_r)
        elif self.name == "rational":
            return Rational(expr_l, expr_r)
        elif self.name == "max":
            return Max(expr_l, expr_r)
        elif self.name == "min":
            return Min(expr_l, expr_r)
        else:
            raise Exception('Unknown variable "{}" at position {}'
                            .format(op, self._tx_position))

class Term(ExpressionElement):
    """Class representing a term in the grammar."""

    @property
    def expr(self):
        """
        Process the term, by returning a sympy expression
        """
        if DEBUG:
            print "> Term "

        ret = self.op[0].expr
        for operation, operand in zip(self.op[1::2], self.op[2::2]):
            if operation == '*':
                ret *= operand.expr
            else:
                ret /= operand.expr
        return ret

class Expression(ExpressionElement):
    """Class representing an expression in the grammar."""

    @property
    def expr(self):
        """
        Process the expression, by returning a sympy expression
        """
        if DEBUG:
            print "> Expression "

        ret = self.op[0].expr
        for operation, operand in zip(self.op[1::2], self.op[2::2]):

            if operation == '+':
                ret += operand.expr
            else:
                ret -= operand.expr

        return ret

class Operand(ExpressionElement):
    """Class representing an operand in the grammar."""

    @property
    def expr(self):
        """
        Process the operand, by returning a sympy atom
        """
        if DEBUG:
            print "> Operand "
            print "> stack : ", stack
            print self.op

        op = self.op
        if type(op) == int:
            return Integer(op)
        elif is_Float(op):
            # op is here a string that can be converted to a number
            return Float(float(op))
        elif type(op) == list:
            # op is a list
            for O in op:
                if O in namespace:
                    return namespace[O]
                elif O in stack:
                    if DEBUG:
                        print ">>> found local variables: " + O
                    return Symbol(O)
                elif type(O) == int:
                    return Integer(O)
                elif type(O) == float:
                    return Float(O)
                else:
                    raise Exception('Unknown variable "{}" at position {}'
                                    .format(O, self._tx_position))
        elif isinstance(op, ExpressionElement):
            return op.expr
        elif op in stack:
            if DEBUG:
                print ">>> found local variables: " + op
            return Symbol(op)
        elif op in namespace:
            if isinstance(namespace[op], FunctionDefStmt):
                return Function(op)
            else:
                return namespace[op]
        elif op in builtin_funcs:
            return Function(op)
        elif op in builtin_types:
            return datatype(op)
        elif(type(op)==unicode):
            return op
        else:
            raise Exception('Undefined variable "{}"'.format(op))

class Test(ExpressionElement):
    """Class representing a test expression as described in the grammmar."""

    @property
    def expr(self):
        """
        Process the test expression, by returning a sympy expression
        """
        if DEBUG:
            print "> DEBUG "
        ret = self.op.expr
        return ret

# TODO improve using sympy And, Or, Not, ...
class OrTest(ExpressionElement):
    """Class representing an Or term expression as described in the grammmar."""

    @property
    def expr(self):
        """
        Process the Or term, by returning a sympy expression
        """
        if DEBUG:
            print "> DEBUG "

        ret = self.op[0].expr
        for operation, operand in zip(self.op[1::2], self.op[2::2]):
            ret = (ret or operand.expr)
        return ret

# TODO improve using sympy And, Or, Not, ...
class AndTest(ExpressionElement):
    """Class representing an And term expression as described in the grammmar."""

    @property
    def expr(self):
        """
        Process the And term, by returning a sympy expression
        """
        if DEBUG:
            print "> DEBUG "

        ret = self.op[0].expr
        for operation, operand in zip(self.op[1::2], self.op[2::2]):
            ret = (ret and operand.expr)
        return ret

# TODO improve using sympy And, Or, Not, ...
class NotTest(ExpressionElement):
    """Class representing an Not term expression as described in the grammmar."""

    @property
    def expr(self):
        """
        Process the Not term, by returning a sympy expression
        """
        if DEBUG:
            print "> DEBUG "

        ret = self.op.expr
        ret = (not ret)
        return ret

# TODO ARA finish
class Comparison(ExpressionElement):
    """Class representing the comparison expression as described in the grammmar."""

    @property
    def expr(self):
        """
        Process the comparison, by returning a sympy expression
        """
        if DEBUG:
            print "> Comparison "

        ret = self.op[0].expr
        for operation, operand in zip(self.op[1::2], self.op[2::2]):
            if operation == "==":
                ret = EqualityStmt(ret, operand.expr)
            elif operation == ">":
#                ret = Gter(ret, operand.expr)
                ret = Gt(ret, operand.expr)
            elif operation == ">=":
#                ret = GOrEq(ret, operand.expr)
                ret = Ge(ret, operand.expr)
            elif operation == "<":
#                ret = Lthan(ret, operand.expr)
                ret = Lt(ret, operand.expr)
            elif operation == "<=":
#                ret = LOrEq(ret, operand.expr)
                ret = Le(ret, operand.expr)
            elif operation == "<>":
                ret = NotequalStmt(ret, operand.expr)
            else:
                raise Exception('operation not yet available at position {}'
                                .format(self._tx_position))
        return ret

class FlowStmt(BasicStmt):
    """Base class representing a Flow statement in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for a Flow statement

        Parameters
        ==========
        label: str
            name of the flow statement.
            One among {'break', 'continue', 'return', 'raise', 'yield'}
        """
        self.label = kwargs.pop('label')

class BreakStmt(FlowStmt):
    """Base class representing a Break statement in the grammar."""
    def __init__(self, **kwargs):
        super(BreakStmt, self).__init__(**kwargs)
    @property
    def expr(self):
        return Break()

class ContinueStmt(FlowStmt):
    """Base class representing a Continue statement in the grammar."""

# TODO improve
class ReturnStmt(FlowStmt):
    """Base class representing a Return statement in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for a return statement flow.

        Parameters
        ==========
        variables: list
            list of variables to return, as strings
        results: list
            list of variables to return, as pyccel.types.ast objects
        """
        self.variables = kwargs.pop('variables')
        self.results   = None

        super(ReturnStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the return flow statement
        """
        self.update()
#        print "namespace = ", namespace
#        print "variables = ", variables

        decs = []
        # TODO depending on additional options from the grammar
        # TODO check that var is in namespace
        for var_name in self.variables:
            if var_name in namespace:
                var = variables[var_name]
                if isinstance(var, Variable):
                    res = Result(var.dtype, var_name, \
                                 rank=var.rank, \
                                 allocatable=var.allocatable, \
                                 shape=var.shape)
                else:
                    # TODO is it correct? raise?
                    datatype = var.datatype
                    res = Result(datatype, var_name)
            else:
                raise()

            decs.append(res)

        self.results = decs
        return decs

class RaiseStmt(FlowStmt):
    """Base class representing a Raise statement in the grammar."""

class YieldStmt(FlowStmt):
    """Base class representing a Yield statement in the grammar."""

class FunctionDefStmt(BasicStmt):
    """Class representing the definition of a function in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for the definition of a function.

        Parameters
        ==========
        name: str
            name of the function
        args: list
            list of the function arguments
        body: list
            list of statements as given by the parser.
        """
        self.name = kwargs.pop('name')
        self.args = kwargs.pop('args')
        self.body = kwargs.pop('body')

        # TODO improve
        namespace[str(self.name)] = self

        super(FunctionDefStmt, self).__init__(**kwargs)

    # TODO: closure?
    def update(self):
        """Inserts arguments that are not in the namespace."""
        for arg_name in self.args:
            if not(arg_name in namespace):
                if DEBUG:
                    print("> Found new argument" + arg_name)

                # TODO define datatype, rank
                # TODO check if arg is a return value
                rank = 0
                datatype = 'float'
                insert_variable(arg_name, datatype=datatype, rank=rank,
                                is_argument=True)
            else:
                print("+++ found already declared argument : ", arg_name)

    @property
    def local_vars(self):
        """returns the local variables of the body."""
        return self.body.local_vars

    @property
    def stmt_vars(self):
        """returns the statement variables of the body."""
        return self.body.stmt_vars

    @property
    def expr(self):
        """
        Process the Function Definition by returning the appropriate object from
        pyccel.types.ast
        """
        self.update()
        body = self.body.expr

        name = str(self.name)

        args    = [variables[arg_name] for arg_name in self.args]
        prelude = [declarations[arg_name] for arg_name in self.args]

        # ...
        results = []
        for stmt in self.body.stmts:
            if isinstance(stmt, ReturnStmt):
                results += stmt.results
        # ...

        # ... cleaning the namespace
        for arg_name in self.args:
            declarations.pop(arg_name)
            variables.pop(arg_name)
            namespace.pop(arg_name)

        ls = self.local_vars + self.stmt_vars
        for var_name in ls:
            if var_name in namespace:
                namespace.pop(var_name, None)
                variables.pop(var_name, None)
                dec = declarations.pop(var_name, None)
                if dec:
                    prelude.append(dec)
        # ...

        body = prelude + body

        local_vars  = []
        global_vars = []

        return FunctionDef(name, args, results, body, local_vars, global_vars)

class NumpyZerosLikeStmt(AssignStmt):
    """Class representing a zeroslike function call."""
    def __init__(self, **kwargs):
        """
        Constructor for a zeros function call.

        Parameters
        ==========
        lhs: str
            variable name to create
        rhs: str
            input variable name
        """
        self.lhs = kwargs.pop('lhs')
        self.rhs = kwargs.pop('rhs')

        super(AssignStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """returns the statement variables."""
        return [self.lhs]

    def update(self):
        """updates the zeroslike function call."""
        var_name = self.lhs
        if not(var_name in namespace):
            if DEBUG:
                print("> Found new variable " + var_name)
        v=variables[self.rhs]

        insert_variable(var_name, \
                            datatype=v.dtype, \
                            rank=v.rank, \
                            allocatable=v.allocatable,shape=v.shape)

    @property
    def expr(self):
        """
        Process the zeroslike statement,
        by returning the appropriate object from pyccel.types.ast
        """
        self.update()
        v=variables[self.rhs]
        shape = v.shape

        if shape==None:
            shape=1

        var_name = self.lhs
        var = Symbol(var_name)

        stmt = NumpyZeros(var, shape)

        return stmt

class ImportFromStmt(BasicStmt):
    """Class representing an Import statement in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor for an Import statement.

        Parameters
        ==========
        dotted_name: list
            modules path
        import_as_names: textX object
            everything that can be imported
        """
        self.dotted_name     = kwargs.pop('dotted_name')
        self.import_as_names = kwargs.pop('import_as_names')

        super(ImportFromStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the Import statement,
        by returning the appropriate object from pyccel.types.ast
        """
        self.update()

        # TODO how to handle dotted packages?
        fil = self.dotted_name.names[0]
        funcs = self.import_as_names.names
        return Import(fil, funcs)

class PythonPrintStmt(BasicStmt):
    """Class representing a Print statement as described in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for a Print statement.

        Parameters
        ==========
        name: str
            is equal to 'print'
        args: list
            list of atoms to print
        """
        self.name = kwargs.pop('name')
        self.args = kwargs.pop('args')

        super(PythonPrintStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the Print statement,
        by returning the appropriate object from pyccel.types.ast
        """
        self.update()

        func_name   = self.name
        args        = self.args
        expressions=[]

        for arg in args:
            if not isinstance(arg,str):
               expressions.append(arg.expr)
            else:
                expressions.append(arg)
        return Print(expressions)

class CommentStmt(BasicStmt):
    """Class representing a Comment in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for a Comment.

        Parameters
        ==========
        text: str
            text that appears in the comment
        """
        self.text = kwargs.pop('text')

        # TODO improve
        #      to remove:  # coding: utf-8
        if ("coding:" in self.text) or ("utf-8" in self.text):
            self.text = ""

        super(CommentStmt, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the Comment statement,
        by returning the appropriate object from pyccel.types.ast
        """
        self.update()
        return Comment(self.text)

class SuiteStmt(BasicStmt):
    """Class representing a Suite statement in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor for a Suite statement.

        Parameters
        ==========
        stmts: list
            list of statements as given by the parser.
        """
        self.stmts = kwargs.pop('stmts')

        super(SuiteStmt, self).__init__(**kwargs)

    @property
    def local_vars(self):
        """returns local variables for every statement in stmts."""
        ls = []
        for stmt in self.stmts:
            ls += stmt.local_vars
        s = set(ls)
        return list(s)

    @property
    def stmt_vars(self):
        """returns statement variables for every statement in stmts."""
        ls = []
        for stmt in self.stmts:
            ls += stmt.stmt_vars
        s = set(ls)
        return list(s)

    @property
    def expr(self):
        """
        Process the Suite statement,
        by returning a list of appropriate objects from pyccel.types.ast
        """
        self.update()
        ls = [stmt.expr for stmt in  self.stmts]
        return ls

class BasicTrailer(BasicStmt):
    """Base class representing a Trailer in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor for a Base Trailer.

        Parameters
        ==========
        args: list or ArgList
            arguments of the trailer
        """
        self.args = kwargs.pop('args', None)

        super(BasicTrailer, self).__init__(**kwargs)

class Trailer(BasicTrailer):
    """Class representing a Trailer in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor for a Trailer.

        Parameters
        ==========
        subs: list or subscripts
            subscripts of the trailer
        """
        self.subs = kwargs.pop('subs', None)

        super(Trailer, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process a Trailer by returning the approriate objects from
        pyccel.types.ast
        """
        self.update()
        if self.args:
            return self.args.expr
        if self.subs:
            return self.subs.expr

class TrailerArgList(BasicTrailer):
    """Class representing a Trailer with list of arguments in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor of the Trailer ArgList
        """
        super(TrailerArgList, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process a Trailer by returning the approriate objects from
        pyccel.types.ast
        """
        self.update()
        return [arg.expr for arg in  self.args]

class TrailerSubscriptList(BasicTrailer):
    """Class representing a Trailer with list of subscripts in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor of the Trailer with subscripts
        """
        super(TrailerSubscriptList, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process a Trailer by returning the approriate objects from
        pyccel.types.ast
        """
        self.update()
        args = []
        for a in self.args:
            if isinstance(a, Expression):
                arg = do_arg(a)

                # TODO treat n correctly
                n = Symbol('n', integer=True)
                i = Idx(arg, n)
                args.append(i)
            elif isinstance(a, BasicSlice):
                arg = a.expr
                args.append(arg)
            else:
                raise Exception('Wrong instance')
        return args

class BasicSlice(BasicStmt):
    """Base class representing a Slice in the grammar."""
    def __init__(self, **kwargs):
        """
        Constructor for the base slice.
        The general form of slices is 'a:b'

        Parameters
        ==========
        start: str, int, Expression
            Starting index of the slice.
        end: str, int, Expression
            Ending index of the slice.
        """
        self.start = kwargs.pop('start', None)
        self.end   = kwargs.pop('end',   None)

        super(BasicSlice, self).__init__(**kwargs)

    def extract_arg(self, name):
        """
        returns an argument as a variable, given its name

        Parameters
        ==========
        name: str
            variable name
        """
        if name is None:
            return None

        var = None
        if isinstance(name, (Integer, Float)):
            var = Integer(name)
        elif isinstance(name, str):
            if name in namespace:
                var = namespace[name]
            else:
                raise Exception("could not find {} in namespace ".format(name))
        elif isinstance(name, Expression):
            var = do_arg(name)
        else:
            raise Exception("Unexpected type {0} for {1}".format(type(name), name))

        return var

    @property
    def expr(self):
        """
        Process the Slice statement, by giving its appropriate object from
        pyccel.types.ast
        """
        start = self.extract_arg(self.start)
        end   = self.extract_arg(self.end)

        return Slice(start, end)

class TrailerSlice(BasicSlice):
    """
    Class representing a Slice in the grammar.
    A Slice is of the form 'a:b'
    """
    pass

class TrailerSliceRight(BasicSlice):
    """
    Class representing a right Slice in the grammar.
    A right Slice is of the form 'a:'
    """
    pass

class TrailerSliceLeft(BasicSlice):
    """
    Class representing a left Slice in the grammar.
    A left Slice is of the form ':b'
    """
    pass

class ThreadStmt(BasicStmt):
    """Class representing a Thread call function in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for a Thread function call.

        Parameters
        ==========
        lhs: str
            variable name to create
        func: str
            function to call
        """
        self.lhs  = kwargs.pop('lhs')
        self.func = kwargs.pop('func')

        super(ThreadStmt, self).__init__(**kwargs)

    def update(self):
        """
        appends the variable to the namespace
        """
        var_name = str(self.lhs)
        if not(var_name in namespace):
            insert_variable(var_name, datatype='int', rank=0)
        else:
            raise Exception('Already declared variable for thread_id.')

    @property
    def expr(self):
        """
        Process the Thread function call,
        by returning the appropriate object from pyccel.types.ast
        """
        self.update()

        var_name = str(self.lhs)
        var = Symbol(var_name)

        func = str(self.func)
        if func == 'thread_id':
            return ThreadID(var)
        elif func == 'thread_number':
            return ThreadsNumber(var)
        else:
            raise Exception('Wrong value for func.')

class ArgList(BasicStmt):
    """Class representing a list of arguments."""
    def __init__(self, **kwargs):
        """
        Constructor for ArgList statement.

        Parameters
        ==========
        args: list
            list of arguments
        """
        self.args = kwargs.pop('args', None)

        super(ArgList, self).__init__(**kwargs)

    @property
    def expr(self):
        """
        Process the ArgList statement,
        by returning a list of appropriate objects from pyccel.types.ast
        """
        ls = []
        for arg in self.args:
            if isinstance(arg, (FactorUnary, ArgList)):
                ls.append(arg.expr)
            elif type(arg) == int:
                ls.append(int(arg))
            elif is_Float(arg):
                ls.append(float(arg))
            else:
                if arg in namespace:
                    ls.append(variables[arg])
                else:
                    ls.append(arg)
        return ls

class StencilStmt(AssignStmt):
    """Class representing a Stencil statement in the grammar."""

    def __init__(self, **kwargs):
        """
        Constructor for a Stencil statement.

        Parameters
        ==========
        lhs: str
            variable name to create
        parameters: list
            list of parameters needed for the Stencil object.
        """
        self.lhs        = kwargs.pop('lhs')
        self.parameters = kwargs.pop('parameters')

        labels = [str(p.label) for p in self.parameters]
        values = [p.value.value for p in self.parameters]
        d = {}
        for (label, value) in zip(labels, values):
            d[label] = value
        self.parameters = d

        try:
            self.datatype = self.parameters['dtype']
        except:
            self.datatype = 'float'

        try:
            self.shape = self.parameters['shape']
            # on LRZ, self.shape can be a list of ArgList
            # this is why we do the following check
            # maybe a bug in textX
            if isinstance(self.shape, list):
                if isinstance(self.shape[0], ArgList):
                    self.shape = self.shape[0].args
            elif isinstance(self.shape, ArgList):
                self.shape = self.shape.args
        except:
            raise Exception('Expecting shape at position {}'
                            .format(self._tx_position))

        try:
            self.step = self.parameters['step']
            # on LRZ, self.step can be a list of ArgList
            # this is why we do the following check
            # maybe a bug in textX
            if isinstance(self.step, list):
                if isinstance(self.step[0], ArgList):
                    self.step = self.step[0].args
            elif isinstance(self.step, ArgList):
                self.step = self.step.args
        except:
            raise Exception('Expecting step at position {}'
                            .format(self._tx_position))

        super(AssignStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """returns statement variables."""
        return [self.lhs]

    def update(self):
        """
        specific treatments before process
        """
        var_name = self.lhs
        if not(var_name in namespace):
            if DEBUG:
                print("> Found new variable " + var_name)

            datatype = self.datatype

            # ...
            def format_entry(s_in):
                rank = 0
                if isinstance(s_in, int):
                    s_out = s_in
                    rank = 1
                elif isinstance(s_in, float):
                    s_out = int(s_in)
                    rank = 1
                elif isinstance(s_in, list):
                    s_out = []
                    for s in s_in:
                        if isinstance(s, (int, float)):
                            s_out.append(int(s))
                        elif isinstance(s, str):
                            if not(s in namespace):
                                raise Exception('Could not find s_out variable.')
                            s_out.append(namespace[s])
                        elif isinstance(s,FactorUnary):
                            s_out.append(s.expr)
    #                    elif isinstance(s,ArgList):
    #                        s_out.append(s.expr)
                        else:
                            print ("> given type: ", type(s))
                            raise TypeError('Expecting a int, float or string')
                    rank = len(s_out)
                elif isinstance(s_in,FactorUnary):
                     s_out=s_in.expr
                else:
                    s_out = str(s_in)
                    if s_out in namespace:
                        s_out = namespace[s_out]
                        # TODO compute rank
                        rank = 1
                    else:
                        raise Exception('Wrong instance for s_out : '.format(type(s_in)))
                return s_out, rank
            # ...

            # ...
            self.shape, r_1 = format_entry(self.shape)
            self.step,  r_2 = format_entry(self.step)
            rank = r_1 + r_2
            # ...

            if datatype is None:
                if DEBUG:
                    print("> No Datatype is specified, int will be used.")
                datatype = 'int'
            elif isinstance(datatype, list):
                datatype = datatype[0] # otherwise, it's not working on LRZ
            # TODO check if var is a return value
            insert_variable(var_name, \
                            datatype=datatype, \
                            rank=rank, \
                            allocatable=True,shape = self.shape)

    @property
    def expr(self):
        """
        Process the Stencil statement,
        by returning the appropriate object from pyccel.types.ast
        """
        self.update()

        shape = self.shape
        step  = self.step

        var_name = self.lhs
        var = Symbol(var_name)

        return Stencil(var, shape, step)

class EvalStmt(BasicStmt):
    """
    Class representing an Eval statement in the grammar
    """
    def __init__(self, **kwargs):
        """
        Constructor for a eval statement.

        Parameters
        ==========
        lhs: str
            variable name to create
        module: str
            module where the function lives
        function: str
            function to call from the module
        args: list
            list of arguments to feed the function call
        """
        self.lhs      = kwargs.pop('lhs')
        self.module   = kwargs.pop('module')
        self.function = kwargs.pop('function')
        self.args     = kwargs.pop('args')

        super(EvalStmt, self).__init__(**kwargs)

    @property
    def stmt_vars(self):
        """returns the statement variables."""
        return self.lhs

    def update(self):
        """
        Pre-process. We check that the lhs is not in the namespace.
        """
        for var_name in self.lhs:
            if not(var_name in namespace):
                raise Exception('Undefined variable {}.'.format(var_name))

    @property
    def expr(self):
        """
        Process the Eval statement,
        by returning a list of appropriate objects from pyccel.types.ast
        """
        # TODO must check compatibility
#        self.update()

        module_name   = self.module
        function_name = self.function

        try:
            import importlib
            module   = importlib.import_module(module_name)
        except:
            raise Exception('Could not import module {}.'.format(module_name))

        try:
            function = getattr(module, "{}".format(function_name))
        except:
            raise Exception('Could not import function {}.'.format(function_name))

        args = self.args.expr
        rs   = function(*args)

        if isinstance(rs, tuple):
            rs = list(rs)

        if not isinstance(rs, list):
            rs = [rs]

        if not(len(rs) == len(self.lhs)):
            raise Exception('Incompatible lhs with function output.')

        ls = []
        for (l,r) in zip(self.lhs, rs):
            if isinstance(r, (int, float, complex)):
                rank        = 0
                shape       = None
                allocatable = False
                # check if numpy variable
                if (type(r).__module__ == np.__name__):
                    t = r.dtype
                else:
                    t = type(r)
                datatype = convert_numpy_type(t)

            elif isinstance(r, ndarray):
                shape       = r.shape
                rank        = len(shape)
                allocatable = True
                datatype    = convert_numpy_type(r.dtype)
            else:
                raise TypeError('Expecting int, float, complex or numpy array.')

            if l in namespace:
                raise Exception('Variable {} already defined, '
                                'cannot be used in eval statement.'.format(l))

            insert_variable(l, \
                            datatype=datatype, \
                            rank=rank, \
                            allocatable=allocatable, \
                            shape=shape)

            var = namespace[l]
#            print type(r)
            if isinstance(r, ndarray):
                stmt = NumpyArray(var, r, shape)
            else:
                stmt = Assign(var, r)

            ls.append(stmt)

        return ls
