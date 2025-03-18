# appends images side by side or top and bottom
# https://cran.r-project.org/web/packages/magick/vignettes/intro.html#Combining

library(magick)

#read
# file_name <- "/Users/sophial/Downloads/outline.png"
# original <- image_read("/Users/sophial/Downloads/svd/1.jpg")
# compressed <- image_read("/Users/sophial/Downloads/svd/img4-250.png")
# img <- c(original, compressed)
# # img <- image_scale(img, "300x300")
# # image_info(img)
# 
# new_img <- image_append(image_scale(img))
# 
# 
# # image_append(image_scale(img, "100"), stack = TRUE)
# # img <- image_composite(border, binarize, operator = "in")
# 
# image_browse(new_img)


# Define lists of image file paths
original <- "/Users/sophial/Downloads/svd/4.jpg"
compressed_list <- c("/Users/sophial/Downloads/svd/img4-50.png",
                     "/Users/sophial/Downloads/svd/img4-250.png", 
                     "/Users/sophial/Downloads/svd/img4-500.png", 
                     "/Users/sophial/Downloads/svd/img4-750.png",
                     "/Users/sophial/Downloads/svd/img4-1000.png",
                     "/Users/sophial/Downloads/svd/img4-1250.png",
                     "/Users/sophial/Downloads/svd/img4-1500.png")

# Output text file for recording image pair placements
output_file <- "image_assignments.txt"
writeLines("Left_Side,Right_Side", output_file)  # Write header to the file

# Output folder for concatenated images
output_folder <- "output_images"
dir.create(output_folder, showWarnings = FALSE)

# Loop through the lists to process images
# set.seed(123)  # For reproducibility of randomization
for (i in seq_along(compressed_list)) {
  # Load one image from each list
  img1 <- image_read(compressed_list[i])
  img2 <- image_read(original)
  
  # Randomly decide which image goes on the left or right
  if (sample(c(TRUE, FALSE), 1)) {
    left_img <- img1
    right_img <- img2
    left_name <- basename(compressed_list[i])
    right_name <- basename(original)
  } else {
    left_img <- img2
    right_img <- img1
    left_name <- basename(original)
    right_name <- basename(compressed_list[i])
  }
  
  # Concatenate the images side by side
  combined <- image_append(c(left_img, right_img))
  
  # Save the combined image
  output_path <- file.path(output_folder, paste0("combined_", i, ".jpg"))
  image_write(combined, path = output_path, format = "jpg")
  
  # Record the filenames into the text file
  # writeLines(paste(left_name, right_name, sep = ","), con = output_file)
  cat(paste(left_name, right_name, sep = ","), "\n", file = output_file, append = TRUE)
}


cat("Processing complete. Output written to:", output_file, "\n")
