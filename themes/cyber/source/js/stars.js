const canvas = document.getElementById('stars');
const ctx = canvas.getContext('2d');

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const stars = Array.from({length: 200}, () => ({
  x: Math.random() * canvas.width,
  y: Math.random() * canvas.height,
  r: Math.random() * 1.5,
  o: Math.random(),
  speed: Math.random() * 0.3 + 0.1,
  color: ['#ffffff','#b400ff','#00d4ff'][Math.floor(Math.random()*3)]
}));

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  stars.forEach(s => {
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fillStyle = s.color;
    ctx.globalAlpha = s.o;
    ctx.fill();
    s.o += (Math.random() - 0.5) * 0.05;
    s.o = Math.max(0.1, Math.min(1, s.o));
  });
  ctx.globalAlpha = 1;
  requestAnimationFrame(draw);
}

draw();

window.addEventListener('resize', () => {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
});