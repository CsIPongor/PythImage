import os
import numpy as np
from skimage.external.tifffile import TiffFile, TiffWriter
import copy
from itertools import product

from . import utils
from .roi import RoiClass

##Add channel, remove channel, extract channel etc.
class ImageClass(object):
    
    '''TOBE FIXED return objects cpy or deepcopy etc.
    
    '''
    
    __protected=['SizeT', 'SizeC','SizeZ', 'SizeX','SizeY', 'SamplesPerPixel', 'Type', 'DimensionOrder']
    __dim_translate={'T':'SizeT', 'C':'SizeC', 'Z':'SizeZ', 'X':'SizeX', 'Y': 'SizeY', 'S':'SamplesPerPixel'}
   
    
    def __init__(self, image, metadata):
        
        #Check if image and metadata is valid
        self.__validate(image, metadata)
        self.__metadata=metadata
        #Reshape image so it contains all dimensions
        self.__image=self.__expand_singleton_dimensions(image, metadata)
        
    def __call__(self, T=None, C=None, Z=None):
  
        local_dict=locals()    
        arg_list = [arg for arg in  ('T', 'C', 'Z') if arg in local_dict.keys() if local_dict[arg]!=None ]
        indexes=tuple([local_dict[arg] for arg in arg_list])
        
        dimensions=list(self.__metadata['DimensionOrder'])
        dimension_order=[dim for dim in dimensions if dim not in arg_list]+arg_list
       
        self.reorder(dimension_order)
        
        shape=tuple(reversed(list(self.__image.shape)))
        metadata_new=self.__metadata.copy()
        for dim in dimension_order:
            if dim in ('T', 'C', 'Z'):
                if isinstance(local_dict[dim], int):
                    metadata_new[self.__dim_translate[dim]]=1
                if isinstance(local_dict[dim], list):    
                    metadata_new[self.__dim_translate[dim]]=len(local_dict[dim])
        
        return self.__init__(image=self.__image[indexes].copy(),metadata=metadata_new)
    
    
    def __getitem__(self, key):
        

        shape=self.__image.shape
        metadata=copy.deepcopy(self.__metadata)
        image=copy.deepcopy(self.__image[key])
        order=tuple(reversed(list(metadata['DimensionOrder'])))
        
        
        if isinstance(key, (int,slice)):
            key=[key]
        if len(key)>len(shape):
            raise ValueError('Invalid slice object!')
     
        for i in range(len(key)):
            
            length=ImageClass.__slice_length(key[i], shape[i])
            dim_current=order[i]
            
            if dim_current=='C':
                metadata['Name']=np.squeeze(metadata['Name'][key[i]]).tolist()
                metadata['SamplesPerPixel']=np.squeeze(metadata['SamplesPerPixel'][key[i]]).tolist()
            metadata[self.__dim_translate[dim_current]]=length
        
        return ImageClass(image=image ,metadata=metadata)
    
    def __repr__(self):
        return utils.dict_to_string(self.__metadata)     
    
    def __getattr__(self, atr):
        raise AttributeError("Attribute: "+str(atr)+" is not available!")           
   
    @property
    def image(self):
        return self.__image
    
    @image.setter
    def image(self, value):
        #Check if new image is compattible with metadata
        self.__validate(value, self.__metadata)
        #Set new image
        self.__image=value
          
    @property
    def metadata(self):
        raise PythImageError('Metadata is a protected attribute. Please use: get_metadata, set_metadata to get/set keys!','')
    
    @metadata.setter
    def metadata(self, value):
        #Check if new metadata is compattible with image
        self.__validate(self.__image, value)
        #Set metadata
        self.__metadata=value

    
    
    @classmethod              
    def load_image(cls, path, tiffType='imageJ', **kwargs):
        '''
        Load image stack from path. RGB images are not supported currently and only first frame is returned.
        '''
        
        kwargs=dict(**kwargs)
        
        if tiffType=='ome':

            
            #Load image and create simplified metadata dictionary
            image, ome_metadata=ImageClass.load_ome(path)
            metadata=ImageClass.convert_ome_metadata(ome_metadata)

                   
        elif tiffType=='imagej':
            
            #Load image and create simplified metadata dictionary
            image, imagej_metadata=ImageClass.load_imagej(path)
            
            metadata=ImageClass.convert_imagej_metadata(imagej_metadata)
            
            '''        
            dim_order_final='XYZCT'
            #Change dimension order to the one specified in dim_order_final
            dim_order=metadata['DimensionOrder']
            image=ImageClass.reorder(dim_order, 'SXYZCT')
             
            #Reshape image so output image has separate channels for S dimension
            if metadata['SamplesPerPixel']>1:
                image=ImageClass.merge_axes(image, 5, 1)
            metadata['DimensionOrder']=dim_order_final
            
            #For hyperstacks remove S singleton dimension
            if image.shape[-1]==1:
                image=np.squeeze(image, axis=5)
            '''    
        
        elif tiffType=='tiff':
             #Load image and create simplified metadata dictionary
            image, metadata=ImageClass.load_tiff(path)
            metadata=ImageClass.convert_tiff_metadata(metadata, order=kwargs['order'], shape=kwargs['shape'])
        
        #Return first timeframe
        return cls(image=image, metadata=metadata)
    

    def __validate(self, image, metadata):

        #Check if image is numpy array and metadata is dict
        if not isinstance(metadata, dict):
            raise TypeError('metadata must be a dictionary!')
        if not isinstance(image, np.ndarray):
            raise TypeError('image must be a a NumPy array!')
        
        #Check if metadata 'Type' field matches the type of the image
        if not metadata['Type']==image.dtype:
             raise TypeError('image data type does not mach the one specified in the metadata!')
             
        #Check if number of channels and length of the name list is the same
        if 'SizeC' in metadata.keys() :
            if utils.length(metadata['Name'])!=metadata['SizeC']:
                raise PythImageError('Missing Name of one or more channels!','')
            if utils.length(metadata['SamplesPerPixel'])!=metadata['SizeC']:
                raise PythImageError('Missing SamplesPerPixel of one or more channels!','')
     
            
        #Check if image shape confers with the one in the metadata
        #Remove singleton dimensions
        shape_image=[val for val in image.shape if val!=1]
        shape_metadata=[metadata[self.__dim_translate[dim]] for dim in reversed(metadata['DimensionOrder']) if metadata[self.__dim_translate[dim]]!=1]
        if shape_image!=shape_metadata:
            raise PythImageError('shape information in metadata is not compattible to the image shape!','')
    
    
    def __expand_singleton_dimensions(self, image, metadata):

        dim_order_list=metadata['DimensionOrder']
      
        shape=[1]*len(dim_order_list)
        for i, dim in enumerate(dim_order_list):
            if dim in self.__dim_translate.keys() and dim!='S':
                key=self.__dim_translate[dim]
             
                if key in metadata.keys():
                    shape[i]=int(metadata[key])
                else:
                    shape[i]=1
        shape.reverse()
       
        return np.reshape(image, tuple(shape))
    
    @staticmethod
    def __slice_length(slice_object, object_length):
        '''Calculate length of slice from slice object.
        '''
        if isinstance(slice_object, int):
            slice_length=1 
        if isinstance(slice_object, slice):
            slice_length=len(range(*slice_object.indices(object_length)))
        
        return  slice_length
    
    def get_metadata(self, key):
        return self.__metadata[key]
    
  
    def set_metadata(self, key, value):

        if key not in self.__protected:

            if key in self.__metadata:
                
                if type(self.__metadata[key])!=type(value):
                    raise TypeError("The type of the given value does not match the metadata type!")
                
                if hasattr(value, '__len__'):

                    if len(self.__metadata[key])!=len(value):
                  
                        raise TypeError("The length of the given value does not match that of metadata type!")
                
                    else:
                        self.__metadata[key]=value
            
            else:
                self.__metadata[key]=value 

        else:
            raise KeyError('Key is not meant for direct access!')

    
    
    def append_to_dimension(self, image, dim):
        
      
        #Append names
        self.__metadata['Name']=utils.concatenate(self.__metadata['Name'],image.get_metadata('Name'))
        self.__metadata['SamplesPerPixel']=utils.concatenate(self.__metadata['SamplesPerPixel'], image.get_metadata('SamplesPerPixel'))
 
        #Get original dimension order
        original_order=self.__metadata['DimensionOrder']
    
        #reshape image so the two confer
        image.reorder(original_order)
        
        #Get the index of the given dimension in the shape of the image
        ind=len(original_order)-original_order.index('C')-1
        
        self.__metadata[self.__dim_translate[dim]]=self.__metadata[self.__dim_translate[dim]]+image.get_metadata(self.__dim_translate[dim])

        self.image=np.concatenate((self.image,image.image), axis=ind)
       
       
        
    def roi_to_channel(self, index, value=1):
      

        if 'ROI' in self.__metadata.keys():
          
            
            #Generate roi list. If image has multiple ROI-s, metadata['ROI'] is a list.
            if isinstance(self.__metadata['ROI'], dict):
                roi_list=[self.__metadata['ROI']]
            elif isinstance(self.__metadata['ROI'], list):
                roi_list=self.__metadata['ROI']
            
            #Check if index is within possible range
            if index>=len(roi_list):
                raise IndexError('Only '+str(len(roi_list))+' ROI(s) available!')
            
            #Get reversed dimension order
            order=self.__metadata['DimensionOrder'][::-1]

            #create metadata dictionary for roi and set channel to 1
            roi_metadata=self.__metadata.copy()
            roi_metadata['SizeC']=1
            roi_metadata['Name']=roi_list[index]['ID']
            roi_metadata['SamplesPerPixel']=1
            del roi_metadata['ROI']
            
            #Create shape tuple
            shape=[1]*len(order)
            for idx, dim in enumerate(order):
                if dim!='C':
                    shape[idx]=self.__metadata[self.__dim_translate[dim]]
                if dim=='C':
                    shape[idx]=1
            
            shape=tuple(shape)

            img=np.zeros(shape, dtype=self.__metadata['Type'])
            
            rr, cc = RoiClass(roi_list[index]).coordinates
            
            #Create slice object to set value of ROI pixels
            slice_object_list=[1]*len(order)
            for idx, dim in enumerate(order):
                if dim=='X':
                    slice_object_list[idx]=rr
                elif dim=='Y':
                    slice_object_list[idx]=cc
                else:    
                    slice_object_list[idx]=slice(None,None,None)
       
            #Set roi pixel values
            img[slice_object_list] = value
            #img[:,:,:,cc,rr] = value

            #Create new ImageClass object
            roi=ImageClass(img, roi_metadata )
            
            self.append_to_dimension(roi, dim='C')

            
        else:
            raise PythImageError('No ROI available!')
                
    
    '''
    def __update_metadata__(self):
        
        order=self.__metadata['DimensionOrder']
        
        
        
        print(len(order))
        
        #remove singleton dimensions
        dim_translate={'T':self.__metadata['SizeT'], 'C':self.__metadata['SizeC'], 'Z':self.__metadata['SizeZ'], 'X':self.__metadata['SizeX'], 'Y': self.__metadata['SizeY']}
        singleton_dim=[key for key in dim_translate if int(dim_translate[key])<=1]
        
        for i in range(len(order)):
            key=dim_translate[order[i]]
            self.__metadata[key]=shape[i]
        
    '''    
        
    def save_image(self, path):
        '''
        Save Image. Metadata not saved currently!!
        '''
   
        if 'S' in self.__metadata['DimensionOrder']:
            order_final='SXYCZT'
        else:
           order_final='XYCZT'

        
        self.reorder(order_final)
        
        file_name=os.path.basename(path)

        
        with TiffWriter(path) as tif:
            #for index, (i, j, k) in enumerate(product(range(metadata['SizeC']), range(metadata['SizeT']), range(metadata['SizeZ']))):
            for i, j, k in product(range(self.__image.shape[0]),range(self.__image.shape[1]),range(self.__image.shape[2])):

                 tif.save(self.__image[i][j][k], description=self.metadata_to_ome(self.__metadata, file_name ))
    
    def save_image2(image, path, file_name):
        '''
        Save Image. Metadata not saved currently!!
        '''
        path=os.path.join(path,file_name)
        with TiffWriter(path) as tif:
            for i, j, k in product(range(image.shape[0]),range(image.shape[1]),range(image.shape[2])):
                 tif.save(image[i][j][k])
    

    
    @staticmethod
    def load_tiff(path, frames_per_sec=1, z_increment=1 ):

        
        with TiffFile(path) as tif:
         
            #Load metadata 
            metadata={'fps':frames_per_sec, 'spacing':z_increment }
            #for page in tif:
            for tag in tif[0].tags.values():

                 metadata[tag.name]=tag.value

            
            images = tif.asarray() 

        return images, metadata
    
    @staticmethod
    def convert_tiff_metadata(metadata_dict, shape, order):
        
        '''
        
        '''
        
        #ImageJ dimension order is'SXYCZT'
        metadata_dict_out={'DimensionOrder':order, 'SizeX':metadata_dict['image_width'], 'SizeY':metadata_dict['image_length']}
        
        #Add bitdepth annd SamplesPerPixel data to dictionary
        bit_depth_lookup={8:'uint8', 16:'uint16', 32:'float'}
        
        bits_per_sample=metadata_dict['bits_per_sample']
        if isinstance( bits_per_sample, int):
             metadata_dict_out['Type']=bit_depth_lookup[bits_per_sample]
             metadata_dict_out['SamplesPerPixel']=1
        
        elif isinstance(bits_per_sample, tuple):
            #Convert to set to determine if all values are equal
            if len(set(bits_per_sample))== 1:
                metadata_dict_out['Type']=bit_depth_lookup[bits_per_sample[0]]
            else:
                raise TypeError('All samples have to have the same bitdepth!')
            metadata_dict_out['SamplesPerPixel']=len(bits_per_sample)
        
        
        #Add remaining shape information
        key_lookup={'T':'SizeT', 'C':'SizeC', 'Z':'SizeZ', 'X':'SizeX', 'Y':'SizeY', 'S':'SamplesPerPixel'}
        for dim in order:
            if dim=='S':

                if metadata_dict_out['SamplesPerPixel']!=shape[-1*(1+order.index(dim))]:
                  raise PythImageError('Invalid shape for dataset','')
                
            if dim=='X':                
                if metadata_dict_out['SizeX']!=shape[-1*(1+order.index(dim))]:
                  raise PythImageError('Invalid shape for dataset','') 
        
            if dim=='Y':                
                if metadata_dict_out['SizeY']!=shape[-1*(1+order.index(dim))]:
                  raise PythImageError('Invalid shape for dataset','')  
            
            metadata_dict_out[key_lookup[dim]]=shape[-1*(1+order.index(dim))]
                
                
        #Add physicalSize and units in X, Y and T to dictionary
        if 'x_resolution' in metadata_dict.keys():
           metadata_dict_out['PhysicalSizeX']=metadata_dict['x_resolution'][1]/metadata_dict['x_resolution'][0]     
           
        if 'y_resolution' in metadata_dict.keys():
           metadata_dict_out['PhysicalSizeY']=metadata_dict['y_resolution'][1]/metadata_dict['y_resolution'][0]
           
        if 'resolution_unit' in metadata_dict.keys():
            unit_dict={1:'None', 2:'inch', 3:'mm'}
            metadata_dict_out['PhysicalSizeXUnit']=unit_dict[metadata_dict['resolution_unit']]
            metadata_dict_out['PhysicalSizeYUnit']=unit_dict[metadata_dict['resolution_unit']]
        else:
            metadata_dict_out['PhysicalSizeXUnit']='inch'
            metadata_dict_out['PhysicalSizeYUnit']='inch'
        
        if 'fps' in metadata_dict.keys():
            metadata_dict_out['TimeIncrement']=1/metadata_dict['fps']
            metadata_dict_out['TimeIncrementUnit']='s'
       
        return metadata_dict_out
    
    
    @staticmethod    
    def load_imagej(path):
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
            #for page in tif:
            for tag in tif[0].tags.values():
                
                # Unpack ImageJ image_description
                if tag.name=='image_description':
                    
                    #Convert bytes type to string, split
                    lines=str(tag.value, 'utf-8').split()
                    
                    for ln in lines:
                        lines_split=ln.split('=')
                        
                        metadata[lines_split[0]]=lines_split[1]
                else:
                   
                    metadata[tag.name]=tag.value
            
            images = tif.asarray()    
            
            '''
            dim_order='SXYCZT'
            dim_order_list=list(dim_order)
            lookup={'S':'samples_per_pixel','C':'channels', 'T':'frames', 'Y':'image_length', 'X':'image_width', 'Z': 'slices'}
            shape=[0]*len(dim_order_list)
            for i in range(len(dim_order_list)):
                if dim_order_list[i] in lookup.keys():
                    key=lookup[dim_order_list[i]]
                    if key in metadata.keys():
                        shape[i]=int(metadata[key])
                    else:
                        shape[i]=1
            shape.reverse()
           
            images=np.reshape(images, tuple(shape))
            '''
        #print(metadata.keys())
        return images, metadata
    
    
    @staticmethod
    def load_ome(path):
        '''
        Read OME-Tiff file. Supported OME dimension orders are :'XYZCT','XYZTC','XYCZT','XYTCZ','XYCTZ'
        and 'XYTZC' (in order of incresing speed). For files with channels where SamplesPerPixel>1 the 
        C dimension will also contain the different Samples separately. For example a 4 channel rgb image
        (SamplesPerPixel=3)  will contain 4*3 channels. Returns ndarray with normalized shape where axes 
        of unit length are also marked. Note that order of axis will be from the slowest to the fastest 
        changing as returned by TiffFile.
        '''
        #Ignore some tiffile warnings that always occur ??Bug??
        import warnings
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
            #pixel_metadata=ome_metadata['OME']['Image']['Pixels']
            
       
            #Reordet dimension order to the one specified in final_dim_order
            #Reshape array so it has all the axes
            #dim_order_list=list(pixel_metadata['DimensionOrder'])
            #dim_translate={'T':'SizeT', 'C':'SizeC', 'Z':'SizeZ', 'X':'SizeX', 'Y': 'SizeY'}
            #size_list=[pixel_metadata[dim_translate[dim_order_list[i]]] if dim_order_list[i] in dim_translate.keys() else None for i in range(len(dim_order_list))  ]
            #size_list.reverse()
            
            #images=np.reshape(images, tuple(size_list))
          
       
        return images, ome_metadata
    
    def merge_axes(ndarray, axis1, axis2):
        '''
        Merge two axes. First the axes are swaped so the two axes are besides each other
        then the ndarray is linearized and reshaped.
        '''
        #Determine which axes is larger
        largest_axis=max(axis1, axis2)
        smallest_axis=min((axis1, axis2))
        
        #Generate final shape
        shape=list(ndarray.shape)
        shape[smallest_axis]=shape[smallest_axis]*shape[largest_axis]
        del shape[largest_axis]
        
        #Swap axes so the two axes are besides each other
        ax=largest_axis
        while ax>smallest_axis:
            ndarray=ndarray.swapaxes(ax,ax-1)
            ax-=1
        #Ravel, reshape and return result
        return np.reshape(ndarray.ravel(), shape)
    
    def merge_axes2(ndarray, dim_order='SXYCZT', axis1='S', axis2='C'):
        '''
        Merge two axes. First the axes are swaped so the two axes are besides each other
        then the ndarray is linearized and reshaped.
        '''
        #Determine which axes is larger
        largest_axis=max(axis1, axis2)
        smallest_axis=min((axis1, axis2))
        
        #Generate final shape
        shape=list(ndarray.shape)
        shape[smallest_axis]=shape[smallest_axis]*shape[largest_axis]
        del shape[largest_axis]
        
        #Swap axes so the two axes are besides each other
        ax=largest_axis
        while ax>smallest_axis:
            ndarray=ndarray.swapaxes(ax,ax-1)
            ax-=1
        #Ravel, reshape and return result
        return np.reshape(ndarray.ravel(), shape)
    
    @staticmethod
    def convert_ome_metadata(metadata_dict):
        
        '''
        Create a simplified metadata dictionary from dictionaries extracted from the OME-Tiff xml files.
        '''
        
        metadata_dict_out={}        
    
        #print(b.keys())
        #Only keep metadata that ar used from the input dictionary 
        pixels_dict=metadata_dict['OME']['Image']['Pixels']

        
        #Add optional keys if present
        unit_keys=['SizeT', 'SizeC', 'SizeZ', 'SizeX', 'SizeY','PhysicalSizeX', 'PhysicalSizeXUnit', 'PhysicalSizeY', 'PhysicalSizeYUnit', 'PhysicalSizeZ', 'PhysicalSizeZUnit', 'TimeIncrement','TimeIncrementUnit','DimensionOrder','Type']
        for key in unit_keys:
            if key in pixels_dict.keys():
                metadata_dict_out[key]=pixels_dict[key]
        
        metadata_dict_out['SamplesPerPixel']=[dic['SamplesPerPixel'] if 'SamplesPerPixel' in dic.keys() else 1 for dic in pixels_dict['Channel']]
        metadata_dict_out['Name']=[dic['Name'] if 'Name' in dic.keys() else 'Ch'+str(index) for index, dic in enumerate(pixels_dict['Channel'])]
        
        #Get ROI-s if present
        if 'ROI' in metadata_dict['OME'].keys():
           metadata_dict_out['ROI']=metadata_dict['OME']['ROI']
                
        
        
        return metadata_dict_out
    
    @staticmethod    
    def convert_imagej_metadata(metadata_dict):
        '''
        Create a metadata dictionary from imageJ metadata dictionary that contains the most relevant image properties.
        Keys are a subset of the keywords used in OME-Tiff xml files.
        '''
        
        #ImageJ dimension order is'SXYCZT'
        metadata_dict_out={'DimensionOrder':'SXYCZT'}
        
        #Add bitdepth data to dictionary
        bit_depth_lookup={8:'uint8', 16:'uint16', 32:'float'}
        
        bits_per_sample=metadata_dict['bits_per_sample']
        if isinstance( bits_per_sample, int):
             metadata_dict_out['Type']=bit_depth_lookup[bits_per_sample]
        elif isinstance(bits_per_sample, tuple):
            #Convert to set to determine if all values are equal
            if len(set(bits_per_sample))== 1:
                metadata_dict_out['Type']=bit_depth_lookup[bits_per_sample[0]]
            else:
                raise TypeError('All samples have to have the same bitdepth!')
        
        #Add key values with direct correspondence
        key_lookup={'frames':'SizeT', 'channels':'SizeC', 'slices':'SizeZ', 'image_width':'SizeX', 'image_length':'SizeY', 'samples_per_pixel':'SamplesPerPixel','spacing':'PhysicalSizeZ', 'unit':'PhysicalSizeZUnit'}
        shape_keys=['SizeT', 'SizeC', 'SizeZ', 'SizeX', 'SizeY']
        for key in key_lookup.keys():
            if key in metadata_dict.keys():
         
                if key_lookup[key] in shape_keys:
          
                    metadata_dict_out[key_lookup[key]]=int(metadata_dict[key])
                else:    
                    metadata_dict_out[key_lookup[key]]=metadata_dict[key]
         
                
        #Add physicalSize and units in X, Y and T to dictionary
        if 'x_resolution' in metadata_dict.keys():
           metadata_dict_out['PhysicalSizeX']=metadata_dict['x_resolution'][1]/metadata_dict['x_resolution'][0]
           metadata_dict_out['PhysicalSizeXUnit']=metadata_dict['unit']
        if 'y_resolution' in metadata_dict.keys():
           metadata_dict_out['PhysicalSizeY']=metadata_dict['y_resolution'][1]/metadata_dict['y_resolution'][0]
           metadata_dict_out['PhysicalSizeYUnit']=metadata_dict['unit']
        
        #Get time interval and unit
        if 'finterval' in metadata_dict.keys():
            metadata_dict_out['TimeIncrement']=metadata_dict['finterval']
            if 'tunit' in metadata_dict.keys():
                metadata_dict_out['TimeIncrementUnit']=metadata_dict['tunit']
        elif 'fps' in metadata_dict.keys():
            metadata_dict_out['TimeIncrement']=1/metadata_dict['fps']
            metadata_dict_out['TimeIncrementUnit']='s'
              
        return metadata_dict_out
    
    def z_projection (self):
        '''Needs to be implemented
        '''
        pass
      
    def reorder(self, order):
        '''
        Reordet dimension order to the one specified in final_dim_order.Both have to 
        be the same length and confer with number of axes in ndarray!
        Reshape array so it has all the axes
        '''
        order=list(order)
        dim_order_list=list(self.__metadata['DimensionOrder'])
        order_final=order.copy()
        
        #Remove singleton dimensions
        dim_translate={'T':self.__metadata['SizeT'], 'C':self.__metadata['SizeC'], 'Z':self.__metadata['SizeZ'], 'X':self.__metadata['SizeX'], 'Y': self.__metadata['SizeY']}
        singleton_dim=[key for key in dim_translate if int(dim_translate[key])<=1]
        
        for dim in singleton_dim:
            order.remove(dim)
            dim_order_list.remove(dim)
      
        #Cycle through image dimension order, check for differences in final order and replace
        axis_number=len(order)-1
        for i in range(len(dim_order_list)):
           
            if dim_order_list[i]!=order[i] :
                axis_index_current=i
                axis_index_final=order.index(dim_order_list[i])
                
                self.__image=self.__image.swapaxes(axis_number-axis_index_current, axis_number-axis_index_final)
                dim_order_list[axis_index_current], dim_order_list[axis_index_final] = dim_order_list[axis_index_final], dim_order_list[axis_index_current]
       
        #Set final dimension order
        self.__metadata['DimensionOrder']=''.join(order_final)
        

      
    
    @staticmethod
    def metadata_to_ome (metadata, file_name):
        '''
        Convert internal metadata representation to conform with ome/tiff specification.
        '''
        import uuid
        from xml.etree import cElementTree as etree 
        
        #Generate uuid
        uid=str(uuid.uuid1())
        uid_attribute={"FileName":file_name}
        uid_element=etree.Element("UUID", uid_attribute)
        uid_element.text="urn:uuid:"+uid
        
        #Generate ome xml element
        attrib={"xmlns":"http://www.openmicroscopy.org/Schemas/OME/2015-01","xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance", "UUID":"urn:uuid:"+uid, "xsi:schemaLocation":"http://www.openmicroscopy.org/Schemas/OME/2015-01 http://www.openmicroscopy.org/Schemas/OME/2015-01/ome.xsd"}
        ome_xml=etree.Element('OME', attrib)
        #Generate Image xml element
        image_element=etree.Element('Image', {"ID":"Image:0"})
        
        #Generate Pixels xml element
        pixels_attrib={str(key):str(metadata[key]) for key in metadata.keys() if key not in ['Name','SamplesPerPixel']}        
        pixels_attrib.update({"BigEndian":"false", "DimensionOrder":"XYZCT", "ID":"Pixels:0"}) 
        pixels_element=etree.Element('Pixels', pixels_attrib)
        
        #Generate Channel elements and add to Pixels element
        for index, samples in enumerate(metadata['SamplesPerPixel']):
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
    
#Class for error handling
class PythImageError(Exception):
    
    def __init__(self, message, errors):
        
        super(PythImageError, self).__init__(message)
        self.message = message
        self.errors = errors
    
    def __str__(self):
        return repr(self.message)