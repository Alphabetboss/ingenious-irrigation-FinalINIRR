# health_detector.py  â€” YOLOv8 ONNX runtime + irrigation scoring
import os
import math
import time
import numpy as np
import onnxruntime as ort
import cv2

# Must match your training 'names' order in data.yaml
CLASS_NAMES = [
    "grass", "water", "dead_grass", "mud", "standing_water",
    "healthy_grass", "dry_patch", "moss", "mulch", "sprinkler_leak"
]

CONF_THR = float(os.getenv("II_CONF_THR", "0.25"))
IOU_THR = float(os.getenv("II_IOU_THR",  "0.45"))


def _letterbox(im, new_shape=(640, 640), color=(114, 114, 114)):
    h, w = im.shape[:2]
    r = min(new_shape[0]/h, new_shape[1]/w)
    nh, nw = int(round(h*r)), int(round(w*r))
    top = (new_shape[0]-nh)//2
    left = (new_shape[1]-nw)//2
    imr = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_shape[0], new_shape[1], 3), color, dtype=np.uint8)
    canvas[top:top+nh, left:left+nw] = imr
    return canvas, r, (left, top)


def _nms(boxes, scores, iou_thr):
    idxs = scores.argsort()[::-1]
    keep = []
    while idxs.size > 0:
        i = idxs[0]
        keep.append(i)
        if idxs.size == 1:
            break
        iou = _iou(boxes[i], boxes[idxs[1:]])
        idxs = idxs[1:][iou < iou_thr]
    return np.array(keep, dtype=int)


def _iou(b1, B):
    # boxes in [x1,y1,x2,y2]
    xx1 = np.maximum(b1[0], B[:, 0])
    yy1 = np.maximum(b1[1], B[:, 1])
    xx2 = np.minimum(b1[2], B[:, 2])
    yy2 = np.minimum(b1[3], B[:, 3])
    inter = np.maximum(0, xx2-xx1)*np.maximum(0, yy2-yy1)
    a1 = (b1[2]-b1[0])*(b1[3]-b1[1])
    a2 = (B[:, 2]-B[:, 0])*(B[:, 3]-B[:, 1])
    return inter / np.maximum(a1+a2-inter, 1e-6)


class YoloV8ONNX:
    def __init__(self, onnx_path="yolov8n.onnx", providers=None):
        if providers is None:
            providers = ["CPUExecutionProvider"]
        self.sess = ort.InferenceSession(onnx_path, providers=providers)
        self.iname = self.sess.get_inputs()[0].name
        self.oname = self.sess.get_outputs()[0].name

    def infer(self, bgr_image):
        im, r, (dx, dy) = _letterbox(bgr_image, (640, 640))
        im_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32)/255.0
        x = np.transpose(im_rgb, (2, 0, 1))[None, ...]  # 1x3x640x640
        # (1, N, 5+nc) or (1, 84, 8400) variants
        y = self.sess.run([self.oname], {self.iname: x})[0]
        y = np.squeeze(y)
        # Handle Ultralytics ONNX layouts
        if y.shape[0] <= y.shape[1]:   # (84, 8400) -> (8400,84)
            y = y.T

        boxes, scores, classes = [], [], []
        nc = len(CLASS_NAMES)
        # y: (num_preds, 4+1+nc)  => [cx,cy,w,h,conf,cls...]
        for p in y:
            obj = p[4]
            if obj < CONF_THR:
                continue
            cls_id = int(np.argmax(p[5:5+nc]))
            conf = float(obj * p[5+cls_id])
            if conf < CONF_THR:
                continue
            cx, cy, w, h = p[:4]
            x1 = (cx - w/2 - dx)/r
            y1 = (cy - h/2 - dy)/r
            x2 = (cx + w/2 - dx)/r
            y2 = (cy + h/2 - dy)/r
            boxes.append([x1, y1, x2, y2])
            scores.append(conf)
            classes.append(cls_id)

        if not boxes:
            return {"detections": [], "hydration_score": 5.0}

        boxes = np.array(boxes, dtype=np.float32)
        scores = np.array(scores, dtype=np.float32)
        keep = _nms(boxes, scores, IOU_THR)

        dets = []
        for i in keep:
            dets.append({
                "class_id": int(classes[i]),
                "class_name": CLASS_NAMES[int(classes[i])],
                "confidence": float(scores[i]),
                "box_xyxy": [float(v) for v in boxes[i].tolist()]
            })

        hydration = self._score_hydration(dets)
        return {"detections": dets, "hydration_score": hydration}

    def _score_hydration(self, dets):
        """
        0=very dry ... 10=overwatered
        """
        score = 5.0
        for d in dets:
            c = d["class_name"]
            s = d["confidence"]
            if c in ("dry_patch", "dead_grass"):
                score -= 2.0*s
            if c in ("healthy_grass",):
                score += 0.3*s
            if c in ("standing_water", "water"):
                score += 2.0*s
            if c == "moss":
                score += 0.8*s
            if c == "mud":
                score += 1.0*s
        return float(max(0.0, min(10.0, score)))