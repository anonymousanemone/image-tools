###### turn all pixels of a certain color transparent

library(magick)

#read
file_name <- "/Users/sophial/Downloads/outline.png"
img <- image_read(file_name)

#turn all white pixels transparent
img = image_threshold(img, type = "white", threshold = "10%")
# image_browse(img)
img <- image_transparent(img, "white", fuzz = 10)
# image_browse(img)

#write to file
image_write(img, path = file_name, format = "png")
