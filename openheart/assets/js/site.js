/* Open Hearts — sidefunksjoner (ingen sporing, ingen informasjonskapsler) */
(function(){
  var route=document.body.getAttribute('data-route')||'';
  var $=function(s,c){return (c||document).querySelector(s)}, $$=function(s,c){return [].slice.call((c||document).querySelectorAll(s))};

  /* aktiv meny */
  var map={pamelding:'kurs',medlem:'pris',puzik:'prosjekter',sprakkafe:'prosjekter',dating:'prosjekter',juridisk:'prosjekter','trygge-relasjoner':'prosjekter',frivillig:'om-oss',donasjonsvilkar:'stott-oss'};
  var top=map[route]||route;
  $$('[data-nav]').forEach(function(a){a.classList.toggle('active',a.getAttribute('data-nav')===top)});

  /* mobilmeny */
  var mnav=$('#mnav'), burger=$('#burger');
  if(burger) burger.addEventListener('click',function(){
    var o=mnav.classList.toggle('open'); burger.setAttribute('aria-expanded',o?'true':'false');
  });
  addEventListener('scroll',function(){$('#hdr').classList.toggle('scrolled',window.scrollY>10)},{passive:true});

  /* skjul bilder som ikke lastes (fargen bak blir stående) */
  $$('img').forEach(function(i){i.addEventListener('error',function(){i.style.opacity=0})});

  /* forhåndsutfylt emne: kontakt.html?emne=... */
  try{
    var emne=new URLSearchParams(location.search).get('emne'), f=$('#k-emne');
    if(emne&&f) f.value=emne;
  }catch(e){}

  /* «Slik fungerer kurset» */
  var simg=$('#stepimg'), steps=$$('#steps .step'), txt=$$('.step-txt p');
  if(simg && steps.length){
    var imgs=steps.map(function(s){return s.getAttribute('data-img')});
    var si=0;
    var setStep=function(i){steps.forEach(function(s,k){s.classList.toggle('on',k===i)});txt.forEach(function(t,k){t.classList.toggle('on',k===i)});simg.src=imgs[i];};
    var timer=setInterval(function(){si=(si+1)%steps.length;setStep(si)},4500);
    steps.forEach(function(s,i){s.addEventListener('click',function(){clearInterval(timer);si=i;setStep(i)})});
  }

  /* «Hvilket kurs passer for deg?» */
  var opts=$('#opts');
  if(opts){
    var C={
      a:['Norsk med fokus på norskprøven','Kurs A1–B2 som forbereder deg til norskprøven. Gratis for medlemmer eller finansiert med offentlige midler.'],
      b:['Norsk og grunnleggende ferdigheter','A1–B1, gratis og finansiert med offentlige midler. Styrker norsk og grunnleggende ferdigheter.'],
      c:['Arbeidsrettet norsk','A1–B2 for ansatte som trenger norsk på arbeidsplassen. Gratis, offentlig finansiert.'],
      d:['Norsk for arbeid og samfunnsliv','«Norsk på vei til arbeid» A1–B2. Gratis, offentlig finansiert.'],
      e:['Betalende norsk med fokus på norskprøven','Online-kurs A1–B2, 180 kr per time. Se timeplanen under.']
    };
    var S=[
      ['Jeg trenger norsk for å bestå norskprøven','a'],
      ['Jeg har brukt opp retten min til gratis norskopplæring','a'],
      ['Jeg har ikke rett til norskopplæring etter integreringsloven','a'],
      ['Jeg ønsker å styrke norsk og grunnleggende ferdigheter','b'],
      ['Jeg er i arbeid og trenger norsk på arbeidsplassen','c'],
      ['Jeg ønsker bedre norsk for å delta i samfunnet','d'],
      ['Jeg bor utenfor Norge eller omfattes ikke av et gratis tilbud','e']
    ];
    S.forEach(function(s){
      var b=document.createElement('button'); b.type='button'; b.className='opt'; b.textContent=s[0];
      b.addEventListener('click',function(){
        $$('.opt',opts).forEach(function(x){x.classList.remove('on')}); b.classList.add('on');
        $('#res-t').textContent=C[s[1]][0]; $('#res-d').textContent=C[s[1]][1];
        document.dispatchEvent(new CustomEvent('oh:choose'));
      });
      opts.appendChild(b);
    });
  }

  /* skjemaer: sendes til Netlify Forms; lokalt (file://) åpnes e-post som reserve */
  $$('form[data-netlify]').forEach(function(f){
    var ok=$('.ok',f), err=$('.err',f), btn=$('button[type=submit]',f);
    f.addEventListener('submit',function(e){
      e.preventDefault();
      ok.classList.remove('show'); err.classList.remove('show');
      var fd=new FormData(f);
      if(location.protocol==='file:'){
        var lines=[], idx={};
        fd.forEach(function(v,k){ if(!v||k==='form-name'||k==='bot-field') return; if(idx[k]!==undefined){lines[idx[k]]+=', '+v;} else {idx[k]=lines.length;lines.push(k.replace(/_/g,' ')+': '+v);} });
        location.href='mailto:post@openhearts.no?subject='+encodeURIComponent(f.getAttribute('data-subject'))+'&body='+encodeURIComponent(lines.join('\n'));
        ok.textContent='Lokal forhåndsvisning: e-posten åpnes i e-postprogrammet ditt.'; ok.classList.add('show');
        return;
      }
      btn.disabled=true; btn.style.opacity=.6;
      var body=new URLSearchParams(); fd.forEach(function(v,k){body.append(k,v)});
      fetch('/',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body.toString()})
        .then(function(r){ if(!r.ok) throw new Error(r.status); ok.classList.add('show'); f.reset(); })
        .catch(function(){ err.classList.add('show'); })
        .then(function(){ btn.disabled=false; btn.style.opacity=''; });
    });
  });
})();
