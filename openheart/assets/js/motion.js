/* Open Hearts — animasjoner (GSAP + ScrollTrigger + Lenis, lastet fra eget domene) */
(function(){
  if(!window.gsap || !window.ScrollTrigger) return;              // uten bibliotekene fungerer siden som vanlig
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  gsap.registerPlugin(ScrollTrigger);
  var root=document.documentElement; root.classList.add('anim');
  var fine=matchMedia('(pointer:fine)').matches;
  var $=function(s,c){return (c||document).querySelector(s)}, $$=function(s,c){return [].slice.call((c||document).querySelectorAll(s))};
  var EASE='expo.out';
  var page=$('.page'); if(!page) return;
  var isHome=document.body.getAttribute('data-route')==='';

  /* myk scrolling (kun mus/styreflate) */
  var lenis=null;
  if(window.Lenis && fine){
    lenis=new Lenis({lerp:.1});
    lenis.on('scroll',ScrollTrigger.update);
    gsap.ticker.add(function(t){lenis.raf(t*1000)});
    gsap.ticker.lagSmoothing(0);
  }

  /* ord som stiger opp fra en maske */
  function splitWords(el){
    if(!el || el.getAttribute('data-split')) return; el.setAttribute('data-split','1');
    (function walk(node){
      [].slice.call(node.childNodes).forEach(function(n){
        if(n.nodeType===3){
          var frag=document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(function(part){
            if(!part) return;
            if(/^\s+$/.test(part)){frag.appendChild(document.createTextNode(' '));return;}
            var m=document.createElement('span');m.className='wm';
            var i=document.createElement('span');i.className='wi';i.textContent=part;
            m.appendChild(i);frag.appendChild(m);
          });
          n.parentNode.replaceChild(frag,n);
        } else if(n.nodeType===1 && n.tagName!=='BR' && n.tagName!=='IMG' && !n.classList.contains('wm')) walk(n);
      });
    })(el);
  }

  /* header gjemmes ved scroll ned */
  var hdr=$('#hdr'), lastY=0;
  function onScrollY(y){ hdr.classList.toggle('hide', y>lastY && y>240 && !$('#mnav').classList.contains('open')); lastY=y; }
  if(lenis) lenis.on('scroll',function(e){onScrollY(e.scroll)}); else addEventListener('scroll',function(){onScrollY(scrollY)},{passive:true});

  var delay=isHome?0.85:0.05;

  /* overskrifter */
  $$('h1.xw, h2.xw, .p-hero h1', page).forEach(splitWords);
  var h1=$$('h1 .wi', page);
  if(h1.length) gsap.fromTo(h1,{yPercent:115},{yPercent:0,duration:1.2,ease:EASE,stagger:.05,delay:delay});
  var intro=isHome ? $$('.hero-grid .lead, .hero-grid .pill, .split-row span', page) : $$('.p-hero .lead, .p-hero .eyebrow, .crumb', page);
  if(intro.length) gsap.fromTo(intro,{y:24,opacity:0},{y:0,opacity:1,duration:1.1,ease:EASE,stagger:.06,delay:delay+.25,clearProps:'transform,opacity'});
  $$('h2.xw', page).forEach(function(h){
    var w=$$('.wi',h); if(!w.length) return;
    gsap.fromTo(w,{yPercent:115},{yPercent:0,duration:1.1,ease:EASE,stagger:.045,scrollTrigger:{trigger:h,start:'top 88%',once:true}});
  });

  /* forsidebilde */
  if(isHome){
    var hp=$('#heroPhoto'), hi=$('#heroPhoto > img'), wu=$('.withus');
    if(hp && hi){
      gsap.fromTo(hp,{clipPath:'inset(18% 6% 0% 6% round 36px)'},{clipPath:'inset(0% 0% 0% 0% round 36px)',duration:1.6,ease:'power3.inOut',delay:delay+.1,clearProps:'clipPath'});
      hi.classList.add('plx');
      gsap.fromTo(hi,{scale:1.25},{scale:1,duration:1.8,ease:EASE,delay:delay+.1});
    }
    if(wu){
      splitWords(wu);
      gsap.fromTo($$('.wi',wu),{yPercent:115},{yPercent:0,duration:1.2,ease:EASE,stagger:.08,delay:delay+.7});
      gsap.to(wu,{xPercent:-8,ease:'none',scrollTrigger:{trigger:hp,start:'top 30%',end:'bottom top',scrub:true}});
    }
  }

  /* kort og fliser i grupper */
  var items=$$('.rc, .card, .gal > *, .person, .three > *, .price > *, .info, .chooser, .tbl, details, .formbox', page)
    .filter(function(el,i,a){return a.indexOf(el)===i && !el.closest('.result')});
  items.forEach(function(el){ gsap.set(el,{y:44,opacity:0}); });
  ScrollTrigger.batch(items,{start:'top 92%',once:true,onEnter:function(batch){
    gsap.to(batch,{y:0,opacity:1,duration:1,ease:EASE,stagger:.07,overwrite:true,clearProps:'transform,opacity'});
  }});

  /* lett parallakse */
  $$('.p-photo > img, .two > .ph > img, .price .ph > img, .gal .ph > img', page).forEach(function(img){
    img.classList.add('plx');
    gsap.fromTo(img,{yPercent:-5,scale:1.12},{yPercent:5,scale:1.12,ease:'none',scrollTrigger:{trigger:img.parentNode,start:'top bottom',end:'bottom top',scrub:true}});
  });

  /* stor logo i bunnen */
  var fw=$('footer a.xw'); splitWords(fw);
  if(fw) gsap.fromTo($$('.wi',fw),{yPercent:115},{yPercent:0,duration:1.2,ease:EASE,stagger:.06,scrollTrigger:{trigger:fw,start:'top 95%',once:true}});

  /* markør «Åpne» + magnetiske knapper */
  if(fine){
    var cur=document.createElement('div'); cur.id='cur'; cur.setAttribute('aria-hidden','true');
    cur.innerHTML='Åpne <svg width="14" height="14"><use href="#arr"></use></svg>'; document.body.appendChild(cur);
    var qx=gsap.quickTo(cur,'x',{duration:.45,ease:'power3'}), qy=gsap.quickTo(cur,'y',{duration:.45,ease:'power3'});
    addEventListener('mousemove',function(e){qx(e.clientX);qy(e.clientY)});
    document.addEventListener('mouseover',function(e){
      var on=!!e.target.closest('a.ph');
      gsap.to(cur,{opacity:on?1:0,scale:on?1:.6,duration:.3,ease:'power3.out',overwrite:'auto'});
    });
    document.addEventListener('mousemove',function(e){
      var p=e.target.closest('.pill'); if(!p) return;
      var r=p.getBoundingClientRect();
      gsap.to(p,{x:(e.clientX-r.left-r.width/2)*.18,y:(e.clientY-r.top-r.height/2)*.3,duration:.4,ease:'power3.out'});
    });
    document.addEventListener('mouseout',function(e){
      var p=e.target.closest('.pill'); if(p && !p.contains(e.relatedTarget)) gsap.to(p,{x:0,y:0,duration:.7,ease:'elastic.out(1,.4)'});
    });
  }

  /* bildeskifte i «Slik fungerer kurset» */
  var simg=$('#stepimg');
  if(simg) new MutationObserver(function(){ gsap.fromTo(simg,{opacity:0,scale:1.08},{opacity:1,scale:1,duration:.8,ease:EASE}); }).observe(simg,{attributes:true,attributeFilter:['src']});

  /* resultat i kursvelgeren */
  document.addEventListener('oh:choose',function(){ gsap.fromTo('#result > *',{y:14,opacity:0},{y:0,opacity:1,duration:.6,ease:EASE,stagger:.05,clearProps:'transform,opacity'}); });

  /* intro-teppe kun på forsiden */
  if(isHome){
    var ld=document.createElement('div'); ld.id='loader'; ld.setAttribute('aria-hidden','true');
    ld.innerHTML='<svg width="34" height="32"><use href="#heart"></use></svg><span class="xw">Open Hearts</span>';
    document.body.appendChild(ld);
    gsap.fromTo('#loader > *',{yPercent:60,opacity:0},{yPercent:0,opacity:1,duration:.6,ease:EASE,stagger:.08});
    gsap.to(ld,{yPercent:-100,duration:.9,ease:'power4.inOut',delay:.6,onComplete:function(){ld.remove()}});
  }

  addEventListener('load',function(){ScrollTrigger.refresh()});
})();
