# coding: utf-8
#------------------------------------------------------------------------------------------#
# This file is part of Pyccel which is released under MIT License. See the LICENSE file or #
# go to https://github.com/pyccel/pyccel/blob/devel/LICENSE for full license details.      #
#------------------------------------------------------------------------------------------#
""" Module containing scripts to remove pyccel generated objects
"""
import os
import shutil
import sysconfig
from argparse import ArgumentParser

ext_suffix = sysconfig.get_config_var('EXT_SUFFIX')

def pyccel_clean(path_dir = None, recursive = True, remove_shared_libs = False, remove_programs = False):
    """
    Remove folders generated by Pyccel.

    Remove `__pyccel__X` and `__epyccel__X` folders as well
    as any Python shared libraries from the directory path_dir.
    The folders `__pyccel__X` are called `__pyccel__` unless
    they were generated using `pytest-xdist`.

    Parameters
    ----------
    path_dir : str, default = current working directory
        The path to the folder which should be cleaned.

    recursive : bool, default = True
        Indicates whether the function should recurse into
        sub-folders.

    remove_shared_libs : bool, default = False
        Indicates whether shared libraries generated by
        Python should also be removed from the directory
        path_dir.

    remove_programs : bool, default = False
        Indicates whether programs should also be removed
        from the directory path_dir.
    """
    if path_dir is None:
        path_dir = os.getcwd()

    files = os.listdir(path_dir)
    for f in files:
        file_name = os.path.join(path_dir,f)
        if f.startswith("__pyccel__") or f.startswith("__epyccel__"):
            shutil.rmtree( file_name, ignore_errors=True)
        elif not os.path.isfile(file_name) and recursive:
            pyccel_clean(file_name, recursive, remove_shared_libs, remove_programs)
        elif f.endswith('.pyccel'):
            os.remove(file_name)
        elif remove_shared_libs and f.endswith(ext_suffix):
            os.remove(file_name)
        elif remove_programs and os.access(file_name, os.X_OK):
            os.remove(file_name)

def pyccel_clean_command():
    """
    Command line wrapper around the pyccel_clean function.

    A wrapper around the pyccel_clean function which allows
    command line arguments to be passed to the function.
    """
    parser = ArgumentParser(description='Tool for removing files generated by pyccel')

    parser.add_argument('folders', metavar='N', type=str, nargs='*',
            help='The folders to be cleaned (default is the current folder')
    parser.add_argument('-n', '--not-recursive', action='store_false',
            help='Only run pyccel-clean in the current directory. Do not recurse into other folders')
    parser.add_argument('-s', '--remove-libs', action='store_true',
            help='Also remove any libraries generated by Python from the folder. Beware this may remove shared libraries generated by tools other than pyccel')
    parser.add_argument('-p', '--remove-programs', action='store_true',
            help='Also remove any programs from the folder. Beware this may remove programs unrelated to pyccel')
    args = parser.parse_args()

    folders = args.folders
    recursive = args.not_recursive
    remove_libs = args.remove_libs
    remove_programs = args.remove_programs

    if len(folders)==0:
        pyccel_clean(None, recursive, remove_libs, remove_programs)
    else:
        for f in folders:
            pyccel_clean(f, recursive, remove_libs, remove_programs)
