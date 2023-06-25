import re

import numpy as np
import cv2
import os
import requests
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
import PIL
from scipy.signal import convolve
import easyocr


def preprocessing(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return np.array(gray_image) / 255


def edge_detect(img: np.array, t_low: np.float32, t_high: np.float32) \
        -> (np.array, np.array):
    '''
    This function receives a grayscale image and locate its edges using the
    Canny Edge Detector algorithm.

    Args:
        img:    image array in float format (range: 0..1) - the source grayscale
                image.
        t_low:  float format (range: 0..1), the Low threshold value.
        t_high: float format (range: 0..1), the High threshold value.

    Returns:
        img_e:    array in int format (values: 0, 1) - binary image with edges
                    pixels set to 1.
        tg_theta: array in float format (range: 0..1) - the matrix of the
                    tangents of the gradients angles.
    '''
    n, m = img.shape

    # smooth the image with a filter
    filter = np.array([[1, 2, 1],
                       [2, 4, 2],
                       [1, 2, 1]]) / 16
    img_s = convolve(img, filter, 'same')

    # crate S and assign thresholds
    Sx = convolve(img_s, np.array([[1, -1]]), 'same')
    Sy = convolve(img_s, np.array([[1, -1]]).T, 'same')
    S = np.sqrt(Sx * Sx + Sy * Sy)
    Sx[Sx == 0] = 0.0001
    tg_theta = Sy / Sx

    # thresholding
    img_e = np.zeros((n, m), dtype=np.int16)

    # scan from top left to bottom right
    for i in range(1, n - 1):
        for j in range(1, m - 1):
            if S[i, j] < t_low:
                img_e[i, j] = 0
            elif S[i, j] > t_high:
                img_e[i, j] = 1
            elif t_low <= S[i, j] <= t_high and np.any(img_e[i - 1: i + 2, j - 1: j + 2]) == 1:
                img_e[i, j] = 1
            else:
                img_e[i, j] = 0
    # scan from bottom right to top left
    for i in range(n - 2, 1, -1):
        for j in range(m - 2, 1, -1):
            if S[i, j] < t_low:
                img_e[i, j] = 0
            elif S[i, j] > t_high:
                img_e[i, j] = 1
            elif t_low <= S[i, j] <= t_high and np.any(img_e[i - 1: i + 2, j - 1: j + 2]) == 1:
                img_e[i, j] = 1
            else:
                img_e[i, j] = 0

    # compute the grad main directions
    grad_dir = np.zeros((n, m), dtype=np.int16)
    for i in range(n):
        for j in range(m):
            if -0.4142 <= tg_theta[i, j] <= 0.4142:
                temp = 1
            elif 0.4142 < tg_theta[i, j] <= 2.4142:
                temp = 2
            elif abs(tg_theta[i, j]) > 2.4142:
                temp = 3
            elif -2.4142 <= tg_theta[i, j] < -0.4142:
                temp = 4
            grad_dir[i][j] = temp

    for i in range(1, n - 1):
        for j in range(1, m - 1):
            if img_e[i, j] == 0:
                continue
            if grad_dir[i, j] == 1:
                if S[i, j] < max(S[i, j - 1], S[i, j + 1]):
                    img_e[i, j] = 0
            if grad_dir[i, j] == 2:
                if S[i, j] < max(S[i - 1, j - 1], S[i + 1, j + 1]):
                    img_e[i, j] = 0
            if grad_dir[i, j] == 3:
                if S[i, j] < max(S[i - 1, j], S[i + 1, j]):
                    img_e[i, j] = 0
            if grad_dir[i, j] == 4:
                if S[i, j] < max(S[i - 1, j + 1], S[i + 1, j - 1]):
                    img_e[i, j] = 0

    return img_e, tg_theta


def find_plate(contours):
    # Initialize lists for ratios and rectangles
    ratios = []
    rectangles = []

    # Iterate over the contours
    for contour in contours:
        # Approximate the contour as a polygon
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        # Check if the polygon has four vertices (a rectangle)
        if len(polygon) == 4:
            x, y, width, height = cv2.boundingRect(polygon)

            # Calculate the length-to-width ratio
            ratio = width / float(height)

            # Add the ratio and rectangle to the lists
            ratios.append(ratio)
            rectangles.append((x, y, width, height))

    # Sort the rectangles based on the absolute difference from the target ratio
    sorted_rectangles = sorted(zip(ratios, rectangles), key=lambda x: abs(x[0] - 5))

    # Filter out rectangles with small areas
    filtered_rectangles = [(x, y, width, height) for ratio, (x, y, width, height) in sorted_rectangles if
                           width * height > 1000]

    # Take the top ten rectangles
    top_ten_rectangles = filtered_rectangles[:10]

    x, y, width, height = top_ten_rectangles[0]
    return x, y, width, height


def OCR(plate):
    reader = easyocr.Reader(['en'])
    result = reader.readtext(plate)
    text = ''.join(e for e in result[0][1])
    pattern = r'[^a-zA-Z0-9]'
    cleaned_string = re.sub(pattern, '', text)
    print(cleaned_string)
    return cleaned_string


def licence_plate_recognition(pil_image):
    original_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    plt.imshow(original_image)
    plt.show()

    image = original_image.copy()

    img1_e, tg_theta1 = edge_detect(img=preprocessing(image), t_low=18/255, t_high=30/255)

    plt.imshow(img1_e)
    plt.show()

    array = np.array(img1_e, np.uint8)

    contours, new = cv2.findContours(array.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    x, y, width, height = find_plate(contours)

    cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)
    plt.imshow(image)
    plt.show()

    plate = original_image[y:y + height, x:x + width]
    return OCR(plate)



if __name__ == '__main__':
    pass
    # original_image = cv2.imread('./try9.jpeg')
    # plt.imshow(original_image)
    # plt.show()
    #
    # image = original_image.copy()
    #
    # img1_e, tg_theta1 = edge_detect(img=preprocessing(image), t_low=18/255, t_high=30/255)
    #
    # plt.imshow(img1_e)
    # plt.show()
    #
    # array = np.array(img1_e, np.uint8)
    #
    # contours, new = cv2.findContours(array.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    # x, y, width, height = find_plate()
    #
    # cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)
    # plt.imshow(image)
    # plt.show()
    #
    # plate = original_image[y:y + height, x:x + width]
    # OCR(plate)









