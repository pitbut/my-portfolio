# Методы моста вызываются из JavaScript по имени — их нельзя переименовывать
-keepclassmembers class com.robutpit.perevodchik.SpeechBridge {
    @android.webkit.JavascriptInterface <methods>;
}
