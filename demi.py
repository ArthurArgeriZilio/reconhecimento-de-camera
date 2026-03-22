"""
DEMI - Detector de Esqueleto, Maos e Identificacao facial
==========================================================
Modulo Inteligente 4.0 — Monitoramento TOTAL de Seguranca Industrial
com visao computacional, coleta de dados e dashboard de KPIs.

=== 12 FILTROS DE SEGURANCA INDUSTRIAL ===

  FACE (requer modulo 3 - Rosto):
    [4]  Sonolencia       — olhos fechados por tempo (EAR)
    [5]  Bocejo           — boca aberta demais (MAR)
    [6]  Distracao        — cabeca virada, nao olhando pra frente
    [8]  Piscadas         — frequencia de piscadas anormal (fadiga)
    [9]  Cabeca baixa     — olhando pra baixo (celular, dormindo)

  POSE (requer modulo 1 - Pose):
    [0]  Postura ombros   — ombros desalinhados / curvado
    [Q]  Incl. tronco     — tronco inclinado pra frente (coluna)
    [W]  Bracos elevados  — bracos acima dos ombros (ergonomia)
    [A]  Agachamento      — joelhos flexionados demais
    [F]  Queda            — desaparecimento subito da pose (pessoa caiu)

  MAOS (requer modulo 2 - Maos):
    [7]  Inatividade      — maos paradas por muito tempo
    [G]  Veloc. excessiva — maos movendo rapido demais (pressa)

Controles gerais:
  1     - Liga/desliga deteccao de POSE
  2     - Liga/desliga deteccao de MAOS
  3     - Liga/desliga deteccao de ROSTO
  C     - Troca cor dos landmarks
  M     - Espelha a imagem
  S     - Salva screenshot (pasta screenshots/)
  R     - Inicia/para gravacao de video (pasta recordings/)
  E     - Exporta dados coletados para CSV
  D     - Abre dashboard no navegador
  T     - Liga/desliga TODOS os filtros de uma vez
  ESC   - Sair

Requisitos:
  pip install opencv-python mediapipe flask numpy
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import os
import sqlite3
import csv
import webbrowser
import math
from datetime import datetime
from collections import deque


# ============================================================
# CONFIGURACOES
# ============================================================

DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.7

COLORS = {
    "Vermelho":  (0, 0, 255),
    "Verde":     (0, 255, 0),
    "Azul":      (255, 0, 0),
    "Amarelo":   (0, 255, 255),
    "Ciano":     (255, 255, 0),
    "Magenta":   (255, 0, 255),
    "Branco":    (255, 255, 255),
}
COLOR_NAMES = list(COLORS.keys())

SCREENSHOT_DIR = "screenshots"
RECORDING_DIR = "recordings"
EXPORT_DIR = "exports"
DB_PATH = "demi_data.db"
LOG_INTERVAL = 1.0

# === LIMIARES DOS 12 FILTROS ===

# [4] Sonolencia (EAR - Eye Aspect Ratio)
EAR_THRESHOLD = 0.22
EAR_CONSEC_SECONDS = 2.0

# [5] Bocejo (MAR - Mouth Aspect Ratio)
MAR_THRESHOLD = 0.55
MAR_CONSEC_SECONDS = 1.5

# [6] Distracao — cabeca virada
HEAD_TURN_THRESHOLD = 0.12

# [7] Inatividade de maos
INACTIVITY_SECONDS = 10
HAND_MOVE_THRESHOLD = 0.02

# [8] Frequencia de piscadas (fadiga)
BLINK_WINDOW_SECONDS = 60
BLINK_HIGH_RATE = 25       # >25 piscadas/min = fadiga
BLINK_LOW_RATE = 5         # <5 piscadas/min = micro-sono

# [9] Cabeca baixa
HEAD_DOWN_THRESHOLD = 0.06  # diferenca Y nariz vs olhos normalizada
HEAD_DOWN_SECONDS = 3.0

# [0] Postura ombros
POSTURE_ANGLE_THRESHOLD = 15

# [Q] Inclinacao do tronco
TRUNK_LEAN_THRESHOLD = 0.08  # diferenca X normalizada ombro-quadril

# [W] Bracos elevados
ARMS_UP_SECONDS = 5.0  # bracos acima do ombro por X segundos

# [A] Agachamento (angulo dos joelhos)
SQUAT_ANGLE_THRESHOLD = 120  # graus — abaixo disso = agachado

# [F] Queda — pose desaparece de repente
FALL_CONSECUTIVE_FRAMES = 15  # frames sem pose apos ter pose

# [G] Velocidade excessiva das maos
HAND_SPEED_THRESHOLD = 0.15  # movimento normalizado por frame


# ============================================================
# BANCO DE DADOS (SQLite)
# ============================================================

def init_database():
    """Cria o banco de dados e tabelas."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            epoch REAL NOT NULL,
            pose_detected INTEGER DEFAULT 0,
            hands_count INTEGER DEFAULT 0,
            fingers_count INTEGER DEFAULT 0,
            face_detected INTEGER DEFAULT 0,
            fps REAL DEFAULT 0,
            session_id TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_frames INTEGER DEFAULT 0,
            total_detections INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            epoch REAL NOT NULL,
            alert_type TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'warning',
            session_id TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Banco inicializado: {DB_PATH}")


