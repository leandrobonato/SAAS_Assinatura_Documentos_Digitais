import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

const SignaturePad = forwardRef(function SignaturePad(_, ref) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const [hasStroke, setHasStroke] = useState(false);

  useEffect(() => {
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineWidth = 2.4;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#1a2035";
  }, []);

  function getPos(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    const point = e.touches ? e.touches[0] : e;
    return {
      x: ((point.clientX - rect.left) / rect.width) * canvasRef.current.width,
      y: ((point.clientY - rect.top) / rect.height) * canvasRef.current.height,
    };
  }

  function start(e) {
    e.preventDefault();
    drawing.current = true;
    const ctx = canvasRef.current.getContext("2d");
    const { x, y } = getPos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  function move(e) {
    if (!drawing.current) return;
    e.preventDefault();
    const ctx = canvasRef.current.getContext("2d");
    const { x, y } = getPos(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasStroke(true);
  }

  function end() {
    drawing.current = false;
  }

  useImperativeHandle(ref, () => ({
    isEmpty: () => !hasStroke,
    getDataUrl: () => canvasRef.current.toDataURL("image/png"),
    clear: () => {
      const canvas = canvasRef.current;
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
      setHasStroke(false);
    },
  }));

  return (
    <canvas
      ref={canvasRef}
      className="signature-canvas"
      width={320}
      height={140}
      onMouseDown={start}
      onMouseMove={move}
      onMouseUp={end}
      onMouseLeave={end}
      onTouchStart={start}
      onTouchMove={move}
      onTouchEnd={end}
    />
  );
});

export default SignaturePad;
