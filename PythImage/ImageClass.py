import numpy as np
import copy
#from .RoiClass import Roi 
from . import imagej_tiff 
from . import ome_tiff
from .roi import roi_to_coordinates
from . import utils



##Add channel, remove channel, extract channel etc.
class ImageClass(object):
    
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!TOBE FIXED return objects cpy or deepcopy etc.
    
    '''
    '''
    __PROTECTED=['SizeT', 'SizeC','SizeZ', 'SizeX','SizeY', 'SamplesPerPixel', 'Type', 'DimensionOrder']
    __DIM_TRANSLATE={'T':'SizeT', 'C':'SizeC', 'Z':'SizeZ', 'X':'SizeX', 'Y': 'SizeY'}#, 'S':'SamplesPerPixel'}
    #__BIT_DEPTH_LOOKUP=ome_tiff.BIT_DEPTH_LOOKUP
    
    
    def __init__(self, ndarray, metadata):

        #Reshape image so it contains all dimensions
        ndarray=self.__expand_singleton_dimensions(ndarray, metadata)
        
        #Check if image and metadata is valid
        self.__validate(ndarray, metadata)
        
        #Set attributes
        self.__metadata=metadata
        self.__image=ndarray

    
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
            metadata[self.__DIM_TRANSLATE[dim_current]]=length
        
        return ImageClass(image , metadata)
    
    def __repr__(self):
        rep='Shape:'+str(self.image.shape)+'\n'+utils.dict_to_string(self.__metadata)
        return rep      
    
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
        #raise PythImageError('Metadata is a protected attribute. Please use: get_metadata, set_metadata to get/set keys!','')
        return self.__metadata
    
    @metadata.setter
    def metadata(self, value):
        #Check if new metadata is compattible with image
        self.__validate(self.__image, value)
        #Set metadata
        self.__metadata=value
  
    @classmethod              
    def load(cls, path, file_type=None):
        '''
        Load image stack from path. RGB images are not supported currently and only first frame is returned.
        '''
        #Define functions to load different filetypes
        def ome(path):
        
            #Load image and create simplified metadata dictionary
            image, ome_metadata=ome_tiff.load_image(path)
    
            metadata=ome_tiff.convert_metadata(ome_metadata)
            
            return image, metadata
    
  
        def imagej(path):
            #Load image and create simplified metadata dictionary
            image, imagej_metadata=imagej_tiff.load_image(path)
            
            metadata=imagej_tiff.convert_metadata(imagej_metadata) 
            
            return image, metadata
        
        #Define dictionary of loader functions
        loader_dict={'ome':ome,'imagej':imagej}

        #Open Image
        if file_type==None:
            
                for loader in loader_dict.values():
                    try:
                        image, metadata=loader(path)
                    except:
                        pass
 

        elif file_type in loader_dict.keys():
            image, metadata=loader_dict[file_type](path)    
        
        if 'image' not in locals():
            raise Exception('Currently only {} files are supported!'.format(list(loader_dict.keys())))
       

        return cls(image, metadata)
    


              
    def save(self, directory, file_name):
        '''
        Load image stack from path. RGB images are not supported currently and only first frame is returned.
        '''        
        #Load image and create simplified metadata dictionary
        self.reorder('XYZCT')

        ome_tiff.save_image(self.image,self.metadata, directory, file_name)
                  
    
    def __validate(self, image, metadata):

        #Check if image is numpy array and metadata is dict
        if not isinstance(metadata, dict):
            raise TypeError('Metadata must be a dictionary!')
        if not isinstance(image, np.ndarray):
            raise TypeError('Image must be a a NumPy array!')
        
        #Check if metadata 'Type' field matches the type of the image
        #print('dsfgewewttergtrhtyhjtyjuyk;uihdhfhhhhhhhhhhh',image.dtype)
        #if self.__BIT_DEPTH_LOOKUP[metadata['Type']]!=image.dtype:
             #metadata['Type']=utils.value_to_key(self.__BIT_DEPTH_LOOKUP, image.dtype)
             #raise TypeError('Image data type does not mach the one specified in the metadata!')
             
        #Check if number of channels and length of the name list is the same
        if 'SizeC' in metadata.keys():
           
            if isinstance(metadata['SamplesPerPixel'], list):
                sample_cnt=sum(metadata['SamplesPerPixel'])
            
            elif isinstance(metadata['SamplesPerPixel'], int):
                sample_cnt=metadata['SamplesPerPixel']
          
            if sample_cnt!=metadata['SizeC']:
                raise Exception('Invalid SamplesPerPixel list!','')  
            
            if utils.length(metadata['Name'])!=metadata['SizeC']:
                raise Exception('Length of Name list is invalid!','')
        
        #Rename duplicate names in the 'Name' field of the metadata
        if isinstance(metadata['Name'], list):
            metadata['Name']=utils.rename_duplicates(metadata['Name'])
        else:
            metadata['Name']=utils.rename_duplicates([metadata['Name']])[0]
    
        
        #Check if dimension order is acceptable;
        dimensions=self.__DIM_TRANSLATE.keys()
        if len(metadata['DimensionOrder'])!=len(dimensions):
            raise Exception('Dimension orders have to be a permutation of accepted dimensions: '+str(dimensions))
        #Check if all letters are in the dimension and only once:
        for dim in dimensions :
            cnt=metadata['DimensionOrder'].count(dim)
            if cnt!=1:
                raise Exception('Dimension orders have to be a permutation of accepted dimensions! Number of occurrences of '+str(dim)+' is '+str(cnt))
                
        #Check if image shape confers with the one in the metadata
        #Remove singleton dimensions
        shape_image=[val for val in image.shape if val!=1]
        available_keys=[self.__DIM_TRANSLATE[dim] for dim in reversed(metadata['DimensionOrder']) if self.__DIM_TRANSLATE[dim] in metadata.keys()]
 
        shape_metadata=[metadata[key] for key in available_keys if metadata[key]!=1]
  
        if shape_image!=shape_metadata:
            raise Exception('shape information in metadata is not compattible to the image shape!','')
    
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

        if key not in self.__PROTECTED:

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

    

    def append_to_dimension(self, img, dim='C'):

        #Append names
        if dim=='C':
            self.__metadata['Name']=utils.concatenate(self.__metadata['Name'],img.get_metadata('Name'))
            self.__metadata['SamplesPerPixel']=utils.concatenate(self.__metadata['SamplesPerPixel'], img.get_metadata('SamplesPerPixel'))
 
        #Get original dimension order
        original_order=self.__metadata['DimensionOrder']
    
        #reshape image so the two confer
        img.reorder(original_order)
        
        #Get the index of the given dimension in the shape of the image
        ind=len(original_order)-original_order.index(dim)-1
        
        self.__metadata[self.__DIM_TRANSLATE[dim]]=self.__metadata[self.__DIM_TRANSLATE[dim]]+img.get_metadata(self.__DIM_TRANSLATE[dim])

        self.image=np.concatenate((self.image,img.image), axis=ind)
       
       
        
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
                        
            #Create shape tuple
            shape=[1]*len(order)
            for idx, dim in enumerate(order):
                if dim!='C':
                    shape[idx]=self.__metadata[self.__DIM_TRANSLATE[dim]]
                if dim=='C':
                    shape[idx]=1
                       
            shape=tuple(shape)

            #create metadata dictionary for roi and set channel to 1
            roi_metadata=self.__metadata.copy()
            roi_metadata['SizeC']=1
            roi_metadata['Name']=roi_list[index]['ID']
            roi_metadata['SamplesPerPixel']=1
            del roi_metadata['ROI']
            
            #Set roi pixel values
            img=np.zeros(shape, dtype=self.__metadata['Type'])
            rr, cc = roi_to_coordinates(roi_list[index])            
            
            cc_mod=[]
            rr_mod=[]
            for idx in range(len(cc)):
                if  rr[idx]<roi_metadata['SizeY'] and cc[idx]<roi_metadata['SizeX']:
                    rr_mod.append(rr[idx])
                    cc_mod.append(cc[idx])
            
            img[:,:,:, cc_mod,rr_mod] = value
            
            #Create new ImageClass object
            roi=ImageClass(img, roi_metadata )

            self.append_to_dimension(roi, dim='C')
        
        else:
            raise Exception('No ROI available!', '')
                
    def reorder(self, order):
        '''
        Reordet dimension order to the one specified in final_dim_order.Both have to 
        be the same length and confer with number of axes in ndarray!
        Reshape array so it has all the axes
        '''
        order_current=list(reversed(list(self.__metadata['DimensionOrder'])))
        order_final=list(reversed(list(order)))
        
        #Cycle through image dimension order, check for differences in final order and replace
        for idx, dim in enumerate(order_current):
            
            if dim!=order_final[idx] :
                
                index_current=idx
                index_final=order_final.index(dim)

                self.__image=self.__image.swapaxes(index_final,index_current)
                
                order_current[index_current], order_current[index_final] = order_current[index_final], order_current[index_current]
                
        #Set final dimension order
        self.__metadata['DimensionOrder']=''.join(reversed(order_current))

    def __merge_axes(ndarray, dim_order='SXYCZT', axis1='S', axis2='C'):
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


    def z_projection (self):
        '''Needs to be implemented
        '''
        #numpy.dstack(tup)[source]¶
        pass
    
    def as_type(self, dtype):
        
        if dtype!=self.metadata['Type']:
            self.__image=self.image.astype(dtype)
            self.__metadata['Type']=dtype

    

    def __expand_singleton_dimensions(self, ndarray, metadata):

        dim_order_list=metadata['DimensionOrder']

     
        shape=[1]*len(dim_order_list)

        for i, dim in enumerate(dim_order_list):
            if dim in ImageClass.__DIM_TRANSLATE.keys() and dim!='S':
                
                key=ImageClass.__DIM_TRANSLATE[dim]
             
                if key in metadata.keys():
                    shape[i]=int(metadata[key])
                else:
                    shape[i]=1
        
        shape.reverse()

        output=np.reshape(ndarray, tuple(shape))
        
        return output
       
    
