# -*- coding: utf-8 -*-
###############################################################################
#Functions to load and save OME-tiff images. Images are loaded using the 
#Tifffile package (https://www.lfd.uci.edu/~gohlke/code/tifffile.py.html)
#of Christian Gohlke. Pixel and channel metadata are loaded into a simplified 
#metadata dictionary. If image contains ROI the structure of the OME-Tiff 
#metadata dictionary returned by Tifffile is used.
###############################################################################
#dfdsffasfa
####
#import tifffile
#from tifffile import TiffFile, TiffWriter

from .external.tifffile import TiffFile, TiffWriter
import os
from . import utils
from itertools import product
#from ..RoiClass import Roi
from .roi import shapes
import warnings


DIM_ORDERS=['XYZCT','XYZTC','XYCTZ','XYCZT','XYTCZ','XYTZC']
DIM_TRANSLATE={'T':'SizeT', 'C':'SizeC', 'Z':'SizeZ', 'X':'SizeX', 'Y': 'SizeY'}#, 'S':'SamplesPerPixel'}

#BIT_DEPTH_LOOKUP={'uint8':'uint8','uint16':'uint16', 'uint32':'uint32', 'float':'float32','double':'float64','uint8':'int8','uint16':'int16','uint32':'int32', 'uint64':'int64'}	#, 'bool':'bool''float64':'float64', 'float32':'float64'
BIT_DEPTH_LOOKUP={'uint8':'uint8','uint16':'uint16', 'uint32':'uint32','uint64':'uint64','int8':'int8','int16':'int16', 'int32':'uint32','int64':'uint64','float':'float32','double':'float64'}

OTHER_KEYS=['DimensionOrder','Type','SamplesPerPixel']
UNIT_KEYS=['PhysicalSizeZUnit', 'PhysicalSizeXUnit', 'PhysicalSizeYUnit', 'TimeIncrementUnit']
SIZE_KEYS=['SizeT', 'SizeC', 'SizeZ', 'SizeX', 'SizeY']
PHYSICAL_SIZE_KEYS=['PhysicalSizeX', 'PhysicalSizeY', 'PhysicalSizeZ','TimeIncrement']

LENGTH_UNITS={'Ym':['yottameter','yottameters','Yottameter','Yottameters','Ym'],
     'Zm':['zettameter','zettameters','Zm'],
     'Em':['exameter', 'exameters', 'em','Em'],
     'Pm':['petameter','petameters','Pm'],
     'Tm':['terameter', 'terameters','tm','Tm'],
     'Gm':['gigameter','gigameters','gm','Gm'],
     'Mm':['megameter', 'megameters','Mm'],
     'km':['kilometer','kilometers', 'Km','km'],
     'hm':['hectometer','hectometers', 'Hm','hm'],
     'dam':['decameter','decameters','Dam','dam'],
     'm':['meter','meters','Meter','Meters','m'],
     'dm':['decimeter','decimeters', 'Decimeter','Decimeters', 'Dm','dm'],
     'cm':['centimeter','centimeters','Centimeter','Centimeters','Cm','cm'],
     'mm':['millimeter','millimeters','Millimeter','Millimeters','mm'],
     'µm':['micrometer','micrometers','Micrometer','Micrometers','um','micron', 'Micron','microns', 'Microns','µm'],
     'nm':['nanometer','nanometers','Nanometers','Nanometer','nm'],
     'pm':['picometer','picometers','Picometer','Picometers','pm'],
     'fm':['femtometer','femtometers','Femtometer','Femtometers','Fm','fm'],
     'am':['attometer','attometers','Attometer','Attometers','Am','am'],
     'zm':['zeptometer','zeptometers','Zeptometer','Zeptometers','Zm','zm'],
     'ym':['yoctometer','yoctometers','Yoctometer','Yoctometers','Ym','ym'],
     'Å':['ångström','ångströms','å','Ångström','Ångströms','Å'],
     'thou':['thou','Thou'],
     'li':['line','Line','Li'],
     'in':['inch','Inch','im','Im'],
     'ft':['foot','Foot','Ft','ft'],
     'yd':['yard','Yard','yards','Yards','Yd','yd'],
     'mi':['mile', 'Mile', 'miles','Miles'],
     'ua':['astronomical unit','Aa','ua','au', 'AU'],
     'ly':['light year','light years','Ly','ly'],
     'pc':['parsec','Parsec', 'Pc', 'pc'],
     'pt':['typographical point','Point','point', 'Pt','Pts','pts','pt'],
     'pixel':['pixel','Pixel','pix','Pix','px','Px','pixel']}

