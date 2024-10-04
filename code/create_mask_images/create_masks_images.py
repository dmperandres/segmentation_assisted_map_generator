import numpy as np
import torch
import matplotlib.pyplot as plt
import cv2
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor

sam_checkpoint = "checkpoint/sam_vit_h_4b8939.pth"
model_type = "vit_h"
device = "cuda"


def show_mask(mask, ax, random_color=False):
    if random_color:
        color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
    else:
        color = np.array([30/255, 144/255, 255/255, 0.6])
    h, w = mask.shape[-2:]
    mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    ax.imshow(mask_image)

def show_points(coords, labels, ax, marker_size=375):
    pos_points = coords[labels==1]
    neg_points = coords[labels==0]
    ax.scatter(pos_points[:, 0], pos_points[:, 1], color='green', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)
    ax.scatter(neg_points[:, 0], neg_points[:, 1], color='red', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)

def show_box(box, ax):
    x0, y0 = box[0], box[1]
    w, h = box[2] - box[0], box[3] - box[1]
    ax.add_patch(plt.Rectangle((x0, y0), w, h, edgecolor='green', facecolor=(0,0,0,0), lw=2))


def show_anns(anns):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    ax = plt.gca()
    ax.set_autoscale_on(False)

    # crea la imagen del tamaño de la imagen original
    img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
    # pone la transparencia a cero -> totalmente transparente
    img[:,:,3] = 0
    for ann in sorted_anns:
        # otiene la matriz que representa la zona segmentada. Son valores true o false
        m = ann['segmentation']
        # calcula un color aleatorio. concatena tres random (RGB) con el canal alfa (0.35)
        color_mask = np.concatenate([np.random.random(3), [1]])
        # aplica el color en los pixeles de la imagen donde la mascara es true
        img[m] = color_mask
    file_name = 'masks/image_mask_' + str(len(sorted_anns)) + '.png'
    cv2.imwrite(file_name, img)
    ax.imshow(img)

def show_anns1(anns):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    ax = plt.gca()
    ax.set_autoscale_on(False)

    # crea la imagen del tamaño de la imagen original
    img = np.full((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4), 255)
    # pone la transparencia a cero -> totalmente transparente
    # img[:,:,3] = 0
    for ann in sorted_anns:
        # otiene la matriz que representa la zona segmentada. Son valores true o false
        m = ann['segmentation']
        # calcula un color aleatorio. concatena tres random (RGB) con el canal alfa (0.35)
        color_mask = np.concatenate([np.random.random(3)*255, [255]])
        # aplica el color en los pixeles de la imagen donde la mascara es true
        img[m] = color_mask
    file_name = 'masks/image_mask_' + str(len(sorted_anns)) + '.png'
    cv2.imwrite(file_name, img)
    ax.imshow(img)


def show_anns_full(anns):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    ax = plt.gca()
    ax.set_autoscale_on(False)

    # crea la imagen del tamaño de la imagen original
    img = np.full((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4), 255)
    # creo la image que contiene un entero para cada pixel que indica a la máscara que pertenece
    img_masks = np.full((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 1), 255, np.uint8)
    # recorre todas las mascaras
    pos = 0
    for ann in sorted_anns:
        # otiene la matriz que representa la zona segmentada. Son valores true o false
        m = ann['segmentation']
        # calcula un color aleatorio. concatena tres random (RGB) con el canal alfa (0.35)
        # color_mask = np.concatenate([np.random.random(3), [0.35]])
        color_mask = np.concatenate([np.random.random(3)*255, [255]])
        # aplica el color en los pixeles de la imagen donde la mascara es true
        img[m] = color_mask
        #file_name = 'masks/mask_'+str(pos) + '.png'
        #
        img_masks[m] = pos
        #
        pos +=1
        #cv2.imwrite(file_name, img)
    file_name = 'masks/color_mask_' + str(len(sorted_anns)) + '.png'
    cv2.imwrite(file_name, img)
    # save the img_masks
    file_name = 'masks/segments_mask_'+ str(len(sorted_anns)) + '.png'
    cv2.imwrite(file_name, img_masks)
    # ax.imshow(img)



def segmentation(points_per_side1, pred_iou_threshold1, stability_score_threshold1, crop_n_layers1, crop_n_points_downscale_factor1,
                 min_mask_region_area1):
    sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
    sam.to(device=device)

    # mask_generator = SamAutomaticMaskGenerator(sam)
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side = points_per_side1,
        pred_iou_thresh = pred_iou_threshold1,
        stability_score_thresh = stability_score_threshold1,
        crop_n_layers = crop_n_layers1,
        crop_n_points_downscale_factor = crop_n_points_downscale_factor1,
        min_mask_region_area = min_mask_region_area1)

    image = cv2.imread('images/vis_visible.png')
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    masks = mask_generator.generate(image)

    print('number of masks=',len(masks))
    # print(masks[0].keys())

    plt.figure(figsize=(20,20))
    plt.imshow(image)
    show_anns_full(masks)
    plt.axis('off')
    plt.show()

def segmentation_point():
    sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
    sam.to(device=device)


    image = cv2.imread('images/vis_visible.jpg')
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    predictor = SamPredictor(sam)
    predictor.set_image(image)

    input_point = np.array([[152, 114]])
    input_label = np.array([1])

    plt.figure(figsize=(10,10))
    plt.imshow(image)
    show_points(input_point, input_label, plt.gca())
    plt.axis('off')
    plt.show()

    masks, scores, logist = predictor.predict(point_coords=input_point, point_labels=input_label, multimask_output=True)

    print(masks.shape)  # (number_of_masks) x H x W

    for i, (mask, score) in enumerate(zip(masks, scores)):
        plt.figure(figsize=(10,10))
        plt.imshow(image)
        show_mask(mask, plt.gca())
        show_points(input_point, input_label, plt.gca())
        plt.title(f"Mask {i+1}, Score: {score:.3f}", fontsize=18)
        plt.axis('off')
        plt.show()



# defaults
# model: Sam,
# points_per_side: Optional[int] = 32,
# points_per_batch: int = 64,
# pred_iou_thresh: float = 0.88, segmentos más grandes si es mayor
# stability_score_thresh: float = 0.95, exactitud de los segmentos, si es menor salen mas segmentos
# stability_score_offset: float = 1.0,
# box_nms_thresh: float = 0.7,
# crop_n_layers: int = 0, permite obtener más detalle si es 1 o más grande
# crop_nms_thresh: float = 0.7,
# crop_overlap_ratio: float = 512 / 1500,
# crop_n_points_downscale_factor: int = 1,
# point_grids: Optional[List[np.ndarray]] = None,
# min_mask_region_area: int = 0,
# output_mode: str = "binary_mask",
#points_per_side, pred_iou_threshold, stability_score_threshold, crop_n_layers, crop_n_points_downscale_factor, min_mask_region_area
#segmentation(32, 0.8, 0.9, 1, 2, 10000)
# segmentation(32, 0.92, 0.95, 1, 2, 10000)
#segmentation(32, 0.92, 0.95, 0, 1, 10000)

segmentation_point()
