# -*- coding: utf-8 -*-
"""
Created on Tue May 15 11:28:54 2018

@author: pongor.csaba
"""
from PythImage import ImageClass


path="D:\\Playground\\testerROI4.ome.tif"#"F:\Workspace\images\\test.tif"#simplergb.ome.tif"
a = ImageClass.load_image(path, tiffType='ome')
 
#file_name="tester.ome.tif"
#a.set_metadata('Name', ['4','4'])

path2="D:\\Playground\\testerSAVEED.ome.tif"



print(a.image.shape)

a.roi_to_channel(index=1)

print(a) 

a.save_image(path=path2)