###############################################################################
#Functions to ONLY load ImageJ images. Images are loaded using the 
#Tifffile package (https://www.lfd.uci.edu/~gohlke/code/tifffile.py.html)
#of Christian Gohlke. ROI-s are read using the package imagej-tiff-meta 
#(https://github.com/csachs/imagej-tiff-meta) of Christian Sachs. Currently  
#Point, Line,Rectangle, Polygon, Ellipse, PolyLine, Polygon, composite 
#roi-s can not beloaded!!
###############################################################################

#import pip #needed to use the pip functions

#for i in pip.get_installed_distributions(local_only=True):
    #print(i)

    
#import tifffile
from .external.tifffile import TiffFile, TiffWriter
#from tifffile import TiffFile, TiffWriter
from . import utils
import numpy as np
from itertools import product
import os

def load_image(path):
    '''
    Read imageJ Tiff file. ImageJ supports maximum 6D images with the following dimension order SXYCZT 
    (in order of incresing speed). Here S is samples per pixel  (for rgb images S=3). Returns ndarray
    with normalized shape where axes of unit length are also marked. Note that order of axis will be 
    from the slowest to the fastest changing as returned by TiffFile.
    '''
    


    
    with TiffFile(path) as tif:
             
        if not tif.is_imagej:
            raise TypeError('The file is corrupt or not an ImageJ tiff file!')
        
        #Load metadata
        metadata={}
        
        #load tags from the first page  in the tiff file
        for tag in tif[0].tags.values():
            
            # Unpack ImageJ image_description and imagej_metadata tiff tags
            if tag.name=='image_description':
                description={}
                #Convert bytes type to string, split
                lines=str(tag.value, 'utf-8').split()
                for ln in lines:
                    lines_split=ln.split('=')  
                    description[lines_split[0]]=lines_split[1]
                
                metadata['image_description']=description
              
            elif tag.name=='imagej_metadata':
                #imagej_parse_overlay accepts list of ndarrays
#asdadasdasdsadsa        
                try:
                    if 'overlays' in tif.pages[0].imagej_tags.values():
                        overlays=tif.pages[0].imagej_tags.overlays
                        if isinstance(overlays, np.ndarray):
                            overlays=np.array([overlays], dtype='uint8')
                            metadata['imagej_metadata']={'overlays':imagej_parse_overlay(overlays)}
                        else:
                            metadata['imagej_metadata']={'overlays':[imagej_parse_overlay(element) for element in overlays]}
                except:
                    pass
                
            #Tiff tags            
            else:
                metadata[tag.name]=tag.value
        
        images = tif.asarray()
       
        #print('########################################')
        #print(tif.pages[0].imagej_tags.overlays[0])
        #print(parse(tif.pages[0].imagej_tags.overlays[0]))
        #print(prepare([tif.pages[0].imagej_tags.overlays[0],tif.pages[0].imagej_tags.overlays[1],tif.pages[0].imagej_tags.overlays[2],tif.pages[0].imagej_tags.overlays[3],tif.pages[0].imagej_tags.overlays[4]]))
        #print('########################################')

    return images, metadata

   
