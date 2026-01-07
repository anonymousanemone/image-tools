# Image Tools
A random suite of image and document processing tools written in a variety of languages.
- [PDF Side-by-Side Combiner: pdf_sidebyside.py](#pdf-side-by-side-combiner-pdf_sidebysidepy)
- [Transparent Image Cropper: img_crop_transparent.py](#transparent-image-cropper-img_crop_transparentpy)
- [Supertitle Creator: supertitler.py](#supertitle-creator-supertitlerpy)
- [Pixel Color Mapper: img_pixel_colors.ipynb](#pixel-color-mapper-img_pixel_colorsipynb)
- [Color Mapper: colormap.R](#color-mapper-colormapr)


## PDF Side-by-Side Combiner: pdf_sidebyside.py
For all the unfortunate souls who recently had to translate a text in a different language, here is a program that combines two PDF files by placing each page next to each other horizontally, page by page. 

Both input PDFs must have the same number of pages. Configure the file path of the two pdfs within the code as below, then run ``python pdf_sidebyside.py``

```python
HARDCODED_PDF_1 = None          # left
HARDCODED_PDF_2 = None          # right
HARDCODED_RESULT_DIR = None
```

It first generates a one-page preview (using the first page of both PDFs), opens it in your system’s default PDF viewer for confirmation, and then produces the full combined PDF. Both are written to the specified result directory (or the first PDF’s folder by default).

- Preview file: ``<first_pdf_name>_preview.pdf``
- Final file: ``<first_pdf_name>_combined.pdf``

Note: If the preview cannot be opened automatically, the full file path is printed.

## Transparent Image Cropper: img_crop_transparent.py
Crops a transparent image to its non-transparent content.

Configure the input and output path within the code as below, then run ``python img_crop_transparent.py``

```python
INPUT_PATH = None   # A file or directory
OUTPUT_PATH = None  # Optional
```

Output defaults to the same directory as the file for single image mode or ``cropped/`` inside the input directory for folder mode.


## Supertitle Creator: supertitler.py
Generates line-by-line supertitles in powerpoint using an input word doc.

Configure the input and output path within the code as below, then run ``python supertitler.py``

```python
INPUT_DOC = None    # .docx
OUTPUT_PPT = None   # .pptx
```

Font size, color, slide dimensions, and other formatting details can be adjusted within the script. It is by default set to a black background with white text, using Times New Roman, size 65 pt.

### Pixel Color Mapper: img_pixel_colors.ipynb
Made for editing pixel art. Switches out colors in an image, pixel-perfect. Includes additional tools to facilitate the process.
- **Plot all distinct colors**: given an image, lists all distinct colors with visualizations and hex codes.
- **Visualize color replacements**: now given a mapping of the color replacements, it will visualize the before and after colors in two rows.
- **Replace mapped colors**: only exact matches of the specified colors are changed.

Follow along the notebook and configure these items below:
```python
IMAGE_PATH = None   
COLOR_MAP = {                   # Define the color replacements as a dictionary
    "#e0f8cf":"#e5d3b3",    # from_color : to_color   
    "#86c06c":"#b99976",    # hex code
    "#071821":"#664229"
}
```

For none pixel art images, see ``colormap.R``

## Color Mapper: colormap.R
Maps the color of an input image to a given color palette/sample image.

Configure the input and output path within the code as below, then run.

```R
input_f <-"input_image.png"
input_palette <-"palette.png"
output_f <- "output.png"
```