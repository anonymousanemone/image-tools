library(magick)
# map colors of an image to the colors of a given palette

input_f <-"/Users/sophial/Downloads/RPG_fantasy_tilesets/RPG_exterior.png"
m_img <- image_read(input_f)
image_browse(m_img)
color_palette <- image_read("/Users/sophial/Documents/Images/palette.png")

m_img <- image_map(m_img, color_palette)
# image_browse(m_img)

# m_img <- image_quantize(m_img, 16)
# m_img <- image_map(m_img, target_img)

output_f <- "/Users/sophial/Desktop/medea.png"
# image_write(m_img, path=output_f, format = "png")
image_browse(m_img)
