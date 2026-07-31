"""Command-line interface for Morva."""

from __future__ import annotations

import argparse

from .beam import Beam, PointLoad, UDL


def point_load(value: str) -> PointLoad:
    try:
        magnitude, position = value.split("@", maxsplit=1)
        return PointLoad(float(magnitude), float(position))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            "point load must use MAGNITUDE@POSITION, for example 20@3"
        ) from exc


def udl(value: str) -> UDL:
    try:
        intensity, segment = value.split("@", maxsplit=1)
        start, end = segment.split(":", maxsplit=1)
        return UDL(float(intensity), float(start), float(end))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            "UDL must use INTENSITY@START:END, for example 5@2:6"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="morva",
        description="Analyse a simply supported beam under point loads and UDLs.",
    )
    parser.add_argument("--length", type=float, required=True, help="beam span in m")
    parser.add_argument(
        "--point-load",
        action="append",
        type=point_load,
        default=[],
        metavar="P@X",
        help="downward point load in kN at x in m; repeatable",
    )
    parser.add_argument(
        "--udl",
        action="append",
        type=udl,
        default=[],
        metavar="W@A:B",
        help="UDL in kN/m from a to b in m; repeatable",
    )
    parser.add_argument("--stations", type=int, default=21)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        beam = Beam(args.length, tuple(args.point_load), tuple(args.udl))
        results = beam.sample(args.stations)
    except ValueError as exc:
        build_parser().error(str(exc))

    left, right = beam.reactions()
    print(f"left_reaction_kN: {left:.3f}")
    print(f"right_reaction_kN: {right:.3f}")
    print("x_m,shear_kN,moment_kNm")
    for result in results:
        print(f"{result.position:.3f},{result.shear:.3f},{result.moment:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
