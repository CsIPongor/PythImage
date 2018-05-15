import collections
from xml.etree import cElementTree as etree 

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