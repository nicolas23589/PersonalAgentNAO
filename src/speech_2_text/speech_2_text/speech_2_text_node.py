#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from naoqi_bridge_msgs.msg import AudioBuffer, HeadTouch
import numpy as np
import whisper
import sys
from pathlib import Path

# Agregar el path de external-integrations al sys.path ANTES de importar gemini_agent
# Usar path absoluto para mayor robustez
current_file = Path(__file__).resolve()
external_integrations_path = current_file.parent.parent.parent.parent / 'src' / 'external-integrations'
sys.path.insert(0, str(external_integrations_path))

# Importar gemini_agent con manejo de errores robusto
GEMINI_AVAILABLE = False
try:
    import speech_2_text.speech_2_text.gemini_agent as gemini_agent
    GEMINI_AVAILABLE = True
    print("✅ Gemini Agent importado exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: No se pudo importar gemini_agent: {e}")
    print("💡 El nodo funcionará sin procesamiento Gemini")
except Exception as e:
    print(f"❌ Error inesperado al importar gemini_agent: {e}")
    print("💡 El nodo funcionará sin procesamiento Gemini")


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
            if text and GEMINI_AVAILABLE:
                try:
                    gemini_agent.main(text)
                except Exception as e:
                    self.get_logger().warning(f"Error al procesar con Gemini: {e}")
            elif text and not GEMINI_AVAILABLE:
                self.get_logger().info(f"Gemini no disponible. Texto: {text}")
            
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