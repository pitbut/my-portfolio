package com.robutpit.zamri.motion

import com.robutpit.zamri.data.db.ViolationSide

/** Describes one triggered sector in human ("Слева, второй") and storage terms. */
data class SectorLabel(
    /** 1-based sector index counted left-to-right across the whole frame. */
    val globalLane: Int,
    val side: ViolationSide,
    /** 1-based index counted outward from the center on [side]; 0 for CENTER. */
    val sideLane: Int
)

/**
 * Maps a zero-based sector index (0 = leftmost) into the left/center/right +
 * outward-counted numbering used for both the voice callout and the archive
 * list, e.g. sectors=5 -> [Left#2, Left#1, Center, Right#1, Right#2].
 */
fun labelForSector(index: Int, sectorCount: Int): SectorLabel {
    val globalLane = index + 1
    return if (sectorCount % 2 == 1) {
        val centerIndex = sectorCount / 2
        when {
            index == centerIndex -> SectorLabel(globalLane, ViolationSide.CENTER, 0)
            index < centerIndex -> SectorLabel(globalLane, ViolationSide.LEFT, centerIndex - index)
            else -> SectorLabel(globalLane, ViolationSide.RIGHT, index - centerIndex)
        }
    } else {
        val leftCount = sectorCount / 2
        if (index < leftCount) {
            SectorLabel(globalLane, ViolationSide.LEFT, leftCount - index)
        } else {
            SectorLabel(globalLane, ViolationSide.RIGHT, index - leftCount + 1)
        }
    }
}
