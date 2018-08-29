###############################################################################
#The ome ROI hierarchi in short is as follows. Each image can have multiple 
#ROI objects with a union object for each. Each union is made up of at least
#one shape. The shapes have a type that can be Rectangle, Mask, Point, Ellipse, 
#Line, Polyline, Polygon, Label. Among the shapes rectangle, line, point, 
#polygon, poltline and ellipse are supported. Each shape#has optional 
#attributes TheT, TheC, TheC. If any of these attributes is not present the roi
#is in all elements of that dimension eg if TheZ is specified the roi is in 
#only the given slice otherwise in all of the slices. This gives the 
#possibility to specify 3D ROI-s. Currently this is not implemented!
###############################################################################

from skimage.draw import polygon, polygon_perimeter, ellipse, line
import numpy as np
from . import utils
    


shapes=['Rectangle','Point','Ellipse','Line','Polyline','Polygon','Mask']


#ROI from imageJ overlay
def roi_from_overlay(cls, overlay):            
    print(overlay)


def roi_to_coordinates(dictionary):

    shape_dict={'Polygon':draw_polygon, 'Rectangle':draw_rectangle, 'Ellipse':draw_ellipse , 
                'Line':draw_line, 'Point': draw_point, 'Polyline':draw_polyline}
    
    #Generate shape list for ROI. ROI is the union of elements in the shape lsit
    if 'Shape' in dictionary['Union'].keys():
        if isinstance(dictionary['Union']['Shape'], dict):
            shape_list=[dictionary['Union']['Shape']]
        elif isinstance(dictionary['Union']['Shape'], list):
            shape_list=dictionary['Union']['Shape']
    else:
        if isinstance(dictionary['Union'], dict):
            shape_list=[dictionary['Union']]
        elif isinstance(dictionary['Union'], list):
            shape_list=dictionary['Union']
   
    x=[];y=[];
    for shape in shape_list:

        for key in shape.keys():
            #print(union_list[j]['Shape'])
     
            #element contains only one shape by definition
            if key in shape_dict.keys():
    
                x_list, y_list=shape_dict[key](shape[key])
     
                utils.concatenate(x,x_list)
                utils.concatenate(y,y_list)

    return x, y
        

def draw_polygon(properties):
    
  points=properties['Points']  
  
  x_coords, y_coords=zip(*map( lambda x : x.split(',') , points.split()))
 
  rr, cc = polygon(np.array(x_coords, dtype=np.uint64), np.array(y_coords, dtype=np.uint64))
  rr_peri, cc_peri = polygon_perimeter(np.array(x_coords, dtype=np.uint64), np.array(y_coords,dtype=np.uint64))
  
  rr, cc=np.concatenate((rr,rr_peri)), np.concatenate((cc,cc_peri))
  
  return rr, cc


def draw_rectangle(rectangle_params):
      
      w=rectangle_params['Width']
      h=rectangle_params['Height']
      
      x0=rectangle_params['X']
      y0=rectangle_params['Y']
      
      x_coords=[x0,x0+w,x0+w,x0]
      y_coords=[y0,y0,y0+h,y0+h]
        
      rr, cc = polygon(np.array(x_coords, dtype=np.uint64), np.array(y_coords, dtype=np.uint64))
      rr_peri, cc_peri = polygon_perimeter(np.array(x_coords, dtype=np.uint64), np.array(y_coords, dtype=np.uint64))
   
      rr, cc=np.concatenate((rr,rr_peri)), np.concatenate((cc,cc_peri))
     
      return rr, cc

 
def draw_point(parameters):
      
      x=[parameters['X']]
      y=[parameters['Y']]
      
      return x, y
  
  
def draw_ellipse(ellipse_params):
     
      
      rx=ellipse_params['RadiusX']+1
      ry=ellipse_params['RadiusY']+1
      
      x0=ellipse_params['X']
      y0=ellipse_params['Y']
      
      rr, cc = ellipse(x0, y0, rx,ry)

    
      return rr, cc

 
def draw_line(line_params):
     
      x1=int(line_params['X1'])
      y1=int(line_params['Y1'])
      
      x2=int(line_params['X2'])
      y2=int(line_params['Y2'])
      
      rr, cc = line(x1, y1, x2,y2)

      return rr, cc

 
def draw_polyline(properties):
      
    points=properties['Points']  
  
    coords=np.array(list(map( lambda x : x.split(',') , points.split())), dtype=np.uint8)
  
    rr=[];cc=[];
    for i in range(len(coords)-1):
       
        
        rr_line, cc_line = line(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1],)
        
        utils.concatenate(rr,rr_line)
        utils.concatenate(cc,cc_line) 


    return rr, cc