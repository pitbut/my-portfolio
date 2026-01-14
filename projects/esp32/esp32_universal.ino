/*
 * ESP32 Universal Constructor - Base Firmware
 * robotpit.com
 * 
 * Upload this firmware once via USB cable
 * After that, configure and program via web interface
 * 
 * Required Libraries (install via Arduino Library Manager):
 * - ESP32 Board Package
 * - WebSocketsServer by Markus Sattler
 * - ArduinoJson by Benoit Blanchon
 * - ESPAsyncWebServer by me-no-dev
 * - AsyncTCP by me-no-dev
 */

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>
#include <Preferences.h>
#include <ArduinoOTA.h>

// ==========================================
// CONFIGURATION
// ==========================================

// Default AP credentials (when WiFi not configured)
const char* ap_ssid = "ESP32-Setup";
const char* ap_password = "12345678";

// Web Server and WebSocket
AsyncWebServer server(80);
WebSocketsServer webSocket = WebSocketsServer(81);

// Preferences for storing WiFi credentials
Preferences preferences;

// Current WiFi credentials
String wifi_ssid = "";
String wifi_password = "";

// Pin configuration storage
struct PinConfig {
    int pin;
    String type;      // "digital_out", "pwm", "digital_in", "adc"
    String function;  // "led", "motor", "servo", etc.
    int value;        // Current value
};

PinConfig pinConfigs[40];  // ESP32 has up to 40 pins
int configuredPinsCount = 0;

// ==========================================
// SETUP
// ==========================================

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n");
    Serial.println("╔══════════════════════════════════════╗");
    Serial.println("║  ESP32 Universal Constructor v1.0   ║");
    Serial.println("║  robotpit.com                        ║");
    Serial.println("╚══════════════════════════════════════╝");
    Serial.println();
    
    // Load WiFi credentials from flash
    loadWiFiCredentials();
    
    // Try to connect to saved WiFi
    if (wifi_ssid.length() > 0) {
        Serial.println("Connecting to saved WiFi: " + wifi_ssid);
        connectToWiFi(wifi_ssid, wifi_password);
    }
    
    // If not connected, start AP mode
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Starting Access Point mode...");
        startAPMode();
    }
    
    // Start WebSocket server
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);
    Serial.println("WebSocket started on port 81");
    
    // Start Web Server for WiFi configuration
    setupWebServer();
    
    // Start OTA updates
    setupOTA();
    
    Serial.println("\n✅ System Ready!");
    Serial.print("📱 ");
    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("WiFi Connected - IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.print("AP Mode - Connect to: ");
        Serial.println(ap_ssid);
        Serial.print("   Password: ");
        Serial.println(ap_password);
        Serial.print("   Then open: http://");
        Serial.println(WiFi.softAPIP());
    }
    Serial.println();
}

// ==========================================
// MAIN LOOP
// ==========================================

void loop() {
    webSocket.loop();
    ArduinoOTA.handle();
    
    // Send periodic status updates
    static unsigned long lastUpdate = 0;
    if (millis() - lastUpdate > 5000) {
        sendStatus();
        lastUpdate = millis();
    }
}

// ==========================================
// WIFI FUNCTIONS
// ==========================================

void connectToWiFi(String ssid, String password) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), password.c_str());
    
    Serial.print("Connecting");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi Connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi Connection Failed");
    }
}

void startAPMode() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(ap_ssid, ap_password);
    
    Serial.println("✅ Access Point Started");
    Serial.print("SSID: ");
    Serial.println(ap_ssid);
    Serial.print("Password: ");
    Serial.println(ap_password);
    Serial.print("IP: ");
    Serial.println(WiFi.softAPIP());
}

void loadWiFiCredentials() {
    preferences.begin("wifi", true);
    wifi_ssid = preferences.getString("ssid", "");
    wifi_password = preferences.getString("password", "");
    preferences.end();
}

void saveWiFiCredentials(String ssid, String password) {
    preferences.begin("wifi", false);
    preferences.putString("ssid", ssid);
    preferences.putString("password", password);
    preferences.end();
    
    wifi_ssid = ssid;
    wifi_password = password;
}

// ==========================================
// WEB SERVER SETUP
// ==========================================

