package com.dividinghead.calc.model

/** Built-in factory presets. Users may edit copies of these or create their own from scratch. */
object Presets {

    val brownSharpePlateSet = IndexPlateSet(
        name = "Brown & Sharpe (дюймовый)",
        plates = listOf(
            IndexPlate("Диск 1", listOf(15, 16, 17, 18, 19, 20)),
            IndexPlate("Диск 2", listOf(21, 23, 27, 29, 31, 33)),
            IndexPlate("Диск 3", listOf(37, 39, 41, 43, 47, 49))
        )
    )

    /** Common metric plate set found on post-Soviet UDG-135/UDG-160 dividing heads. */
    val udgMetricPlateSet = IndexPlateSet(
        name = "УДГ-135/160 (метрический)",
        plates = listOf(
            IndexPlate("Диск 1", listOf(16, 17, 18, 19, 20, 23)),
            IndexPlate("Диск 2", listOf(27, 29, 31, 33, 37, 39)),
            IndexPlate("Диск 3", listOf(41, 43, 47, 49, 54, 58)),
            IndexPlate("Диск 4", listOf(62, 66, 71, 77, 79, 83))
        )
    )

    val brownSharpeGearSet = GearSet(
        name = "Стандартная гитара Brown & Sharpe",
        gears = listOf(24, 28, 32, 40, 44, 48, 56, 64, 72, 86, 100)
    )

    val udgGearSet = GearSet(
        name = "Гитара УДГ (метрическая)",
        gears = listOf(25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 127)
    )

    val brownSharpe40 = DividingHeadPreset(
        name = "Brown & Sharpe, N=40",
        characteristicN = 40,
        plateSet = brownSharpePlateSet,
        gearSet = brownSharpeGearSet,
        leadScrewPitchMm = 6.0,
        isMetric = false
    )

    val udg135_40 = DividingHeadPreset(
        name = "УДГ-135, N=40",
        characteristicN = 40,
        plateSet = udgMetricPlateSet,
        gearSet = udgGearSet,
        leadScrewPitchMm = 6.0,
        isMetric = true
    )

    val udg160_40 = DividingHeadPreset(
        name = "УДГ-160, N=40",
        characteristicN = 40,
        plateSet = udgMetricPlateSet,
        gearSet = udgGearSet,
        leadScrewPitchMm = 6.0,
        isMetric = true
    )

    val all: List<DividingHeadPreset> = listOf(brownSharpe40, udg135_40, udg160_40)
}
