"""Statics model for a simply supported beam."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _positive_finite(value: float, name: str) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


@dataclass(frozen=True, slots=True)
class PointLoad:
    """A downward point load.

    Args:
        magnitude: Load magnitude in kN.
        position: Distance from the left support in m.
    """

    magnitude: float
    position: float

    def __post_init__(self) -> None:
        _positive_finite(self.magnitude, "point-load magnitude")
        if not isfinite(self.position) or self.position < 0:
            raise ValueError("point-load position must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class UDL:
    """A downward uniformly distributed load over a beam segment."""

    intensity: float
    start: float
    end: float

    def __post_init__(self) -> None:
        _positive_finite(self.intensity, "UDL intensity")
        if not all(isfinite(value) for value in (self.start, self.end)):
            raise ValueError("UDL bounds must be finite")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("UDL requires 0 <= start < end")

    @property
    def resultant(self) -> float:
        return self.intensity * (self.end - self.start)

    @property
    def centroid(self) -> float:
        return (self.start + self.end) / 2


@dataclass(frozen=True, slots=True)
class Result:
    position: float
    shear: float
    moment: float


@dataclass(frozen=True, slots=True)
class Beam:
    """A simply supported beam under downward transverse loading."""

    length: float
    point_loads: tuple[PointLoad, ...] = ()
    udls: tuple[UDL, ...] = ()

    def __post_init__(self) -> None:
        _positive_finite(self.length, "beam length")
        outside_points = [
            load.position for load in self.point_loads if load.position > self.length
        ]
        outside_udls = [
            (load.start, load.end)
            for load in self.udls
            if load.end > self.length
        ]
        if outside_points or outside_udls:
            raise ValueError("all loads must lie within the beam span")

    def reactions(self) -> tuple[float, float]:
        """Return upward reactions at the left and right supports in kN."""
        point_force = sum(load.magnitude for load in self.point_loads)
        udl_force = sum(load.resultant for load in self.udls)
        moment_about_left = sum(
            load.magnitude * load.position for load in self.point_loads
        ) + sum(load.resultant * load.centroid for load in self.udls)
        right = moment_about_left / self.length
        left = point_force + udl_force - right
        return left, right

    def shear_at(self, position: float) -> float:
        """Return shear in kN immediately to the right of ``position``."""
        self._validate_position(position)
        left, _ = self.reactions()
        point_force = sum(
            load.magnitude
            for load in self.point_loads
            if load.position <= position
        )
        udl_force = sum(
            load.intensity * max(0.0, min(position, load.end) - load.start)
            for load in self.udls
            if position > load.start
        )
        return left - point_force - udl_force

    def moment_at(self, position: float) -> float:
        """Return sagging bending moment in kN·m at ``position``."""
        self._validate_position(position)
        left, _ = self.reactions()
        point_moment = sum(
            load.magnitude * (position - load.position)
            for load in self.point_loads
            if load.position <= position
        )
        udl_moment = 0.0
        for load in self.udls:
            loaded_length = max(0.0, min(position, load.end) - load.start)
            udl_moment += (
                load.intensity * loaded_length * (position - load.start - loaded_length / 2)
            )
        return left * position - point_moment - udl_moment

    def sample(self, stations: int = 21) -> tuple[Result, ...]:
        """Sample shear and moment at equally spaced stations."""
        if isinstance(stations, bool) or not isinstance(stations, int) or stations < 2:
            raise ValueError("stations must be an integer of at least 2")
        spacing = self.length / (stations - 1)
        return tuple(
            Result(x := index * spacing, self.shear_at(x), self.moment_at(x))
            for index in range(stations)
        )

    def _validate_position(self, position: float) -> None:
        if not isfinite(position) or not 0 <= position <= self.length:
            raise ValueError("position must lie within the beam span")
