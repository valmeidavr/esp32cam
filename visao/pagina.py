"""A pagina servida em http://<ip>:8000/.

Tudo num arquivo so (HTML + CSS + JS) para o programa nao depender de pasta
de arquivos estaticos nem de internet: numa banca nao da para contar com
Wi-Fi para carregar fonte ou biblioteca. O som e a voz tambem sao do proprio
navegador (Web Audio e Web Speech), sem arquivo de audio.
"""

PAGINA = r"""<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Classificador de peças — ESP32-CAM</title>
<style>
  :root {
    color-scheme: dark;
    --fundo: #0b0d12; --painel: #141821; --painel-2: #1b2029; --borda: #262c38;
    --texto: #e8ebf0; --texto-2: #98a2b3; --texto-3: #5f6b7d; --acento: #5b8def;
    --circulo: #ff7878; --quadrado: #78ff78; --triangulo: #ffc850;
    --estrela: #d25aff; --outros: #9aa3b2;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--fundo); color: var(--texto);
         font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         padding: 0 16px 24px; }

  /* ---------------------------------------------------------- cabecalho */
  header { max-width: 1240px; margin: 0 auto; padding: 18px 0 14px; display: flex;
           align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  header h1 { margin: 0; font-size: 17px; font-weight: 600; }
  header h1 small { color: var(--texto-3); font-weight: 500; margin-left: 8px; }
  .status { display: flex; gap: 10px; align-items: center; color: var(--texto-2);
            font-size: 13px; font-variant-numeric: tabular-nums; flex-wrap: wrap; }
  .led { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 6px;
         background: #ff6262; vertical-align: -1px; box-shadow: 0 0 0 3px rgba(255,98,98,.18); }
  .led.ok { background: #4de08a; box-shadow: 0 0 0 3px rgba(77,224,138,.18); }
  .chip { background: var(--painel-2); border: 1px solid var(--borda); color: var(--texto);
          border-radius: 999px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
  .chip:hover { background: #222835; }
  .chip.ativo { border-color: var(--acento); color: #cfe0ff; }

  /* -------------------------------------------------------------- grade */
  .grade { max-width: 1240px; margin: 0 auto; display: grid;
           grid-template-columns: minmax(0, 1.35fr) minmax(300px, 1fr); gap: 18px; align-items: start; }
  @media (max-width: 860px) { .grade { grid-template-columns: 1fr; } }
  .cartao { background: var(--painel); border: 1px solid var(--borda); border-radius: 14px; padding: 16px; }
  .cartao h2 { margin: 0 0 12px; font-size: 11px; font-weight: 600; letter-spacing: .1em;
               text-transform: uppercase; color: var(--texto-3); display: flex;
               justify-content: space-between; align-items: center; gap: 8px; }
  .cartao h2 .dica { text-transform: none; letter-spacing: 0; font-weight: 500; color: var(--texto-3); }

  /* ------------------------------------------------------------- camera */
  .camera { position: relative; }
  .quadro { position: relative; user-select: none; }
  .quadro img { width: 100%; aspect-ratio: 4 / 3; object-fit: contain; display: block;
                background: #000; border-radius: 10px; cursor: crosshair; }
  .selecao { position: absolute; border: 2px dashed #ffd36a; background: rgba(255,211,106,.12);
             pointer-events: none; display: none; border-radius: 3px; }
  .legenda { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,.55);
             backdrop-filter: blur(4px); padding: 4px 9px; border-radius: 6px; font-size: 12px;
             color: var(--texto-2); pointer-events: none; }
  .aviso-som { position: absolute; right: 10px; top: 10px; background: rgba(201,162,39,.9);
               color: #15171c; padding: 4px 10px; border-radius: 6px; font-size: 12px;
               font-weight: 600; pointer-events: none; display: none; }

  /* ------------------------------------------------------------ esteira */
  .esteira { margin-top: 14px; position: relative; height: 74px; }
  .esteira .rolo { position: absolute; top: 14px; width: 34px; height: 34px; border-radius: 50%;
                   background: radial-gradient(circle at 35% 35%, #4b5468, #232937 70%);
                   border: 2px solid #3a4152; animation: girar 1.4s linear infinite; }
  .esteira .rolo::after { content: ""; position: absolute; inset: 11px; border-radius: 50%;
                          border: 2px dashed #6b7488; }
  .esteira .rolo.esq { left: 0; } .esteira .rolo.dir { right: 0; }
  .esteira .correia { position: absolute; left: 17px; right: 17px; top: 14px; height: 34px;
                      border-radius: 6px; overflow: hidden; border: 1px solid #3a4152;
                      background:
                        repeating-linear-gradient(90deg, #262d3b 0 36px, #1f2531 36px 40px),
                        #232937;
                      background-size: 40px 100%; animation: correr 1.4s linear infinite;
                      box-shadow: inset 0 6px 10px rgba(0,0,0,.45), inset 0 -4px 8px rgba(0,0,0,.35); }
  .esteira .correia::before { content: ""; position: absolute; inset: 0;
                              background: linear-gradient(180deg, rgba(255,255,255,.06), transparent 45%, rgba(0,0,0,.25)); }
  .esteira .pecas { position: absolute; left: 17px; right: 17px; top: 4px; height: 44px; pointer-events: none; }
  .esteira .peca { position: absolute; top: 0; width: 34px; height: 34px; margin-left: -17px;
                   transition: left .12s linear; filter: drop-shadow(0 4px 3px rgba(0,0,0,.6)); }
  .esteira .peca svg { width: 100%; height: 100%; }
  .esteira .peca span { position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
                        font-size: 10px; color: var(--texto-2); white-space: nowrap; }
  .esteira .linha { position: absolute; top: 8px; width: 2px; height: 46px; margin-left: -1px;
                    background: repeating-linear-gradient(180deg, #9aa3b2 0 5px, transparent 5px 9px); }
  .esteira .sentido { position: absolute; left: 0; right: 0; bottom: 0; text-align: center;
                      font-size: 11px; letter-spacing: .14em; color: var(--texto-3); text-transform: uppercase; }
  @keyframes correr { to { background-position: 40px 0; } }
  @keyframes girar  { to { transform: rotate(360deg); } }

  /* ----------------------------------------------------------- destaque */
  .destaque { display: grid; grid-template-columns: 96px 1fr; gap: 16px; align-items: center; min-height: 118px; }
  .destaque .icone { width: 96px; height: 96px; border-radius: 16px; display: grid; place-items: center;
                     background: var(--painel-2); border: 1px solid var(--borda); }
  .destaque .icone svg { width: 58px; height: 58px; }
  .destaque .nome { font-size: 26px; font-weight: 700; line-height: 1.1; text-transform: capitalize; }
  .destaque .destino { color: var(--texto-2); margin-top: 6px; }
  .destaque .destino b { color: var(--texto); font-weight: 600; }
  .destaque .meta { color: var(--texto-3); font-size: 12px; margin-top: 8px; font-variant-numeric: tabular-nums; }
  .destaque.vazio .nome { color: var(--texto-3); font-weight: 500; font-size: 18px; }
  .destaque.novo .icone { animation: pulso .9s ease-out; }
  @keyframes pulso { 0% { box-shadow: 0 0 0 0 var(--cor-viva, #fff); } 100% { box-shadow: 0 0 0 22px transparent; } }

  /* -------------------------------------------------------------- caixa */
  .caixa-wrap { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: start; }
  @media (max-width: 420px) { .caixa-wrap { grid-template-columns: 1fr; } }
  .caixa { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 5px; padding: 5px;
           background: #0c0e13; border-radius: 12px; border: 2px solid #3a4150; aspect-ratio: 1 / 1; }
  .comp { position: relative; border-radius: 8px; background: var(--painel-2); border: 1px solid var(--borda);
          display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
          min-height: 96px; transition: background .2s, border-color .2s, box-shadow .2s; --cor: var(--outros); }
  .comp .num { position: absolute; top: 7px; left: 9px; font-size: 11px; color: var(--texto-3); font-weight: 600; }
  .comp svg { width: 34px; height: 34px; opacity: .85; }
  .comp .rotulo { font-size: 12px; color: var(--texto-2); text-transform: capitalize; }
  .comp .cont { font-size: 24px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; transition: transform .15s; }
  .comp.acende { background: color-mix(in srgb, var(--cor) 22%, var(--painel-2)); border-color: var(--cor);
                 box-shadow: 0 0 0 1px var(--cor), 0 0 28px color-mix(in srgb, var(--cor) 55%, transparent); }
  .comp.acende .cont { transform: scale(1.25); }
  .comp.acende svg { opacity: 1; }
  .resumo { display: flex; flex-direction: column; gap: 8px; min-width: 120px; }
  .bloco { background: var(--painel-2); border: 1px solid var(--borda); border-radius: 10px; padding: 10px 12px; }
  .bloco .t { font-size: 11px; color: var(--texto-3); text-transform: uppercase; letter-spacing: .08em; }
  .bloco .v { font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .bloco.outros .v { font-size: 18px; color: var(--texto-2); }

  /* ---------------------------------------------------------- historico */
  .historico ul { list-style: none; margin: 0; padding: 0; }
  .historico li { display: grid; grid-template-columns: 22px 1fr auto auto; gap: 10px; align-items: center;
                  padding: 7px 0; border-bottom: 1px solid var(--borda); font-size: 13px; }
  .historico li:last-child { border-bottom: 0; }
  .historico svg { width: 18px; height: 18px; }
  .historico .f { text-transform: capitalize; }
  .historico .d { color: var(--texto-2); }
  .historico .h { color: var(--texto-3); font-variant-numeric: tabular-nums; font-size: 12px; }
  .vazio { color: var(--texto-3); font-style: italic; padding: 6px 0; }

  /* ------------------------------------------------------------ ajustes */
  details { margin-top: 18px; max-width: 1240px; margin-inline: auto; }
  summary { cursor: pointer; color: var(--texto-2); font-size: 13px; user-select: none; padding: 6px 0; }
  .ajustes { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px 22px; margin-top: 10px; }
  .ajustes h3 { grid-column: 1 / -1; margin: 8px 0 -4px; font-size: 11px; text-transform: uppercase;
                letter-spacing: .1em; color: var(--texto-3); font-weight: 600; }
  label { display: block; color: var(--texto-2); font-size: 12px; }
  label span { float: right; color: var(--texto); font-variant-numeric: tabular-nums; }
  input[type=range] { width: 100%; margin-top: 8px; accent-color: var(--acento); }
  select, button { width: 100%; margin-top: 8px; background: var(--painel-2); color: var(--texto);
                   border: 1px solid var(--borda); border-radius: 8px; padding: 9px 12px; font-size: 13px; cursor: pointer; }
  button:hover, select:hover { background: #222835; }
  button.ligado { background: #c9a227; color: #15171c; border-color: #c9a227; }
  button.perigo { color: #ff8a8a; }
  .rodape { max-width: 1240px; margin: 14px auto 0; color: var(--texto-3); font-size: 12px; }
  .creditos { margin-top: 6px; padding-top: 10px; border-top: 1px solid var(--borda); }
  .creditos b { color: var(--texto-2); font-weight: 600; }

  /* -------------------------------------------------------------- modal */
  .veu { position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
         display: none; place-items: center; z-index: 50; }
  .veu.aberto { display: grid; }
  .modal { background: var(--painel); border: 1px solid var(--borda); border-radius: 14px; padding: 22px;
           width: min(380px, 92vw); box-shadow: 0 20px 60px rgba(0,0,0,.6); animation: surgir .18s ease-out; }
  .modal h3 { margin: 0 0 8px; font-size: 16px; }
  .modal p { margin: 0 0 18px; color: var(--texto-2); }
  .modal .botoes { display: flex; gap: 10px; justify-content: flex-end; }
  .modal .botoes button { width: auto; margin: 0; padding: 9px 16px; }
  .modal .botoes .confirmar { background: #b33a3a; border-color: #b33a3a; color: #fff; }
  @keyframes surgir { from { transform: translateY(8px); opacity: 0; } }
</style>

<header>
  <h1>Classificador de peças <small>ESP32-CAM · visão computacional <span id="versao"></span></small></h1>
  <div class="status">
    <span><i class="led" id="led"></i><span id="porta">conectando…</span></span>
    <span id="fps">— fps</span>
    <button class="chip" id="som" title="Som ao identificar uma peça">🔊 Som: voz</button>
  </div>
</header>

<div class="grade">
  <div>
    <div class="cartao camera">
      <h2>Compartimento de vidro · câmera
        <span class="dica">arraste sobre o vídeo para marcar a área da esteira</span></h2>
      <div class="quadro" id="quadro">
        <img id="video" src="/stream" alt="imagem da câmera" draggable="false">
        <div class="selecao" id="selecao"></div>
        <div class="legenda" id="legenda">aguardando peças</div>
        <div class="aviso-som" id="aviso-som">clique na página para ativar o som</div>
      </div>
      <div class="esteira">
        <div class="rolo esq"></div>
        <div class="correia"></div>
        <div class="rolo dir"></div>
        <div class="pecas" id="esteira-pecas"></div>
        <div class="sentido">sentido da esteira →</div>
      </div>
    </div>

    <div class="cartao historico" style="margin-top:18px">
      <h2>Últimas peças</h2>
      <ul id="historico"><li class="vazio">nenhuma peça passou ainda</li></ul>
    </div>
  </div>

  <div>
    <div class="cartao">
      <h2>Peça identificada</h2>
      <div class="destaque vazio" id="destaque">
        <div class="icone" id="destaque-icone"></div>
        <div>
          <div class="nome" id="destaque-nome">aguardando…</div>
          <div class="destino" id="destaque-destino"></div>
          <div class="meta" id="destaque-meta"></div>
        </div>
      </div>
    </div>

    <div class="cartao" style="margin-top:18px">
      <h2>Compartimento de destino</h2>
      <div class="caixa-wrap">
        <div class="caixa" id="caixa">
          <div class="comp" data-c="circulo"   style="--cor:var(--circulo)"><span class="num">1</span><div class="ico"></div><div class="cont">0</div><div class="rotulo">círculo</div></div>
          <div class="comp" data-c="quadrado"  style="--cor:var(--quadrado)"><span class="num">2</span><div class="ico"></div><div class="cont">0</div><div class="rotulo">quadrado</div></div>
          <div class="comp" data-c="triangulo" style="--cor:var(--triangulo)"><span class="num">3</span><div class="ico"></div><div class="cont">0</div><div class="rotulo">triângulo</div></div>
          <div class="comp" data-c="estrela"   style="--cor:var(--estrela)"><span class="num">4</span><div class="ico"></div><div class="cont">0</div><div class="rotulo">estrela</div></div>
        </div>
        <div class="resumo">
          <div class="bloco"><div class="t">total</div><div class="v" id="total">0</div></div>
          <div class="bloco outros"><div class="t">sem compartimento</div><div class="v" id="outros">0</div></div>
          <button class="perigo" id="zerar">Zerar contagem</button>
        </div>
      </div>
    </div>
  </div>
</div>

<details>
  <summary>Ajustes e calibração</summary>
  <div class="ajustes">
    <h3>Contagem</h3>
    <label>Linha de despejo (posição x) <span id="linha-v">192</span>
      <input id="linha" type="range" min="20" max="300" value="192"></label>
    <label>Contar a peça quando
      <select id="modo"><option value="linha">cruzar a linha de despejo</option><option value="saida">sair da imagem</option></select></label>
    <label>Tamanho mínimo da peça <span id="area-v">700</span>
      <input id="area" type="range" min="200" max="6000" step="100" value="700"></label>

    <h3>O que é peça (calibração)</h3>
    <label>Sensibilidade a cor <span id="sat-v">90</span>
      <input id="sat" type="range" min="20" max="200" value="90"></label>
    <label>Sensibilidade a escuro <span id="escuro-v">70</span>
      <input id="escuro" type="range" min="0" max="160" value="70"></label>
    <label>Visão do detector <button id="mascara">Ver o que o detector enxerga</button></label>
    <label>Área da esteira <button id="limpar-roi">Usar a imagem inteira</button></label>

    <h3>Câmera</h3>
    <label>Qualidade da imagem <span id="qual-v">12</span>
      <input id="qual" type="range" min="10" max="40" value="12"></label>
    <label>Iluminação <button id="luz">Flash da placa</button></label>
    <label>Sobreposição <button id="mostrar">Esconder linha no vídeo</button></label>
  </div>
</details>

<p class="rodape">Detecção por cor e forma (OpenCV) no PC · imagem chegando pela USB ·
cada peça é rastreada e contada uma única vez ao cruzar a linha de despejo.</p>
<p class="rodape creditos"><b>ETPC — Escola Técnica</b> · Matheus Pedrosa, Carlos Eduardo Borges, Maria Eduarda Mazza,
Milena Maia, Milena Rodrigues · Apoio: Prof. Vinicius (Tecnologia) · © 2026 Todos os direitos reservados</p>

<div class="veu" id="veu">
  <div class="modal" role="dialog" aria-modal="true">
    <h3>Zerar a contagem?</h3>
    <p>Os contadores dos quatro compartimentos, o total e o histórico voltam a zero. A câmera continua rodando.</p>
    <div class="botoes">
      <button id="modal-cancelar">Cancelar</button>
      <button class="confirmar" id="modal-confirmar">Zerar</button>
    </div>
  </div>
</div>

<script>
  // ------------------------------------------------------------ icones
  const ICONES = {
    circulo:   c => `<svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="15" fill="${c}"/></svg>`,
    quadrado:  c => `<svg viewBox="0 0 40 40"><rect x="6" y="6" width="28" height="28" rx="3" fill="${c}"/></svg>`,
    triangulo: c => `<svg viewBox="0 0 40 40"><path d="M20 5 L36 34 L4 34 Z" fill="${c}"/></svg>`,
    estrela:   c => `<svg viewBox="0 0 40 40"><path d="M20 3l4.9 10.6 11.6 1.3-8.6 7.9 2.3 11.4L20 28.5l-10.2 5.7 2.3-11.4-8.6-7.9 11.6-1.3z" fill="${c}"/></svg>`,
    outros:    c => `<svg viewBox="0 0 40 40"><path d="M20 4l14 8v16l-14 8-14-8V12z" fill="none" stroke="${c}" stroke-width="3"/></svg>`,
  };
  const COR = { circulo:'var(--circulo)', quadrado:'var(--quadrado)', triangulo:'var(--triangulo)',
                estrela:'var(--estrela)', outros:'var(--outros)' };
  const NOME_COMP = { circulo:'Círculo', quadrado:'Quadrado', triangulo:'Triângulo', estrela:'Estrela', outros:'sem compartimento' };
  const NUMERO = { circulo:1, quadrado:2, triangulo:3, estrela:4 };
  const FALADO = { circulo:'círculo', quadrado:'quadrado', triangulo:'triângulo', estrela:'estrela',
                   retangulo:'retângulo', pentagono:'pentágono', hexagono:'hexágono', poligono:'polígono' };
  const icone = (forma, cor) => (ICONES[forma] || ICONES.outros)(cor || COR[forma] || COR.outros);
  const compDe = f => (f in NUMERO) ? f : 'outros';
  const $ = id => document.getElementById(id);
  const hora = t => new Date(t * 1000).toLocaleTimeString('pt-BR');

  document.querySelectorAll('.comp').forEach(el => { el.querySelector('.ico').innerHTML = icone(el.dataset.c); });

  // --------------------------------------------------------------- som
  // Tudo gerado no navegador: bipes pelo Web Audio, voz pelo Web Speech.
  // Os navegadores so liberam audio depois de um clique na pagina.
  const MODOS_SOM = ['voz', 'bipe', 'desligado'];
  let modoSom = localStorage.getItem('som') || 'voz';
  let audio = null, somLiberado = false;

  const PADROES = {   // [frequencia Hz, duracao s] — um "ritmo" por forma
    circulo:   [[660, .18]],
    quadrado:  [[520, .10], [520, .10]],
    triangulo: [[440, .08], [550, .08], [660, .12]],
    estrela:   [[523, .07], [659, .07], [784, .07], [1047, .16]],
    outros:    [[220, .25]],
  };

  function liberarSom() {
    if (somLiberado) return;
    somLiberado = true;
    try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch {}
    $('aviso-som').style.display = 'none';
  }
  document.addEventListener('pointerdown', liberarSom, { once: true });
  document.addEventListener('keydown', liberarSom, { once: true });

  function bipar(comp) {
    if (!audio) return;
    let t = audio.currentTime + 0.02;
    for (const [freq, dur] of (PADROES[comp] || PADROES.outros)) {
      const osc = audio.createOscillator(), g = audio.createGain();
      osc.type = 'sine'; osc.frequency.value = freq;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.35, t + .01);
      g.gain.exponentialRampToValueAtTime(.001, t + dur);
      osc.connect(g).connect(audio.destination); osc.start(t); osc.stop(t + dur + .02);
      t += dur + .06;
    }
  }

  function falar(ev) {
    if (!('speechSynthesis' in window)) { bipar(compDe(ev.forma)); return; }
    const texto = ev.compartimento === 'outros'
      ? `${FALADO[ev.forma] || ev.forma}, sem compartimento`
      : `${FALADO[ev.forma] || ev.forma}, compartimento ${NUMERO[ev.compartimento]}`;
    const fala = new SpeechSynthesisUtterance(texto);
    fala.lang = 'pt-BR'; fala.rate = 1.05;
    const voz = speechSynthesis.getVoices().find(v => v.lang && v.lang.toLowerCase().startsWith('pt'));
    if (voz) fala.voice = voz;
    speechSynthesis.cancel();       // a peca nova interrompe a anterior
    speechSynthesis.speak(fala);
  }

  function anunciar(ev) {
    if (modoSom === 'desligado') return;
    if (!somLiberado) { $('aviso-som').style.display = 'block'; return; }
    if (modoSom === 'voz') falar(ev); else bipar(compDe(ev.forma));
  }

  function mostrarModoSom() {
    $('som').textContent = { voz: '🔊 Som: voz', bipe: '🔔 Som: bipe', desligado: '🔇 Som: desligado' }[modoSom];
    $('som').classList.toggle('ativo', modoSom !== 'desligado');
  }
  $('som').onclick = () => {
    modoSom = MODOS_SOM[(MODOS_SOM.indexOf(modoSom) + 1) % MODOS_SOM.length];
    localStorage.setItem('som', modoSom); mostrarModoSom();
    if (modoSom !== 'desligado') anunciar({ forma: 'quadrado', compartimento: 'quadrado' });   // amostra
  };
  mostrarModoSom();

  // ------------------------------------------------------ area da esteira
  // Arrastar sobre o video define a ROI em coordenadas de 320x240.
  const quadro = $('quadro'), video = $('video'), selecao = $('selecao');
  let arrasto = null;
  const posVideo = e => {
    const r = video.getBoundingClientRect();
    return { x: Math.max(0, Math.min(r.width, e.clientX - r.left)),
             y: Math.max(0, Math.min(r.height, e.clientY - r.top)), w: r.width, h: r.height };
  };
  video.addEventListener('pointerdown', e => {
    arrasto = posVideo(e); video.setPointerCapture(e.pointerId);
    selecao.style.display = 'block'; e.preventDefault();
  });
  video.addEventListener('pointermove', e => {
    if (!arrasto) return;
    const p = posVideo(e);
    const x = Math.min(arrasto.x, p.x), y = Math.min(arrasto.y, p.y);
    Object.assign(selecao.style, { left: x + 'px', top: y + 'px',
      width: Math.abs(p.x - arrasto.x) + 'px', height: Math.abs(p.y - arrasto.y) + 'px' });
  });
  video.addEventListener('pointerup', e => {
    if (!arrasto) return;
    const p = posVideo(e); selecao.style.display = 'none';
    const sx = 320 / arrasto.w, sy = 240 / arrasto.h;
    const roi = [arrasto.x * sx, arrasto.y * sy, p.x * sx, p.y * sy].map(v => Math.round(v));
    arrasto = null;
    if (Math.abs(roi[2] - roi[0]) >= 20 && Math.abs(roi[3] - roi[1]) >= 20) ajustar('roi=' + roi.join(','));
  });
  $('limpar-roi').onclick = () => ajustar('roi=');

  // ------------------------------------------------------------- estado
  let serieVista = 0, timers = {};

  function acender(comp) {
    const el = document.querySelector(`.comp[data-c="${comp}"]`);
    if (!el) return;
    el.classList.add('acende'); clearTimeout(timers[comp]);
    timers[comp] = setTimeout(() => el.classList.remove('acende'), 1600);
  }

  function destacar(ev) {
    const d = $('destaque');
    d.classList.remove('vazio'); d.style.setProperty('--cor-viva', COR[ev.compartimento]);
    $('destaque-icone').innerHTML = icone(ev.forma, COR[ev.compartimento]);
    $('destaque-nome').textContent = FALADO[ev.forma] || ev.forma;
    $('destaque-destino').innerHTML = ev.compartimento === 'outros'
      ? 'não tem compartimento próprio'
      : `vai para o compartimento <b>${NUMERO[ev.compartimento]} · ${NOME_COMP[ev.compartimento]}</b>`;
    $('destaque-meta').textContent = `peça #${ev.id} · confiança ${Math.round(ev.confianca * 100)}% · ${hora(ev.instante)}`;
    d.classList.remove('novo'); void d.offsetWidth; d.classList.add('novo');
  }

  function renderHistorico(eventos) {
    const ul = $('historico');
    if (!eventos.length) { ul.innerHTML = '<li class="vazio">nenhuma peça passou ainda</li>'; return; }
    ul.innerHTML = eventos.map(e => `
      <li>${icone(e.forma, COR[e.compartimento])}
        <span class="f">${FALADO[e.forma] || e.forma}</span>
        <span class="d">${e.compartimento === 'outros' ? '—' : 'comp. ' + NUMERO[e.compartimento]}</span>
        <span class="h">${hora(e.instante)}</span></li>`).join('');
  }

  // As pecas que a camera ve agora deslizam na esteira desenhada, na mesma
  // posicao horizontal em que estao no video.
  function renderEsteira(pecas, linha) {
    const el = $('esteira-pecas');
    let html = `<div class="linha" style="left:${linha / 320 * 100}%"></div>`;
    for (const p of pecas) {
      const comp = compDe(p.forma);
      html += `<div class="peca" style="left:${p.centro[0] / 320 * 100}%">
                 <span>#${p.id}${p.contada ? ' ✓' : ''}</span>${icone(p.forma, COR[comp])}</div>`;
    }
    el.innerHTML = html;
  }

  // ------------------------------------------------------ vigia do video
  const religar = () => { video.src = '/stream?t=' + Date.now(); };
  video.onerror = () => setTimeout(religar, 1500);
  let ultimoProcessado = -1, paradoDesde = Date.now();
  function vigiar(d) {
    const agora = Date.now();
    if (d.processados !== ultimoProcessado) { ultimoProcessado = d.processados; paradoDesde = agora; return; }
    if (agora - paradoDesde > 4000) {
      $('legenda').textContent = d.conectada ? 'sem imagem — religando…' : 'placa desconectada';
      religar(); paradoDesde = agora;
    }
  }

  async function atualizar() {
    let d;
    try { d = await (await fetch('/estado', { cache: 'no-store' })).json(); }
    catch { $('led').classList.remove('ok'); $('porta').textContent = 'servidor fora'; return; }

    $('led').classList.toggle('ok', d.conectada);
    $('porta').textContent = d.conectada ? d.porta : 'placa desconectada';
    $('fps').textContent = d.fps.toFixed(1) + ' fps';
    if (d.versao) $('versao').textContent = '· v' + d.versao;
    vigiar(d);

    for (const c in d.contagens) {
      const el = document.querySelector(`.comp[data-c="${c}"] .cont`);
      if (el) el.textContent = d.contagens[c];
    }
    $('total').textContent = d.total;
    $('outros').textContent = d.contagens.outros || 0;

    $('legenda').textContent = d.pecas.length
      ? d.pecas.map(p => `#${p.id} ${FALADO[p.forma] || p.forma}`).join(' · ')
      : (d.mascara ? 'visão do detector: branco = peça' : 'aguardando peças');
    renderEsteira(d.pecas, d.linha);

    if (d.serie > serieVista) {
      const novos = d.eventos.slice(0, d.serie - serieVista).reverse();
      novos.forEach(ev => { acender(ev.compartimento); destacar(ev); });
      anunciar(novos[novos.length - 1]);
      serieVista = d.serie; renderHistorico(d.eventos);
    } else if (serieVista === 0 && d.eventos.length) {
      serieVista = d.serie; renderHistorico(d.eventos); destacar(d.eventos[0]);
    }

    // sincroniza os controles (podem ter sido mexidos em outro aparelho)
    const sinc = (id, valor) => { if (document.activeElement !== $(id)) { $(id).value = valor; $(id + '-v').textContent = valor; } };
    sinc('linha', d.linha); sinc('area', d.area); sinc('sat', d.sat); sinc('escuro', d.escuro);
    $('modo').value = d.modo;
    $('mascara').classList.toggle('ligado', d.mascara);
    $('mascara').textContent = d.mascara ? 'Voltar para a câmera' : 'Ver o que o detector enxerga';
    $('limpar-roi').textContent = d.roi ? `Usar a imagem inteira (área: ${d.roi.join(',')})` : 'Usar a imagem inteira (nenhuma área marcada)';
  }
  setInterval(atualizar, 250);
  atualizar();

  // ------------------------------------------------------------ ajustes
  const ajustar = q => fetch('/ajuste?' + q);
  const deslizante = (id, chave) => {
    $(id).oninput  = e => $(id + '-v').textContent = e.target.value;
    $(id).onchange = e => ajustar(`${chave}=${e.target.value}`);
  };
  deslizante('linha', 'linha'); deslizante('area', 'area'); deslizante('qual', 'qualidade');
  deslizante('sat', 'sat'); deslizante('escuro', 'escuro');
  $('modo').onchange = e => ajustar('modo=' + e.target.value);

  let mascaraLigada = false;
  $('mascara').onclick = () => { mascaraLigada = !mascaraLigada; ajustar('mascara=' + (mascaraLigada ? 1 : 0)); };

  let luz = false;
  $('luz').onclick = e => { luz = !luz; e.target.classList.toggle('ligado', luz); ajustar('flash=' + (luz ? 1 : 0)); };

  let linhaVisivel = true;
  $('mostrar').onclick = e => {
    linhaVisivel = !linhaVisivel;
    e.target.textContent = linhaVisivel ? 'Esconder linha no vídeo' : 'Mostrar linha no vídeo';
    ajustar('mostrar_linha=' + (linhaVisivel ? 1 : 0));
  };

  // -------------------------------------------------------------- modal
  const veu = $('veu');
  $('zerar').onclick = () => { veu.classList.add('aberto'); $('modal-cancelar').focus(); };
  $('modal-cancelar').onclick = () => veu.classList.remove('aberto');
  veu.onclick = e => { if (e.target === veu) veu.classList.remove('aberto'); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') veu.classList.remove('aberto'); });
  $('modal-confirmar').onclick = async () => {
    veu.classList.remove('aberto');
    await fetch('/zerar'); serieVista = 0;
    $('destaque').classList.add('vazio'); $('destaque-icone').innerHTML = '';
    $('destaque-nome').textContent = 'aguardando…';
    $('destaque-destino').textContent = ''; $('destaque-meta').textContent = '';
    renderHistorico([]);
  };
</script>
</html>
"""
