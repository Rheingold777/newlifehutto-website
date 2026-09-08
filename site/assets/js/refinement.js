document.addEventListener('DOMContentLoaded',()=>{
  const button=document.querySelector('.menu-toggle');
  const menu=document.querySelector('.site-menu');
  if(!button||!menu)return;
  const setOpen=open=>{button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-label',open?'Close navigation':'Open navigation');menu.classList.toggle('is-open',open)};
  button.addEventListener('click',()=>setOpen(button.getAttribute('aria-expanded')!=='true'));
  menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>setOpen(false)));
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&button.getAttribute('aria-expanded')==='true'){setOpen(false);button.focus()}});
  document.addEventListener('click',event=>{if(!event.target.closest('.site-header'))setOpen(false)});
  const media=matchMedia('(min-width:761px)');media.addEventListener('change',event=>{if(event.matches)setOpen(false)});
  document.querySelectorAll('.site-menu a,.header-give').forEach(a=>{if(new URL(a.href).pathname===location.pathname)a.setAttribute('aria-current','page')});
});
