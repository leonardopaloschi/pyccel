# coding: utf-8
#------------------------------------------------------------------------------------------#
# This file is part of Pyccel which is released under MIT License. See the LICENSE file or #
# go to https://github.com/pyccel/pyccel/blob/master/LICENSE for full license details.     #
#------------------------------------------------------------------------------------------#
"""
Functions for solving an ordinary differential equation using the explicit midpoint method. The code is adapted from examples written by [J. Burkardt](https://people.sc.fsu.edu/~jburkardt/py_src/py_src.html)
To be accelerated with pyccel or pythran
"""
from numpy import zeros
from numpy import linspace

# ================================================================
def midpoint_explicit (dydt: '()(real, const real[:], real[:])',
                       tspan: 'real[:]', y0: 'real[:]', n: int,
                       t: 'real[:]', y: 'real[:,:]'):
    """
    Function implementing the explicit midpoint method
    """

    m = len( y0 )
    ym = zeros(m)

    dt = ( tspan[1] - tspan[0] ) / float ( n )

    t[0] = tspan[0]
    y[0,:] = y0[:]

    for i in range ( 0, n ):

        tm = t[i]   + 0.5 * dt
        dydt ( t[i], y[i,:], ym[:] )
        ym[:] = y[i,:] + 0.5 * dt * ym[:]

        t[i+1]   = t[i]   + dt
        dydt ( tm, ym[:], y[i+1,:] )
        y[i+1,:] = y[i,:] + dt * y[i+1,:]

# ================================================================
# pythran export humps_fun(float)
def humps_fun ( x : float ):
    """
    Humps function
    """

    y = 1.0 / ( ( x - 0.3 )**2 + 0.01 ) \
            + 1.0 / ( ( x - 0.9 )**2 + 0.04 ) \
            - 6.0

    return y

# ================================================================
def humps_deriv ( x: 'real', y: 'real[:]', out: 'real[:]' ):
    """
    Derivative of the humps function
    """

    out[0] = - 2.0 * ( x - 0.3 ) / ( ( x - 0.3 )**2 + 0.01 )**2 - 2.0 * ( x - 0.9 ) / ( ( x - 0.9 )**2 + 0.04 )**2

# ================================================================
# pythran export midpoint_explicit_humps_test(float[:],float[:],int)
def midpoint_explicit_humps_test ( tspan: 'real[:]', y0: 'real[:]', n: int ):
    """
    Run n steps of an explicit midpoint method starting from y0

    Parameters
    ----------
    tspan : array of 2 floats
            The first element is the start time.
            The second element is the end time.
    y0    : array of floats
            The starting point for the evolution
    n     : int
            The number of time steps
    """

    m = len ( y0 )

    t0 = tspan[0]
    t1 = tspan[1]

    t = linspace ( t0, t1, n + 1 )
    y = zeros ( [ n + 1, m ] )

    midpoint_explicit ( humps_deriv, tspan, y0, n, t, y )
