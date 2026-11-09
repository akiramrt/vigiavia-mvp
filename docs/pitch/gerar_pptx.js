/* Gera o deck do pitch (docs/pitch/VigiaVia_Pitch.pptx), com a fala de cada slide nas anotações do apresentador,
 * o roteiro (docs/pitch/roteiro.md) a partir dessas mesmas falas e, se PREVIA=<arquivo.html>, uma prévia HTML com as
 * mesmas medidas, para conferir o visual sem o PowerPoint.
 * Dependências: npm i pptxgenjs@3.12.0 react@18.3.1 react-dom@18.3.1 react-icons@5.4.0 sharp@0.33.5
 * Uso: node docs/pitch/gerar_pptx.js            (números vêm de docs/pitch/viabilidade.json)
 */
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const pptxgen = require("pptxgenjs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");
const fa = require("react-icons/fa6");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));

const AQUI = __dirname;
const RAIZ = path.resolve(AQUI, "..", "..");
const V = JSON.parse(fs.readFileSync(path.join(AQUI, "viabilidade.json"), "utf8"));
const URL_MVP = "https://ca-vigiavia-prod.happywave-0bf5b4c3.brazilsouth.azurecontainerapps.io";
const W = 13.333, H = 7.5, M = 0.6;

// paleta do MVP (tema escuro + âmbar). No tema do arquivo: dk1 = fundo, lt1 = texto (as anotações seguem legíveis).
const COR = { fundo: "0F1419", cartao: "182029", borda: "2B3743", texto: "EEF2F5", suave: "A9B6C2",
  ambar: "FFB020", verm: "FF5A4E", verde: "3CCF7A", azul: "7CC4FF", laranja: "FD9D24" };
const THEME = { name: "VigiaVia", headFontFace: "Segoe UI", bodyFontFace: "Segoe UI",
  colors: { dk1: COR.fundo, lt1: COR.texto, dk2: COR.cartao, lt2: COR.suave, accent1: COR.ambar, accent2: COR.verm,
    accent3: COR.verde, accent4: COR.borda, accent5: COR.azul, accent6: COR.laranja, hlink: COR.azul, folHlink: COR.suave } };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "VigiaVia — pitch";
pres.author = "Deivison Pertel, Eduardo Akira Murata, Wesley Souza de Oliveira";
pres.company = "FIAP Global Solution 2026.2";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const ESQ = { fundo: C.text1, cartao: C.text2, texto: C.background1, suave: C.background2, ambar: C.accent1,
  verm: C.accent2, verde: C.accent3, borda: C.accent4, azul: C.accent5, laranja: C.accent6 };
const cor = (n) => ESQ[n] || n;      // nome da paleta -> cor do tema; hex passa direto (cores oficiais dos ODS)
const hex = (n) => COR[n] || n;
const br = (v, c = 0) => v.toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });

// ------------------------------------------------------------------ primitivas: desenham no slide e na prévia HTML
const IN = 96, PT = 96 / 72;
const css = (o) => Object.entries(o).map(([k, v]) => `${k}:${v}`).join(";");
const rgba = (h, t) => { const n = parseInt(h, 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${t == null ? 1 : 1 - t / 100})`; };
const pos = (x, y, w, h) => ({ position: "absolute", left: `${x * IN}px`, top: `${y * IN}px`, width: `${w * IN}px`, height: `${h * IN}px` });
const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");

function caixa(s, x, y, w, h, o = {}) {
  const raio = o.raio ?? 0.14;
  const opt = { x, y, w, h, fill: { color: cor(o.fill || "cartao") }, objectName: o.nome || "cartão" };
  if (o.transp != null) opt.fill.transparency = o.transp;
  if (o.linha !== false) opt.line = { color: cor(o.linha || "borda"), width: o.esp || 1 };
  s.p.addShape(raio ? pres.shapes.ROUNDED_RECTANGLE : pres.shapes.RECTANGLE, raio ? { ...opt, rectRadius: raio } : opt);
  s.h.push(`<div style="${css({ ...pos(x, y, w, h), "box-sizing": "border-box", background: rgba(hex(o.fill || "cartao"), o.transp),
    border: o.linha === false ? "none" : `${(o.esp || 1) * PT}px solid #${hex(o.linha || "borda")}`, "border-radius": `${raio * IN}px` })}"></div>`);
}

function circulo(s, x, y, d, o = {}) {
  s.p.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: cor(o.fill || "borda") }, objectName: o.nome || "círculo" });
  s.h.push(`<div style="${css({ ...pos(x, y, d, d), background: `#${hex(o.fill || "borda")}`, "border-radius": "50%" })}"></div>`);
}

