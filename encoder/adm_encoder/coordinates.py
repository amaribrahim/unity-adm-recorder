"""Unity left-handed Y-up world space → ADM Cartesian (ITU-R BS.2076 Annex A) conversion."""


def unity_to_adm(
    x: float, y: float, z: float, scene_radius: float
) -> tuple[float, float, float]:
    """
    Unity (left-handed Y-up): X=right, Y=up, Z=forward
    ADM Cartesian:            X=right, Y=front(+1)/rear(-1), Z=up(+1)/down(-1)

    Divides by scene_radius and clamps to [-1, 1].
    """
    def _norm(v: float) -> float:
        return max(-1.0, min(1.0, v / scene_radius))

    return _norm(x), _norm(z), _norm(y)
