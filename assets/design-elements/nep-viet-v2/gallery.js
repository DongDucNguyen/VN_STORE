const surface=document.querySelector('#surface');
surface.addEventListener('change',()=>document.body.dataset.surface=surface.value);
const reduce=document.querySelector('#reduce');
const system=matchMedia('(prefers-reduced-motion: reduce)');
const status=document.querySelector('#motion-status');
function stop(){document.querySelectorAll('.nv-motion').forEach(el=>el.classList.remove('is-playing'));}
function update(){const reduced=reduce.checked||system.matches;document.body.dataset.reduced=String(reduced);if(reduced)stop();status.textContent=reduced?'Đang giảm chuyển động: giữ hình tĩnh.':'Chuyển động theo thiết lập hệ thống.';}
reduce.addEventListener('change',update);system.addEventListener('change',update);update();
document.querySelectorAll('[data-demo]').forEach(button=>button.addEventListener('click',()=>{stop();if(reduce.checked||system.matches)return;const el=document.querySelector(button.dataset.demo);void el.offsetWidth;el.classList.add('is-playing');status.textContent=button.textContent+' — một lượt.';}));
const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(!entry.isIntersecting)entry.target.classList.remove('is-playing');}));
document.querySelectorAll('.nv-motion').forEach(el=>observer.observe(el));
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
