from PIL import Image


def hex_to_rgb(hex_color):
  """Converts hexadecimal color representation to RGB."""
  hex_color = hex_color.strip("#")
  return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def apply_color_mapping(image_path, color_map):
  # Open the image
  image = Image.open(image_path)
  # print(image)
  width, height = image.size

  # Load the pixels
  pixels = image.load()
  # print(pixels)
  # image.save("hello.png")

  # Iterate through each pixel
  for y in range(height):
    for x in range(width):
      # Get the RGB values of the pixel
      # print(pixels[x, y])
      r, g, b, t = pixels[x, y]
      hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
      # if r != 0 and g != 0 and b != 0:
      #   print(hex_color)
      # Check if the pixel color is in the color map
      if hex_color in color_map:
        # If it is, replace the color according to the map
        new_hex_color = color_map[hex_color]
        new_r, new_g, new_b = hex_to_rgb(new_hex_color)
        # new_r, new_g, new_b = color_map[(r, g, b)]
        pixels[x, y] = (new_r, new_g, new_b)

  # Save the modified image
  image.save("modified_image.png")


# Example usage:
if __name__ == "__main__":
  # Path to the image
  image_path = "TilesetFloor.png"
  

  # Define the color mapping as a dictionary
  color_map = {
    # "#5b5848": "#b5aa30",  #eyes
    # "#b1ae9b": "#2d3131",  #head
    # "#c2bfae": "#252828",  #body
    # "#383530": "#101313",  #outline
    # "#dca05d": "#5b5848",   #ears
    # "#b5aa30": "#303837"    #yellow correction
    "#6c7342":"#3a5941",      #main dark green
    "#304d2e":"#273931",        # darker outline
    "#708e47":"#65845c"        #default light green
  }

  # Apply the color mapping
  apply_color_mapping(image_path, color_map)
  print("done")
