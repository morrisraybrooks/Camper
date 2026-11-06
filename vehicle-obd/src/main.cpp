// Sequoia OBD box (2026-10-17) - does what the Torque app does, without the phone app:
//  * Bluetooth Classic SPP to the ELM327 mini ("OBDII", PIN 1234)
//  * standard OBD-II mode 01 PIDs: speed 0D, RPM 0C, coolant 05, fuel 2F, module voltage 42
//  * Toyota transmission temp: header 7E1 (transmission ECU), mode 21 PID 82 (community PID,
//    not verified on a 2016 Sequoia - trans_raw is sent too so the formula can be corrected)
//  * POST JSON every ~5 s to Home Assistant (Home Assistant Cloud webhook), Wi-Fi = camper
//    Wi-Fi or Morris's phone hotspot set to the same name/password
//  * buzzer on GPIO25: 2 beeps = connected to the truck; trans > 230F beeps every 5 s,
//    > 245F fast beeping. Works with no signal.
#include <Arduino.h>
#include <BluetoothSerial.h>
#include <ELMduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "secrets.h"

#define BUZZER 25
#define LED 2
static const char *OBD_NAMES[] = {"OBDII", "OBD2", "OBD II", "V-LINK", "Android-Vlink", "OBDBLE"};

BluetoothSerial SerialBT;
ELM327 elm;
WiFiClientSecure tls;
// hooks.nabu.casa chains to Amazon Root CA 1 (checked 2026-11-06; valid to 2038).
// If Nabu Casa ever changes CA, POSTs will fail with a TLS error: update this.
static const char HOOK_ROOT_CA[] = R"PEM(
-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv
b3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj
ca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM
9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw
IFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6
VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L
93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm
jgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC
AYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA
A4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI
U5PMCCjjmCXPI6T53iHTfIUJrU6adTrCC2qJeHZERxhlbI1Bjjt/msv0tadQ1wUs
N+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V8viTO96LXFvKWlJbYK8U90vv
o/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJcJmApzyMZFo6IQ6XU
5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeXeGADbkpy
rqXRfboQnoZsG4q5WTP468SQvvG5
-----END CERTIFICATE-----
)PEM";

enum Step { S_SPEED, S_RPM, S_COOL, S_FUEL, S_VOLT, S_TRANS, S_SEND };
Step step = S_SPEED;
float speedMph = NAN, rpm = NAN, coolF = NAN, fuel = NAN, volts = NAN, transF = NAN;
long transRaw = -1;
int failRound = 0, okRound = 0;
bool btUp = false, engineOn = false, sentOff = true;
unsigned long lastSend = 0, lastBeep = 0;

void beep(int n, int ms = 120) {
  for (int i = 0; i < n; i++) { digitalWrite(BUZZER, HIGH); delay(ms); digitalWrite(BUZZER, LOW); delay(ms); }
}

bool connectObd() {
  SerialBT.begin("SequoiaOBD", true);
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  SerialBT.setPin("1234", 4);             // Arduino-ESP32 3.x wants the length too
#else
  SerialBT.setPin("1234");
#endif
  for (const char *n : OBD_NAMES) {
    Serial.printf("BT: trying %s\n", n);
    if (SerialBT.connect(n)) {
      Serial.printf("BT: connected to %s\n", n);
      if (elm.begin(SerialBT, false, 2000)) { beep(2); return true; }
      Serial.println("ELM327: no reply");
      SerialBT.disconnect();
    }
  }
  return false;
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  static bool tried = false;               // first try right away at boot
  static unsigned long lastTry = 0;
  if (tried && millis() - lastTry < 15000) return;
  tried = true;
  lastTry = millis();
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void post(bool withData) {
  if (WiFi.status() != WL_CONNECTED) return;
  String j = "{";
  auto add = [&](const char *k, float v, int dp) { if (!isnan(v)) { if (j.length() > 1) j += ","; j += "\"" + String(k) + "\":" + String(v, dp); } };
  if (withData) {
    add("speed", speedMph, 0); add("rpm", rpm, 0); add("coolant", coolF, 0);
    add("trans", transF, 0); add("fuel", fuel, 1); add("volts", volts, 1);
    if (transRaw >= 0) { if (j.length() > 1) j += ","; j += "\"trans_raw\":\"" + String(transRaw) + "\""; }
  }
  j += "}";
  HTTPClient http;
  tls.setCACert(HOOK_ROOT_CA);             // check the cloudhook's certificate
  if (http.begin(tls, HOOK_URL)) {
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(j);
    Serial.printf("POST %d %s\n", code, j.c_str());
    http.end();
  }
}

// Non-blocking ELMduino read: returns true when this step is finished (ok or failed)
template <typename F> bool readPid(F fn, float &out, float scale = 1, float bias = 0) {
  float v = fn();
  if (elm.nb_rx_state == ELM_SUCCESS) { out = v * scale + bias; okRound++; return true; }
  if (elm.nb_rx_state != ELM_GETTING_MSG) { out = NAN; failRound++; return true; }
  return false;
}

void readTrans() {
  elm.sendCommand_Blocking("AT SH 7E1");
  double raw = elm.processPID(0x21, 0x82, 1, 2);
  unsigned long t0 = millis();
  while (elm.nb_rx_state == ELM_GETTING_MSG && millis() - t0 < 1500) { raw = elm.processPID(0x21, 0x82, 1, 2); delay(5); }
  if (elm.nb_rx_state == ELM_SUCCESS) {
    transRaw = (long)raw;
    float c = ((raw * 84.0 / 1000.0) - 480.0) / 12.0;   // community formula, °C
    transF = c * 9.0 / 5.0 + 32.0;
    if (transF < -40 || transF > 400) transF = NAN;    // nonsense = wrong formula / not supported
  } else { transF = NAN; transRaw = -1; }
  elm.sendCommand_Blocking("AT SH 7DF");
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER, OUTPUT); pinMode(LED, OUTPUT);
  beep(1, 60);
  ensureWifi();
  btUp = connectObd();
}

void loop() {
  ensureWifi();
  if (!btUp) { digitalWrite(LED, LOW); delay(5000); btUp = connectObd(); return; }
  if (!SerialBT.connected()) { btUp = false; return; }
  digitalWrite(LED, HIGH);
  bool done = false;
  switch (step) {
    case S_SPEED: done = readPid([] { return elm.kph(); }, speedMph, 0.621371); break;
    case S_RPM:   done = readPid([] { return elm.rpm(); }, rpm); break;
    case S_COOL:  done = readPid([] { return elm.engineCoolantTemp(); }, coolF, 1.8, 32); break;
    case S_FUEL:  done = readPid([] { return elm.fuelLevel(); }, fuel); break;
    case S_VOLT:  done = readPid([] { return elm.ctrlModVoltage(); }, volts); break;
    case S_TRANS: readTrans(); done = true; break;
    case S_SEND:
      engineOn = okRound > 0;
      if (engineOn) { if (millis() - lastSend > 4000) { post(true); lastSend = millis(); sentOff = false; } }
      else if (!sentOff) { post(false); sentOff = true; }       // truck off: clear the gauges once
      okRound = failRound = 0;
      if (!engineOn) delay(10000);                              // ignition off: check again in 10 s
      done = true; break;
  }
  if (done) step = (Step)((step + 1) % (S_SEND + 1));
  // local transmission alarm (no phone or internet needed)
  if (!isnan(transF) && transF > 230 && millis() - lastBeep > (transF > 245 ? 600 : 5000)) {
    beep(transF > 245 ? 2 : 1, transF > 245 ? 80 : 200); lastBeep = millis();
  }
}