TIME_UNITS={'Ys':['yottasecond','yottaseconds','Ys'],
    'Zs':['zettasecond','zettaseconds','Zs'],
    'Es':['exasecond','exaseconds','Es'],
    'Ps':['petasecond','petaseconds', 'Ps'],
    'Ts':['terasecond', 'teraseconds','ts','Ts'],
    'Gs':['gigasecond','gigaseconds','gs','Gs'],
    'Ms':['megasecond','megaseconds','Ms'],
    'ks':['kilosecond', 'kiloseconds','Ks','ks'],
    'hs':['hectosecond','hectoseconds','Hs','hs'],
    'das':['decasecond','decaseconds','Das','das'],
    's':['second','seconds', 's'],
    'ds':['decisecond','deciseconds','Ds','ds'],
    'cs':['centisecond','centiseconds','Cs','cs'],
    'ms':['millisecond','milliseconds','ms'],
    'µs':['microsecond', 'microseconds','µs'],
    'ns':['nanosecond', 'nanoseconds', 'Ns', 'ns'],
    'ps':['picosecond','picoseconds', 'ps'],
    'fs':['femtosecond', 'femtoseconds','Fs','fs'],
    'as':['attosecond', 'attoseconds','as'],
    'zs':['zeptosecond','zeptoseconds', 'zs'],
    'ys':['yoctosecond','yoctoseconds','Ys','ys'],
    'min':['minute','minutes', 'mins', 'min'],
    'h':['hour','hours','h','hr','hrs','Hr','Hrs'],
    'd':['day','days','d']}

UNITS= {**TIME_UNITS, **LENGTH_UNITS}


def load_image(path):
    '''
    Read OME-Tiff file. Supported OME dimension orders are :'XYZCT','XYZTC','XYCZT','XYTCZ','XYCTZ'
    and 'XYTZC' (in order of incresing speed). For files with channels where SamplesPerPixel>1 the 
    C dimension will also contain the different Samples separately. For example a 4 channel rgb image
    (SamplesPerPixel=3)  will contain 4*3 channels. Returns ndarray with normalized shape where axes 
    of unit length are also marked. Note that order of axis will be from the slowest to the fastest 
    changing as returned by TiffFile.
    '''
    
    #Ignore some tiffile warnings that always occur ??Bug??
    warnings.filterwarnings("ignore", message="ome-xml: index out of range")
    warnings.filterwarnings("ignore", message="ome-xml: not well-formed")
    
    with TiffFile(path, is_ome=True) as tif:
                
        #Check if image is OME-Tiff
        if not tif.is_ome:
            raise TypeError('The file is corrupt or not an OME-tiff file!')
      
        #Load image into nd array
        images = tif.asarray()

        #Load metadata
        ome_metadata=utils.xml2dict(tif[0].tags['image_description'].value, sanitize=True, prefix=None)
    
    return images, ome_metadata
        
def save_image(image, metadata, directory, file_name):
    '''
    Save Image. Metadata not saved currently!!
    ''' 

    if metadata["DimensionOrder"]=='XYZCT':
        
        with TiffWriter(os.path.join(directory, file_name)) as tif:
            #for index, (i, j, k) in enumerate(product(range(metadata['SizeC']), range(metadata['SizeT']), range(metadata['SizeZ']))):
            for i, j, k in product(range(image.shape[0]),range(image.shape[1]),range(image.shape[2])):

                if i==0 and j==0 and k==0:
                     
                     tif.save(image[i][j][k], description=metadata_to_ome(metadata, file_name))
                else:
                     tif.save(image[i][j][k])
    else:
        raise Exception('The dimension order has to be XYCZT!')

