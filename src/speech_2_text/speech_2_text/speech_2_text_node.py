#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from naoqi_bridge_msgs.msg import AudioBuffer, HeadTouch
import numpy as np
import whisper
import sys
from pathlib import Path
from .external_integrations.gemini_agent import GeminiAgent


class AudioTranscriber(Node):
    """
    Toca la cabeza: inicia/termina grabación.
    Al terminar: transcribe con Whisper, llama a GeminiAgent con el texto y la emoción detectada,
    y publica la respuesta en /tts/say para que BehaviorRenderer la vocalice.
    """
    def __init__(self):
        super().__init__('audio_transcriber')
        self.recording = False
        self.audio_buffer = bytearray()
        self.last_emotion = "neutral"  # Emoción más reciente detectada por EmotionNode

        self.create_subscription(AudioBuffer, '/mic', self.on_audio, 10)
        self.create_subscription(HeadTouch, '/head_touch', self.on_touch, 10)
        self.create_subscription(String, '/emotion', self.on_emotion, 10)

        TELEGRAM_CHAT_ID = "1242472265"

        # Crear agente
        self.gemini_agent = GeminiAgent(telegram_chat_id=TELEGRAM_CHAT_ID)

        self.pub_text = self.create_publisher(String, '/asr/text', 10)
        self.pub_tts  = self.create_publisher(String, '/tts/say', 10)  # Respuesta para el robot

        self.model = whisper.load_model("base")
        self.get_logger().info("AudioTranscriber listo. Toca la cabeza para grabar/parar.")

    def on_emotion(self, msg: String):
        """Guarda la emoción más reciente publicada por EmotionClassifierNode."""
        if msg.data:
            self.last_emotion = msg.data.strip()
            self.get_logger().debug(f"Emoción actualizada: {self.last_emotion}")

    def on_touch(self, msg: HeadTouch):
        if msg.state != 1:
            return
        if not self.recording:
            self.recording = True
            self.audio_buffer.clear()
            self.get_logger().info("🎙️ Grabación iniciada.")
        else:
            self.recording = False
            self.get_logger().info("🛑 Grabación finalizada. Transcribiendo...")
            if len(self.audio_buffer) == 0:
                self.get_logger().warning("Buffer vacío; publicaré texto mínimo para no bloquear.")
                self.pub_text.publish(String(data=""))
                return
            text = self.transcribe(bytes(self.audio_buffer))
            self.pub_text.publish(String(data=text))
            self.get_logger().info(f"Texto transcrito: {text}")

    def on_audio(self, msg: AudioBuffer):
        if self.recording:
            arr = np.array(msg.data, dtype=np.int16)
            self.audio_buffer.extend(arr.tobytes())

    def transcribe(self, raw_audio_bytes: bytes) -> str:
        try:
            int_audio = np.frombuffer(raw_audio_bytes, dtype=np.int16)
            float_audio = int_audio.astype(np.float32) / 32768.0
            result = self.model.transcribe(float_audio, language="es")

            text = (result.get("text", "") or "").strip()

            self.get_logger().info("Enviando a Gemini Agent...")

            # Incluir la emoción detectada como contexto para Gemini
            message_with_emotion = text
            if self.last_emotion and self.last_emotion != "neutral":
                message_with_emotion = f"[El usuario parece estar {self.last_emotion}] {text}"

            response = self.gemini_agent.process_message(message_with_emotion)

            natural_response = response.get('natural_response', '')
            self.get_logger().info(f"Respuesta Gemini: {natural_response}")
            self.get_logger().info(f"Funciones ejecutadas: {len(response.get('function_calls', []))}")

            # Publicar la respuesta para que BehaviorRenderer la vocalice
            if natural_response:
                self.pub_tts.publish(String(data=natural_response))
                self.get_logger().info("✅ Respuesta publicada en /tts/say")

            return text
        except Exception as e:
            self.get_logger().error(f"Error al transcribir/procesar: {e}")
            return ""


def main():
    rclpy.init()
    node = AudioTranscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