def convert_metadata(metadata_dict):
    
    '''
    Create a metadata dictionary from imageJ metadata dictionary that contains the most relevant image properties.
    Keys are a subset of the keywords used in OME-Tiff xml files.
    '''
    
    #ImageJ dimension order is'SXYCZT'
    metadata_dict_out={'DimensionOrder':'XYCZT'}
    
    #Add bitdepth data to dictionary
    bit_depth_lookup={8:'uint8', 16:'uint16', 32:'float'}
    
    bits_per_sample=metadata_dict['bits_per_sample']
    if isinstance( bits_per_sample, int):
         metadata_dict_out['Type']=bit_depth_lookup[bits_per_sample]
    
    #Add key:value pairs from image_descriptor tiff tag with direct corespondence
    shape_keys=['SizeT', 'SizeC', 'SizeZ', 'SizeX', 'SizeY']
    key_lookup={'frames':'SizeT', 'channels':'SizeC', 'slices':'SizeZ', 'spacing':'PhysicalSizeZ'}
    for key in key_lookup.keys():
        if key in metadata_dict['image_description'].keys():
     
            if key_lookup[key] in shape_keys:
      
                metadata_dict_out[key_lookup[key]]=int(metadata_dict['image_description'][key])
            else:    
                metadata_dict_out[key_lookup[key]]=metadata_dict['image_description'][key]
        
        else:
            metadata_dict_out[key_lookup[key]]=1
    
    #Add key:value pairs from non imagej specific tiff tags with direct corespondence
    key_lookup={ 'image_width':'SizeX', 'image_length':'SizeY'}
    for key in key_lookup.keys():
        if key in metadata_dict.keys():
     
            if key_lookup[key] in shape_keys:
      
                metadata_dict_out[key_lookup[key]]=int(metadata_dict[key])
            else:    
                metadata_dict_out[key_lookup[key]]=metadata_dict[key]
        else:
            metadata_dict_out[key_lookup[key]]=1

    #Create Samples per pixel and channel name list    
    metadata_dict_out['SamplesPerPixel']=[metadata_dict['samples_per_pixel']]*metadata_dict_out['SizeC']
    metadata_dict_out['Name']=['Ch'+str(i+1) for i in range(metadata_dict_out['SizeC'])]

    #Create image type list and check if all bitdepths are equal
    if not isinstance(metadata_dict['bits_per_sample'], int) :
        if utils.length(set(metadata_dict['bits_per_sample'])) != utils.length(metadata_dict['bits_per_sample']):
            metadata_dict_out['Type']=bit_depth_lookup[metadata_dict['bits_per_sample'][0]]
        else:
            raise Exception('Each sample has to have the same bitdepth!','')
    
    #Add physicalSize and units in X, Y and T to dictionary
    if 'unit' in metadata_dict.keys():
       metadata_dict_out['PhysicalSizeZUnit']=metadata_dict['unit']
    if 'x_resolution' in metadata_dict.keys():
       metadata_dict_out['PhysicalSizeX']=metadata_dict['x_resolution'][1]/metadata_dict['x_resolution'][0]
       metadata_dict_out['PhysicalSizeXUnit']=metadata_dict['image_description']['unit']
    if 'y_resolution' in metadata_dict.keys():
       metadata_dict_out['PhysicalSizeY']=metadata_dict['y_resolution'][1]/metadata_dict['y_resolution'][0]
       metadata_dict_out['PhysicalSizeYUnit']=metadata_dict['image_description']['unit']
    
    #Get time interval and unit
    if 'finterval' in metadata_dict['image_description'].keys():
        metadata_dict_out['TimeIncrement']=metadata_dict['image_description']['finterval']
        if 'tunit' in metadata_dict['image_description'].keys():
            metadata_dict_out['TimeIncrementUnit']=metadata_dict['image_description']['tunit']
    elif 'fps' in metadata_dict.keys():
        metadata_dict_out['TimeIncrement']=1/metadata_dict['image_description']['fps']
        metadata_dict_out['TimeIncrementUnit']='s'
         
    #convert overlay to roi
    if 'imagej_metadata' in metadata_dict.keys():
        if 'overlays' in metadata_dict['imagej_metadata']:
        
            for idx, overlay in enumerate(metadata_dict['imagej_metadata']['overlays']):
                    
                    #Create Union Dictionary
                    union_prop_dict={'name':'Text', 'c':'TheC', 'z':'TheZ', 't':'TheT', 'stroke_width':'StrokeWidth', 'fill_color':'FillColor', 'stroke_color':'StrokeColor', 'fill_color':'FillColor' }
                    union={union_prop_dict[key]:overlay[key] for key in  union_prop_dict.keys() if key in  overlay.keys() }
                    union['Shape']=get_shape(overlay)
                    
                    #Create ROI dictionary
                    metadata_dict_out['ROI']={'ID':'ROI:0:'+str(idx), 'Name':overlay['name'],'Union':union}
    
    #print(metadata_to_imageJ(metadata_dict_out))
    return metadata_dict_out



    