def convert_metadata(metadata_dict):
    
    '''
    Create a simplified metadata dictionary from dictionaries extracted from the OME-Tiff xml files.
    '''
  
    metadata_dict_out={}        
    
    #print(b.keys())
    #Only keep metadata that ar used from the input dictionary 
    pixels_dict=metadata_dict['OME']['Image']['Pixels']
   
    #Add optional keys if present
    keys=SIZE_KEYS+PHYSICAL_SIZE_KEYS+UNIT_KEYS+OTHER_KEYS
    for key in keys:
        if key in pixels_dict.keys():
            metadata_dict_out[key]=pixels_dict[key]
    
    #Check units: trsanslate to OME compattible unit or else delete metadata      
    metadata_dict_out=convert_units(metadata_dict_out, UNIT_KEYS, UNITS) 
           
    if isinstance(pixels_dict['Channel'], list): 
        
        metadata_dict_out['SamplesPerPixel']=[1 for n in range(len(pixels_dict['Channel']))]

        for idx, dic in enumerate(pixels_dict['Channel']):
            if 'SamplesPerPixel' in dic.keys():
                metadata_dict_out['SamplesPerPixel'][idx]=dic['SamplesPerPixel']

        name_list=[dic['Name'] if 'Name' in dic.keys() else 'Ch'+str(index+1) for index, dic in enumerate(pixels_dict['Channel'])]
        
        metadata_dict_out['Name']=[]
        for idx, name in enumerate(name_list):
            if metadata_dict_out['SamplesPerPixel'][idx]==1:
                metadata_dict_out['Name'].append(name)
            else: 
                for n in range(metadata_dict_out['SamplesPerPixel'][idx]):
                   metadata_dict_out['Name'].append(name+'_S'+str(n))
                
    elif isinstance(pixels_dict['Channel'], dict):
        if 'SamplesPerPixel' in pixels_dict['Channel']:
            metadata_dict_out['SamplesPerPixel']=pixels_dict['Channel']['SamplesPerPixel']
        else:
            metadata_dict_out['SamplesPerPixel']=1
       
        if 'Name' in pixels_dict['Channel'].keys():
            name=pixels_dict['Channel']['Name']
        else:
            name='Ch0'
        
        metadata_dict_out['Name']=[]
        if metadata_dict_out['SamplesPerPixel']==1:
            metadata_dict_out['Name'].append(name)
        else: 
            for n in range(metadata_dict_out['SamplesPerPixel']):
               metadata_dict_out['Name'].append(name+'_S'+str(n))
     
    #Set metadata type from ome type to numpy array
    metadata_dict_out['Type']=BIT_DEPTH_LOOKUP[metadata_dict_out['Type']]
             
    #Get ROI-s if present
    if 'ROI' in metadata_dict['OME'].keys():
       metadata_dict_out['ROI']=metadata_dict['OME']['ROI']
     
    return metadata_dict_out

