# Room generates code at compile time; keep entities/DAO annotations intact.
-keep class com.robutpit.zamri.data.db.** { *; }

# CameraX and ML Kit ship their own consumer rules; nothing extra needed here.
