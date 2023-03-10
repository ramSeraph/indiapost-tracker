from io import BytesIO
from pathlib import Path

import cv2
import tesserocr
import numpy as np
from PIL import Image, ImageSequence, ImageOps

from responders import get_responder

debug_data = {}

#def get_green_mask(img_hsv):
#    lower = np.array([89, 128, 242])
#    upper = np.array([92, 255, 255])
#    img_mask = cv2.inRange(img_hsv, lower, upper)
#    return img_mask

#cv_img_hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
#g_mask = get_green_mask(cv_img_hsv)
#g_mask_d = g_mask.astype(np.uint8)
#g_mask_d = g_mask_d * 255
#imgcat(Image.fromarray(g_mask))



def extract_bbox(img, bbox, m=0):
    ih, iw = img.shape[:2]
    x, y, w, h = bbox

    xe = min(x + w + m - 1, iw - 1)
    ye = min(y + h + m - 1, ih - 1)
    x = max(x - m, 0)
    y = max(y - m, 0)
    w = 1 + xe - x
    h = 1 + ye - y
    sub_img = img[y:y + h, x:x + w]
    sub_pil_image = Image.fromarray(sub_img)
    width, height = sub_pil_image.size
    ideal_height = 32 + 2*m
    scale_factor = float(ideal_height)/float(height)
    scaled = ImageOps.scale(sub_pil_image, scale_factor)
    bordered = ImageOps.expand(scaled, border=20, fill='black')
    #bordered = ImageOps.invert(bordered)
    return bordered


def merge(b1, b2):
    
    b1x, b1y, b1w, b1h = b1
    b2x, b2y, b2w, b2h = b2
    b1xe = b1x + b1w - 1
    b2xe = b2x + b2w - 1
    b1ye = b1y + b1h - 1
    b2ye = b2y + b2h - 1

    nbx = min(b1x, b2x) 
    nby = min(b1y, b2y)
    nbxe = max(b1xe, b2xe)
    nbye = max(b1ye, b2ye)
    nb = nbx, nby, 1 + nbxe - nbx, 1 + nbye - nby
    return nb


def merge_bboxes(bboxes):
    #TODO: merge pieces which are too small as well?
    out = []
    for b in bboxes:
        if len(out) == 0:
            out.append(b)
            continue

        p = out[-1]

        bx, by, bw, bh = b
        px, py, pw, ph = p
        
        bxe = bx + bw
        pxe = px + pw
        bye = by + bh - 1
        pye = py + ph - 1

        if bx > pxe:
            out.append(b)
            continue
        coi = pxe - bx
        if coi < bw/2 and coi < pw/2:
            out.append(b)
            continue

        #merge
        nb = merge(b, p)
        out[-1] = nb
    return out


def thresholding_cv(cv_img):
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)
    #_, thresh = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY|cv2.THRESH_OTSU)
    return thresh


def extract_frame(img_content):
    img = Image.open(BytesIO(img_content))
    img = img.convert('RGB')
    frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
    return frames[0]

   
def reset_debug_info():
    global debug_data
    debug_data = {
        'imgs': {},
        'bboxes': {},
        'responder': [],
    }


def get_debug_info():
    global debug_data
    return debug_data


def guess(tess_api_new, tess_api_old, img_content, label_text):
    reset_debug_info()
    img = extract_frame(img_content)
    debug_data['imgs']['main'] = img
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    cv_img = thresholding_cv(cv_img)
    debug_data['imgs']['thresh'] = Image.fromarray(cv_img)

    #debug_data['imgs']['dilated'] = Image.fromarray(cv_img)
    #el = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    #cv_img_less = cv2.dilate(cv_img, el)

    el = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cv_img = cv2.dilate(cv_img, el)
    debug_data['imgs']['dilated'] = Image.fromarray(cv_img)
    #debug_data['imgs']['dilated_more'] = Image.fromarray(cv_img)
    contours, _ = cv2.findContours(
        cv_img.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    c_bboxes = [ cv2.boundingRect(c) for c in contours ] 
    c_bboxes = sorted(c_bboxes, key=lambda b: b[0])
    c_bboxes = merge_bboxes(c_bboxes)
    debug_data['bboxes'] = c_bboxes
    c_imgs = [ extract_bbox(cv_img, bbox, 3) for bbox in c_bboxes ]
    #c_imgs = [ extract_bbox(cv_img_less, bbox, 3) for bbox in c_bboxes ]
    debug_data['imgs']['pieces'] = c_imgs

    responder = None
    try:
        responder = get_responder(label_text, c_imgs, c_bboxes, tess_api_new, tess_api_old) 
        ans = responder.answer()
        return ans
    except:
        raise
    finally:
        if responder is not None:
            debug_data['responder'] = responder.to_log


def get_tess_api_old():
    tess_data_old_dirname = str(Path('data/models/old/').resolve()) + '/'
    tess_api = tesserocr.PyTessBaseAPI(init=True,
                                       path=tess_data_old_dirname,
                                       psm=tesserocr.PSM.SINGLE_CHAR,
                                       oem=tesserocr.OEM.TESSERACT_ONLY)
    return tess_api

def get_tess_api_new():
    tess_data_new_dirname = str(Path('data/models/lstm/').resolve()) + '/'
    tess_api = tesserocr.PyTessBaseAPI(init=True,
                                       path=tess_data_new_dirname,
                                       psm=tesserocr.PSM.SINGLE_CHAR,
                                       oem=tesserocr.OEM.LSTM_ONLY)
    return tess_api