def metadata_to_imageJ(metadata, rgb=None, colormaped=False, version='1.11a',
                       hyperstack=None, mode=None, loop=None, **kwargs):
    
    """Return ImageJ image description from data shape.
    """
    
    if colormaped:
        raise NotImplementedError('ImageJ colormapping not supported')

    #Create list of imagej specific descriptors for imagej_descriptors tiff tag
    descriptors = []
    
    if hyperstack is None:
        hyperstack = True
        descriptors.append('hyperstack=true ')
    else:
        descriptors.append('hyperstack=%s ' % bool(hyperstack))
    
    if mode is None and not rgb:
        mode = 'grayscale'
        
    if hyperstack and mode:
        descriptors.append('mode=%s ' % mode)
    
    if loop is not None:
        descriptors.append('loop=%s ' % bool(loop))
    
    for key, value in kwargs.items():
        descriptors.append('%s=%s ' % (key.lower(), value))
    
   
    #Create list of general descriptors for imagej_metadata tiff tag
    imagej_metadata = ['ImageJ=%s ' % version]
    imagej_metadata.append('images=%i ' % int(metadata['SizeC']*metadata['SizeZ']*metadata['SizeT']))
    
    if 'SizeC' in metadata:
        imagej_metadata.append('channels=%i ' % metadata['SizeC'])    
    
    if 'SizeZ' in metadata:
        imagej_metadata.append('slices=%i ' % metadata['SizeZ'])         
        
    
    if 'SizeT' in metadata:
        imagej_metadata.append('frames=%i ' % metadata['SizeT'])
        if loop is None:
            descriptors.append('loop=false ')
    '''
    
    #Create list of general descriptors for imagej_metadata tiff tag
    imagej_metadata = {'ImageJ': version, 'images':int(metadata['SizeC']*metadata['SizeZ']*metadata['SizeT'])}
    
    if 'SizeC' in metadata:
        imagej_metadata['channels']=metadata['SizeC']   
    
    if 'SizeZ' in metadata:
        imagej_metadata['slices']=metadata['SizeZ']         
        
    
    if 'SizeT' in metadata:
        imagej_metadata['frames']= metadata['SizeT']
        if loop is None:
            descriptors.append('loop=false ')
    '''           
    # return imagej_metadata and imagej_descriptors tiff tag string 
    return ''.join(descriptors), ''.join(imagej_metadata)
                  
                   
def save_image(image, metadata, directory, file_name):
    '''
    Save Image. Metadata not saved currently!!
    '''
    
    #if metadata["DimensionOrder"]!='XYCZT':
        #image.reorder('XYCZT')
   
    imagej_description, imagej_metadata=metadata_to_imageJ(metadata) 
    
    print(image.shape)
    
    with TiffWriter(os.path.join(directory, file_name)) as tif:
        #for index, (i, j, k) in enumerate(product(range(metadata['SizeC']), range(metadata['SizeT']), range(metadata['SizeZ']))):
        for i, j, k in product(range(image.shape[0]),range(image.shape[1]),range(image.shape[2])):
             if i==0 and j==0 and k==0:
                 tif.save(image[i][j][k], description=imagej_description, metadata=imagej_metadata)
             else:
                 tif.save(image[i][j][k])

def get_shape(overlay):
    
    #Function to convert imageJ coordinates that are relative to top left point
    #of the bounding box
    def coordinates_to_string(left, top, coordinate_array):
        
        string=''
        for coord in coordinate_array:
            string=string+str(coord[0]+left)+','+str(coord[1]+top)+' '
    
        return string   
    
    #Get reference coordinates and coordinate array
    y1=overlay['top']
    y2=overlay['bottom']
    x1=overlay['left']    
    x2=overlay['right']

    coorinates=overlay['coordinates']
    
    #Translation of roi_type to ome-tiff roi element. Freehand roi in imagej is roi_type 7 translates to Polygon
    roi_type_dict={10:'Point',3:'Line',1:'Rectangle',0:'Polygon',2:'Ellipse', 5:'Polyline', 7:'Polygon'}
    shape=roi_type_dict[overlay['roi_type']]
    
    #Create shape dictionary
    if shape=='Point':
        shape_properties={'X':x1, 'Y':y2}
    
    if shape=='Rectangle':
        shape_properties={'X': x1, 'Y': y1, 'Width': x2-x1,  'Height': y2-y1}
        
    if shape=='Polygon':
        shape_properties={'Points':coordinates_to_string(x1, y1, coorinates)}
    
    if shape=='Polyline':
        shape_properties={'Points':coordinates_to_string(x1, y1, coorinates)}
        
    if shape=='Ellipse':
        
        width=x2-x1+1
        height=y2-y1+1
        
        x_center=x1+(width/2)
        y_center=y1+(height/2)
        
        shape_properties={'X': x_center, 'Y': y_center, 'Width': width,  'Height': height}
    
    if shape=='Line':

        shape_properties={'X1': x1, 'X2': x2, 'Y1': y2, 'Y2': y1}, 
    
    
    
    shape={shape:shape_properties}
    
    return shape
    
