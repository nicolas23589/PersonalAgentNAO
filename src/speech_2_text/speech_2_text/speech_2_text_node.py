#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from naoqi_bridge_msgs.msg import AudioBuffer, HeadTouch
import numpy as np
import whisper
import sys
from pathlib import Path
from .external_integrations.gemini_agent import GeminiAgent  # Importar el módulo de Gemini Agent


class AudioTranscriber(Node):
    """
    Toca la cabeza: inicia/termina grabación.
    Al terminar: transcribe con Whisper y publica en /asr/text.
    """
    def __init__(self):
        super().__init__('audio_transcriber')
        self.recording = False
        self.audio_buffer = bytearray()

        self.create_subscription(AudioBuffer, '/mic', self.on_audio, 10)
        self.create_subscription(HeadTouch, '/head_touch', self.on_touch, 10)
        
        TELEGRAM_CHAT_ID = "1242472265"

        # Crear agente
        self.gemini_agent = GeminiAgent(telegram_chat_id=TELEGRAM_CHAT_ID)

        self.pub_text = self.create_publisher(String, '/asr/text', 10)

        self.model = whisper.load_model("base")
        self.get_logger().info("AudioTranscriber listo. Toca la cabeza para grabar/parar.")

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
            
            text = (result.get("text","") or "").strip()
            
            # Llamar a gemini_agent.main con el texto transcrito

            print("Iniciando Gemini Agent...")
            print("=" * 60)

            response = self.gemini_agent.process_message(text)

            print(f"Respuesta para TTS: {response['natural_response']}")
            print("-" * 60)
            print(f"Funciones ejecutadas: {len(response['function_calls'])}")
            for fc in response['function_calls']:
                print(f"  - {fc['name']}: {fc['result']['status']}")
            print("=" * 60)
            

            return text
        except Exception as e:
            self.get_logger().error(f"Error al transcribir con Whisper: {e}")
            return ""

def main():
    rclpy.init()
    node = AudioTranscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()