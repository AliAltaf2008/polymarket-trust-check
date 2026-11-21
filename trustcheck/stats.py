import math

def wilson_interval(successes, n, z=1.96):
    if n<= 0:
        raise ValueError("n must be at least one")
    if successes < 0 or successes > n:
        raise ValueError("successes must be within 0 and n")

    #Observed rate
    p = successes / n

    z2 = z * z

    denominator = 1 + z2 / n

    #Center is not exactly at p and is pulled towards 0.5 so it does not claim certainty at 0% or 100%
    center = (p + z2 / (2* n)) / denominator
    half_width = z * math.sqrt(p * (1-p) / n+ z2 / (4 * n * n)) / denominator

    low = max(0.0, center - half_width)
    high = min(1.0, center + half_width)
    return low, high