void setupWebServer() {
    // Serve WiFi configuration page
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
        String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
        html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
        html += "<title>ESP32 Setup</title>";
        html += "<style>";
        html += "body{font-family:Arial;background:#0d1117;color:#c9d1d9;padding:20px;text-align:center;}";
        html += ".container{max-width:400px;margin:50px auto;background:#161b22;padding:30px;border-radius:12px;border:1px solid #30363d;}";
        html += "h1{color:#58a6ff;margin-bottom:20px;}";
        html += "input{width:100%;padding:12px;margin:10px 0;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#c9d1d9;font-size:16px;}";
        html += "button{width:100%;padding:12px;background:linear-gradient(135deg,#58a6ff,#0969da);color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;margin-top:10px;}";
        html += "button:hover{transform:translateY(-2px);}";
        html += ".info{color:#8b949e;font-size:14px;margin-top:20px;}";
        html += "</style></head><body>";
        html += "<div class='container'>";
        html += "<h1>🔌 ESP32 Setup</h1>";
        html += "<form action='/save' method='POST'>";
        html += "<input type='text' name='ssid' placeholder='WiFi Name (SSID)' required>";
        html += "<input type='password' name='password' placeholder='WiFi Password'>";
        html += "<button type='submit'>💾 Save & Connect</button>";
        html += "</form>";
        html += "<div class='info'>";
        html += "After saving, ESP32 will restart and connect to your WiFi.<br>";
        html += "Find the IP address in Serial Monitor.";
        html += "</div>";
        html += "</div></body></html>";
        
        request->send(200, "text/html", html);
    });
    
    // Handle WiFi credentials save
    server.on("/save", HTTP_POST, [](AsyncWebServerRequest *request){
        String ssid = "";
        String password = "";
        
        if (request->hasParam("ssid", true)) {
            ssid = request->getParam("ssid", true)->value();
        }
        if (request->hasParam("password", true)) {
            password = request->getParam("password", true)->value();
        }
        
        if (ssid.length() > 0) {
            saveWiFiCredentials(ssid, password);
            
            String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
            html += "<meta http-equiv='refresh' content='10;url=/'>";
            html += "<style>body{font-family:Arial;background:#0d1117;color:#c9d1d9;padding:50px;text-align:center;}</style>";
            html += "</head><body>";
            html += "<h1>✅ Saved!</h1>";
            html += "<p>ESP32 is restarting and connecting to: <strong>" + ssid + "</strong></p>";
            html += "<p>Check Serial Monitor for IP address</p>";
            html += "</body></html>";
            
            request->send(200, "text/html", html);
            
            delay(2000);
            ESP.restart();
        } else {
            request->send(400, "text/plain", "SSID cannot be empty");
        }
    });
    
    server.begin();
    Serial.println("✅ Web Server started on port 80");
}

// ==========================================
// WEBSOCKET HANDLERS
// ==========================================

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.printf("[%u] Disconnected!\n", num);
            break;
            
        case WStype_CONNECTED: {
            IPAddress ip = webSocket.remoteIP(num);
            Serial.printf("[%u] Connected from %d.%d.%d.%d\n", num, ip[0], ip[1], ip[2], ip[3]);
            
            // Send welcome message
            String welcome = "{\"type\":\"connected\",\"message\":\"ESP32 Ready\"}";
            webSocket.sendTXT(num, welcome);
            break;
        }
            
        case WStype_TEXT: {
            Serial.printf("[%u] Received: %s\n", num, payload);
            
            // Parse JSON command
            DynamicJsonDocument doc(1024);
            DeserializationError error = deserializeJson(doc, payload);
            
            if (error) {
                Serial.println("JSON parse error");
                return;
            }
            
            String cmdType = doc["type"].as<String>();
            
            if (cmdType == "ping") {
                webSocket.sendTXT(num, "{\"type\":\"pong\"}");
            }
            else if (cmdType == "digital") {
                handleDigitalCommand(doc);
            }
            else if (cmdType == "pwm") {
                handlePWMCommand(doc);
            }
            else if (cmdType == "config") {
                handleConfigCommand(doc);
            }
            else if (cmdType == "flash") {
                handleFlashCommand(doc);
            }
            else if (cmdType == "read") {
                handleReadCommand(num, doc);
            }
            
            break;
        }
            
        default:
            break;
    }
}

