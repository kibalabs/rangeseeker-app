import React from 'react';

import styled from 'styled-components';

const BackgroundContainer = styled.div`
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
`;

const GlassOverlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 1;
  background-color: rgba(10, 10, 10, 0.7);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  pointer-events: none;
`;

const ShapesContainer = styled.div`
  position: fixed;
  inset: 0;
  z-index: 0;
`;

const Shape = styled.div<{ $color: string }>`
  position: absolute;
  width: 500px;
  aspect-ratio: 1;
  border-radius: 50%;
  background-color: ${(props) => props.$color};
  will-change: transform;
`;

interface ShapeData {
  id: number;
  color: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

const random = (min: number, max: number): number => Math.random() * (max - min) + min;

export function AnimatedBackground(): React.ReactElement {
  const [shapes, setShapes] = React.useState<ShapeData[]>([]);
  const shapesRef = React.useRef<ShapeData[]>([]);
  const animationIdRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    const size = 500;
    const min = 1;
    const max = 1.5;

    const colors = [
      'rgba(110, 211, 233, 0.4)',
      'rgba(196, 242, 200, 0.4)',
      'rgba(194, 59, 235, 0.4)',
      'rgba(110, 211, 233, 0.3)',
      'rgba(196, 242, 200, 0.3)',
      'rgba(194, 59, 235, 0.3)',
    ];

    const initialShapes: ShapeData[] = Array.from({ length: 25 }, (_, i) => ({
      id: i,
      color: colors[i % colors.length],
      x: random(0, window.innerWidth - size),
      y: random(0, window.innerHeight - size),
      vx: random(min, max) * (Math.random() > 0.5 ? 1 : -1),
      vy: random(min, max) * (Math.random() > 0.5 ? 1 : -1),
    }));

    shapesRef.current = initialShapes;
    setShapes(initialShapes);

    const updateShapes = () => {
      shapesRef.current = shapesRef.current.map((shape) => {
        let newX = shape.x + shape.vx;
        let newY = shape.y + shape.vy;
        let newVx = shape.vx;
        let newVy = shape.vy;

        if (newX >= window.innerWidth - size) {
          newVx *= -1;
          newX = window.innerWidth - size;
        }
        if (newY >= window.innerHeight - size) {
          newVy *= -1;
          newY = window.innerHeight - size;
        }
        if (newX <= 0) {
          newVx *= -1;
          newX = 0;
        }
        if (newY <= 0) {
          newVy *= -1;
          newY = 0;
        }

        return {
          ...shape,
          x: newX,
          y: newY,
          vx: newVx,
          vy: newVy,
        };
      });

      setShapes([...shapesRef.current]);
      animationIdRef.current = requestAnimationFrame(updateShapes);
    };

    animationIdRef.current = requestAnimationFrame(updateShapes);

    return () => {
      if (animationIdRef.current !== null) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, []);

  return (
    <BackgroundContainer>
      <ShapesContainer>
        {shapes.map((shape) => (
          <Shape
            key={shape.id}
            $color={shape.color}
            style={{
              transform: `translate(${shape.x}px, ${shape.y}px)`,
            }}
          />
        ))}
      </ShapesContainer>
      <GlassOverlay />
    </BackgroundContainer>
  );
}