###############################################################################
###############################################################################
###############################################################################
# encoding: utf-8
# Copyright (c) 2017, Christian C. Sachs
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the copyright holders nor the names of any
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# https://github.com/imagej/imagej1/blob/2a6c191b027b5b1f5f22484506159f80adda21c5/ij/io/TiffDecoder.java

CONSTANT_MAGIC_NUMBER = 0x494a494a  # "IJIJ"
CONSTANT_INFO = 0x696e666f  # "info" (Info image property)
CONSTANT_LABELS = 0x6c61626c  # "labl" (slice labels)
CONSTANT_RANGES = 0x72616e67  # "rang" (display ranges)
CONSTANT_LUTS = 0x6c757473  # "luts" (channel LUTs)
CONSTANT_ROI = 0x726f6920  # "roi " (ROI)
CONSTANT_OVERLAY = 0x6f766572  # "over" (overlay)

CONST_IJ_POLYGON,\
    CONST_IJ_RECT,\
    CONST_IJ_OVAL,\
    CONST_IJ_LINE,\
    CONST_IJ_FREELINE,\
    CONST_IJ_POLYLINE,\
    CONST_IJ_NOROI,\
    CONST_IJ_FREEHAND,\
    CONST_IJ_TRACED,\
    CONST_IJ_ANGLE,\
    CONST_IJ_POINT\
    = range(11)

# https://docs.oracle.com/javase/7/docs/api/constant-values.html#java.awt.geom.PathIterator

CONST_PATH_ITERATOR_SEG_MOVETO, \
    CONST_PATH_ITERATOR_SEG_LINETO, \
    CONST_PATH_ITERATOR_SEG_QUADTO, \
    CONST_PATH_ITERATOR_SEG_CUBICTO, \
    CONST_PATH_ITERATOR_SEG_CLOSE = range(5)

# https://github.com/imagej/imagej1/blob/86280b4e0756d1f4c0fcb44ac7410138e8e6a6d8/ij/io/RoiDecoder.java

CONST_IJ_OPT_SPLINE_FIT,\
    CONST_IJ_OPT_DOUBLE_HEADED, \
    CONST_IJ_OPT_OUTLINE, \
    CONST_IJ_OPT_OVERLAY_LABELS,\
    CONST_IJ_OPT_OVERLAY_NAMES,\
    CONST_IJ_OPT_OVERLAY_BACKGROUNDS,\
    CONST_IJ_OPT_OVERLAY_BOLD, \
    CONST_IJ_OPT_SUB_PIXEL_RESOLUTION,\
    CONST_IJ_OPT_DRAW_OFFSET,\
    CONST_IJ_OPT_ZERO_TRANSPARENT,\
    = [2**bits for bits in range(10)]

IMAGEJ_ROI_HEADER_BEGIN = [
    ('_iout', '4a1'),  # always b'Iout'
    ('version', 'i2'),
    ('roi_type', 'i1'),
    ('_pad_byte', 'u1'),
    ('top', 'i2'),
    ('left', 'i2'),
    ('bottom', 'i2'),
    ('right', 'i2'),
    ('n_coordinates', 'i2')]

IMAGEJ_ROI_HEADER_PIXEL_RESOLUTION_MIDDLE = [
    ('x1', 'i4'),
    ('y1', 'i4'),
    ('x2', 'i4'),
    ('y2', 'i4'),
]

IMAGEJ_ROI_HEADER_SUB_PIXEL_RESOLUTION_MIDDLE = [
    ('x1', 'f4'),
    ('y1', 'f4'),
    ('x2', 'f4'),
    ('y2', 'f4'),
]

IMAGEJ_ROI_HEADER_END = [
    ('stroke_width', 'i2'),
    ('shape_roi_size', 'i4'),
    ('stroke_color', 'i4'),
    ('fill_color', 'i4'),
    ('subtype', 'i2'),
    ('options', 'i2'),
    ('arrow_style_or_aspect_ratio', 'u1'),
    ('arrow_head_size', 'u1'),
    ('rounded_rect_arc_size', 'i2'),
    ('position', 'i4'),
    ('header2_offset', 'i4'),
]

