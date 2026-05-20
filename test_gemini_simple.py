"""
Script simple para testear el agente de Gemini sin depender del speech-to-text.
Permite definir un mensaje manualmente y ver la respuesta del agente.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'speech_2_text'))

from speech_2_text.external_integrations.gemini_agent import GeminiAgent


MENSAJE_PRUEBA = "me puedes mandar un mensaje diciendo hola david al telegram?"

# ID de chat de Telegram (opcional, si quieres probar funciones de Telegram)
TELEGRAM_CHAT_ID = None  # Puedes cambiarlo o dejarlo en None

# Habilitar/deshabilitar calendario
ENABLE_CALENDAR = True


def main():
    print("=" * 70)
    print("TEST GEMINI AGENT")
    print("=" * 70)
    print(f"\n📤 Mensaje enviado: {MENSAJE_PRUEBA}\n")
    
    # Crear el agente
    agent = GeminiAgent(
        telegram_chat_id=TELEGRAM_CHAT_ID,
        enable_calendar=ENABLE_CALENDAR
    )
    
    # Procesar el mensaje
    try:
        response = agent.process_message(MENSAJE_PRUEBA)
        
        print("-" * 70)
        print(" RESPUESTA DEL AGENTE:")
        print("-" * 70)
        print(response['natural_response'])
        print()
        
        # Mostrar funciones ejecutadas si las hay
        if response['function_calls']:
            print("-" * 70)
            print(f"  FUNCIONES EJECUTADAS: {len(response['function_calls'])}")
            print("-" * 70)
            for fc in response['function_calls']:
                print(f"  • {fc['name']}")
                print(f"    Argumentos: {fc['args']}")
                print(f"    Resultado: {fc['result']['status']}")
                print()
        else:
            print("-" * 70)
            print("  No se ejecutaron funciones")
            print("-" * 70)
        
        print("=" * 70)
        print(" Test completado exitosamente")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
