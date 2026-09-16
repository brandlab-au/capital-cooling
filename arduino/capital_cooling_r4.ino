#include <WiFiS3.h>
#include <ArduinoMqttClient.h>
#include "arduino_secrets.h"

// Sensible default placeholder pins
const int TEMP_PIN = A0;
const int ACTUATOR_PWM_PIN = 9;

// Network details
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Update these to point to the Linode server when deployed
const char broker[] = "109.74.202.29"; // Placeholder IP
int        port     = 1883;

// Topic names
const char topicCommand[]   = "capital_cooling/command";
const char topicTelemetry[] = "capital_cooling/telemetry";
const char topicAck[]       = "capital_cooling/ack";

// Non-blocking timers
unsigned long previousMillis = 0;
const long interval = 5000; // Heartbeat interval (5s)

// Variables
int currentPwmValue = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }

  pinMode(ACTUATOR_PWM_PIN, OUTPUT);
  analogWrite(ACTUATOR_PWM_PIN, currentPwmValue);

  // Attempt to connect to WiFi network:
  Serial.print("Attempting to connect to WPA SSID: ");
  Serial.println(ssid);
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    Serial.print(".");
    delay(5000);
  }
  Serial.println("\nYou're connected to the network");

  // You can set a username and password for MQTT if needed
  mqttClient.setUsernamePassword(SECRET_MQTT_USER, SECRET_MQTT_PASS);

  Serial.print("Attempting to connect to the MQTT broker: ");
  Serial.println(broker);

  if (!mqttClient.connect(broker, port)) {
    Serial.print("MQTT connection failed! Error code = ");
    Serial.println(mqttClient.connectError());
    while (1);
  }
  Serial.println("You're connected to the MQTT broker!");

  mqttClient.onMessage(onMqttMessage);
  mqttClient.subscribe(topicCommand);
}

void loop() {
  mqttClient.poll();

  unsigned long currentMillis = millis();

  // Heartbeat / Periodic Telemetry
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    sendTelemetry();
  }
}

void onMqttMessage(int messageSize) {
  // Read payload into a String
  String payload = "";
  while (mqttClient.available()) {
    payload += (char)mqttClient.read();
  }

  Serial.print("Received a message with topic '");
  Serial.print(mqttClient.messageTopic());
  Serial.print("', length ");
  Serial.print(messageSize);
  Serial.println(" bytes:");
  Serial.println(payload);

  // Minimal JSON parsing (in production, use ArduinoJson library)
  // Example payload: {"action": "ping"} or {"action": "pwm_set", "value": 128}
  if (payload.indexOf("\"action\": \"ping\"") > 0) {
    handlePing();
  }
  else if (payload.indexOf("\"action\": \"read_sensors\"") > 0) {
    sendTelemetry();
  }
  else if (payload.indexOf("\"action\": \"pwm_set\"") > 0) {
    // Very basic extraction of "value": 128
    int valueIndex = payload.indexOf("\"value\":");
    if (valueIndex > 0) {
      int valueStart = valueIndex + 8;
      // Skip spaces
      while (payload.charAt(valueStart) == ' ') valueStart++;
      String valueStr = payload.substring(valueStart);
      int pwmVal = valueStr.toInt();
      handlePwmSet(pwmVal);
    }
  }
}

void handlePing() {
  // Flash onboard LED as physical feedback
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(100); // Small blocking delay just for visual flash
  digitalWrite(LED_BUILTIN, LOW);

  // Send ACK back
  mqttClient.beginMessage(topicAck);
  // Fake latency measurement context; the server calculates real latency.
  // We just return a standard ACK payload.
  mqttClient.print("{\"status\": \"ack\", \"msg\": \"pong\"}");
  mqttClient.endMessage();
  Serial.println("Sent ping ACK");
}

void handlePwmSet(int value) {
  // Constrain just to be safe
  if(value < 0) value = 0;
  if(value > 255) value = 255;

  currentPwmValue = value;
  analogWrite(ACTUATOR_PWM_PIN, currentPwmValue);

  Serial.print("Set PWM to: ");
  Serial.println(currentPwmValue);
}

void sendTelemetry() {
  int rawAnalog = analogRead(TEMP_PIN);

  // Dummy conversion formula for placeholder (e.g. TMP36)
  // Voltage at pin in milliVolts = (reading from ADC) * (5000/1024)
  // Centigrade temperature = [(analog voltage in mV) - 500] / 10
  float voltage = (rawAnalog / 1024.0) * 5.0;
  float tempC = (voltage - 0.5) * 100.0;

  // Build JSON string
  String jsonPayload = "{\"temp_c\": ";
  jsonPayload += String(tempC, 2);
  jsonPayload += ", \"status\": \"nominal\", \"pwm_val\": ";
  jsonPayload += String(currentPwmValue);
  jsonPayload += "}";

  mqttClient.beginMessage(topicTelemetry);
  mqttClient.print(jsonPayload);
  mqttClient.endMessage();

  Serial.println("Sent telemetry: " + jsonPayload);
}