IMAGEJ_ROI_HEADER = IMAGEJ_ROI_HEADER_BEGIN +\
                    IMAGEJ_ROI_HEADER_PIXEL_RESOLUTION_MIDDLE +\
                    IMAGEJ_ROI_HEADER_END

IMAGEJ_ROI_HEADER_SUB_PIXEL = IMAGEJ_ROI_HEADER_BEGIN +\
                              IMAGEJ_ROI_HEADER_SUB_PIXEL_RESOLUTION_MIDDLE +\
                              IMAGEJ_ROI_HEADER_END

IMAGEJ_ROI_HEADER2 = [
    ('_nil', 'i4'),
    ('c', 'i4'),
    ('z', 'i4'),
    ('t', 'i4'),
    ('name_offset', 'i4'),
    ('name_length', 'i4'),
    #
    ('overlay_label_color', 'i4'),
    ('overlay_font_size', 'i2'),
    ('available_byte1', 'i1'),
    ('image_opacity', 'i1'),
    ('image_size', 'i4'),
    ('float_stroke_width', 'f4'),
    ('roi_props_offset', 'i4'),
    ('roi_props_length', 'i4'),
    ('counters_offset', 'i4')
]

IMAGEJ_META_HEADER = [
    ('magic', 'i4'),
    ('type', 'i4'),
    ('count', 'i4'),
]

IJM_ROI_VERSION = 226

IMAGEJ_SUPPORTED_OVERLAYS = {
        CONST_IJ_POLYGON,
        CONST_IJ_FREEHAND,
        CONST_IJ_TRACED,
        CONST_IJ_POLYLINE,
        CONST_IJ_FREELINE,
        CONST_IJ_ANGLE,
        CONST_IJ_POINT
    }


def new_record(dtype, data=None, offset=0):
    
    tmp = np.recarray(shape=(1,), dtype=dtype, aligned=False, buf=data, offset=offset).newbyteorder('>')[0]
    if data is None:
        tmp.fill(0)  # recarray does not initialize empty memory! that's pretty scary
    return tmp



def imagej_parse_overlay(data):
  
    header = new_record(IMAGEJ_ROI_HEADER, data=data)
    headerf = new_record(IMAGEJ_ROI_HEADER_SUB_PIXEL, data=data)

    header2 = new_record(IMAGEJ_ROI_HEADER2, data=data, offset=header.header2_offset)

    if header2.name_offset > 0:
        name = str(data[header2.name_offset:header2.name_offset + header2.name_length * 2], 'utf-16be')
    else:
        name = ''

    sub_pixel_resolution = (header.options & CONST_IJ_OPT_SUB_PIXEL_RESOLUTION) and header.version >= 222
    draw_offset = sub_pixel_resolution and (header.options & CONST_IJ_OPT_DRAW_OFFSET)

    sub_pixel_resolution = False

    if sub_pixel_resolution:
        header = headerf

    overlay = dict(
        name=name,
        coordinates=None,
        sub_pixel_resolution=sub_pixel_resolution,
        draw_offset=draw_offset,
    )

    if header.roi_type in IMAGEJ_SUPPORTED_OVERLAYS:
        dtype_to_fetch = np.dtype(np.float32) if sub_pixel_resolution else np.dtype(np.int16)

        coordinates_to_fetch = header.n_coordinates

        if sub_pixel_resolution:
            coordinate_offset = coordinates_to_fetch * np.dtype(np.uint16).itemsize * 2
        else:
            coordinate_offset = 0

        overlay['coordinates'] = np.ndarray(
            shape=(coordinates_to_fetch, 2),
            dtype=dtype_to_fetch.newbyteorder('>'),
            buffer=data[
                   header.itemsize + coordinate_offset:
                   header.itemsize + coordinate_offset + 2 * dtype_to_fetch.itemsize * coordinates_to_fetch
                   ],
            order='F'
        ).copy()

        overlay['multi_coordinates'] = [overlay['coordinates'].copy()]

    elif header.roi_type == CONST_IJ_RECT and header.shape_roi_size > 0:
        
        raise Exception('Composite ROI-s are not supported yet!')
        '''
        # composite / shape ROI ... not pretty to parse
        #print(header.itemsize + np.dtype(np.float32).itemsize * header.shape_roi_size)
        shape_array = np.ndarray(
            shape=header.shape_roi_size,
            dtype=np.dtype(np.float32).newbyteorder('>'),
            buffer=data[
                   header.itemsize:
                   header.itemsize + np.dtype(np.float32).itemsize * header.shape_roi_size
                   ]
        ).copy()
        print(shape_array)
        overlay['multi_coordinates'] = shape_array_to_coordinates(shape_array)

        for coords in overlay['multi_coordinates']:
            coords -= [header.left, header.top]

        overlay['coordinates'] = next(
            iter(
                sorted(
                    overlay['multi_coordinates'],
                    key=lambda coords: len(coords),
                    reverse=True
                )
            )
        )
    '''
    for to_insert in [header, header2]:
        for key in to_insert.dtype.names:
            if key[0] == '_':
                continue
            overlay[key] = np.asscalar(getattr(to_insert, key))

    return overlay


