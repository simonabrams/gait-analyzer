/** cm <-> feet/inches conversion for the height input. Backend contract is a
 * plain integer cm, 100-250 (see backend/main.py's height_cm Form field). */
export type HeightUnit = "cm" | "ftin";

export const HEIGHT_MIN_CM = 100;
export const HEIGHT_MAX_CM = 250;

export function cmToFeetInches(cm: number): { feet: number; inches: number } {
  const totalInches = cm / 2.54;
  let feet = Math.floor(totalInches / 12);
  let inches = Math.round(totalInches - feet * 12);
  if (inches === 12) {
    feet += 1;
    inches = 0;
  }
  return { feet, inches };
}

export function feetInchesToCm(feet: number, inches: number): number {
  return Math.round((feet * 12 + inches) * 2.54);
}

export function isHeightInRange(cm: number): boolean {
  return cm >= HEIGHT_MIN_CM && cm <= HEIGHT_MAX_CM;
}
