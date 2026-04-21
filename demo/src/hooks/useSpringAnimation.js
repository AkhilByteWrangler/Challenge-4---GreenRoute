import { useEffect, useRef, useState } from 'react';

// Spring physics: natural deceleration with mass, tension, damping
// Config presets: stiff (responsive), wobbly (playful), molasses (slow)
const presets = {
  stiff: { mass: 1, tension: 170, friction: 26 },
  bouncy: { mass: 1, tension: 120, friction: 14 },
  molasses: { mass: 1, tension: 80, friction: 20 },
};

function solveSpring(value, target, velocity, mass, tension, friction, dt = 0.016) {
  if (Math.abs(target - value) < 0.0001 && Math.abs(velocity) < 0.0001) {
    return [target, 0];
  }
  const springForce = -tension * (value - target);
  const dampingForce = -friction * velocity;
  const acceleration = (springForce + dampingForce) / mass;
  const newVelocity = velocity + acceleration * dt;
  const newValue = value + newVelocity * dt;
  return [newValue, newVelocity];
}

export function useSpringAnimation(targetValue, preset = 'stiff', onComplete) {
  const [animatedValue, setAnimatedValue] = useState(targetValue);
  const state = useRef({ value: targetValue, velocity: 0 });
  const frameRef = useRef(null);
  const config = typeof preset === 'string' ? presets[preset] : preset;

  useEffect(() => {
    state.current.value = animatedValue;
  }, [animatedValue]);

  useEffect(() => {
    const animate = () => {
      const [newValue, newVelocity] = solveSpring(
        state.current.value,
        targetValue,
        state.current.velocity,
        config.mass,
        config.tension,
        config.friction
      );

      state.current.value = newValue;
      state.current.velocity = newVelocity;

      setAnimatedValue(newValue);

      if (Math.abs(targetValue - newValue) < 0.0001 && Math.abs(newVelocity) < 0.0001) {
        setAnimatedValue(targetValue);
        if (onComplete) onComplete();
        return;
      }

      frameRef.current = requestAnimationFrame(animate);
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [targetValue, config, onComplete]);

  return animatedValue;
}
