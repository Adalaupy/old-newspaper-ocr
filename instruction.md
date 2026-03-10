Planning:

# Introduction:
a python program for OCR, specified for traditional Chinese old newspaper with user interface.

# General Step to use:
1. user import 1 or multiple newspaper (image/pdf) to the program
2. allow user to use a rectangle selection tool to select a specific parts of the news (can be multiple), if no selection, default full page
3. as it's old Chinese newspaper, the direction can be either from left to right or vice reverse, horizontally or vertically. by default right top to left bottom, provide a drop down list for user to select
4. UI also provide a OCR result preview in text
5. save the result to a folder


# UI - maybe tkinter library
- allow multiple upload each batch, but display one image each time, click arrow to switch

1. Input Elements for whole batch (shared)
	- read direction
	- language
	
2. Input Elements for each image
	- file name: text, if null , auto set date in "yyyymmdd_{id + 1}"
	- read direction: specify if different from others
	- crop area: drag select and return x,y,w,h, label your crop with red rantangles
	
3. Other buttons:
	- zoom in / out or back to original size
	- rotatation: click button and immediate rotate the image --> instant update the image content
	- submit: push the data to create a class "Image" and backend handle OCR "Fn_Preprocess_Img" and "Fn_OCR"
	- redo: remove current crop rectangle --> update the "cropped" variable from class

4. Preview Result in text
	- Save -> trigger:Fn_Save_Result


# Backend Part: To enhance the program changeability, split the whole application into parts, not a must to use python Class

1. Main Class: Imported Image / pdf : unit: each single imported item
==> self init / class method to define: [Image]
	- content: what you import
	- height: full height
	- width: full width
	- read_dir : e.g. top right to left bottom
	- language
	- file_name
==> static method to create/update the cropped variable: "Fn_Crop"
==> static method to remove all cropped (for redo button)
==> from above "cropped": list of tuple, with cropped x, y, width, height, default full image


2. Other functions
==> "Fn_Preprocess_Img" 
	-> Preprocess the image: e.g. grayscale, denoise
	-> input parameter: image content
==> "Fn_OCR" 
	-> OCR: Convert to text
	-> input parameter: image, read_dir
==> "Fn_Save_Result" 
	-> Save result: open a new folder, include :
		1. original image
		2. image with cropped label (the rectangle) and the size should follow the original
		3. text file with OCR result.