def metadata_to_ome (metadata, file_name):
    '''
    Convert internal metadata representation to conform with ome/tiff specification.
    '''
    import uuid
    from xml.etree import cElementTree as etree
    
    #Set metadata type from ome type to numpy array

    metadata['Type']=BIT_DEPTH_LOOKUP[metadata['Type']]
    
    #Generate uuid
    uid=str(uuid.uuid1())
    uid_attribute={"FileName":file_name}
    uid_element=etree.Element("UUID", uid_attribute)
    uid_element.text="urn:uuid:"+uid
    
    #Generate ome xml element
    attrib={"xmlns":"http://www.openmicroscopy.org/Schemas/OME/2015-01","xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance", "UUID":"urn:uuid:"+uid, "xsi:schemaLocation":"http://www.openmicroscopy.org/Schemas/OME/2015-01 http://www.openmicroscopy.org/Schemas/OME/2015-01/ome.xsd"}
    ome_xml=etree.Element('OME', attrib)

    if 'ROI' in metadata.keys():
 
        if not isinstance(metadata['ROI'], list):
            metadata['ROI']=[metadata['ROI']]
            
        for index, roi in enumerate(metadata['ROI']):
            
            roi_attrib={str(key):str(metadata['ROI'][index][key]) for key in metadata['ROI'][index].keys() if key not in ['Union']} 
            roi_element=etree.Element('ROI', roi_attrib)
            
            #Create list of shapes
            if isinstance(metadata['ROI'][index]['Union']['Shape'], list):
                shape_list=metadata['ROI'][index]['Union']['Shape']
            else:
                shape_list=[metadata['ROI'][index]['Union']['Shape']]
            
            #Generate Union element
            union_element=etree.Element('Union')
            
            #Cycle through shape list. Create shape elements
            for shape in shape_list:
                
                shape_attrib={str(key):str(shape[key]) for key in shape.keys() if key not in shapes}
                shape_element=etree.Element('Shape', shape_attrib)
            
                #Create shape_type element. Shape can only contain one shape type
                shape_type_key=[key for key in shape.keys() if key in shapes][0]
                shape_type_attrib={str(key):str(shape[shape_type_key][key]) for key in shape[shape_type_key].keys()}
                shape_type_element=etree.Element(shape_type_key, shape_type_attrib)
                shape_element.append(shape_type_element)
            
                union_element.append(shape_element)
               
            roi_element.append(union_element)
        
            #Add ROI Element to OME Element
            ome_xml.append( roi_element)
      
    #Generate Image xml element
    image_element=etree.Element('Image', {"ID":"Image:0"})
    
    #Generate Pixels xml element
    pixels_attrib={str(key):str(metadata[key]) for key in metadata.keys() if key not in ['Name','SamplesPerPixel','ROI']}  
    pixels_attrib.update({"BigEndian":"false", "DimensionOrder":metadata["DimensionOrder"], "ID":"Pixels:0"}) 
    pixels_element=etree.Element('Pixels', pixels_attrib)
    
    #Generate Channel elements and add to Pixels element
    if isinstance(metadata['SamplesPerPixel'], list):
        samples_list=metadata['SamplesPerPixel']
    else:
        samples_list=[metadata['SamplesPerPixel']]
    
    for index, samples in enumerate(samples_list):
        channel_attrib={"ID":"Channel:0:"+str(index), "SamplesPerPixel":str(samples),"Name":str(metadata['Name'][index])}
        channel_element=etree.Element('Channel', channel_attrib)
        etree.SubElement(channel_element, "LightPath")
        pixels_element.append(channel_element)

    #Generate TiffData elements and add to Pixels element
    for index, (i, j, k) in enumerate(product(range(metadata['SizeC']), range(metadata['SizeT']), range(metadata['SizeZ']))):
        tiff_data_attrib={"FirstC":str(i) ,"FirstT":str(j), "FirstZ":str(k), "IFD":str(index), "PlaneCount":"1"}
        tiff_data_element=etree.Element('TiffData', tiff_data_attrib)
        tiff_data_element.append(uid_element)
        pixels_element.append(tiff_data_element)
    
    #Add Pixels Element to Image Element
    image_element.append(pixels_element)
    
    #Add Image Element to OME Element
    ome_xml.append(image_element)
    
    return etree.tostring(ome_xml, encoding="utf-8")   


def convert_units(metadata, unit_keys, unit_dict):
    #Check units: trsanslate to OME compattible unit or else delete metadata  
    for un in unit_keys:
        
        #Try to translate unit
        if un in metadata.keys():
            
            unit=None
            if metadata[un] not in unit_dict.keys():
                for key in unit_dict.keys():
                    synonim_list=unit_dict[key]
                    if metadata[un] in synonim_list:
                        unit=key     
            else:
                unit=metadata[un]
        
            #If unit could be translated change metadata or else delete
            if unit==None:
                del metadata[un]
            else:
                metadata[un]=unit
            
    return  metadata 
