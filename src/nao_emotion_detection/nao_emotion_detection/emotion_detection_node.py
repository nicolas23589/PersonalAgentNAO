#!/usr/bin/env python3
# -- coding: utf-8 --

import os, json, time, base64, cv2, re
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from naoqi_bridge_msgs.msg import HeadTouch
from std_msgs.msg import String
from cv_bridge import CvBridge
from dotenv import load_dotenv, find_dotenv

import vertexai
from vertexai.generative_models import GenerativeModel, Part, Image as VertexImage

from naoqi_utilities_msgs.msg import LedParameters

# Cargar .env
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
GCP_LOCATION   = os.getenv('GCP_LOCATION', 'us-central1')
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

ALLOWED = ["feliz", "triste", "enojado", "sorprendido", "neutral", "no visible"]

class EmotionClassifierNode(Node):
    """
    Tap 1: captura frame1 → publica estado RECORDING y ojos AMARILLOS
    Tap 2: captura frame2, clasifica (frame1, frame2), publica emociones y estado REC_DONE con ojos VERDES
    El BehaviorNode señalará INTERACTION_DONE (morado) al terminar el plan.
    """
    def __init__(self):
        super().__init__('emotion_classifier_node')

        # Parámetros
        self.declare_parameter('camera_topic', '/camera/front/image_raw')
        self.declare_parameter('gemini_model', 'gemini-2.5-pro')
        self.declare_parameter('timeout_sec', 25.0)

        self.camera_topic = self.get_parameter('camera_topic').get_parameter_value().string_value
        self.model_name   = self.get_parameter('gemini_model').get_parameter_value().string_value
        self.timeout_sec  = float(self.get_parameter('timeout_sec').value)

        self._gemini = GenerativeModel(self.model_name)

        self.bridge = CvBridge()
        self.last_frame_bgr = None
        self.frame1 = None
        self.frame2 = None
        self.tap_count = 0

        # ROS IO
        self.create_subscription(Image, self.camera_topic, self._on_image, 10)
        self.create_subscription(HeadTouch, '/head_touch', self._on_touch, 10)
        self.pub_emotion = self.create_publisher(String, '/emotion', 10)
        self.pub_state   = self.create_publisher(String, '/interaction/state', 10)
        self.pub_leds    = self.create_publisher(LedParameters, '/set_leds', 10)

        self.get_logger().info(f"[emotion] listo | cam={self.camera_topic} | model={self.model_name}")

    # Callbacks
    def _on_image(self, msg: Image):
        try:
            self.last_frame_bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().warning(f"[emotion] error convirtiendo imagen: {e}")

    def _on_touch(self, msg: HeadTouch):
        if msg.state != 1:
            return
        if self.last_frame_bgr is None:
            self.get_logger().warning("[emotion] no hay frame aún.")
            return

        self.tap_count = 1 if self.tap_count >= 2 else self.tap_count + 1

        if self.tap_count == 1:
            self.frame1 = self.last_frame_bgr.copy()
            self.frame2 = None
            self._publish_state("RECORDING")
            self._set_eyes_rgb(255, 255, 0, duration=0.8)
            self.get_logger().info("[emotion] TAP1 capturado (esperando TAP2 para clasificar)")
        elif self.tap_count == 2:
            self._publish_state("REC_DONE")
            self._set_eyes_rgb(0, 255, 0, duration=0.8)
            self.frame2 = self.last_frame_bgr.copy()
            self.get_logger().info("[emotion] TAP2 capturado → clasificando…")

            e1 = self._classify(self.frame1) if self.frame1 is not None else "no visible"
            e2 = self._classify(self.frame2) if self.frame2 is not None else "no visible"
            out = f"[{self._cap(e1)}, {self._cap(e2)}]"
            self.pub_emotion.publish(String(data=out))
            self.get_logger().info(f"[emotion] publicado: {out}")

            self.frame1 = None
            self.frame2 = None
            self.tap_count = 0

    def _classify(self, frame_bgr):
        if frame_bgr is None:
            return "no visible"
        try:
            # Codificar frame como JPEG en memoria
            ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if not ok:
                return "neutral"
            image_bytes = buf.tobytes()

            prompt = (
                "Detecta una sola emoción facial en español, "
                "entre: feliz, triste, enojado, sorprendido, neutral, no visible. "
                "Responde SOLO la palabra, sin puntuación ni explicación."
            )

            response = self._gemini.generate_content([
                Part.from_image(VertexImage.from_bytes(image_bytes)),
                prompt
            ])

            s = (response.text or "").strip().lower()
            return self._normalize(s)
        except Exception as e:
            self.get_logger().warning(f"[emotion] fallo LLM: {e}")
            return "neutral"

    def _normalize(self, s):
        s = (s or "").strip().lower()
        m = {
            "feliz": ["feliz","contento","alegre","happy"],
            "triste": ["triste","sad"],
            "enojado": ["enojado","enfadado","molesto","angry"],
            "sorprendido": ["sorprendido","sorpresa","surprised"],
            "neutral": ["neutral"],
            "no visible": ["no visible","sin rostro","no face","none","unknown"],
        }
        for k, arr in m.items():
            if s in arr: return k
        for k in ALLOWED:
            if k in s: return k
        return "neutral"

    def _cap(self, s):
        return s.capitalize() if s else "Desconocida"

    def _publish_state(self, st: str):
        self.pub_state.publish(String(data=st))

    def _set_eyes_rgb(self, r, g, b, duration=0.5, name="FaceLeds"):
        msg = LedParameters()
        msg.name, msg.red, msg.green, msg.blue, msg.duration = (
            name,
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b))),
            float(max(0.05, min(2.0, duration))),
        )
        self.get_logger().info(f"▶ SET_LEDS {name} RGB=({msg.red},{msg.green},{msg.blue}) dur={msg.duration:.2f}s")
        self.pub_leds.publish(msg)


def main():
    rclpy.init()
    node = EmotionClassifierNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
