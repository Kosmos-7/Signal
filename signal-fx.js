/* Signal — fond : réseau de particules lumineuses (partagé par toutes les pages).
   Requiert <canvas id="bg"></canvas>. S'auto-initialise. Respecte prefers-reduced-motion. */
(function(){
  const cv=document.getElementById('bg');if(!cv)return;
  const x=cv.getContext('2d');if(!x)return;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  let W,H,DPR,nodes;
  function size(){
    W=innerWidth;H=innerHeight;DPR=Math.min(devicePixelRatio||1,2);
    cv.width=W*DPR;cv.height=H*DPR;cv.style.width=W+'px';cv.style.height=H+'px';x.setTransform(DPR,0,0,DPR,0,0);
    nodes=Array.from({length:54},()=>({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*0.12,vy:(Math.random()-.5)*0.12,r:0.8+Math.random()*1.1,ph:Math.random()*6.28}));
  }
  function draw(){
    x.clearRect(0,0,W,H);
    for(const n of nodes){if(!reduce){n.x+=n.vx;n.y+=n.vy;n.ph+=0.018;}if(n.x<0)n.x=W;if(n.x>W)n.x=0;if(n.y<0)n.y=H;if(n.y>H)n.y=0;}
    for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){const a=nodes[i],b=nodes[j],d=Math.hypot(a.x-b.x,a.y-b.y);if(d<135){x.strokeStyle='rgba(45,105,160,'+((1-d/135)*0.09)+')';x.beginPath();x.moveTo(a.x,a.y);x.lineTo(b.x,b.y);x.stroke();}}
    for(const n of nodes){const tw=0.55+0.45*Math.sin(n.ph);x.fillStyle='rgba(38,111,158,'+(0.07*tw)+')';x.beginPath();x.arc(n.x,n.y,n.r*3.4,0,6.2832);x.fill();x.fillStyle='rgba(30,90,140,'+(0.55*tw)+')';x.beginPath();x.arc(n.x,n.y,n.r,0,6.2832);x.fill();}
    requestAnimationFrame(draw);
  }
  size();draw();window.addEventListener('resize',size);
})();

/* Header : frost au scroll — partagé par toutes les pages.
   Écoute la fenêtre ET la .stage : la watchlist (index) ne fait pas défiler la
   fenêtre (body overflow:hidden) mais sa .stage en interne. Seuil unifié à 10px. */
(function(){
  const hdr=document.querySelector('header');if(!hdr)return;
  const stage=document.querySelector('.stage');
  const upd=()=>{const s=Math.max(window.scrollY||0,stage?stage.scrollTop:0);hdr.classList.toggle('scrolled',s>10);};
  window.addEventListener('scroll',upd,{passive:true});
  if(stage)stage.addEventListener('scroll',upd,{passive:true});
  upd();
})();
