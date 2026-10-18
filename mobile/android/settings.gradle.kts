// The MathMate Android app (plan: docs/mobile-android-plan.md, progress: docs/mobile-android-checklist.md).
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://jitpack.io")
    }
}

rootProject.name = "MathMate"
include(":app")

// The math renderer is the AndroidMath fork (xuanthinhJB/AndroidMath, branch mathmate). A checkout
// next to the repo (../AndroidMath, like ../SwiftMath for iOS) is built in place of the JitPack
// artifact, so changes to the fork show up at once. -Pmathmate.jitpack forces the artifact.
val localMath = file("../../../AndroidMath")
if (localMath.resolve("mathdisplaylib").isDirectory && !providers.gradleProperty("mathmate.jitpack").isPresent) {
    includeBuild(localMath) {
        dependencySubstitution {
            substitute(module("com.github.xuanthinhJB:AndroidMath")).using(project(":mathdisplaylib"))
        }
    }
}
