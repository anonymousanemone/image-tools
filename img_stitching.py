import cv2
import numpy as np
import os
import glob

# ==========================
# INPUT VALUES
# ==========================
IMG_DIR = "data/penn_E431"
IMG_LIST = []

def load_images(dir_path):
    """
    Reads all images from a directory and returns them as a list sorted by filename
    """
    image_files = sorted(
        glob.glob(os.path.join(dir_path, '*.*'))
    )

    images = []
    for file in image_files:
        img = cv2.imread(file)
        if img is None:
            print(f"Warning: Could not read {file}, skipping.")
            continue
        images.append(img)
    return images

def stitch_images(images, output_path='stitched_result.jpg'):
    if len(images) < 2:
        print("Need at least two images to stitch.")
        return None

    stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
    status, stitched = stitcher.stitch(images)

    if status == cv2.Stitcher_OK:
        cv2.imwrite(output_path, stitched)
        print(f"Stitching completed successfully! Saved as {output_path}")
        return stitched
    else:
        print(f"Stitching failed with status {status}")
        return None

def stitch_images_manual(images, ransac_thresh=4.0):
    """
    Manually stitches images left to right using ORB/SIFT + RANSAC homography.
    ransac_thresh: lower = stricter, higher = more tolerant to noise.
    """
    stitched = images[0]

    for i in range(1, len(images)):
        img2 = images[i]

        # Feature detection and matching
        sift = cv2.SIFT_create()
        kp1, des1 = sift.detectAndCompute(stitched, None)
        kp2, des2 = sift.detectAndCompute(img2, None)

        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)

        # Lowe's ratio test
        good_matches = [m for m, n in matches if m.distance < 0.75 * n.distance]
        if len(good_matches) < 4:
            print(f"Not enough matches between images {i-1} and {i}")
            continue

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Compute homography with custom RANSAC threshold
        H, mask_h = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, ransac_thresh)

        # Warp img2 to stitched coordinates
        h1, w1 = stitched.shape[:2]
        h2, w2 = img2.shape[:2]

        corners_img2 = np.array([[0,0],[0,h2],[w2,h2],[w2,0]], dtype=np.float32).reshape(-1,1,2)
        warped_corners = cv2.perspectiveTransform(corners_img2, H)
        all_corners = np.vstack((np.array([[0,0],[0,h1],[w1,h1],[w1,0]], dtype=np.float32).reshape(-1,1,2), warped_corners))

        xmin, ymin = np.int32(all_corners.min(axis=0).ravel())
        xmax, ymax = np.int32(all_corners.max(axis=0).ravel())
        translation = [-xmin, -ymin]

        H_translation = np.array([[1,0,translation[0]],[0,1,translation[1]],[0,0,1]])

        # Warp img2
        warped_img2 = cv2.warpPerspective(img2, H_translation @ H, (xmax - xmin, ymax - ymin))
        canvas = np.zeros_like(warped_img2)
        canvas[translation[1]:translation[1]+h1, translation[0]:translation[0]+w1] = stitched

        # Create a mask for blending: 1 where warped_img2 has content
        mask_img2 = (warped_img2 > 0).astype(np.float32)
        mask_canvas = (canvas > 0).astype(np.float32)
        overlap = np.minimum(mask_img2, mask_canvas)

        # Avoid division by zero
        total_mask = mask_img2 + mask_canvas
        total_mask[total_mask == 0] = 1

        # Linear blend only in overlapping region
        blended_region = linear_blend(canvas, warped_img2, overlap)

        # Non-overlapping regions: take whichever is non-zero
        stitched = np.where(overlap, blended_region, canvas + warped_img2)

    return stitched


import numpy as np
import cv2

def linear_blend(img1, img2, mask, feather=0.1):
    """
    Linear blend two images with distance-based feathering at edges.

    Parameters:
    - img1, img2: images to blend (same size)
    - mask: binary mask where img2 is present (1) and img1 is present (0)
    - feather: fraction of overlap width/height to fade (0.0 to 1.0)
    """
    mask = mask.astype(float)

    # Compute distance transform from edges of mask (distance to zero)
    dist = cv2.distanceTransform((mask*255).astype(np.uint8), cv2.DIST_L2, 5)

    # Normalize distance to [0,1] based on max distance
    if np.max(dist) > 0:
        dist_norm = dist / np.max(dist)
    else:
        dist_norm = dist

    # Apply feather factor
    dist_mask = np.clip(dist_norm / feather, 0, 1)

    # Final blending weight: img2 fades toward edge
    final_mask = mask * dist_mask

    blended = img1 * (1 - final_mask) + img2 * final_mask
    return blended.astype(np.uint8)


def remove_dark_border(img, n=10, threshold=30):
    """
    Removes dark pixels near the border of an image.
    
    Parameters:
    - img: input image (BGR or grayscale)
    - n: number of pixels from the border to check
    - threshold: pixel intensity below this is considered "dark" (0-255)
    
    Returns:
    - img with dark border pixels set to black
    """
    # Convert to grayscale for easy thresholding
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    mask = gray < threshold

    # Create a mask for n-pixel border
    border_mask = np.zeros_like(mask)
    border_mask[:n, :] = 1         # Top border
    border_mask[-n:, :] = 1        # Bottom border
    border_mask[:, :n] = 1         # Left border
    border_mask[:, -n:] = 1        # Right border

    # Only keep dark pixels near the border
    final_mask = mask & border_mask

    # Set those pixels to black
    img[final_mask] = 0

    return img


if __name__ == "__main__":
    images = load_images(IMG_DIR) or IMG_LIST

    images = [remove_dark_border(img, n=60, threshold=60) for img in images]

    stitched_image = stitch_images_manual(images)
    cv2.imwrite("stitched.png", stitched_image)
    
    if stitched_image is not None:
        cv2.imshow("Stitched Image", stitched_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
