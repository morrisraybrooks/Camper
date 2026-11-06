"""Action test: ask Camper Brain to switch Power Strip Plug 1 on, then off, and
verify the real switch state (and that the other sockets were not touched).
Usage: python3 test_ha_action.py"""
import time
from ha_ws import HA
ha = HA()
PLUGS = ['switch.tp_link_power_strip_63ce_light', 'switch.tp_link_power_strip_63ce_plug_2',
         'switch.tp_link_power_strip_63ce_plug_3', 'switch.tp_link_power_strip_63ce']
def states():
    st = {s['entity_id']: s['state'] for s in ha.call({'type': 'get_states'})}
    return {p.split('63ce')[1] or '(whole strip)': st.get(p) for p in PLUGS}
def ask(text, conv_id=None):
    t = time.time()
    msg = {'type': 'conversation/process', 'text': text, 'agent_id': 'conversation.camper_brain', 'language': 'en'}
    if conv_id: msg['conversation_id'] = conv_id
    r = ha.call(msg)
    print(f"{time.time()-t:5.1f}s  Q: {text}\n        A: {r['response']['speech'].get('plain', {}).get('speech', '')}")
    return r.get('conversation_id')
print('before:', states())
ask('turn on power strip plug 1'); time.sleep(3); after_on = states(); print('after on: ', after_on)
ask('turn off power strip plug 1'); time.sleep(3); after_off = states(); print('after off:', after_off)
# '(whole strip)' reports 'on' whenever ANY socket is on, so it is not a "touched" signal.
ok = after_on['_light'] == 'on' and after_off['_light'] == 'off' and \
     after_on['_plug_2'] == after_on['_plug_3'] == 'off'
print('\nRESULT:', 'PASS - plug 1 switched on and off, nothing else touched' if ok else 'FAIL')
