from tifffile import TiffFile

import collections
from xml.etree import cElementTree as etree 
import traceback

#Class for error handling
class PythImageError(Exception):
    
    def __init__(self, message, errors):
        
        super(PythImageError, self).__init__(message)
        
        self.traceback=str(traceback.format_exc()).replace('\n', '\n\t\t')
        self.message = message
        self.errors = errors
    
    def __str__(self):
        return repr(self.message)#+"\n\nERROR:"+repr(self.errors)+"\n\nTRACEBACK:"+str(self.traceback)

class lazyattr(object):
    """Attribute whose value is computed on first access. As in tifffile.py from Christoph Gohlke"""


    def __init__(self, func):
        self.func = func


    def __get__(self, instance, owner):
        # with self.lock:
        if instance is None:
            return self
        try:
            value = self.func(instance)
        except AttributeError as e:
            raise RuntimeError(e)
        if value is NotImplemented:
            return getattr(super(owner, instance), self.func.__name__)
        setattr(instance, self.func.__name__, value)
        return value 
             

def get_image_source(path):
    '''
    Return the image type. Currently only imageJ and ome Tiff files are supported.
    '''
          
    with TiffFile(path) as tif:
             
        if tif.is_imagej:
            output='imagej'
        
        if tif.is_imagej:
            output='ome'
            
    return output

def length(a):
    '''
    Append elements of two lists using slice notation. Elements of list b are added to the end of a.
    '''
  
    if not isinstance(a, collections.Iterable) or isinstance(a, str):
        length=1
    else:
        length=len(a)
    
    return length

           
def dict_to_string(d, string='', lvl=0):

    for k, v in d.items():
        string+='%s%s' % (lvl * '\t', str(k))
        if type(v) == dict:
            string+=':%s'%str(v)+'\n'
            #If deeper recursion is needed
            #utils.dict_to_string(v, string, lvl+1)
        else:
           string+=':%s'%v+'\n'
    return string            
 
          
def xml2dict( xml, sanitize=True, prefix=None):
    """Return XML as dict. Adapted from 	the tiffile package authored b Christoph .

    >>> xml2dict('<?xml version="1.0" ?><root attr="name"><key>1</key></root>')
    {'root': {'key': 1, 'attr': 'name'}}

    """
  
    
    #Decode to avert parsing errors as some software dump large text
    #fields into the file that occasionally contain erronious chars
    xml=xml.decode('utf-8', errors='ignore')

    
    return etree2dict(etree.fromstring(xml), sanitize, prefix) 

def asbool(value, true=(b'true', u'true'), false=(b'false', u'false')):
    """Return string as bool if possible, else raise TypeError.

    >>> asbool(b' False ')
    False

    """
    value = value.strip().lower()
    if value in true:  # might raise UnicodeWarning/BytesWarning
        return True
    if value in false:
        return False
    raise TypeError()


def astype(value):
    # return value as int, float, bool, or str
    for t in (int, float, asbool):
        try:
            return t(value)
        except Exception:
            pass
    return value


def etree2dict(t, sanitize=True, prefix=None):
        '''Convert eTree object to dict. 
        Adapted from https://stackoverflow.com/a/10077069/453463
        '''
        at = tx = ''
        if prefix:
            at, tx = prefix
        
        key = t.tag
        if sanitize:
            key = key.rsplit('}', 1)[-1]
        d = {key: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = collections.defaultdict(list)
            for dc in map(etree2dict, children):
                for k, v in dc.items():
                    dd[k].append(astype(v))
            d = {key: {k: astype(v[0]) if len(v) == 1 else astype(v)
                       for k, v in dd.items()}}
        if t.attrib:
            d[key].update((at + k, astype(v)) for k, v in t.attrib.items())
        
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[key][tx + 'value'] = astype(text)
            else:
                d[key] = astype(text)
        return d
    
def represents_type(s, atype):
    '''
    Check if string represents type given through atype!
    '''
    try: 
        atype(s)
        return True
    except ValueError:
        return False  

    
def concatenate(a,b):
    '''
    Append elements of two lists using slice notation. Elements of list b are added to the end of a.
    '''
    if not isinstance(a, collections.Iterable) or isinstance(a, (str,dict)):
        a=[a]
    if not isinstance(b, collections.Iterable) or isinstance(b, (str,dict)):
        b=[b]
    a[len(a):len(a)]=b

    return a   

def list_of(lst, object_type):
    return any((isinstance(x, object_type) for x in lst))


def value_to_key(dictionary, val):
    
    #Get the ocurrences of val among dictionary values
    count=sum(value == val for value in dictionary.values())
    #version 2: count=sum(map((val).__eq__, dictionary.values()))
    
    #If value is not in dictionary.values raise exception
    if count==0:
        raise LookupError('Value %s is not in dictionary'.format(str(val)))
    if count>1:
        raise LookupError('More than one key have value %s!'.format(str(val)))
    
    #get value
    #version 2: list(dictionary.keys())[list(dictionary.values()).index(val)]
    for key, value in dictionary.items():
        if value == val:
            return key
        
def rename_duplicates(string_list):
    '''Processes a list of strings. If list has duplicate elements an index is added to it.
    '''
    if isinstance(string_list, str) or not isinstance(string_list, list):
        raise Exception('Object must be list of strings!')
    
    output = []
    for idx, val in enumerate(string_list):
        totalcount = string_list.count(val)
        count = string_list[:idx].count(val)
        output.append(val +'_'+ str(count + 1) if totalcount > 1 else val)
    
    return output

def get_version(package_name):
    
    '''Return package version number.
    '''
    
    from pip._vendor import pkg_resources
   
    return str(pkg_resources.get_distribution(package_name).version)