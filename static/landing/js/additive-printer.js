import { animate } from '../vendor/animejs/anime.esm.min.js';
const NS = 'http://www.w3.org/2000/svg';
// Both the toolhead and deposited material use the same projected XY toolpath.
export function createAdditivePrinter(root, onProgress = () => {}) {
    if (!root) return null;
    const count = 18, duration = 14400, group = root.querySelector('[data-print-layers]');
    const trail = root.querySelector('[data-print-trail]'), head = root.querySelector('[data-print-head]');
    const feed = root.querySelector('[data-print-feed]'), beam = root.querySelector('[data-print-beam]');
    const spool = root.querySelector('[data-print-spool]'), label = root.querySelector('[data-print-layer-label]');
    const state = { progress: 0 }, layers = [], routes = [];
    const project = (x, y, z) => [282 + x - y, 326 + (x + y) * .44 - z];
    const pathD = points => points.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ');
    group.replaceChildren();
    for (let i = 0; i < count; i++) {
        const half = 53 - i * 1.15, z = i * 4.2;
        const corners = [[-half,-half],[half,-half],[half,half],[-half,half],[-half,-half]];
        const route = [...corners];
        for(let row = 0; row < 7; row++) {
            const y = -half + (row + 1) * (2 * half / 8);
            route.push([row % 2 ? half : -half,y],[row % 2 ? -half : half,y]);
        }
        routes.push(route.map(([x,y]) => project(x,y,z)));
        const face = document.createElementNS(NS,'path');
        const top = corners.map(([x,y]) => project(x,y,z));
        const lower = [[-half,half],[half,half],[half,-half]].map(([x,y]) => project(x,y,z - 4.2));
        face.setAttribute('d',pathD([...top, ...lower])+'Z');
        face.style.fill = `hsl(${133 - i * 1.4} 70% ${29 + i * .8}%)`;
        face.style.stroke = '#a6eb19'; face.style.strokeWidth = '.6';
        group.appendChild(face); layers.push(face);
    }
    function render(progress) {
        const scaled = Math.min(count - .00001, progress * count), index = Math.floor(scaled), fraction = scaled - index;
        layers.forEach((layer,i) => { layer.style.opacity = i < index || progress >= 1 ? '1' : '0'; });
        const points = routes[index], lengths = points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
        let distance = fraction * lengths.reduce((a,b)=>a+b,0), visible = [points[0]], pos = points[0];
        for(let i=0;i<lengths.length;i++) {
            if(distance >= lengths[i]) { visible.push(points[i+1]);distance-=lengths[i];pos=points[i+1]; }
            else {const f=distance/lengths[i];pos=points[i].map((v,k)=>v+(points[i+1][k]-v)*f);visible.push(pos);break;}
        }
        trail.setAttribute('d',pathD(visible));
        head.setAttribute('transform',`translate(${pos[0]} ${pos[1]})`);
        beam.setAttribute('d',`M146 ${pos[1]-41}H388`);
        feed.setAttribute('d',`M89 43C160 10 ${pos[0]} 32 ${pos[0]} ${pos[1]-49}`);
        feed.style.strokeDashoffset=String(-progress*700);
        spool.setAttribute('transform',`translate(89 79) rotate(${progress*1080})`);
        head.style.opacity=progress >= 1 ? '.35' : '1';
        label.textContent=`CAPA ${Math.min(count,index+1)} / ${count} · ${progress>=1?'PIEZA LISTA':'DEPOSICIÓN + RELLENO'}`;
        onProgress(progress);
    }
    const animation=animate(state,{progress:[0,1],duration,ease:'linear',autoplay:false,onUpdate:()=>render(state.progress),onComplete:()=>render(1)});
    render(1); // Meaningful final illustration even before the observer activates.
    return {play(){state.progress=0;render(0);animation.restart();},pause(){animation.pause();},resume(){animation.play();},static(){animation.pause();render(1);}};
}