function texto(s, x, y, w, h, conteudo, o = {}) {
  const runs = (typeof conteudo === "string" ? [{ text: conteudo }] : conteudo).map((r) => ({ text: r.text, options: { ...(r.options || {}) } }));
  // hyperlink vai no trecho (run): na caixa, o pptxgenjs grava uma relação inexistente (rIdundefined)
  s.p.addText(runs.map((r) => ({ text: r.text, options: { ...r.options, color: cor(r.options.color || o.cor || "texto"),
    ...(o.link ? { hyperlink: { url: o.link } } : {}) } })), {
    x, y, w, h, fontSize: o.tam || 14, bold: !!o.negrito, italic: !!o.italico, align: o.alinha || "left", valign: o.valign || "top",
    margin: 0, isTextBox: true, charSpacing: o.espaco, objectName: o.nome || "texto", fit: "none" });
  const just = { top: "flex-start", middle: "center", bottom: "flex-end" }[o.valign || "top"];
  const spans = runs.map((r) => `<span style="${css({ color: `#${hex(r.options.color || o.cor || "texto")}`, "font-weight": (r.options.bold ?? o.negrito) ? 700 : 400 })}">${esc(r.text)}</span>${r.options.breakLine ? "<br>" : ""}`).join("");
  s.h.push(`<div style="${css({ ...pos(x, y, w, h), display: "flex", "flex-direction": "column", "justify-content": just, "text-align": o.alinha || "left",
    "font-size": `${(o.tam || 14) * PT}px`, "font-style": o.italico ? "italic" : "normal", "letter-spacing": `${(o.espaco || 0) * PT}px`, outline: "1px dashed rgba(255,0,255,.25)" })}"><div>${spans}</div></div>`);
}

function lista(s, x, y, w, h, itens, o = {}) {
  const tam = o.tam || 15, gap = o.gap ?? 8;
  s.p.addText(itens.map((t, i) => ({ text: t, options: { bullet: { indent: 18 }, breakLine: i < itens.length - 1, paraSpaceAfter: gap, color: cor(o.cor || "texto") } })),
    { x, y, w, h, fontSize: tam, valign: "top", margin: 0, isTextBox: true, objectName: o.nome || "lista", fit: "none" });
  s.h.push(`<div style="${css({ ...pos(x, y, w, h), "font-size": `${tam * PT}px`, color: `#${hex(o.cor || "texto")}`, outline: "1px dashed rgba(255,0,255,.25)" })}">` +
    itens.map((t) => `<div style="${css({ position: "relative", "padding-left": `${18 * PT}px`, "margin-bottom": `${gap * PT}px` })}"><span style="position:absolute;left:0">•</span>${esc(t)}</div>`).join("") + "</div>");
}

function imagem(s, arq, x, y, w, h, o = {}) {
  s.p.addImage({ path: arq, x, y, w, h, objectName: o.nome || "imagem", altText: o.alt || "" });
  s.h.push(`<img src="${pathToFileURL(arq)}" style="${css(pos(x, y, w, h))}">`);
  caixa(s, x, y, w, h, { fill: "fundo", transp: 100, linha: "borda", raio: 0, nome: "moldura" });
}

function icone(s, png, x, y, d) {
  s.p.addImage({ data: png, x, y, w: d, h: d, objectName: "ícone" });
  s.h.push(`<img src="data:${png}" style="${css(pos(x, y, d, d))}">`);
}

function grafico(s, tipo, series, x, y, w, h, opt) {
  s.p.addChart(tipo, series, { x, y, w, h, ...opt });
  const vals = series.flatMap((r) => r.values), max = Math.max(...vals.map(Math.abs));
  s.h.push(`<div style="${css({ ...pos(x, y, w, h), border: "1px dashed #7CC4FF", color: "#7CC4FF", "font-size": "12px", padding: "4px", "box-sizing": "border-box" })}">` +
    `[gráfico nativo] ${esc(opt.title || "")}: ${series.map((r) => `${r.name} = ${r.values.join(" / ")}`).join(" · ")} (máx ${max})</div>`);
}

async function iconePng(Comp, corHex) {
  const svg = renderToStaticMarkup(React.createElement(Comp, { size: 256, color: `#${corHex}` }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

// ------------------------------------------------------------------ conteúdo
const nuvemMvp = V.nuvem_brl_mes.mvp, nuvemSp = V.nuvem_brl_mes.sp_inteira;
const preco = V.premissas.preco_km_ano_brl;
const kmSub = V.premissas.km_pavimentados_sp / V.premissas.subprefeituras_sp;
const cv = V.custo_variavel_brl_km_ano;
const margem = Math.round(V.margem_bruta * 100);
// valor em reais por extenso para a fala: 6.577 -> "6 mil e 600" (arredondado à centena)
const milFalado = (v) => { const r = Math.round(v / 100) * 100, mil = Math.floor(r / 1000), resto = r % 1000;
  return resto ? `${mil} mil e ${resto}` : `${mil} mil`; };
const proj = V.projecao;
const anos = Object.keys(proj);

const SLIDES = [];   // { secao, layout, rotulo, titulo, sub, tempo, bloco, notas, desenhar(s) }

async function montar() {
  const I = {};
  const ICONES = { tel: lu.LuPhoneCall, din: lu.LuBanknote, moto: fa.FaMotorcycle, cam: lu.LuCamera, pin: lu.LuMapPin,
    fila: lu.LuListChecks, pref: lu.LuLandmark, usu: lu.LuUsers, canal: lu.LuHandshake, graf: lu.LuChartColumn,
    saude: lu.LuHeartPulse, fog: lu.LuRocket, cel: lu.LuSmartphone, escudo: lu.LuShieldCheck, nuvem: lu.LuCloud, rota: lu.LuRoute };
  for (const [k, comp] of Object.entries(ICONES)) I[k] = await iconePng(comp, COR.ambar);
  I.motoVerm = await iconePng(fa.FaMotorcycle, COR.verm);
  const svgLogo = `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><circle cx="128" cy="128" r="116" fill="#${COR.ambar}"/><circle cx="128" cy="128" r="46" fill="#${COR.fundo}"/></svg>`;
  const LOGO = "image/png;base64," + (await sharp(Buffer.from(svgLogo)).png().toBuffer()).toString("base64");

  // layouts: conteúdo (rótulo + título + subtítulo) e encerramento; logo, marca e número no rodapé
  const rodape = [
    { image: { x: M, y: 6.98, w: 0.24, h: 0.24, data: LOGO } },
    { text: { text: "VigiaVia", options: { x: M + 0.34, y: 6.95, w: 3, h: 0.3, fontSize: 12, bold: true, color: ESQ.texto, margin: 0 } } },
  ];
  const numero = { x: W - M - 0.8, y: 6.95, w: 0.8, h: 0.3, fontSize: 11, color: ESQ.suave, align: "right" };
  pres.defineSlideMaster({ title: "CONTEUDO", background: { color: ESQ.fundo }, slideNumber: numero, objects: [
    { placeholder: { options: { name: "rotulo", type: "body", x: M, y: 0.45, w: 9, h: 0.32, fontSize: 12, bold: true, color: ESQ.ambar, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.78, w: W - 2 * M, h: 0.72, fontSize: 32, bold: true, color: ESQ.texto, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "sub", type: "body", x: M, y: 1.5, w: W - 2 * M, h: 0.4, fontSize: 16, color: ESQ.suave, margin: 0, valign: "top" }, text: "" } },
    ...rodape] });
  pres.defineSlideMaster({ title: "ENCERRAMENTO", background: { color: ESQ.fundo }, slideNumber: numero, objects: [
    { placeholder: { options: { name: "rotulo", type: "body", x: M, y: 1.0, w: 9, h: 0.32, fontSize: 12, bold: true, color: ESQ.ambar, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.38, w: 10.5, h: 1.45, fontSize: 38, bold: true, color: ESQ.texto, margin: 0, valign: "top" }, text: "" } },
    ...rodape] });

  const L3 = (gap) => (W - 2 * M - 2 * gap) / 3;

  SLIDES.push({ secao: "Problema", rotulo: "UMA REFLEXÃO ANTES DE COMEÇAR", titulo: "Quantas vezes você desviou de um buraco hoje?",
    sub: "Nós também. E é com essa dor que vamos trabalhar.", tempo: "0:00", bloco: "Abertura e problema",
    notas: "Olá! Eu sou o Wesley e, com o Deivison e o Eduardo, criamos o VigiaVia. Quantas vezes você desviou de um buraco hoje? Em 2025, São Paulo recebeu 113 mil pedidos de tapa-buraco — e a própria prefeitura reconhece que o mesmo buraco gera vários chamados. Só em 2019, a cidade empenhou 144 milhões de reais em tapa-buraco. E quem anda de moto é o mais exposto: 475 motociclistas morreram no trânsito da capital em 2025.",
    desenhar: (s) => {
      const g = 0.35, w = L3(g), y = 2.25, h = 3.65;
      [["113,1 mil", "pedidos de tapa-buraco em São Paulo em 2025", "e o mesmo buraco gera vários chamados", I.tel, "ambar"],
       ["R$ 144 mi", "empenhados só em tapa-buraco em 2019", "trabalho guiado por chamados manuais", I.din, "ambar"],
       ["475", "motociclistas mortos no trânsito da capital em 2025", "quem anda de moto sente o buraco primeiro", I.motoVerm, "verm"]]
        .forEach(([num, rot, sub, ic, c], i) => {
          const x = M + i * (w + g);
          caixa(s, x, y, w, h);
          circulo(s, x + 0.35, y + 0.35, 0.8); icone(s, ic, x + 0.53, y + 0.53, 0.44);
          texto(s, x + 0.35, y + 1.35, w - 0.7, 0.85, num, { tam: 40, negrito: true, cor: c, nome: "número" });
          texto(s, x + 0.35, y + 2.2, w - 0.7, 0.75, rot, { tam: 16 });
          texto(s, x + 0.35, y + 2.95, w - 0.7, 0.5, sub, { tam: 12, cor: "suave" });
        });
      texto(s, M, 6.2, W - 2 * M, 0.3, "Fontes: SMSUB/PMSP via BNews SP (2026) · CartaCapital · Infosiga/Detran-SP via Portal do Trânsito (2026)", { tam: 10, cor: "suave" });
    } });

  SLIDES.push({ secao: "Solução e demonstração", rotulo: "A SOLUÇÃO VIGIAVIA", titulo: "Cada buraco vira um relato único, priorizado",
    sub: "Em vez de esperar o chamado, a cidade enxerga o buraco", tempo: "0:35", bloco: "Solução e proposta de valor",
    notas: "O VigiaVia muda essa lógica: em vez de esperar o chamado, usamos as câmeras que já circulam pela cidade — celulares, ônibus, entregadores e viaturas da prefeitura — para detectar buracos automaticamente. A zeladoria recebe um único relato por buraco, com localização, foto da via e prioridade. Sem guardar rosto nem foto inteira, e sempre com validação humana.",
    desenhar: (s) => {
      const g = 0.6, w = L3(g), y = 2.2, h = 2.95;
      [["Detecta", "Câmeras que já circulam — celulares, ônibus, entregadores e viaturas — com IA em tempo real.", I.cam],
       ["Relata", "Só o recorte da via e a localização. Nenhum rosto, nenhuma foto inteira guardada.", I.pin],
       ["Prioriza", "Fila única por buraco, por severidade e confirmações. A zeladoria valida e gera a ordem de serviço.", I.fila]]
        .forEach(([tit, desc, ic], i) => {
          const x = M + i * (w + g);
          caixa(s, x, y, w, h);
          circulo(s, x + 0.35, y + 0.35, 0.8); icone(s, ic, x + 0.53, y + 0.53, 0.44);
          texto(s, x + 1.35, y + 0.47, w - 1.6, 0.55, `${i + 1}. ${tit}`, { tam: 22, negrito: true, valign: "middle" });
          texto(s, x + 0.35, y + 1.4, w - 0.7, 1.35, desc, { tam: 15 });
          if (i < 2) {
            s.p.addShape(pres.shapes.RIGHT_ARROW, { x: x + w + 0.14, y: y + h / 2 - 0.17, w: 0.32, h: 0.34, fill: { color: cor("ambar") }, objectName: "seta" });
            s.h.push(`<div style="${css({ ...pos(x + w + 0.14, y + h / 2 - 0.17, 0.32, 0.34), background: "#FFB020", "clip-path": "polygon(0 30%,55% 30%,55% 0,100% 50%,55% 100%,55% 70%,0 70%)" })}"></div>`);
          }
        });
      caixa(s, M, 5.5, W - 2 * M, 0.85, { fill: "ambar", transp: 86, linha: "ambar" });
      texto(s, M + 0.35, 5.5, W - 2 * M - 0.7, 0.85, [{ text: "Proposta de valor: " }, { text: "menos chamados duplicados e reparo mais rápido", options: { bold: true, color: "ambar" } }, { text: ", com evidência para cada ordem de serviço." }], { tam: 17, valign: "middle" });
    } });

  SLIDES.push({ secao: "Solução e demonstração", rotulo: "DEMONSTRAÇÃO", titulo: "Chega de slide. Vamos à prática.",
    sub: "O MVP funcionando de verdade, na URL pública", tempo: "1:00", bloco: "Demonstração do MVP real (gravação da tela)",
    notas: "[Troque para o navegador: aqui entra a gravação do MVP em uso real.] Este é o VigiaVia funcionando de verdade, na URL pública, no Azure. Na visão do cidadão, eu abro a câmera — ou envio um vídeo gravado na rua. O modelo detecta o buraco em tempo real e avisa: atenção, buraco à frente, com a severidade. Com um toque, envio o relato: vai só o recorte da via e a localização; nenhuma foto inteira é guardada. Agora, a visão da zeladoria: os relatos chegam numa fila priorizada por severidade e confirmações, e aparecem no mapa. Se outra pessoa relatar o mesmo buraco, ele não vira um chamado novo: vira uma confirmação e sobe na fila. O agente valida com um clique, e o relato vira ordem de serviço. E tudo roda em produção, com deploy automático e segurança no pipeline.",
    desenhar: (s) => {
      const y = 2.15, h = 3.9;
      const w1 = h * (1366 / 1231), w2 = h * (1366 / 1235);
      imagem(s, path.join(RAIZ, "docs/evidencias/img/mvp_cidadao.png"), M, y, w1, h, { alt: "Tela do cidadão: buraco detectado" });
      imagem(s, path.join(RAIZ, "docs/evidencias/img/mvp_zeladoria.png"), M + w1 + 0.3, y, w2, h, { alt: "Tela da zeladoria: fila e mapa" });
      texto(s, M, y + h + 0.1, w1, 0.3, "Cidadão: detecção e relato", { tam: 12, cor: "suave" });
      texto(s, M + w1 + 0.3, y + h + 0.1, w2, 0.3, "Zeladoria: fila priorizada e mapa", { tam: 12, cor: "suave" });
      const x = M + w1 + w2 + 0.65, wd = W - M - x;
      [["Cidadão", "detecta e relata", I.cam], ["Zeladoria", "prioriza e valida", I.fila], ["Produção", "Azure · HTTPS · CI/CD", I.nuvem]]
        .forEach(([t, d, ic], i) => {
          const yy = y + i * 0.95;
          circulo(s, x, yy, 0.62); icone(s, ic, x + 0.14, yy + 0.14, 0.34);
          texto(s, x + 0.8, yy - 0.02, wd - 0.8, 0.36, t, { tam: 16, negrito: true });
          texto(s, x + 0.8, yy + 0.32, wd - 0.8, 0.32, d, { tam: 12, cor: "suave" });
        });
      caixa(s, x, y + 2.95, wd, 0.95, { fill: "ambar", transp: 86, linha: "ambar" });
      texto(s, x + 0.15, y + 2.95, wd - 0.3, 0.95, "Vamos abrir o MVP agora.", { tam: 15, negrito: true, cor: "ambar", valign: "middle", alinha: "center" });
    } });

  SLIDES.push({ secao: "Negócio", rotulo: "MODELO DE NEGÓCIO", titulo: "Quem paga, quem usa e por qual canal",
    sub: "Assinatura B2G por quilômetro de via monitorado", tempo: "2:30", bloco: "Modelo de negócio",
    notas: `Quem paga é a prefeitura: uma assinatura de ${preco} reais por quilômetro de via monitorado por ano — cerca de 2 mil reais por mês por subprefeitura, abaixo dos 63 reais da vialytics, que já atende mais de 600 municípios na Europa e nos Estados Unidos. Quem usa: o cidadão, de graça; os agentes de zeladoria; e frotas parceiras, que rodam com um celular embarcado em troca do alerta para os seus motoristas.`,
    desenhar: (s) => {
      const g = 0.35, w = L3(g), y = 2.2, h = 3.85;
      const cab = (x, t, ic) => { circulo(s, x + 0.35, y + 0.35, 0.7); icone(s, ic, x + 0.5, y + 0.5, 0.4); texto(s, x + 1.2, y + 0.35, w - 1.45, 0.7, t, { tam: 20, negrito: true, cor: "ambar", valign: "middle" }); };
      let x = M; caixa(s, x, y, w, h); cab(x, "Quem paga", I.pref);
      texto(s, x + 0.35, y + 1.25, w - 0.7, 0.75, `R$ ${preco}`, { tam: 40, negrito: true, nome: "número" });
      texto(s, x + 0.35, y + 2.0, w - 0.7, 0.6, `por km de via por ano ≈ R$ ${br(Math.round(kmSub * preco / 12 / 1000))} mil por mês por subprefeitura`, { tam: 14 });
      texto(s, x + 0.35, y + 2.75, w - 0.7, 0.85, `Referência: vialytics, 600+ municípios, ≈ R$ ${br(Math.round(V.referencia_brl_km_ano))}/km/ano`, { tam: 13, cor: "suave" });
      x += w + g; caixa(s, x, y, w, h); cab(x, "Quem usa", I.usu);
      lista(s, x + 0.35, y + 1.3, w - 0.7, 2.4, ["Cidadão: grátis, na web e no celular", "Agentes de zeladoria: fila e mapa", "Frotas parceiras: celular embarcado em troca do alerta"], { tam: 15, gap: 10 });
      x += w + g; caixa(s, x, y, w, h); cab(x, "Canal", I.canal);
      lista(s, x + 0.35, y + 1.3, w - 0.7, 2.4, ["Venda à prefeitura via CPSI (Marco Legal das Startups)", "Integração com o 156 e o Colab", "Frotas parceiras ampliam a cobertura"], { tam: 15, gap: 10 });
      texto(s, M, 6.2, W - 2 * M, 0.3, "Fontes: piloto vialytics em Louth, Irlanda (€17.500/ano para 1.691 km) · PTAX do euro · LC 182/2021", { tam: 10, cor: "suave" });
    } });

  SLIDES.push({ secao: "Negócio", rotulo: "ESTRATÉGIA DE LANÇAMENTO", titulo: "Go-to-Market",
    sub: "Validar com um piloto antes de escalar", tempo: "2:55", bloco: "Go-to-market",
    notas: "Para chegar lá, usamos o Marco Legal das Startups: um contrato público de solução inovadora permite um piloto de até 1,6 milhão de reais. Começamos pela Subprefeitura Sé, provamos as metas, escalamos para as 32 subprefeituras de São Paulo e levamos o caso para cidades médias.",
    desenhar: (s) => {
      const g = 0.3, w = (W - 2 * M - 3 * g) / 4, y = 2.2, h = 3.25;
      [["01", "Piloto CPSI na Sé", "6 meses, R$ 150 mil, 10 viaturas da zeladoria com celular embarcado."],
       ["02", "Prova de conceito", "Metas: −30% de chamados duplicados, OS em menos de 48 h, precisão ≥ 80%."],
       ["03", "32 subprefeituras", "Contrato de fornecimento após o CPSI, de até R$ 8 mi."],
       ["04", "Cidades médias", "O caso de SP, consórcios intermunicipais e integração com o 156."]]
        .forEach(([n, t, d], i) => {
          const x = M + i * (w + g);
          caixa(s, x, y, w, h);
          texto(s, x + 0.3, y + 0.3, w - 0.6, 0.7, n, { tam: 34, negrito: true, cor: "ambar" });
          texto(s, x + 0.3, y + 1.05, w - 0.6, 0.5, t, { tam: 17, negrito: true });
          texto(s, x + 0.3, y + 1.6, w - 0.6, 1.45, d, { tam: 14, cor: "suave" });
        });
      caixa(s, M, 5.75, W - 2 * M, 0.7, { fill: "ambar", transp: 86, linha: "ambar" });
      texto(s, M + 0.35, 5.75, W - 2 * M - 0.7, 0.7, [{ text: "CPSI: ", options: { bold: true, color: "ambar" } }, { text: "piloto de até R$ 1,6 mi por 12 meses e contrato de fornecimento de até R$ 8 mi, sem nova licitação." }], { tam: 15, valign: "middle" });
    } });

  SLIDES.push({ secao: "Negócio", rotulo: "MODELO DE NEGÓCIO · PREÇO", titulo: "Unit Economics",
    sub: `Exemplo: uma subprefeitura de São Paulo (~${br(Math.round(kmSub))} km de vias)`, tempo: "3:15", bloco: "Unit economics",
    notas: `Em uma subprefeitura típica, com ${br(Math.round(kmSub))} quilômetros, a receita é de ${milFalado(kmSub * preco)} reais por ano e o custo variável — nuvem, celulares e suporte — fica em ${milFalado(kmSub * cv.total)}. Margem bruta de ${margem}%.`,
    desenhar: (s) => {
      const g = 0.35, w = L3(g), y = 2.2, h = 1.95;
      [[`R$ ${br(kmSub * preco / 1000, 1)} mil`, "receita por ano", `R$ ${preco}/km × ${br(Math.round(kmSub))} km`, "ambar"],
       [`R$ ${br(kmSub * cv.total / 1000, 1)} mil`, "custo variável por ano", "nuvem + celulares + suporte", "texto"],
       [`${margem}%`, "margem bruta", "receita menos custo variável", "verde"]]
        .forEach(([n, r, d, c], i) => {
          const x = M + i * (w + g);
          caixa(s, x, y, w, h);
          texto(s, x + 0.35, y + 0.25, w - 0.7, 0.75, n, { tam: 34, negrito: true, cor: c, nome: "número" });
          texto(s, x + 0.35, y + 1.0, w - 0.7, 0.4, r, { tam: 16, negrito: true });
          texto(s, x + 0.35, y + 1.4, w - 0.7, 0.35, d, { tam: 12, cor: "suave" });
        });
      grafico(s, pres.charts.BAR, [{ name: "R$ por km por ano", labels: ["Suporte", "Celulares", "Nuvem", "Preço"], values: [cv.suporte, cv.dispositivos, cv.nuvem, preco] }],
        M, 4.4, W - 2 * M, 1.95, {
          barDir: "bar", chartColors: [COR.ambar], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0.00",
          dataLabelColor: COR.texto, dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", showLegend: false,
          showTitle: true, title: "Preço e custo variável por km de via por ano (R$)", titleColor: COR.texto, titleFontSize: 13, titleFontFace: "+mn-lt",
          catAxisLabelColor: COR.suave, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
          valGridLine: { style: "none" }, catGridLine: { style: "none" }, catAxisLineShow: false, barGapWidthPct: 40,
          plotArea: { fill: { color: COR.fundo } }, chartArea: { fill: { color: COR.fundo } } });
    } });

  SLIDES.push({ secao: "Indicadores e viabilidade", rotulo: "INDICADORES", titulo: "O que medimos: negócio e impacto",
    sub: "Os mesmos números que a prefeitura e os investidores acompanham", tempo: "3:30", bloco: "Indicadores e ODS",
    notas: "Medimos o sucesso em duas frentes. No negócio: quilômetros monitorados, receita recorrente, margem e renovação de contratos. No cidadão: o tempo entre a detecção e o reparo, os chamados duplicados evitados e a precisão confirmada pela zeladoria. Isso conecta o VigiaVia aos ODS 11, de cidades sustentáveis; 9, de infraestrutura; e 3, de redução de mortes no trânsito.",
    desenhar: (s) => {
      const g = 0.35, w = (W - 2 * M - g) / 2, y = 2.2, h = 3.25;
      [["Negócio", I.graf, ["km monitorados e cidades contratantes", "Receita recorrente anual (ARR)", `Margem bruta: ${margem}%`, "Renovação de contratos e custo por km"]],
       ["Impacto no cidadão", I.saude, ["Tempo entre a detecção e o reparo", "% de chamados duplicados evitados", "Buracos detectados por km", "Precisão confirmada pela zeladoria"]]]
        .forEach(([t, ic, itens], i) => {
          const x = M + i * (w + g);
          caixa(s, x, y, w, h);
          circulo(s, x + 0.35, y + 0.3, 0.7); icone(s, ic, x + 0.5, y + 0.45, 0.4);
          texto(s, x + 1.2, y + 0.3, w - 1.5, 0.7, t, { tam: 20, negrito: true, cor: "ambar", valign: "middle" });
          lista(s, x + 0.35, y + 1.2, w - 0.7, 1.9, itens, { tam: 16, gap: 8 });
        });
      [["ODS 11 · Cidades sustentáveis", "FD9D24"], ["ODS 9 · Infraestrutura", "FD6925"], ["ODS 3 · Mortes no trânsito (3.6)", "4C9F38"]]
        .forEach(([t, c], i) => {
          const wb = (W - 2 * M - 2 * 0.3) / 3, x = M + i * (wb + 0.3);
          caixa(s, x, 5.75, wb, 0.62, { fill: c, linha: false, raio: 0.1 });
          texto(s, x, 5.75, wb, 0.62, t, { tam: 15, negrito: true, cor: "FFFFFF", alinha: "center", valign: "middle" });
        });
    } });

  SLIDES.push({ secao: "Indicadores e viabilidade", rotulo: "VIABILIDADE E PEDIDO", titulo: "Custa pouco e se paga em 2029",
    sub: "Custos reais de nuvem e projeção a partir do piloto", tempo: "3:55", bloco: "Viabilidade e pedido",
    notas: `E é viável: a nuvem custa ${br(Math.round(nuvemMvp))} reais por mês no MVP e cerca de ${br(nuvemSp / 1000, 1)} mil para São Paulo inteira. Monitorar a cidade toda renderia ${br(V.sp_inteira_brl_ano / 1000)} mil reais por ano — meio por cento do que ela empenhou em tapa-buraco em 2019 — e o equilíbrio chega em 2029. Nosso pedido: para a prefeitura, um piloto de seis meses na Sé, de 150 mil reais; e para investidores, ${br(V.pedido_investimento_brl / 1000)} mil reais de pré-seed.`,
    desenhar: (s) => {
      grafico(s, pres.charts.BAR, [
        { name: "Receita", labels: anos, values: anos.map((a) => Math.round(proj[a].receita_brl / 1000)) },
        { name: "Resultado", labels: anos, values: anos.map((a) => Math.round(proj[a].resultado_brl / 1000)) }],
        M, 2.15, 6.7, 3.7, {
          barDir: "col", barGrouping: "clustered", chartColors: [COR.ambar, COR.azul], showValue: true, dataLabelPosition: "outEnd",
          dataLabelFormatCode: "#,##0", dataLabelColor: COR.texto, dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt",
          showTitle: true, title: "Receita e resultado por ano (R$ mil)", titleColor: COR.texto, titleFontSize: 13, titleFontFace: "+mn-lt",
          showLegend: true, legendPos: "b", legendColor: COR.suave, legendFontSize: 12, legendFontFace: "+mn-lt",
          catAxisLabelColor: COR.suave, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
          valGridLine: { style: "none" }, catGridLine: { style: "none" }, catAxisLineShow: false,
          plotArea: { fill: { color: COR.fundo } }, chartArea: { fill: { color: COR.fundo } } });
      texto(s, M, 5.95, 6.7, 0.55, `Nuvem: R$ ${br(Math.round(nuvemMvp))}/mês no MVP e R$ ${br(Math.round(nuvemSp))}/mês para SP inteira. SP inteira = R$ ${br(V.sp_inteira_brl_ano / 1000)} mil/ano, ${br(V.sp_inteira_vs_tapa_buraco_2019 * 100, 2)}% do tapa-buraco de 2019.`, { tam: 12, cor: "suave" });
      const x = M + 7.05, w = W - M - x;
      [["Para a prefeitura", "R$ 150 mil", "piloto de 6 meses na Subprefeitura Sé, via CPSI. Meta: −30% de chamados duplicados.", I.pref],
       ["Para investidores", `R$ ${br(V.pedido_investimento_brl / 1000)} mil`, "pré-seed para chegar ao ponto de equilíbrio em 2029.", I.fog]]
        .forEach(([t, n, d, ic], i) => {
          const y = 2.15 + i * 2.2, h = 2.0;
          caixa(s, x, y, w, h, i === 0 ? { linha: "ambar", esp: 2 } : {});
          circulo(s, x + 0.3, y + 0.3, 0.62); icone(s, ic, x + 0.44, y + 0.44, 0.34);
          texto(s, x + 1.1, y + 0.3, w - 1.4, 0.62, t, { tam: 16, negrito: true, valign: "middle" });
          texto(s, x + 0.3, y + 0.98, w - 0.6, 0.55, n, { tam: 28, negrito: true, cor: "ambar", nome: "número" });
          texto(s, x + 0.3, y + 1.48, w - 0.6, 0.45, d, { tam: 12, cor: "suave" });
        });
    } });

  SLIDES.push({ secao: "Encerramento", layout: "ENCERRAMENTO", rotulo: "ENCERRAMENTO", titulo: "Cada buraco vira um relato, antes de virar um acidente.",
    tempo: "4:30", bloco: "Encerramento",
    notas: "VigiaVia: cada buraco vira um relato, antes de virar um acidente. Obrigado!",
    desenhar: (s) => {
      texto(s, M, 3.2, 6, 0.32, "FUNDADORES", { tam: 12, negrito: true, cor: "ambar", espaco: 2 });
      const g = 0.35, w = L3(g);
      [["Deivison Pertel", "RM 550803"], ["Eduardo Akira Murata", "RM 98713"], ["Wesley Souza de Oliveira", "RM 97874"]].forEach(([n, rm], i) => {
        const x = M + i * (w + g);
        caixa(s, x, 3.65, w, 1.15);
        texto(s, x + 0.3, 3.8, w - 0.6, 0.45, n, { tam: 18, negrito: true });
        texto(s, x + 0.3, 4.25, w - 0.6, 0.4, `${rm} · Engenharia de Software`, { tam: 13, cor: "suave" });
      });
      texto(s, M, 5.15, 6, 0.65, "Obrigado!", { tam: 30, negrito: true, cor: "ambar" });
      texto(s, M, 5.85, W - 2 * M, 0.32, URL_MVP, { tam: 12, cor: "azul", link: URL_MVP });
      texto(s, M, 6.2, W - 2 * M, 0.32, "github.com/akiramrt/vigiavia-mvp · FIAP Global Solution 2026.2 · CitizenTech", { tam: 12, cor: "suave" });
    } });

  // ------------------------------------------------------------------ montagem do .pptx e da prévia
  const previa = [];
  let secaoAtual = null;
  for (const [i, d] of SLIDES.entries()) {
    if (d.secao !== secaoAtual) { pres.addSection({ title: d.secao }); secaoAtual = d.secao; }
    const layout = d.layout || "CONTEUDO";
    const p = pres.addSlide({ masterName: layout, sectionTitle: d.secao });
    const h = [];
    const enc = layout === "ENCERRAMENTO";
    p.addText(d.rotulo, { placeholder: "rotulo", bullet: false });
    p.addText(d.titulo, { placeholder: "title" });
    if (d.sub) p.addText(d.sub, { placeholder: "sub", bullet: false });
    // prévia: cabeçalho e rodapé do layout
    h.push(`<div style="${css({ ...pos(M, enc ? 1.0 : 0.45, 9, 0.32), color: "#FFB020", "font-size": `${12 * PT}px`, "font-weight": 700, "letter-spacing": `${2 * PT}px` })}">${esc(d.rotulo)}</div>`);
    h.push(`<div style="${css({ ...pos(M, enc ? 1.38 : 0.78, enc ? 10.5 : W - 2 * M, enc ? 1.45 : 0.72), color: "#EEF2F5", "font-size": `${(enc ? 38 : 32) * PT}px`, "font-weight": 700, outline: "1px dashed rgba(255,0,255,.25)" })}">${esc(d.titulo)}</div>`);
    if (d.sub) h.push(`<div style="${css({ ...pos(M, 1.5, W - 2 * M, 0.4), color: "#A9B6C2", "font-size": `${16 * PT}px` })}">${esc(d.sub)}</div>`);
    h.push(`<img src="data:${LOGO}" style="${css(pos(M, 6.98, 0.24, 0.24))}"><div style="${css({ ...pos(M + 0.34, 6.95, 3, 0.3), "font-size": `${12 * PT}px`, "font-weight": 700, color: "#EEF2F5" })}">VigiaVia</div>`);
    h.push(`<div style="${css({ ...pos(W - M - 0.8, 6.95, 0.8, 0.3), "font-size": `${11 * PT}px`, color: "#A9B6C2", "text-align": "right" })}">${i + 1}</div>`);
    d.desenhar({ p, h });
    p.addNotes(d.notas);
    previa.push(`<section style="position:relative;width:${W * IN}px;height:${H * IN}px;background:#0F1419;margin:0 0 24px;overflow:hidden">${h.join("")}</section>`);
  }
  const saida = path.join(AQUI, "VigiaVia_Pitch.pptx");
  await pres.writeFile({ fileName: saida });
  await aplicarTema(saida);
  escreverRoteiro();
  if (process.env.PREVIA) {
    fs.writeFileSync(process.env.PREVIA, `<!doctype html><meta charset="utf-8"><body style="margin:0;background:#333;font-family:'Segoe UI',sans-serif">${previa.join("")}</body>`);
  }
  console.log("ok:", saida, `(${SLIDES.length} slides)`);
}

// cores do tema escritas no theme1.xml (o pptxgenjs só grava as fontes)
async function aplicarTema(arq) {
  const zip = await JSZip.loadAsync(fs.readFileSync(arq));
  for (const n of Object.keys(zip.files).filter((f) => /^ppt\/theme\/theme\d+\.xml$/.test(f))) {
    let xml = await zip.file(n).async("string");
    for (const [k, v] of Object.entries(THEME.colors)) {        // troca o conteúdo de <a:dk1>…</a:dk1> etc., sem regex dinâmica
      const ini = xml.indexOf(`<a:${k}>`), fim = xml.indexOf(`</a:${k}>`, ini);
      if (ini >= 0 && fim > ini) xml = `${xml.slice(0, ini)}<a:${k}><a:srgbClr val="${v}"/>${xml.slice(fim)}`;
    }
    xml = xml.replace(/<a:clrScheme name="[^"]*">/, `<a:clrScheme name="${THEME.name}">`);
    zip.file(n, xml);
  }
  fs.writeFileSync(arq, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

function escreverRoteiro() {
  const linhas = [
    "# Roteiro do pitch — VigiaVia (até 5 minutos)", "",
    "> Business Intelligence & Startup Development · Prof. André Maluf · FIAP GS 2026.2.",
    "> **Apresentador: Wesley Souza de Oliveira.** Gerado por `gerar_pptx.js` a partir das anotações de",
    "> [`VigiaVia_Pitch.pptx`](VigiaVia_Pitch.pptx) — na gravação do PowerPoint, a fala aparece como teleprompter.",
    "> Números e fontes: [modelo_de_negocio.md](modelo_de_negocio.md). Como gravar: [guia_gravacao.md](guia_gravacao.md).", "",
    "| Slide | Início | Bloco | Palavras |", "|---|---|---|---|",
    ...SLIDES.map((d, i) => `| ${i + 1} · ${d.titulo} | ${d.tempo} | ${d.bloco} | ${d.notas.split(/\s+/).length} |`), "",
    `Total: ${SLIDES.reduce((a, d) => a + d.notas.split(/\s+/).length, 0)} palavras ≈ 4min30s (com a demonstração).`, "", "---", "",
    ...SLIDES.flatMap((d, i) => [`**${i + 1} · ${d.bloco}** (a partir de ${d.tempo})`, "", `> ${d.notas}`, ""]),
  ];
  fs.writeFileSync(path.join(AQUI, "roteiro.md"), linhas.join("\n"));
}

montar().catch((e) => { console.error(e); process.exit(1); });
