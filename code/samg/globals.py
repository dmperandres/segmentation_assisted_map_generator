import numpy as np

MODE_NONE = -1
MODE_DRAW = 0
MODE_ADD_POSITIONS = 1
MODE_REMOVE_POSITIONS = 2
MODE_MINIMUM = 3

BRUSH_MIN_SIZE = 1
BRUSH_MAX_SIZE = 100
BRUSH_SIZE_DEFAULT = 80

MHD_PARAMETERS = [True, True, True, True, True]

KMEANS_NUM_CLUSTERS = 10
KMEANS_NUM_ITERACTIONS = 10

PIXMAP_SIZE = 500

TAB_SIZE = 300

COLOR_MODELS = ['RGB', 'HSV', 'HLS']

COLOR_SMOOTH_KERNEL_SIZE = [1, 3, 5, 7, 9, 11, 13, 15, 25, 49]

BLACK_TRESHOLD = 0
WHITE_TRESHOLD = 255

BRUSH_OUT_CIRCLE = [0,0,255]
BRUSH_IN_CIRCLE = [255,255,0]

PROBE_SIZE_DEFAULT = 0 # the index in the vector -> 0 => 0 -> 1x1
PROBE_SIZES = [0, 1, 2, 3, 4, 5, 6, 7, 12, 24] # 0 > 1x1, 1 > 3x3 ...
PROBE_SIZES_TEXT = ['1x1', '3x3', '5x5', '7x7', '9x9', '11x11', '13x13', '15x15', '25x25', '49x49']

VALUE_NORMALIZATION_DEFAULT = False
POSITION_NORMALIZATION_DEFAULT = False

SPACE_TO_TEXT = 20

LABEL_TEXT_DEFAULT = 'view1'

LAYER_TYPE_IMAGE = int(0)
LAYER_TYPE_MASK = int(1)
LAYER_TYPE_MAP = int(2)
LAYER_TYPE_EFFECT = int(3)

MAX_VALUE_COLORBAR_DEFAULT = 1

COLORBAR_SQUARE_SIZE: int = 20
COLORBAR_MARGIN: int = 10
COLORBAR_SPACE: int = 5

POSITION_FONT_SIZE = 15
POSITION_OUT_CIRCLE_SIZE = 15
POSITION_FONT_COLOR = [0, 0, 255, 255]
POSITION_OUT_CIRCLE_COLOR = [0, 0, 255, 255]
POSITION_IN_CIRCLE_COLOR = [255, 255, 0, 255]
POSITION_SELECTION_OUT_CIRCLE_COLOR = [255, 0, 255, 255]
POSITION_FONT_SCALE = 1


INTERPOLATION_METHOD_MHD = 0
INTERPOLATION_METHOD_SEGMENT_BASED_MHD = 1
INTERPOLATION_METHOD_SEGMENT_BASED_MEAN = 2
INTERPOLATION_METHOD_SEGMENT_BASED_MIN = 3
INTERPOLATION_METHOD_SEGMENT_BASED_MAX = 4
INTERPOLATION_METHODS_TEXT = ['MHD', 'SEGMENT-BASED MHD', 'SEGMENT-BASED MEAN', 'SEGMENT-BASED MIN', 'SEGMENT-BASED MAX']
INTERPOLATION_METHODS_SHORT_TEXT = ['MHD', 'SBMHD', 'SBMEA', 'SBMIN', 'SBMAX']
INTERPOLATION_METHOD_DEFAULT = INTERPOLATION_METHOD_MHD

GL_WIDGET_MODE_POSITIONING = 0
GL_WIDGET_MODE_COPY_POSITION = 1
GL_WIDGET_MODE_DELETE_POSITION = 2
