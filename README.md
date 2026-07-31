# Morva

Morva is a small, dependency-free Python toolkit for preliminary analysis of simply supported beams. It calculates support reactions, shear force, and bending moment for combinations of point loads and uniformly distributed loads.

The project is intended for education and preliminary checks. It is not a substitute for a qualified structural engineer or code-compliant design software.

## Quick start

Morva requires Python 3.10 or newer.

```bash
python -m morva --length 8 \
  --point-load 20@3 \
  --udl 5@2:6 \
  --stations 9
```

## Python API

```python
from morva import Beam, PointLoad, UDL

beam = Beam(
    length=8.0,
    point_loads=(PointLoad(20.0, 3.0),),
    udls=(UDL(5.0, 2.0, 6.0),),
)

left, right = beam.reactions()
results = beam.sample(stations=17)
```

All lengths are in metres, forces in kN, and moments in kN·m. Loads are entered as positive downward magnitudes; upward support reactions are reported as positive.

## Model and sign convention

Equilibrium is solved from:

```text
R_A + R_B = sum(vertical loads)
R_B L = sum(load × distance from A)
```

Positive bending moment denotes sagging. At a point-load discontinuity, `shear_at(x)` returns the value immediately to the right of the load.

## Development

```bash
python -m unittest discover -s tests -v
```

## Limitations

- simply supported, statically determinate beams only;
- vertical point loads and UDLs only;
- no stiffness, stress, or deflection calculation;
- no partial safety factors or design-code checks.

## License

MIT