def imagej_create_roi(points, name=None, c=0, z=0, t=0, index=None):
    if name is None:
        if index is None:
            name = 'F%02d-%x' % (t+1, np.random.randint(0, 2**32 - 1),)
        else:
            name = 'F%02d-C%d' % (t+1, index,)

    points = points.copy()
    left, top = points[:, 0].min(), points[:, 1].min()
    points[:, 0] -= left
    points[:, 1] -= top

    sub_pixel_resolution = False

    if points.dtype == np.float32 or points.dtype == np.float64:
        sub_pixel_resolution = True

    encoded_data = points.astype(np.dtype(np.int16).newbyteorder('>')).tobytes(order='F')

    encoded_data_size = len(encoded_data)

    if sub_pixel_resolution:
        points[:, 0] += left
        points[:, 1] += top
        sub_pixel_data = points.astype(np.dtype(np.float32).newbyteorder('>')).tobytes(order='F')
        encoded_data += sub_pixel_data
        encoded_data_size += len(sub_pixel_data)

    header = new_record(IMAGEJ_ROI_HEADER) if not sub_pixel_resolution else new_record(IMAGEJ_ROI_HEADER_SUB_PIXEL)

    header._iout = b'I', b'o', b'u', b't'

    header.version = IJM_ROI_VERSION

    header.roi_type = CONST_IJ_FREEHAND  # CONST_IJ_POLYGON

    header.left = left
    header.top = top

    header.n_coordinates = len(points)

    header.options = 40

    if sub_pixel_resolution:
        header.options |= CONST_IJ_OPT_SUB_PIXEL_RESOLUTION

    header.position = t + 1
    header.header2_offset = header.itemsize + encoded_data_size

    header2 = new_record(IMAGEJ_ROI_HEADER2)

    # header.position is enough, otherwise it will not work as intended

    # header2.c = c + 1
    # header2.z = z + 1
    # header2.t = t + 1

    header2.name_offset = header.header2_offset + header2.itemsize
    header2.name_length = len(name)

    return header.tobytes() + encoded_data + header2.tobytes() + name.encode('utf-16be')


def imagej_prepare_metadata(overlays):
    mh = new_record(IMAGEJ_META_HEADER)

    mh.magic = CONSTANT_MAGIC_NUMBER

    # mh.type = CONSTANT_ROI
    mh.type = CONSTANT_OVERLAY
    mh.count = len(overlays)

    meta_data = mh.tobytes() + b''.join(overlays)

    byte_counts = [mh.itemsize] + [len(r) for r in overlays]  # len of overlays

    return meta_data, byte_counts

def shape_array_to_coordinates(shape_array):
    results = []
    result = []
    n = 0

    last_moveto = 0

    while n < len(shape_array):
        op = int(shape_array[n])
        if op == CONST_PATH_ITERATOR_SEG_MOVETO:
            if n > 0:
                results.append(np.array(result))
                result = []
            result.append([shape_array[n + 1], shape_array[n + 2]])
            last_moveto = len(result)
            n += 3
        elif op == CONST_PATH_ITERATOR_SEG_LINETO:
            result.append([shape_array[n + 1], shape_array[n + 2]])
            n += 3
        elif op == CONST_PATH_ITERATOR_SEG_CLOSE:
            result.append(result[last_moveto])
            n += 1
        elif op == CONST_PATH_ITERATOR_SEG_QUADTO or op == CONST_PATH_ITERATOR_SEG_CUBICTO:
            raise RuntimeError("Unsupported PathIterator commands in ShapeRoi")

    results.append(np.array(result))
    return results
