library(magick)
# map colors of an image to the colors of a given palette

input_f <-"~/Downloads/papyrusani/Plate 11 Assembled 1.jpg"
input_palette <-"~/Documents/githubs/ReassemblingOsiris/palettes/palette3.png"
output_f <- "~/Documents/githubs/ReassemblingOsiris/Images/region-graphics/oxyrhynchus.png-new.png"


m_img <- image_read(input_f)
# color_palette <- image_read(input_palette)

# image_browse(target_img)
# m_img <- image_scale(m_img,'32')
# m_img <- grayscale(m_img)
# m_img <- image_contrast(m_img, sharpen = 100)

# m_img <- image_map(m_img, target_img)
m_img <- image_quantize(m_img, 10)

# m_img <- image_scale(m_img,'500')
# m_img <- image_modulate(m_img, brightness = 100, saturation = 100, hue = 100)
# m_img <- image_level(m_img, "50%x80%")

# image_browse(m_img)
# m_img <- image_map(m_img, color_palette)
# image_browse(m_img)

# m_img <- image_quantize(m_img, 16)
# m_img <- image_map(m_img, target_img)

# image_write(m_img, path=output_f, format = "png")
image_browse(m_img)
