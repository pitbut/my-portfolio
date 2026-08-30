package com.robutpit.roachrace.model

/** Every individual roach gets one of these on top of its breed — same
 * species, different personality, so two "Чёрный таракан" roaches don't
 * play identically. Multipliers apply to the gym economy (see
 * RoachEconomy) and to how often it gets spooked on the track. */
enum class Trait(
    val displayName: String,
    val description: String,
    val feedGainMult: Float,
    val trainChanceMult: Float,
    val satietyDecayMult: Float,
    val stressGrowthMult: Float,
) {
    GLUTTON("Прожорливый", "Быстро наедается, но хуже тренируется", 1.5f, 0.75f, 1f, 1f),
    WORKAHOLIC("Трудяга", "Отлично тренируется, но быстрее голодает", 0.8f, 1.3f, 1.35f, 1f),
    TOUGH("Живучий", "Медленнее слабеет от голода", 1f, 1f, 0.6f, 1f),
    NERVOUS("Нервный", "На бегах пугается легче, зато резвее тренируется", 1f, 1.2f, 1f, 0.55f),
    CALM("Невозмутимый", "Реже пугается на трассе, но тренируется чуть медленнее", 1f, 0.8f, 1f, 1.6f),
    ;

    companion object {
        fun random() = entries.random()
        fun byId(id: String?): Trait? = entries.firstOrNull { it.name == id }
    }
}
