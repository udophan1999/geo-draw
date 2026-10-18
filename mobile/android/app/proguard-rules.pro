# kotlinx.serialization keeps what it needs through its own consumer rules.
# The math renderer reaches its FreeType bindings through JNI.
-keep class com.pvporbit.freetype.** { *; }
