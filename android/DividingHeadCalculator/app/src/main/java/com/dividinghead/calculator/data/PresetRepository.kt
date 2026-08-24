package com.dividinghead.calculator.data

import com.dividinghead.calc.model.DividingHeadPreset
import com.dividinghead.calc.model.GearSet
import com.dividinghead.calc.model.IndexPlate
import com.dividinghead.calc.model.IndexPlateSet
import com.dividinghead.calc.model.Presets
import com.dividinghead.calculator.data.datastore.AppSettings
import com.dividinghead.calculator.data.db.PresetDao
import com.dividinghead.calculator.data.db.PresetEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/** A preset together with the stable id used to reference it from settings/history. */
data class IdentifiedPreset(
    val id: String,
    val preset: DividingHeadPreset,
    val isBuiltIn: Boolean,
    val entity: PresetEntity? = null
)

private val builtInIds = mapOf(
    "brown_sharpe_40" to Presets.brownSharpe40,
    "udg_135_40" to Presets.udg135_40,
    "udg_160_40" to Presets.udg160_40
)

class PresetRepository(private val presetDao: PresetDao) {

    val allPresets: Flow<List<IdentifiedPreset>> = presetDao.observeAll().map { customEntities ->
        val builtIns = builtInIds.map { (id, preset) ->
            IdentifiedPreset(AppSettings.BUILTIN_PRESET_PREFIX + id, preset, isBuiltIn = true)
        }
        val customs = customEntities.map { entity -> entity.toIdentifiedPreset() }
        builtIns + customs
    }

    suspend fun saveCustomPreset(entity: PresetEntity): Long = presetDao.insert(entity)

    suspend fun updateCustomPreset(entity: PresetEntity) = presetDao.update(entity)

    suspend fun deleteCustomPreset(entity: PresetEntity) = presetDao.delete(entity)

    private fun PresetEntity.toIdentifiedPreset(): IdentifiedPreset {
        val circles = circlesCsv.split(",").mapNotNull { it.trim().toIntOrNull() }.filter { it > 0 }
        val gears = gearsCsv.split(",").mapNotNull { it.trim().toIntOrNull() }.filter { it > 0 }
        val preset = DividingHeadPreset(
            name = name,
            characteristicN = characteristicN,
            plateSet = IndexPlateSet(name, listOf(IndexPlate("Круги", circles))),
            gearSet = GearSet(name, gears),
            leadScrewPitchMm = leadScrewPitchMm,
            isMetric = isMetric
        )
        return IdentifiedPreset(AppSettings.CUSTOM_PRESET_PREFIX + id, preset, isBuiltIn = false, entity = this)
    }
}
