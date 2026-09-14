"""A pagina servida em http://<ip>:8000/.

Tudo num arquivo so (HTML + CSS + JS) para o programa nao depender de pasta
de arquivos estaticos nem de internet: numa banca nao da para contar com
Wi-Fi para carregar fonte ou biblioteca.
"""

PAGINA = r"""<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Classificador de peças — ESP32-CAM</title>
<style>
  :root {
    color-scheme: dark;
    --fundo: #0b0d12;
    --painel: #141821;
    --painel-2: #1b2029;
    --borda: #262c38;
    --texto: #e8ebf0;
    --texto-2: #98a2b3;
    --texto-3: #5f6b7d;
    --acento: #5b8def;

    --circulo:   #ff7878;
    --quadrado:  #78ff78;
    --triangulo: #ffc850;
    --estrela:   #d25aff;
    --outros:    #9aa3b2;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; background: var(--fundo); color: var(--texto);
    font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    padding: 0 16px 24px;
  }

  /* ---------------------------------------------------------- cabecalho */
  header {
    max-width: 1240px; margin: 0 auto; padding: 18px 0 14px;
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    flex-wrap: wrap;
  }
  header h1 { margin: 0; font-size: 17px; font-weight: 600; letter-spacing: .01em; }
  header h1 small { color: var(--texto-3); font-weight: 500; margin-left: 8px; }
  .status { display: flex; gap: 14px; align-items: center; color: var(--texto-2);
            font-size: 13px; font-variant-numeric: tabular-nums; }
  .status .led { width: 9px; height: 9px; border-radius: 50%; display: inline-block;
                 margin-right: 6px; background: #ff6262; vertical-align: -1px;
                 box-shadow: 0 0 0 3px rgba(255,98,98,.18); }
  .status .led.ok { background: #4de08a; box-shadow: 0 0 0 3px rgba(77,224,138,.18); }

  /* ------------------------------------------------------------- grade */
  .grade {
    max-width: 1240px; margin: 0 auto;
    display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, 1fr);
    gap: 18px; align-items: start;
  }
  @media (max-width: 860px) { .grade { grid-template-columns: 1fr; } }

  .cartao {
    background: var(--painel); border: 1px solid var(--borda); border-radius: 14px;
    padding: 16px;
  }
  .cartao h2 {
    margin: 0 0 12px; font-size: 11px; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; color: var(--texto-3);
  }

  /* ------------------------------------------------------------ camera */
  .camera { position: relative; }
  .camera img {
    width: 100%; aspect-ratio: 4 / 3; object-fit: contain; display: block;
    background: #000; border-radius: 10px; image-rendering: auto;
  }
  .camera .legenda {
    position: absolute; top: 26px; left: 26px; background: rgba(0,0,0,.55);
    backdrop-filter: blur(4px); padding: 4px 9px; border-radius: 6px;
    font-size: 12px; color: var(--texto-2);
  }
  .esteira {
    margin-top: 12px; height: 34px; border-radius: 8px; position: relative;
    background: repeating-linear-gradient(90deg, #202633 0 22px, #2a3140 22px 44px);
    background-size: 44px 100%; animation: rodar 1.2s linear infinite;
    border: 1px solid var(--borda); overflow: hidden;
  }
  .esteira span {
    position: absolute; inset: 0; display: flex; align-items: center;
    justify-content: center; font-size: 11px; letter-spacing: .12em;
    color: var(--texto-2); text-transform: uppercase;
    background: linear-gradient(90deg, rgba(20,24,33,.85), rgba(20,24,33,0) 30%,
                                rgba(20,24,33,0) 70%, rgba(20,24,33,.85));
  }
  @keyframes rodar { to { background-position: -44px 0; } }

  /* ---------------------------------------------------------- destaque */
  .destaque {
    display: grid; grid-template-columns: 96px 1fr; gap: 16px; align-items: center;
    min-height: 118px;
  }
  .destaque .icone {
    width: 96px; height: 96px; border-radius: 16px; display: grid; place-items: center;
    background: var(--painel-2); border: 1px solid var(--borda);
    transition: background .25s, border-color .25s, box-shadow .25s;
  }
  .destaque .icone svg { width: 58px; height: 58px; }
  .destaque .nome { font-size: 26px; font-weight: 700; letter-spacing: -.01em;
                    line-height: 1.1; text-transform: capitalize; }
  .destaque .destino { color: var(--texto-2); margin-top: 6px; font-size: 14px; }
  .destaque .destino b { color: var(--texto); font-weight: 600; }
  .destaque .meta { color: var(--texto-3); font-size: 12px; margin-top: 8px;
                    font-variant-numeric: tabular-nums; }
  .destaque.vazio .nome { color: var(--texto-3); font-weight: 500; font-size: 18px; }
  .destaque.novo .icone { animation: pulso .9s ease-out; }
  @keyframes pulso {
    0%   { box-shadow: 0 0 0 0 var(--cor-viva, #fff); }
    100% { box-shadow: 0 0 0 22px transparent; }
  }

  /* --------------------------------------------------------------- caixa */
  .caixa-wrap { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: start; }
  @media (max-width: 420px) { .caixa-wrap { grid-template-columns: 1fr; } }
  .caixa {
    display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;
    gap: 5px; padding: 5px; background: #0c0e13; border-radius: 12px;
    border: 2px solid #3a4150; aspect-ratio: 1 / 1;
  }
  .comp {
    position: relative; border-radius: 8px; background: var(--painel-2);
    border: 1px solid var(--borda); display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 4px; min-height: 96px;
    transition: background .2s, border-color .2s, box-shadow .2s;
    --cor: var(--outros);
  }
  .comp .num { position: absolute; top: 7px; left: 9px; font-size: 11px;
               color: var(--texto-3); font-weight: 600; }
  .comp svg { width: 34px; height: 34px; opacity: .85; }
  .comp .rotulo { font-size: 12px; color: var(--texto-2); text-transform: capitalize; }
  .comp .cont { font-size: 24px; font-weight: 700; line-height: 1;
                font-variant-numeric: tabular-nums; transition: transform .15s; }
  .comp.acende {
    background: color-mix(in srgb, var(--cor) 22%, var(--painel-2));
    border-color: var(--cor);
    box-shadow: 0 0 0 1px var(--cor), 0 0 28px color-mix(in srgb, var(--cor) 55%, transparent);
  }
  .comp.acende .cont { transform: scale(1.25); }
  .comp.acende svg { opacity: 1; }

  .resumo { display: flex; flex-direction: column; gap: 8px; min-width: 120px; }
  .resumo .bloco { background: var(--painel-2); border: 1px solid var(--borda);
                   border-radius: 10px; padding: 10px 12px; }
  .resumo .bloco .t { font-size: 11px; color: var(--texto-3); text-transform: uppercase;
                      letter-spacing: .08em; }
  .resumo .bloco .v { font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .resumo .bloco.outros .v { font-size: 18px; color: var(--texto-2); }

  /* ----------------------------------------------------------- historico */
  .historico ul { list-style: none; margin: 0; padding: 0; }
  .historico li {
    display: grid; grid-template-columns: 22px 1fr auto auto; gap: 10px; align-items: center;
    padding: 7px 0; border-bottom: 1px solid var(--borda); font-size: 13px;
  }
  .historico li:last-child { border-bottom: 0; }
  .historico svg { width: 18px; height: 18px; }
  .historico .f { text-transform: capitalize; }
  .historico .d { color: var(--texto-2); }
  .historico .h { color: var(--texto-3); font-variant-numeric: tabular-nums; font-size: 12px; }
  .historico .vazio { color: var(--texto-3); font-style: italic; padding: 6px 0; }

  /* ------------------------------------------------------------ ajustes */
  details { margin-top: 18px; max-width: 1240px; margin-inline: auto; }
  details summary { cursor: pointer; color: var(--texto-2); font-size: 13px;
                    user-select: none; padding: 6px 0; }
  .ajustes { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
             gap: 14px 22px; margin-top: 10px; }
  label { display: block; color: var(--texto-2); font-size: 12px; }
  label span { float: right; color: var(--texto); font-variant-numeric: tabular-nums; }
  input[type=range] { width: 100%; margin-top: 8px; accent-color: var(--acento); }
  select, button {
    width: 100%; margin-top: 8px; background: var(--painel-2); color: var(--texto);
    border: 1px solid var(--borda); border-radius: 8px; padding: 9px 12px;
    font-size: 13px; cursor: pointer;
  }
  button:hover, select:hover { background: #222835; }
  button.ligado { background: #c9a227; color: #15171c; border-color: #c9a227; }
  button.perigo { color: #ff8a8a; }
  .rodape { max-width: 1240px; margin: 14px auto 0; color: var(--texto-3); font-size: 12px; }
  .creditos { margin-top: 6px; padding-top: 10px; border-top: 1px solid var(--borda); }
  .creditos b { color: var(--texto-2); font-weight: 600; }
</style>

<header>
  <h1>Classificador de peças <small>ESP32-CAM · visão computacional</small></h1>
  <div class="status">
    <span><i class="led" id="led"></i><span id="porta">conectando…</span></span>
    <span id="fps">— fps</span>
  </div>
</header>

<div class="grade">
  <!-- ============================================ coluna da esquerda -->
  <div>
    <div class="cartao camera">
      <h2>Compartimento de vidro · câmera</h2>
      <img id="video" src="/stream" alt="imagem da câmera">
      <div class="legenda" id="legenda">aguardando peças</div>
      <div class="esteira"><span>esteira em movimento →</span></div>
    </div>

    <div class="cartao historico" style="margin-top:18px">
      <h2>Últimas peças</h2>
      <ul id="historico"><li class="vazio">nenhuma peça passou ainda</li></ul>
    </div>
  </div>

  <!-- ============================================= coluna da direita -->
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
          <div class="comp" data-c="circulo"   style="--cor:var(--circulo)">
            <span class="num">1</span><div class="ico"></div>
            <div class="cont">0</div><div class="rotulo">círculo</div></div>
          <div class="comp" data-c="quadrado"  style="--cor:var(--quadrado)">
            <span class="num">2</span><div class="ico"></div>
            <div class="cont">0</div><div class="rotulo">quadrado</div></div>
          <div class="comp" data-c="triangulo" style="--cor:var(--triangulo)">
            <span class="num">3</span><div class="ico"></div>
            <div class="cont">0</div><div class="rotulo">triângulo</div></div>
          <div class="comp" data-c="estrela"   style="--cor:var(--estrela)">
            <span class="num">4</span><div class="ico"></div>
            <div class="cont">0</div><div class="rotulo">estrela</div></div>
        </div>
        <div class="resumo">
          <div class="bloco"><div class="t">total</div><div class="v" id="total">0</div></div>
          <div class="bloco outros"><div class="t">sem compartimento</div>
            <div class="v" id="outros">0</div></div>
          <button class="perigo" id="zerar">Zerar contagem</button>
        </div>
      </div>
    </div>
  </div>
</div>

<details>
  <summary>Ajustes</summary>
  <div class="ajustes">
    <label>Linha de despejo (posição x) <span id="linha-v">192</span>
      <input id="linha" type="range" min="20" max="300" value="192"></label>
    <label>Contar a peça quando
      <select id="modo">
        <option value="linha">cruzar a linha de despejo</option>
        <option value="saida">sair da imagem</option>
      </select></label>
    <label>Tamanho mínimo da peça <span id="area-v">700</span>
      <input id="area" type="range" min="200" max="6000" step="100" value="700"></label>
    <label>Qualidade da imagem <span id="qual-v">12</span>
      <input id="qual" type="range" min="10" max="40" value="12"></label>
    <label>Iluminação <button id="luz">Flash da placa</button></label>
    <label>Sobreposição <button id="mostrar">Esconder linha no vídeo</button></label>
  </div>
</details>

<p class="rodape">Detecção por contorno (OpenCV) no PC · imagem chegando pela USB ·
cada peça é rastreada e contada uma única vez ao cruzar a linha de despejo.</p>

<p class="rodape creditos">
  <b>ETPC — Escola Técnica</b> · Matheus Pedrosa, Carlos Eduardo Borges, Maria Eduarda Mazza,
  Milena Maia, Milena Rodrigues · Apoio: Prof. Vinicius (Tecnologia) · © 2026 Todos os direitos reservados
</p>

<script>
  // Icones das formas, em SVG, para nao depender de fonte nem de imagem externa.
  const ICONES = {
    circulo:   c => `<svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="15" fill="${c}"/></svg>`,
    quadrado:  c => `<svg viewBox="0 0 40 40"><rect x="6" y="6" width="28" height="28" rx="3" fill="${c}"/></svg>`,
    triangulo: c => `<svg viewBox="0 0 40 40"><path d="M20 5 L36 34 L4 34 Z" fill="${c}"/></svg>`,
    estrela:   c => `<svg viewBox="0 0 40 40"><path d="M20 3l4.9 10.6 11.6 1.3-8.6 7.9 2.3 11.4L20 28.5l-10.2 5.7 2.3-11.4-8.6-7.9 11.6-1.3z" fill="${c}"/></svg>`,
    outros:    c => `<svg viewBox="0 0 40 40"><path d="M20 4l14 8v16l-14 8-14-8V12z" fill="none" stroke="${c}" stroke-width="3"/></svg>`,
  };
  const COR = {
    circulo: 'var(--circulo)', quadrado: 'var(--quadrado)',
    triangulo: 'var(--triangulo)', estrela: 'var(--estrela)', outros: 'var(--outros)',
  };
  const NOME_COMP = { circulo: 'Círculo', quadrado: 'Quadrado', triangulo: 'Triângulo',
                      estrela: 'Estrela', outros: 'sem compartimento' };
  const NUMERO = { circulo: 1, quadrado: 2, triangulo: 3, estrela: 4 };
  const icone = (forma, cor) => (ICONES[forma] || ICONES.outros)(cor || COR[forma] || COR.outros);

  // icones fixos dos compartimentos
  document.querySelectorAll('.comp').forEach(el => {
    el.querySelector('.ico').innerHTML = icone(el.dataset.c);
  });

  const $ = id => document.getElementById(id);
  let serieVista = 0;
  let timers = {};

  function acender(comp) {
    const el = document.querySelector(`.comp[data-c="${comp}"]`);
    if (!el) return;
    el.classList.add('acende');
    clearTimeout(timers[comp]);
    timers[comp] = setTimeout(() => el.classList.remove('acende'), 1600);
  }

  function destacar(ev) {
    const d = $('destaque');
    d.classList.remove('vazio');
    d.style.setProperty('--cor-viva', COR[ev.compartimento]);
    $('destaque-icone').innerHTML = icone(ev.forma, COR[ev.compartimento]);
    $('destaque-nome').textContent = ev.forma;
    $('destaque-destino').innerHTML = ev.compartimento === 'outros'
      ? 'não tem compartimento próprio'
      : `vai para o compartimento <b>${NUMERO[ev.compartimento]} · ${NOME_COMP[ev.compartimento]}</b>`;
    $('destaque-meta').textContent =
      `peça #${ev.id} · confiança ${Math.round(ev.confianca * 100)}% · ${hora(ev.instante)}`;
    d.classList.remove('novo'); void d.offsetWidth; d.classList.add('novo');
  }

  const hora = t => new Date(t * 1000).toLocaleTimeString('pt-BR');

  function renderHistorico(eventos) {
    const ul = $('historico');
    if (!eventos.length) { ul.innerHTML = '<li class="vazio">nenhuma peça passou ainda</li>'; return; }
    ul.innerHTML = eventos.map(e => `
      <li>${icone(e.forma, COR[e.compartimento])}
        <span class="f">${e.forma}</span>
        <span class="d">${e.compartimento === 'outros' ? '—' : 'comp. ' + NUMERO[e.compartimento]}</span>
        <span class="h">${hora(e.instante)}</span></li>`).join('');
  }

  async function atualizar() {
    let d;
    try { d = await (await fetch('/estado', { cache: 'no-store' })).json(); }
    catch { $('led').classList.remove('ok'); $('porta').textContent = 'servidor fora'; return; }

    $('led').classList.toggle('ok', d.conectada);
    $('porta').textContent = d.conectada ? d.porta : 'placa desconectada';
    $('fps').textContent = d.fps.toFixed(1) + ' fps';

    for (const c in d.contagens) {
      const el = document.querySelector(`.comp[data-c="${c}"] .cont`);
      if (el) el.textContent = d.contagens[c];
    }
    $('total').textContent = d.total;
    $('outros').textContent = d.contagens.outros || 0;

    // o que esta na frente da camera agora
    $('legenda').textContent = d.pecas.length
      ? d.pecas.map(p => `#${p.id} ${p.forma}`).join(' · ')
      : 'aguardando peças';

    // despejos novos desde a ultima consulta
    if (d.serie > serieVista) {
      const novos = d.eventos.slice(0, d.serie - serieVista).reverse();
      novos.forEach(ev => { acender(ev.compartimento); destacar(ev); });
      serieVista = d.serie;
      renderHistorico(d.eventos);
    } else if (serieVista === 0 && d.eventos.length) {
      // pagina aberta com o programa ja rodando: mostra o que ja passou
      serieVista = d.serie; renderHistorico(d.eventos); destacar(d.eventos[0]);
    }

    // ajustes vindos de outra aba/aparelho
    if (document.activeElement !== $('linha')) { $('linha').value = d.linha; $('linha-v').textContent = d.linha; }
    if (document.activeElement !== $('area'))  { $('area').value = d.area;   $('area-v').textContent = d.area; }
    $('modo').value = d.modo;
  }
  setInterval(atualizar, 250);
  atualizar();

  // ----------------------------------------------------------- ajustes
  const ajustar = q => fetch('/ajuste?' + q);
  const deslizante = (id, rotulo, chave) => {
    $(id).oninput  = e => $(rotulo).textContent = e.target.value;
    $(id).onchange = e => ajustar(`${chave}=${e.target.value}`);
  };
  deslizante('linha', 'linha-v', 'linha');
  deslizante('area',  'area-v',  'area');
  deslizante('qual',  'qual-v',  'qualidade');
  $('modo').onchange = e => ajustar('modo=' + e.target.value);

  let luz = false;
  $('luz').onclick = e => { luz = !luz; e.target.classList.toggle('ligado', luz); ajustar('flash=' + (luz ? 1 : 0)); };

  let linhaVisivel = true;
  $('mostrar').onclick = e => {
    linhaVisivel = !linhaVisivel;
    e.target.textContent = linhaVisivel ? 'Esconder linha no vídeo' : 'Mostrar linha no vídeo';
    ajustar('mostrar_linha=' + (linhaVisivel ? 1 : 0));
  };

  $('zerar').onclick = async () => {
    if (!confirm('Zerar todas as contagens?')) return;
    await fetch('/zerar'); serieVista = 0;
    $('destaque').classList.add('vazio'); $('destaque-icone').innerHTML = '';
    $('destaque-nome').textContent = 'aguardando…';
    $('destaque-destino').textContent = ''; $('destaque-meta').textContent = '';
    renderHistorico([]);
  };

  // se o stream cair (placa reiniciou), tenta de novo sozinho
  $('video').onerror = () => setTimeout(() => { $('video').src = '/stream?t=' + Date.now(); }, 1500);
</script>
</html>
"""
