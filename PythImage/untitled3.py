# -*- coding: utf-8 -*-
"""
Created on Tue Aug 21 08:12:48 2018

@author: pongor.csaba
"""

import os, sys, subprocess
import warnings
path='C:\\Users\\pongor.csaba\\Desktop\\timing1.xlsx'


def open_file(path):
    '''Open file using its associated program in an os (MacOS, Linux, Windows) 
    dependent manner. Exceptions are raised as warnings using a try statement.
    
    path(str): The path of the file to be opened
    '''
    try:
        #Windows
        if sys.platform == "win32":
            os.startfile(path)
        #MacOS
        elif sys.platform == "darwin":
           subprocess.call(["open", path]) 
        #Linux/Unix
        else:
            subprocess.call(["xdg-open", path])
    
    except Exception as e:
        raise Warning(e.value)
        
        
open_file(path)    
