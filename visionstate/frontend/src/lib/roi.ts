// Geometry for regions of interest. Coordinates are normalised (0–1) relative to the image.
import type { Roi } from './types';

export type Pt = [number, number];

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** The four corners of a rectangle, clockwise from top-left. */
export function rectPoints(r: { x: number; y: number; w: number; h: number }): Pt[] {
  return [
    [r.x, r.y],
    [r.x + r.w, r.y],
    [r.x + r.w, r.y + r.h],
    [r.x, r.y + r.h],
  ];
}

/** Corners of a region: its polygon, or the rectangle's corners. */
export const toPoints = (roi: Roi): Pt[] => (roi.points?.length ? roi.points.map((p) => [p[0], p[1]]) : rectPoints(roi));

/** A region from polygon corners; x/y/w/h is the bounding box (the backend recomputes it too). */
export function fromPoints(points: Pt[]): Roi {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  const w = Math.max(...xs) - x;
  const h = Math.max(...ys) - y;
  // The bounding box's four corners, clockwise from its top-left, are a plain rectangle again (e.g.
  // after removing an added corner), so it is stored and shown as one. Starting elsewhere they stay
  // corners: a straightened region's top is its first edge (turnTop).
  const EPS = 1e-6;
  const same = (p: Pt, q: Pt) => Math.abs(p[0] - q[0]) < EPS && Math.abs(p[1] - q[1]) < EPS;
  const box = rectPoints({ x, y, w, h });
  if (points.length === 4 && points.every((p, i) => same(p, box[i]))) return { x, y, w, h };
  return { x, y, w, h, points };
}

/** A straightened region turned a quarter: the next edge clockwise becomes its top (the first edge,
 * from the first corner to the second). */
export function turnTop(roi: Roi): Roi {
  const points = toPoints(roi);
  return fromPoints([...points.slice(1), points[0]]);
}

/** What takes a point (u, v) of the upright rectangle (0–1, top-left first) to the image, for four
 * corners with the top edge first: the perspective the backend straightens (imaging.Plane). Null when
 * the corners make no area to straighten. */
export function quadMap(points: Pt[]): ((u: number, v: number) => Pt) | null {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = points;
  const [dx1, dx2, sx] = [x1 - x2, x3 - x2, x0 - x1 + x2 - x3];
  const [dy1, dy2, sy] = [y1 - y2, y3 - y2, y0 - y1 + y2 - y3];
  const det = dx1 * dy2 - dx2 * dy1;
  if (Math.abs(det) < 1e-9) return null;
  const g = (sx * dy2 - dx2 * sy) / det;
  const h = (dx1 * sy - sx * dy1) / det;
  return (u, v) => {
    const w = g * u + h * v + 1;
    return [
      ((x1 - x0 + g * x1) * u + (x3 - x0 + h * x3) * v + x0) / w,
      ((y1 - y0 + g * y1) * u + (y3 - y0 + h * y3) * v + y0) / w,
    ];
  };
}

/**
 * A box placed in the plane a reading sensor's region is read in (an extra region: x, y, w, h in units
 * of the region's height from its top-left corner) as four corners in the frame (0–1), the way the
 * backend cuts it (imaging.reading_plane, Plane.crop): the region's four corners when it is
 * straightened, else its bounding box. ``aspect`` is the frame's width over its height (the plane's
 * units are pixels). Null without a region that makes an area.
 */
export function planeBox(
  roi: Roi | null,
  straightened: boolean,
  box: { x: number; y: number; w: number; h: number },
  aspect: number,
): Pt[] | null {
  if (!roi || !(aspect > 0)) return null;
  const corners = straightened && isPolygon(roi) && toPoints(roi).length === 4 ? toPoints(roi) : rectPoints(roi);
  const map = quadMap(corners);
  if (!map) return null;
  const px = corners.map(([x, y]) => [x * aspect, y]);
  const dist = (a: number[], b: number[]) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  // The plane's width in units of its height: the mean of its top and bottom edges over the mean of its sides.
  const width = (dist(px[0], px[1]) + dist(px[3], px[2])) / (dist(px[0], px[3]) + dist(px[1], px[2]));
  if (!(width > 0)) return null;
  const at = (x: number, y: number) => map(x / width, y);
  return [at(box.x, box.y), at(box.x + box.w, box.y), at(box.x + box.w, box.y + box.h), at(box.x, box.y + box.h)];
}

/** The bounding rectangle of a region, without polygon corners. */
export const toRectangle = (roi: Roi): Roi => ({ x: roi.x, y: roi.y, w: roi.w, h: roi.h });

/** Midpoint of each edge (edge i runs from corner i to corner i+1). */
export const midpoints = (points: Pt[]): Pt[] =>
  points.map((p, i) => {
    const q = points[(i + 1) % points.length];
    return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
  });

export const isPolygon = (roi: Roi | null | undefined) => !!roi?.points?.length;
