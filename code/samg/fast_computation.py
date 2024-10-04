import math
import numpy as np
from numba import jit


@jit
def compute_mhd_one_position(positions, colors, image, mhd_parameters_values, x , y):
    width = image.shape[1]-1
    height = image.shape[0]-1

    parameters = np.zeros(5)

    parameters[3] = x/width
    parameters[4] = y/height

    color = image[y, x]

    parameters[0] = float(color[0]) / 255.0
    parameters[1] = float(color[1]) / 255.0
    parameters[2] = float(color[2]) / 255.0

    min = 1e10
    pos_min = 0
    parameters_know = np.zeros(5)
    for pos in range(len(positions)):
        parameters_know[0] = float(colors[pos][0]) / 255.0
        parameters_know[1] = float(colors[pos][1]) / 255.0
        parameters_know[2] = float(colors[pos][2]) / 255.0
        parameters_know[3] = positions[pos][1]/width
        parameters_know[4] = positions[pos][0]/height

        sum = 0.0
        for i in range(5):
            if mhd_parameters_values[i]:
                sum = sum + (parameters[i]-parameters_know[i])**2

        distance = math.sqrt(sum)
        if distance < min:
            min = distance
            pos_min = pos

    return pos_min


@jit
def compute_mhd(positions, colors, image, mhd_parameters_values):
    result = np.zeros(image.shape, dtype=np.uint8)

    width = image.shape[1]-1
    height = image.shape[0]-1

    parameters = np.zeros(5)
    for x in range(image.shape[1]):
        parameters[3] = x/width
        for y in range(image.shape[0]):
            parameters[4] = y/height

            color = image[y, x]

            parameters[0] = float(color[0]) / 255.0
            parameters[1] = float(color[1]) / 255.0
            parameters[2] = float(color[2]) / 255.0

            # if x==100:
            #     print("Color ", color)
            #     print("Parameters ", parameters)

            min = 1e10
            pos_min = 0
            parameters_know = np.zeros(5)
            for pos in range(len(positions)):
                parameters_know[0] = float(colors[pos][0]) / 255.0
                parameters_know[1] = float(colors[pos][1]) / 255.0
                parameters_know[2] = float(colors[pos][2]) / 255.0
                parameters_know[3] = positions[pos][1]/width
                parameters_know[4] = positions[pos][0]/height

                sum = 0.0
                for i in range(5):
                    if mhd_parameters_values[i]:
                        sum = sum + (parameters[i]-parameters_know[i])**2

                distance = math.sqrt(sum)
                if distance < min:
                    min = distance
                    pos_min = pos

            result[y, x] = colors[pos_min]
            # result[y, x] = [255,0,255,255]

            # if x == 100:
            #     print("Result ", result[y, x])
    return result

# @jit
# def compute_differences(image_original, image_mhd):
#     result = np.zeros(image_original.shape, dtype=np.uint8)
#
#     for x in range(image_original.shape[1]):
#         for y in range(image_original.shape[0]):
#             if not (image_original[y, x]==image_mhd[y, x]).all():
#                 # pintar las diferencias en rojo (o cualquier otro color que prefieras)
#                 result[y, x] = [255, 255, 255]
#
#     return result

# @jit
# def compute_differences(image_original, image_mhd):
#     return np.abs(image_original-image_original)

@jit
def compute_differences(image_original, image_mhd, threshold):
    if image_original is image_mhd:
        print("---------------------------")
    result = np.zeros(image_original.shape, dtype=np.uint8)

    num_different=0
    for x in range(image_original.shape[1]):
        for y in range(image_original.shape[0]):
            value = np.sqrt(np.sum((image_original[y,x]-image_mhd[y,x])**2))
            # if y==0 and x<10:
            #     print("1 ", image_original[y,x])
            #     print("2 ", image_mhd[y, x])
            #     print(value)
            if value > threshold:
                num_different = num_different + 1
                result[y,x] = [255, 255, 255]
            else:
                result[y,x] = [0, 0, 0]

    return result, int(float(num_different)*100.0/(result.shape[0]*result.shape[1]))


@jit
def process_hsl(image, black_threshold, white_threshold):
    for x in range(image.shape[1]):
        for y in range(image.shape[0]):
            if image[y, x, 1] < black_threshold: # if L < black threshold change to black
                image[y, x, 1] = 0
            elif image[y, x, 1] > white_threshold: # if L > white threshold change to white
                image[y, x, 1] = 255
            else:
                image[y, x, 1] = 127
