# Winter solar irradiation on roof surfaces

**Bochum, North Rhine-Westphalia · ArcGIS Pro Spatial Analyst · guided course exercise GÜ 08 “Solarstrahlung”**

*In January the orientation of a roof plane decides more than its location – and the course parameters make every absolute value far too low.*

![Map of mean irradiation per roof surface](GUE08_Solarstrahlung_map.png)

| File | Content |
|---|---|
| [GUE08_Solarstrahlung_description.pdf](GUE08_Solarstrahlung_description.pdf) | One-page description: question, data, method, result, limits |
| [GUE08_Solarstrahlung_map.pdf](GUE08_Solarstrahlung_map.pdf) | Map layout (A4, vector) |

> Guided course exercise: the task, its parameters and the data were set by GIS-Akademie GmbH, where the core workflow was demonstrated in class. I repeated the analysis on my own; data checks, roof-edge treatment, climate comparison, map and assessment are my own work.

## Question

How much solar energy reaches each roof surface during the first ten days of the year, in Wh/m²? The course sets the atmosphere: transmissivity 0.4 and diffuse proportion 0.4.

## Data

- **Surface model (DOM)**, about 1 m, 725 × 342 m – course data, no metadata supplied
- **Orthophoto** – course data, map background only
- **Roof surfaces** – 62 polygons, one per roof plane – GIS-Akademie (exercise data, not included)

## Method

- **Raster Solar Radiation** on the whole surface model, 1–10 January, uniform sky. No mask, so the shade of neighbouring trees and buildings is part of the calculation.
- **Roof edges removed:** polygons shrunk by 1 m, because at 1 m resolution the outline cells partly show walls and ground.
- **Zonal Statistics as Table** per roof surface on the shrunk polygons, with the original polygons as a comparison. Surfaces with no interior cell get no value; fewer than 10 interior cells are flagged as low confidence.

## Result

| Roof surfaces | Minimum | Median | Maximum |
|---|---:|---:|---:|
| 56 of 62 with a value | 273 Wh/m² | 504 Wh/m² | 1,591 Wh/m² |

South-facing planes receive up to six times as much as the least favoured surface. The distribution is bimodal: most surfaces stay below about 600 Wh/m², a small group exceeds 1,430. Removing edge cells changes a single roof’s mean by a median of 6 %, in both directions, so it matters for comparing roofs, not for the overall picture.

## Analytical limits

- **The absolute values are far too low; the ranking is the result.** DWD’s January mean for Germany is 23 kWh/m² on a horizontal surface; the model gives at most 1.9 kWh/m² for ten days. At a 16° sun, a transmissivity of 0.4 lets almost no direct radiation through.
- **Ten January days are not a year.** With a low sun, orientation and shade dominate; the values say nothing about annual yield.
- **The surface model sets the horizon.** Obstacles beyond its edge are missing, and trees modelled with summer foliage shade more than in January.
- **Orientation was read from the map, not measured**, and small surfaces are fragile: 6 have no value, 8 rest on fewer than 10 cells.

The full discussion is in the description PDF.
