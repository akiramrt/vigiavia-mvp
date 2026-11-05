"""
Detector de buracos para PRODUÇÃO: ONNX Runtime puro (sem PyTorch/Ultralytics no container).

Reproduz o pré e o pós-processamento do Ultralytics para o modelo exportado em ONNX:
letterbox 640x640 (cinza 114) -> RGB/255 -> CHW -> rede -> saída [1, 5, N] (cx, cy, w, h, score)
-> limiar -> NMS (IoU) -> desfaz o letterbox. Também aceita a saída fim a fim [1, 300, 6].
"""
from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from . import severidade as sev
from .tipos import ZONA_TRAJETORIA, Deteccao, dentro_do_poligono, suprimir_aninhadas, zona_em_pixels


class DetectorONNX:
    def __init__(self, pesos: str | Path, conf: float = 0.25, iou: float = 0.5, imgsz: int = 640,
                 zona=ZONA_TRAJETORIA, threads: int | None = None):
        self.pesos = Path(pesos)
        if not self.pesos.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {self.pesos}")
        opcoes = ort.SessionOptions()
        opcoes.intra_op_num_threads = threads or int(os.getenv("VIGIAVIA_THREADS", "2"))
        opcoes.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sessao = ort.InferenceSession(str(self.pesos), opcoes, providers=["CPUExecutionProvider"])
        self.entrada = self.sessao.get_inputs()[0].name
        self.conf, self.iou, self.imgsz, self.zona = conf, iou, imgsz, zona

    @property
    def nome(self) -> str:
        return self.pesos.stem

    def _letterbox(self, img: np.ndarray) -> tuple[np.ndarray, float, float, float]:
        h, w = img.shape[:2]
        r = min(self.imgsz / h, self.imgsz / w)
        nw, nh = int(round(w * r)), int(round(h * r))
        dw, dh = (self.imgsz - nw) / 2, (self.imgsz - nh) / 2
        if (w, h) != (nw, nh):
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        topo, base = int(round(dh - 0.1)), int(round(dh + 0.1))
        esq, dir_ = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, topo, base, esq, dir_, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        x = img[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        return np.ascontiguousarray(x), r, esq, topo

    def detectar(self, imagem: np.ndarray, conf: float | None = None) -> list[Deteccao]:
        limiar = conf or self.conf
        h, w = imagem.shape[:2]
        x, r, px, py = self._letterbox(imagem)
        saida = self.sessao.run(None, {self.entrada: x})[0][0]
        if saida.shape[-1] == 6:                                    # fim a fim: [300, 6] xyxy, score, classe
            linhas = saida[saida[:, 4] >= limiar]
            caixas, scores = linhas[:, :4].copy(), linhas[:, 4]
        else:                                                       # clássica: [5, N] -> NMS
            pred = saida.T
            pred = pred[pred[:, 4] >= limiar]
            cx, cy, bw, bh, scores = pred.T
            caixas = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], axis=1)
            if len(caixas):
                xywh = np.stack([caixas[:, 0], caixas[:, 1], bw, bh], axis=1).tolist()
                manter = cv2.dnn.NMSBoxes(xywh, scores.tolist(), limiar, self.iou)
                idx = np.array(manter).reshape(-1)
                caixas, scores = caixas[idx], scores[idx]
        caixas = (caixas - np.array([px, py, px, py], dtype=np.float32)) / r
        caixas[:, [0, 2]] = caixas[:, [0, 2]].clip(0, w)
        caixas[:, [1, 3]] = caixas[:, [1, 3]].clip(0, h)
        zona = zona_em_pixels(w, h, self.zona)
        deteccoes = []
        for (x1, y1, x2, y2), s in zip(caixas.astype(float), scores.astype(float)):
            if x2 - x1 < 1 or y2 - y1 < 1:
                continue
            idx_sev = float(sev.indice_severidade(x1, y1, x2, y2, w, h))
            deteccoes.append(Deteccao(x1, y1, x2, y2, s, sev.classificar(idx_sev), idx_sev,
                                      float(sev.area_relativa(x1, y1, x2, y2, w, h)),
                                      dentro_do_poligono(((x1 + x2) / 2, y2), zona)))
        return suprimir_aninhadas(deteccoes)
