"""Configuration defaults and validation for storage case generation."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Config:
    """Configuration for storage case generation."""

    max_footprint: Tuple[float, float] = (350.0, 300.0)
    case_size: Optional[Tuple[float, float]] = None  # Fixed outer dimensions (WxL) when set
    clearance: float = 1.5
    wall_thickness: float = 2.0
    divider_thickness: float = 1.5
    base_height: float = 2.0
    corner_radius: float = 0.0  # 0 = sharp corners
    stackable: bool = False
    stack_lip_inner: float = 2.0  # mm lip extends inward from top
    stack_lip_height: float = 2.0  # mm lip thickness
    stack_clearance: float = 0.3  # mm fit clearance
    label_size: Optional[Tuple[float, float]] = None  # WxL for label area next to bin
    label_dir: str = "X"  # X = label to the right, Y = label below
    label_text_size: float = 4.0  # font size in mm for label text
    label_text_depth: float = 0.5  # engrave depth into top surface in mm

    def validate(self) -> None:
        """Validate configuration values."""
        if self.max_footprint[0] <= 0 or self.max_footprint[1] <= 0:
            raise ValueError("max_footprint must have positive dimensions")
        if self.case_size is not None:
            if self.case_size[0] <= 0 or self.case_size[1] <= 0:
                raise ValueError("case_size must have positive dimensions")
            inner_x = self.case_size[0] - 2 * self.wall_thickness
            inner_y = self.case_size[1] - 2 * self.wall_thickness
            if inner_x <= 0 or inner_y <= 0:
                raise ValueError(
                    "case_size too small for wall thickness (need room for slots)"
                )
        if self.clearance < 0:
            raise ValueError("clearance must be non-negative")
        if self.wall_thickness <= 0:
            raise ValueError("wall_thickness must be positive")
        if self.divider_thickness <= 0:
            raise ValueError("divider_thickness must be positive")
        if self.base_height <= 0:
            raise ValueError("base_height must be positive")
        if self.corner_radius < 0:
            raise ValueError("corner_radius must be non-negative")
        if self.stackable:
            if self.stack_lip_inner <= 0:
                raise ValueError("stack_lip_inner must be positive when stackable")
            if self.stack_lip_height <= 0:
                raise ValueError("stack_lip_height must be positive when stackable")
            if self.stack_clearance < 0:
                raise ValueError("stack_clearance must be non-negative")
        if self.label_size is not None:
            if self.label_size[0] <= 0 or self.label_size[1] <= 0:
                raise ValueError("label_size must have positive dimensions")
        if self.label_dir not in ("X", "Y"):
            raise ValueError("label_dir must be X or Y")
        if self.label_text_size <= 0:
            raise ValueError("label_text_size must be positive")
        if self.label_text_depth <= 0:
            raise ValueError("label_text_depth must be positive")

    @property
    def max_x(self) -> float:
        """Outer width (max footprint or fixed case size)."""
        if self.case_size is not None:
            return self.case_size[0]
        return self.max_footprint[0]

    @property
    def max_y(self) -> float:
        """Outer length (max footprint or fixed case size)."""
        if self.case_size is not None:
            return self.case_size[1]
        return self.max_footprint[1]


def parse_dimensions(s: str) -> Tuple[float, float, float]:
    """Parse 'WxLxH' or 'WxL' (height optional) string to (width, length, height)."""
    parts = s.lower().replace(" ", "").split("x")
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError(f"Expected format WxLxH or WxL, got: {s}")
    dims = [float(p) for p in parts]
    if any(d <= 0 for d in dims):
        raise ValueError(f"Dimensions must be positive, got: {s}")
    if len(dims) == 2:
        dims.append(dims[0])  # Default height = width for square-ish
    return (dims[0], dims[1], dims[2])


def parse_footprint(s: str) -> Tuple[float, float]:
    """Parse 'WxL' string to (width, length)."""
    parts = s.lower().replace(" ", "").split("x")
    if len(parts) != 2:
        raise ValueError(f"Expected format WxL, got: {s}")
    dims = [float(p) for p in parts]
    if any(d <= 0 for d in dims):
        raise ValueError(f"Dimensions must be positive, got: {s}")
    return (dims[0], dims[1])