def start_session():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO sessions (id, start_time) VALUES (?, ?)",
                 (session_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[DB] Sessao: {session_id}")
    return session_id


def end_session(session_id, total_frames, total_detections):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE sessions SET end_time=?, total_frames=?, total_detections=? WHERE id=?",
                 (datetime.now().isoformat(), total_frames, total_detections, session_id))
    conn.commit()
    conn.close()


def log_detection(session_id, pose_detected, hands_count, fingers_count, face_detected, fps):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now()
    conn.execute(
        """INSERT INTO detections
           (timestamp, epoch, pose_detected, hands_count, fingers_count, face_detected, fps, session_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (now.isoformat(), now.timestamp(), pose_detected, hands_count,
         fingers_count, face_detected, round(fps, 1), session_id))
    conn.commit()
    conn.close()


def log_alert(session_id, alert_type, description, severity="warning"):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now()
    conn.execute(
        "INSERT INTO alerts (timestamp, epoch, alert_type, description, severity, session_id) VALUES (?, ?, ?, ?, ?, ?)",
        (now.isoformat(), now.timestamp(), alert_type, description, severity, session_id))
    conn.commit()
    conn.close()


def export_to_csv():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table_name in ["detections", "sessions", "alerts"]:
        path = os.path.join(EXPORT_DIR, f"{table_name}_{ts}.csv")
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        print(f"[EXPORT] {table_name}: {path} ({len(rows)} registros)")
    conn.close()


# ============================================================
# INICIALIZACAO DO MEDIAPIPE
# ============================================================

def init_pose(det_conf, track_conf):
    return mp.solutions.pose.Pose(
        min_detection_confidence=det_conf, min_tracking_confidence=track_conf)

def init_hands(det_conf, track_conf):
    return mp.solutions.hands.Hands(
        max_num_hands=2, min_detection_confidence=det_conf, min_tracking_confidence=track_conf)

def init_face_mesh(det_conf, track_conf):
    return mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=det_conf, min_tracking_confidence=track_conf)


# ============================================================
# FUNCOES AUXILIARES DE GEOMETRIA
# ============================================================

def _dist(a, b):
    """Distancia euclidiana entre 2 landmarks."""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)


def _angle_3pts(a, b, c):
    """Angulo em graus no ponto B formado por A-B-C (landmarks)."""
    ba = (a.x - b.x, a.y - b.y)
    bc = (c.x - b.x, c.y - b.y)
    dot = ba[0]*bc[0] + ba[1]*bc[1]
    mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
    mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)
    if mag_ba * mag_bc == 0:
        return 180
    cos_angle = max(-1, min(1, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


# ============================================================
# OS 12 FILTROS DE SEGURANCA INDUSTRIAL
# ============================================================

# ---------- FACE ----------

def calc_ear(face_lm, eye_indices):
    """Eye Aspect Ratio — 0=fechado, ~0.3=aberto."""
    p = [face_lm.landmark[i] for i in eye_indices]
    v1 = _dist(p[1], p[5])
    v2 = _dist(p[2], p[4])
    h = _dist(p[0], p[3])
    return (v1 + v2) / (2.0 * h) if h > 0 else 0.3


def check_drowsiness(face_lm):
    """[4] Retorna EAR medio dos 2 olhos."""
    L = [33, 160, 158, 133, 153, 144]
    R = [362, 385, 387, 263, 373, 380]
    return (calc_ear(face_lm, L) + calc_ear(face_lm, R)) / 2.0


def check_yawn(face_lm):
    """[5] Mouth Aspect Ratio — boca aberta = valor alto."""
    top = face_lm.landmark[13]
    bottom = face_lm.landmark[14]
    left = face_lm.landmark[78]
    right = face_lm.landmark[308]
    vertical = _dist(top, bottom)
    horizontal = _dist(left, right)
    return vertical / horizontal if horizontal > 0 else 0


def check_distraction(face_lm):
    """[6] Desvio horizontal da cabeca."""
    nose = face_lm.landmark[1]
    left_eye = face_lm.landmark[133]
    right_eye = face_lm.landmark[362]
    center_x = (left_eye.x + right_eye.x) / 2
    return abs(nose.x - center_x)


def check_blink(face_lm, prev_ear_open, ear_threshold):
    """[8] Detecta uma unica piscada (transicao aberto->fechado).
    Retorna (blinked: bool, currently_open: bool).
    """
    ear = check_drowsiness(face_lm)
    currently_open = ear >= ear_threshold
    blinked = prev_ear_open and not currently_open
    return blinked, currently_open


def check_head_down(face_lm):
    """[9] Verifica se a cabeca esta inclinada para baixo.
    Valor positivo grande = olhando pra baixo.
    """
    nose = face_lm.landmark[1]
    left_eye = face_lm.landmark[133]
    right_eye = face_lm.landmark[362]
    eye_y = (left_eye.y + right_eye.y) / 2
    return nose.y - eye_y


# ---------- POSE ----------

def check_posture(pose_lm):
    """[0] Angulo de inclinacao dos ombros em graus."""
    ls = pose_lm.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
    rs = pose_lm.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
    dy = ls.y - rs.y
    dx = ls.x - rs.x
    if dx == 0:
        return 0
    angle = abs(math.degrees(math.atan2(dy, dx)))
    if angle > 90:
        angle = 180 - angle
    return angle


def check_trunk_lean(pose_lm):
    """[Q] Verifica inclinacao do tronco para frente.
    Compara posicao horizontal dos ombros com os quadris.
    """
    PL = mp.solutions.pose.PoseLandmark
    ls = pose_lm.landmark[PL.LEFT_SHOULDER]
    rs = pose_lm.landmark[PL.RIGHT_SHOULDER]
    lh = pose_lm.landmark[PL.LEFT_HIP]
    rh = pose_lm.landmark[PL.RIGHT_HIP]

    shoulder_y = (ls.y + rs.y) / 2
    hip_y = (lh.y + rh.y) / 2
    shoulder_x = (ls.x + rs.x) / 2
    hip_x = (lh.x + rh.x) / 2

    vertical_dist = hip_y - shoulder_y
    if vertical_dist < 0.1:
        return 0.5  # Corpo comprimido = curvado
    return abs(shoulder_x - hip_x)


def check_arms_elevated(pose_lm):
    """[W] Verifica se bracos estao acima dos ombros.
    Retorna (left_up, right_up).
    """
    PL = mp.solutions.pose.PoseLandmark
    ls = pose_lm.landmark[PL.LEFT_SHOULDER]
    rs = pose_lm.landmark[PL.RIGHT_SHOULDER]
    lw = pose_lm.landmark[PL.LEFT_WRIST]
    rw = pose_lm.landmark[PL.RIGHT_WRIST]
    le = pose_lm.landmark[PL.LEFT_ELBOW]
    re = pose_lm.landmark[PL.RIGHT_ELBOW]

    left_up = lw.y < ls.y and le.y < ls.y
    right_up = rw.y < rs.y and re.y < rs.y
    return left_up, right_up


def check_squat(pose_lm):
    """[A] Angulo dos joelhos (graus). <threshold = agachado."""
    PL = mp.solutions.pose.PoseLandmark
    left_angle = _angle_3pts(
        pose_lm.landmark[PL.LEFT_HIP],
        pose_lm.landmark[PL.LEFT_KNEE],
        pose_lm.landmark[PL.LEFT_ANKLE])
    right_angle = _angle_3pts(
        pose_lm.landmark[PL.RIGHT_HIP],
        pose_lm.landmark[PL.RIGHT_KNEE],
        pose_lm.landmark[PL.RIGHT_ANKLE])
    return min(left_angle, right_angle)


# ---------- MAOS ----------

def check_hand_activity(hand_lm_list, prev_positions):
    """[7] Verifica se maos estao paradas. Retorna (active, new_pos)."""
    if not hand_lm_list:
        return False, prev_positions
    curr = [(hl.landmark[0].x, hl.landmark[0].y) for hl in hand_lm_list]
    if not prev_positions:
        return True, curr
    max_mov = 0
    for c in curr:
        for p in prev_positions:
            mov = math.sqrt((c[0]-p[0])**2 + (c[1]-p[1])**2)
            max_mov = max(max_mov, mov)
    return max_mov > HAND_MOVE_THRESHOLD, curr


def check_hand_speed(hand_lm_list, prev_positions):
    """[G] Velocidade maxima das maos entre frames."""
    if not hand_lm_list or not prev_positions:
        return 0
    curr = [(hl.landmark[0].x, hl.landmark[0].y) for hl in hand_lm_list]
    max_speed = 0
    for c in curr:
        for p in prev_positions:
            speed = math.sqrt((c[0]-p[0])**2 + (c[1]-p[1])**2)
            max_speed = max(max_speed, speed)
    return max_speed


# ============================================================
# FUNCOES DE DESENHO
# ============================================================

def draw_pose(frame, results, drawing, color):
    if results.pose_landmarks:
        drawing.draw_landmarks(frame, results.pose_landmarks,
            mp.solutions.pose.POSE_CONNECTIONS,
            drawing.DrawingSpec(color=color, thickness=2, circle_radius=3),
            drawing.DrawingSpec(color=color, thickness=2, circle_radius=2))


def draw_hands(frame, results, drawing, color):
    if results.multi_hand_landmarks:
        for i, hl in enumerate(results.multi_hand_landmarks):
            drawing.draw_landmarks(frame, hl, mp.solutions.hands.HAND_CONNECTIONS,
                drawing.DrawingSpec(color=color, thickness=2, circle_radius=3),
                drawing.DrawingSpec(color=color, thickness=2, circle_radius=2))
            if results.multi_handedness:
                label = results.multi_handedness[i].classification[0].label
                label_pt = "Esq" if label == "Left" else "Dir"
                conf = results.multi_handedness[i].classification[0].score
                wrist = hl.landmark[0]
                h, w, _ = frame.shape
                cx, cy = int(wrist.x * w), int(wrist.y * h)
                cv2.putText(frame, f"{label_pt} ({conf:.0%})", (cx-30, cy-20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def draw_face(frame, results, drawing, color):
    if results.multi_face_landmarks:
        for fl in results.multi_face_landmarks:
            drawing.draw_landmarks(frame, fl,
                mp.solutions.face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp.solutions.drawing_styles
                    .get_default_face_mesh_tesselation_style())
            drawing.draw_landmarks(frame, fl,
                mp.solutions.face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=drawing.DrawingSpec(color=color, thickness=1))


def count_raised_fingers(hand_landmarks):
    tips = [8, 12, 16, 20]
    count = 0
    if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
        count += 1
    for tip_id in tips:
        if hand_landmarks.landmark[tip_id].y < hand_landmarks.landmark[tip_id - 2].y:
            count += 1
    return count


def draw_finger_count(frame, results, color):
    if not results.multi_hand_landmarks:
        return
    total = sum(count_raised_fingers(hl) for hl in results.multi_hand_landmarks)
    cv2.putText(frame, f"Dedos: {total}", (10, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)


# ============================================================
# ALERTAS VISUAIS
# ============================================================

def draw_alert_banners(frame, alert_messages):
    """Desenha ate 3 banners de alerta empilhados."""
    h, w, _ = frame.shape
    overlay = frame.copy()
    for i, (text, severity) in enumerate(alert_messages[:3]):
        y_start = 80 + i * 32
        if severity == "danger":
            bg = (0, 0, 200)
            tc = (255, 255, 255)
        elif severity == "critical":
            bg = (0, 0, 255)
            tc = (255, 255, 0)
        else:
            bg = (0, 180, 255)
            tc = (0, 0, 0)
        cv2.rectangle(overlay, (0, y_start), (w, y_start + 30), bg, -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.putText(frame, text, (10, y_start + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, tc, 1, cv2.LINE_AA)


# Todos os filtros com labels e teclas
ALL_FILTERS = [
    ("4", "drowsiness",  "Sonolencia"),
    ("5", "yawn",        "Bocejo"),
    ("6", "distraction", "Distracao"),
    ("7", "inactivity",  "Inatividade"),
    ("8", "blink_rate",  "Piscadas"),
    ("9", "head_down",   "Cab.Baixa"),
    ("0", "posture",     "Postura"),
    ("Q", "trunk_lean",  "Tronco"),
    ("W", "arms_up",     "Bracos"),
    ("A", "squat",       "Agachamento"),
    ("F", "fall",        "Queda"),
    ("G", "hand_speed",  "Veloc.Maos"),
]


def draw_safety_panel(frame, active_alerts, filters):
    """Painel lateral com todos os 12 filtros."""
    h, w, _ = frame.shape
    panel_x = w - 265
    panel_y = 80
    panel_h = 30 + len(ALL_FILTERS) * 22

    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x - 8, panel_y - 8), (w, panel_y + panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    cv2.putText(frame, "SEGURANCA INDUSTRIAL (12)", (panel_x, panel_y + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1, cv2.LINE_AA)

    for i, (key, fid, label) in enumerate(ALL_FILTERS):
        y = panel_y + 32 + i * 22
        enabled = filters.get(fid, False)
        if not enabled:
            color = (80, 80, 80)
            status = "OFF"
        elif fid in active_alerts:
            color = (0, 0, 255)
            status = "ALERTA"
            if int(time.time() * 4) % 2 == 0:
                cv2.circle(frame, (panel_x + 4, y - 3), 5, (0, 0, 255), -1)
        else:
            color = (0, 200, 0)
            status = "OK"
            cv2.circle(frame, (panel_x + 4, y - 3), 4, (0, 200, 0), -1)

        cv2.putText(frame, f"[{key}]{label}", (panel_x + 14, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)
        cv2.putText(frame, status, (panel_x + 175, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)


# ============================================================
# HUD
# ============================================================

def draw_hud(frame, fps, color_name, modules, is_recording, is_mirrored,
             session_id, log_count, alert_count, active_count, total_filters):
    h, w, _ = frame.shape
    overlay = frame.copy()

    cv2.rectangle(overlay, (0, 0), (w, 75), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    fps_color = (0, 255, 0) if fps >= 24 else (0, 255, 255) if fps >= 15 else (0, 0, 255)
    cv2.putText(frame, f"FPS: {fps:.0f}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"Cor: {color_name}", (10, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Dados:{log_count} Alertas:{alert_count} Filtros:{active_count}/{total_filters} Sessao:{session_id}",
                (10, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (100, 255, 100), 1, cv2.LINE_AA)

    p = "ON" if modules["pose"] else "OFF"
    m = "ON" if modules["hands"] else "OFF"
    f = "ON" if modules["face"] else "OFF"
    cv2.putText(frame, f"[1]Pose:{p} [2]Maos:{m} [3]Rosto:{f}",
                (200, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    if is_mirrored:
        cv2.putText(frame, "ESPELHADO", (200, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    if is_recording:
        cv2.circle(frame, (w - 25, 25), 10, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (w - 65, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)

    controls = "[S]Foto [R]Gravar [M]Espelhar [C]Cor [E]CSV [D]Dashboard [T]Filtros [ESC]Sair"
    cv2.rectangle(overlay, (0, h - 28), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, controls, (10, h - 9),
                cv2.FONT_HERSHEY_SIMPLEX, 0.33, (180, 180, 180), 1, cv2.LINE_AA)


# ============================================================
# METRICAS NO CANTO INFERIOR ESQUERDO
# ============================================================

def draw_metrics(frame, metrics):
    """Desenha metricas numericas dos filtros no canto inferior esquerdo."""
    h, w, _ = frame.shape
    y_base = h - 40
    overlay = frame.copy()
    num = len(metrics)
    box_h = num * 18 + 10
    cv2.rectangle(overlay, (0, y_base - box_h), (270, y_base), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for i, (label, value, ok) in enumerate(metrics):
        y = y_base - box_h + 16 + i * 18
        color = (0, 200, 0) if ok else (0, 0, 255)
        cv2.putText(frame, f"{label}: {value}", (8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)


# ============================================================
# UTILITARIOS
# ============================================================

def save_screenshot(frame):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"screenshot_{ts}.png")
    cv2.imwrite(path, frame)
    print(f"[SCREENSHOT] {path}")

def start_recording(width, height, fps=20.0):
    os.makedirs(RECORDING_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RECORDING_DIR, f"gravacao_{ts}.avi")
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    print(f"[GRAVACAO] Iniciada: {path}")
    return writer, path

def stop_recording(writer, path):
    writer.release()
    print(f"[GRAVACAO] Finalizada: {path}")


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def main():
    print("=" * 62)
    print("  DEMI — Monitoramento TOTAL de Seguranca Industrial")
    print("  12 Filtros de Seguranca | Industria 4.0")
    print("=" * 62)
    print("Iniciando camera...")

    mp_drawing = mp.solutions.drawing_utils
    init_database()

    pose = init_pose(DETECTION_CONFIDENCE, TRACKING_CONFIDENCE)
    hand_detector = init_hands(DETECTION_CONFIDENCE, TRACKING_CONFIDENCE)
    face_mesh = init_face_mesh(DETECTION_CONFIDENCE, TRACKING_CONFIDENCE)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERRO: Nao foi possivel acessar a webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera: {frame_w}x{frame_h}")

    win_name = "DEMI - Monitoramento TOTAL de Seguranca Industrial"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 720)
    print("Pressione ESC para sair.\n")

    session_id = start_session()

    # Estado geral
    modules = {"pose": True, "hands": True, "face": True}
    filters = {
        "drowsiness": True, "yawn": True, "distraction": True,
        "inactivity": True, "blink_rate": True, "head_down": True,
        "posture": True, "trunk_lean": True, "arms_up": True,
        "squat": True, "fall": True, "hand_speed": True,
    }

    color_index = 0
    is_mirrored = True
    is_recording = False
    video_writer = None
    recording_path = ""

    # FPS e coleta
    prev_time = time.time()
    fps = 0
    last_log_time = time.time()
    log_count = 0
    alert_count = 0
    total_frames = 0

    # Estado dos filtros
    eyes_closed_start = None
    yawn_start = None
    head_down_start = None
    arms_up_start = None
    last_hand_positions = []
    last_hand_active_time = time.time()
    prev_ear_open = True
    blink_times = deque()
    had_pose_before = False
    no_pose_frames = 0
    last_alert_time = {}

    ALERT_COOLDOWN = 5.0

    # Mapeamento tecla -> filtro
    KEY_FILTER_MAP = {
        ord("4"): "drowsiness",
        ord("5"): "yawn",
        ord("6"): "distraction",
        ord("7"): "inactivity",
        ord("8"): "blink_rate",
        ord("9"): "head_down",
        ord("0"): "posture",
        ord("q"): "trunk_lean", ord("Q"): "trunk_lean",
        ord("w"): "arms_up",   ord("W"): "arms_up",
        ord("a"): "squat",     ord("A"): "squat",
        ord("f"): "fall",      ord("F"): "fall",
        ord("g"): "hand_speed", ord("G"): "hand_speed",
    }

    FILTER_NAMES_PT = {
        "drowsiness": "SONOLENCIA", "yawn": "BOCEJO", "distraction": "DISTRACAO",
        "inactivity": "INATIVIDADE", "blink_rate": "PISCADAS", "head_down": "CABECA BAIXA",
        "posture": "POSTURA", "trunk_lean": "TRONCO", "arms_up": "BRACOS",
        "squat": "AGACHAMENTO", "fall": "QUEDA", "hand_speed": "VELOC.MAOS",
    }

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            total_frames += 1
            curr_time = time.time()

            if is_mirrored:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False

            color_name = COLOR_NAMES[color_index]
            color = COLORS[color_name]

            pose_detected = 0
            hands_count = 0
            fingers_count = 0
            face_detected = 0
            active_alerts = set()
            banners = []
            metrics = []

            # ============================
            # DETECCAO
            # ============================

            results_pose = None
            if modules["pose"]:
                results_pose = pose.process(rgb)
                draw_pose(frame, results_pose, mp_drawing, color)
                if results_pose.pose_landmarks:
                    pose_detected = 1

            results_hands = None
            if modules["hands"]:
                results_hands = hand_detector.process(rgb)
                draw_hands(frame, results_hands, mp_drawing, color)
                draw_finger_count(frame, results_hands, color)
                if results_hands.multi_hand_landmarks:
                    hands_count = len(results_hands.multi_hand_landmarks)
                    for hl in results_hands.multi_hand_landmarks:
                        fingers_count += count_raised_fingers(hl)

            results_face = None
            if modules["face"]:
                results_face = face_mesh.process(rgb)
                draw_face(frame, results_face, mp_drawing, color)
                if results_face.multi_face_landmarks:
                    face_detected = 1

            has_face = results_face and results_face.multi_face_landmarks
            has_pose = results_pose and results_pose.pose_landmarks
            has_hands = results_hands and results_hands.multi_hand_landmarks
            face_lm = results_face.multi_face_landmarks[0] if has_face else None
            pose_lm = results_pose.pose_landmarks if has_pose else None

            # ============================
            # 12 FILTROS DE SEGURANCA
            # ============================

            def _fire(fid, desc, sev="warning"):
                """Registra alerta se cooldown passou."""
                nonlocal alert_count
                active_alerts.add(fid)
                banners.append((desc, sev))
                if curr_time - last_alert_time.get(fid, 0) > ALERT_COOLDOWN:
                    log_alert(session_id, fid, desc, sev)
                    alert_count += 1
                    last_alert_time[fid] = curr_time

            # --- [4] SONOLENCIA ---
            if filters["drowsiness"] and face_lm:
                ear = check_drowsiness(face_lm)
                metrics.append(("EAR", f"{ear:.2f}", ear >= EAR_THRESHOLD))
                if ear < EAR_THRESHOLD:
                    if eyes_closed_start is None:
                        eyes_closed_start = curr_time
                    elif (curr_time - eyes_closed_start) >= EAR_CONSEC_SECONDS:
                        dur = curr_time - eyes_closed_start
                        _fire("drowsiness",
                              f"SONOLENCIA! Olhos fechados {dur:.0f}s (EAR:{ear:.2f})", "danger")
                else:
                    eyes_closed_start = None

            # --- [5] BOCEJO ---
            if filters["yawn"] and face_lm:
                mar = check_yawn(face_lm)
                metrics.append(("MAR", f"{mar:.2f}", mar < MAR_THRESHOLD))
                if mar >= MAR_THRESHOLD:
                    if yawn_start is None:
                        yawn_start = curr_time
                    elif (curr_time - yawn_start) >= MAR_CONSEC_SECONDS:
                        _fire("yawn",
                              f"BOCEJO detectado! Boca aberta (MAR:{mar:.2f})", "warning")
                else:
                    yawn_start = None

            # --- [6] DISTRACAO ---
            if filters["distraction"] and face_lm:
                dev = check_distraction(face_lm)
                metrics.append(("Desvio", f"{dev:.3f}", dev <= HEAD_TURN_THRESHOLD))
                if dev > HEAD_TURN_THRESHOLD:
                    _fire("distraction",
                          f"DISTRACAO! Cabeca virada (desvio:{dev:.2f})", "warning")

            # --- [8] PISCADAS / FADIGA ---
            if filters["blink_rate"] and face_lm:
                blinked, prev_ear_open = check_blink(face_lm, prev_ear_open, EAR_THRESHOLD)
                if blinked:
                    blink_times.append(curr_time)
                while blink_times and (curr_time - blink_times[0]) > BLINK_WINDOW_SECONDS:
                    blink_times.popleft()
                bpm = len(blink_times)
                is_ok = BLINK_LOW_RATE <= bpm <= BLINK_HIGH_RATE
                metrics.append(("Pisc/min", str(bpm), is_ok))
                if bpm > BLINK_HIGH_RATE:
                    _fire("blink_rate",
                          f"FADIGA! Piscadas alta: {bpm}/min", "warning")
                elif bpm < BLINK_LOW_RATE and curr_time - last_alert_time.get("blink_rate_low", 0) > 30:
                    active_alerts.add("blink_rate")
                    banners.append((f"MICRO-SONO? Poucas piscadas ({bpm}/min)", "danger"))
                    if curr_time - last_alert_time.get("blink_rate", 0) > ALERT_COOLDOWN:
                        log_alert(session_id, "blink_rate",
                                  f"Piscadas baixa: {bpm}/min", "danger")
                        alert_count += 1
                        last_alert_time["blink_rate"] = curr_time

            # --- [9] CABECA BAIXA ---
            if filters["head_down"] and face_lm:
                head_val = check_head_down(face_lm)
                metrics.append(("Cab.Y", f"{head_val:.3f}", head_val < HEAD_DOWN_THRESHOLD))
                if head_val >= HEAD_DOWN_THRESHOLD:
                    if head_down_start is None:
                        head_down_start = curr_time
                    elif (curr_time - head_down_start) >= HEAD_DOWN_SECONDS:
                        dur = curr_time - head_down_start
                        _fire("head_down",
                              f"CABECA BAIXA ha {dur:.0f}s!", "warning")
                else:
                    head_down_start = None

            # --- [0] POSTURA OMBROS ---
            if filters["posture"] and pose_lm:
                angle = check_posture(pose_lm)
                metrics.append(("Ombros", f"{angle:.0f} deg", angle <= POSTURE_ANGLE_THRESHOLD))
                if angle > POSTURE_ANGLE_THRESHOLD:
                    _fire("posture",
                          f"POSTURA! Ombros inclinados {angle:.0f} graus", "warning")

            # --- [Q] INCLINACAO DO TRONCO ---
            if filters["trunk_lean"] and pose_lm:
                lean = check_trunk_lean(pose_lm)
                metrics.append(("Tronco", f"{lean:.3f}", lean < TRUNK_LEAN_THRESHOLD))
                if lean >= TRUNK_LEAN_THRESHOLD:
                    _fire("trunk_lean",
                          f"TRONCO INCLINADO! Desvio: {lean:.3f}", "warning")

            # --- [W] BRACOS ELEVADOS ---
            if filters["arms_up"] and pose_lm:
                left_up, right_up = check_arms_elevated(pose_lm)
                any_up = left_up or right_up
                sides = ("E" if left_up else "") + ("D" if right_up else "") or "-"
                metrics.append(("Bracos", sides, not any_up))
                if any_up:
                    if arms_up_start is None:
                        arms_up_start = curr_time
                    elif (curr_time - arms_up_start) >= ARMS_UP_SECONDS:
                        dur = curr_time - arms_up_start
                        _fire("arms_up",
                              f"BRACOS ELEVADOS ha {dur:.0f}s! Risco ergonomico", "warning")
                else:
                    arms_up_start = None

            # --- [A] AGACHAMENTO ---
            if filters["squat"] and pose_lm:
                knee_angle = check_squat(pose_lm)
                metrics.append(("Joelhos", f"{knee_angle:.0f} deg", knee_angle >= SQUAT_ANGLE_THRESHOLD))
                if knee_angle < SQUAT_ANGLE_THRESHOLD:
                    _fire("squat",
                          f"AGACHAMENTO! Joelhos a {knee_angle:.0f} graus", "warning")

            # --- [F] QUEDA ---
            if filters["fall"]:
                if had_pose_before and not has_pose:
                    no_pose_frames += 1
                    if no_pose_frames >= FALL_CONSECUTIVE_FRAMES:
                        _fire("fall",
                              f"POSSIVEL QUEDA! Pose perdida por {no_pose_frames} frames", "critical")
                else:
                    no_pose_frames = 0
                if has_pose:
                    had_pose_before = True

            # --- [7] INATIVIDADE ---
            if filters["inactivity"] and results_hands:
                hand_lms = results_hands.multi_hand_landmarks or []
                is_active, new_pos = check_hand_activity(hand_lms, last_hand_positions)
                last_hand_positions = new_pos
                if is_active:
                    last_hand_active_time = curr_time
                else:
                    idle = curr_time - last_hand_active_time
                    if idle > INACTIVITY_SECONDS:
                        _fire("inactivity",
                              f"INATIVIDADE! Maos paradas ha {idle:.0f}s", "warning")

            # --- [G] VELOCIDADE EXCESSIVA ---
            if filters["hand_speed"] and results_hands:
                hand_lms = results_hands.multi_hand_landmarks or []
                speed = check_hand_speed(hand_lms, last_hand_positions)
                metrics.append(("Vel.Mao", f"{speed:.3f}", speed < HAND_SPEED_THRESHOLD))
                if speed >= HAND_SPEED_THRESHOLD:
                    _fire("hand_speed",
                          f"VELOCIDADE EXCESSIVA! Mao a {speed:.3f} u/frame", "warning")

            # ============================
            # DESENHO
            # ============================

            if banners:
                draw_alert_banners(frame, banners)

            draw_safety_panel(frame, active_alerts, filters)

            if metrics:
                draw_metrics(frame, metrics)

            # FPS
            fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time

            # Coleta
            if (curr_time - last_log_time) >= LOG_INTERVAL:
                log_detection(session_id, pose_detected, hands_count,
                              fingers_count, face_detected, fps)
                log_count += 1
                last_log_time = curr_time

            # HUD
            active_filter_count = sum(1 for v in filters.values() if v)
            draw_hud(frame, fps, color_name, modules, is_recording,
                     is_mirrored, session_id, log_count, alert_count,
                     active_filter_count, len(filters))

            # Gravacao
            if is_recording and video_writer is not None:
                video_writer.write(frame)

            cv2.imshow(win_name, frame)

            # ============================
            # CONTROLES
            # ============================
            key = cv2.waitKey(5) & 0xFF

            if key == 27:
                break
            elif key == ord("1"):
                modules["pose"] = not modules["pose"]
                print(f"[POSE] {'ON' if modules['pose'] else 'OFF'}")
            elif key == ord("2"):
                modules["hands"] = not modules["hands"]
                print(f"[MAOS] {'ON' if modules['hands'] else 'OFF'}")
            elif key == ord("3"):
                modules["face"] = not modules["face"]
                print(f"[ROSTO] {'ON' if modules['face'] else 'OFF'}")
            elif key in KEY_FILTER_MAP:
                fid = KEY_FILTER_MAP[key]
                filters[fid] = not filters[fid]
                name = FILTER_NAMES_PT.get(fid, fid)
                print(f"[{name}] {'ON' if filters[fid] else 'OFF'}")
            elif key == ord("t") or key == ord("T"):
                any_on = any(filters.values())
                for k in filters:
                    filters[k] = not any_on
                print(f"[TODOS FILTROS] {'OFF' if any_on else 'ON'}")
            elif key == ord("c") or key == ord("C"):
                color_index = (color_index + 1) % len(COLOR_NAMES)
                print(f"[COR] {COLOR_NAMES[color_index]}")
            elif key == ord("m") or key == ord("M"):
                is_mirrored = not is_mirrored
                print(f"[ESPELHO] {'ON' if is_mirrored else 'OFF'}")
            elif key == ord("s") or key == ord("S"):
                save_screenshot(frame)
            elif key == ord("r") or key == ord("R"):
                if not is_recording:
                    video_writer, recording_path = start_recording(frame_w, frame_h)
                    is_recording = True
                else:
                    stop_recording(video_writer, recording_path)
                    video_writer = None
                    is_recording = False
            elif key == ord("e") or key == ord("E"):
                export_to_csv()
            elif key == ord("d") or key == ord("D"):
                print("[DASHBOARD] Abrindo: http://localhost:5000")
                webbrowser.open("http://localhost:5000")

    except KeyboardInterrupt:
        print("\nInterrompido.")

    finally:
        end_session(session_id, total_frames, log_count)
        if is_recording and video_writer is not None:
            stop_recording(video_writer, recording_path)
        cap.release()
        pose.close()
        hand_detector.close()
        face_mesh.close()
        cv2.destroyAllWindows()
        print(f"DEMI finalizado. {alert_count} alertas nesta sessao.")


if __name__ == "__main__":
    main()
