"use client";
import { useEffect, useRef } from "react";
import { Farm } from "../game/Farm";

export default function FarmCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const farmRef = useRef<Farm | null>(null);

  useEffect(() => {
    if (!canvasRef.current || farmRef.current) return;
    farmRef.current = new Farm(canvasRef.current);
    return () => {
      farmRef.current?.destroy();
      farmRef.current = null;
    };
  }, []);

  return (
    <div className="flex items-center justify-center w-full h-full bg-black">
      <canvas ref={canvasRef} style={{ imageRendering: "pixelated", maxWidth: "100%", maxHeight: "100%" }} />
    </div>
  );
}
