# Anthropic SDK сериализует запросы/ответы через Jackson (рефлексия) — ничего не переименовываем и не выкидываем.
-dontobfuscate
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod,Exceptions,RuntimeVisible*Annotations,KotlinMetadata
-keep class com.anthropic.** { *; }
-keep class com.fasterxml.jackson.** { *; }
-keep class kotlin.Metadata { *; }
-keep class kotlin.reflect.** { *; }
-keep class okhttp3.** { *; }
-keep class okio.** { *; }
-dontwarn com.anthropic.**
-dontwarn com.fasterxml.jackson.**
-dontwarn kotlin.reflect.**
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn org.slf4j.**
-dontwarn java.lang.invoke.**
-dontwarn javax.annotation.**
-dontwarn org.jetbrains.annotations.**
-dontwarn com.google.errorprone.annotations.**

# victools jsonschema-generator (генерация схем из Java-классов — мы её не используем) ссылается на классы,
# которых нет в Android; R8 сгенерировал этот список:
-dontwarn java.lang.reflect.AnnotatedParameterizedType
-dontwarn java.lang.reflect.AnnotatedType
-dontwarn com.github.victools.**
