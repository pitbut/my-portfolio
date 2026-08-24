package com.dividinghead.calc

import java.math.BigInteger

/**
 * Exact rational number used to avoid floating point drift when comparing
 * indexing/gear ratios for an exact match.
 */
data class Fraction(val numerator: BigInteger, val denominator: BigInteger) {

    init {
        require(denominator != BigInteger.ZERO) { "Denominator must not be zero" }
    }

    val isZero: Boolean get() = numerator == BigInteger.ZERO

    fun reduced(): Fraction {
        var n = numerator
        var d = denominator
        if (d < BigInteger.ZERO) {
            n = -n
            d = -d
        }
        val g = n.gcd(d)
        return if (g == BigInteger.ZERO) Fraction(BigInteger.ZERO, BigInteger.ONE)
        else Fraction(n / g, d / g)
    }

    operator fun minus(other: Fraction): Fraction =
        Fraction(numerator * other.denominator - other.numerator * denominator, denominator * other.denominator).reduced()

    operator fun times(other: Fraction): Fraction =
        Fraction(numerator * other.numerator, denominator * other.denominator).reduced()

    fun toDouble(): Double = numerator.toDouble() / denominator.toDouble()

    /** True if this fraction can be represented exactly as holes/circle for the given circle size. */
    fun exactHolesOn(circle: Int): Boolean {
        val r = reduced()
        return BigInteger.valueOf(circle.toLong()).mod(r.denominator) == BigInteger.ZERO
    }

    companion object {
        fun of(numerator: Long, denominator: Long): Fraction =
            Fraction(BigInteger.valueOf(numerator), BigInteger.valueOf(denominator)).reduced()

        fun of(numerator: Int, denominator: Int): Fraction = of(numerator.toLong(), denominator.toLong())
    }
}

fun gcd(a: Int, b: Int): Int {
    var x = kotlin.math.abs(a)
    var y = kotlin.math.abs(b)
    while (y != 0) {
        val t = y
        y = x % y
        x = t
    }
    return x
}
