"""Ask the real Camper Brain agent read-only questions through Home Assistant and
show its answers. Nothing is switched -- questions only. Usage: python3 test_ha_questions.py"""
import time
from ha_ws import HA
QUESTIONS = [
    "what's the temperature inside?",
    "what is the thermostat set to?",
    "is the water pump on?",
    "is the water heater on?",
    "is the awning out?",
    "is Daisy home alone?",
    "is Morris working tonight?",
    "what's on the shopping list?",
    "is the coffee pot on?",
    "what's the humidity?",
]
ha = HA()
for q in QUESTIONS:
    t = time.time()
    r = ha.call({'type': 'conversation/process', 'text': q, 'agent_id': 'conversation.camper_brain', 'language': 'en'})
    speech = r['response']['speech'].get('plain', {}).get('speech', '')
    print(f"{time.time()-t:5.1f}s  Q: {q}\n        A: {speech}")