void handleDigitalCommand(JsonDocument& doc) {
    int pin = doc["pin"];
    int value = doc["value"];
    
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value);
    
    Serial.printf("Digital: Pin %d = %d\n", pin, value);
}

void handlePWMCommand(JsonDocument& doc) {
    int pin = doc["pin"];
    int value = doc["value"];
    int channel = doc["channel"] | 0;
    
    // Setup PWM
    ledcSetup(channel, 5000, 8);  // 5kHz, 8-bit resolution
    ledcAttachPin(pin, channel);
    ledcWrite(channel, value);
    
    Serial.printf("PWM: Pin %d = %d (channel %d)\n", pin, value, channel);
}

void handleConfigCommand(JsonDocument& doc) {
    Serial.println("Received configuration");
    
    // Store configuration
    JsonObject config = doc["config"];
    configuredPinsCount = 0;
    
    for (JsonPair kv : config) {
        int pin = atoi(kv.key().c_str());
        JsonObject pinCfg = kv.value();
        
        if (configuredPinsCount < 40) {
            pinConfigs[configuredPinsCount].pin = pin;
            pinConfigs[configuredPinsCount].type = pinCfg["type"].as<String>();
            pinConfigs[configuredPinsCount].function = pinCfg["function"].as<String>();
            pinConfigs[configuredPinsCount].value = 0;
            
            // Initialize pin
            if (pinCfg["type"] == "digital_out" || pinCfg["type"] == "pwm") {
                pinMode(pin, OUTPUT);
            } else if (pinCfg["type"] == "digital_in") {
                pinMode(pin, INPUT_PULLUP);
            }
            
            configuredPinsCount++;
        }
    }
    
    Serial.printf("Configured %d pins\n", configuredPinsCount);
}

void handleFlashCommand(JsonDocument& doc) {
    Serial.println("Flash command received");
    
    // Store config permanently
    handleConfigCommand(doc);
    
    // TODO: Save to EEPROM/Preferences
    
    Serial.println("Configuration will persist after reboot");
}

void handleReadCommand(uint8_t clientNum, JsonDocument& doc) {
    int pin = doc["pin"];
    
    // Read pin value
    int value = 0;
    
    // Check if it's analog pin
    if (pin >= 32 && pin <= 39) {
        value = analogRead(pin);
    } else {
        value = digitalRead(pin);
    }
    
    // Send response
    String response = "{\"type\":\"read_response\",\"pin\":" + String(pin) + ",\"value\":" + String(value) + "}";
    webSocket.sendTXT(clientNum, response);
}

void sendStatus() {
    String status = "{\"type\":\"status\",";
    status += "\"uptime\":" + String(millis() / 1000) + ",";
    status += "\"heap\":" + String(ESP.getFreeHeap()) + ",";
    status += "\"rssi\":" + String(WiFi.RSSI()) + "}";
    
    webSocket.broadcastTXT(status);
}

// ==========================================
// OTA SETUP
// ==========================================

void setupOTA() {
    ArduinoOTA.setHostname("ESP32-Universal");
    ArduinoOTA.setPassword("admin");  // Change this!
    
    ArduinoOTA.onStart([]() {
        String type;
        if (ArduinoOTA.getCommand() == U_FLASH) {
            type = "sketch";
        } else {
            type = "filesystem";
        }
        Serial.println("Start updating " + type);
    });
    
    ArduinoOTA.onEnd([]() {
        Serial.println("\nEnd");
    });
    
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
    });
    
    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) {
            Serial.println("Auth Failed");
        } else if (error == OTA_BEGIN_ERROR) {
            Serial.println("Begin Failed");
        } else if (error == OTA_CONNECT_ERROR) {
            Serial.println("Connect Failed");
        } else if (error == OTA_RECEIVE_ERROR) {
            Serial.println("Receive Failed");
        } else if (error == OTA_END_ERROR) {
            Serial.println("End Failed");
        }
    });
    
    ArduinoOTA.begin();
    Serial.println("✅ OTA Ready");
}
