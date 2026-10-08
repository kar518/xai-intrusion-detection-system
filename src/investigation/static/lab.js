const $ = id => document.getElementById(id);
let currentCase, original, guess;
let busy = false;
const number = value => Number(value).toLocaleString(undefined, {maximumFractionDigits: 3});
const percent = value => `${(value * 100).toFixed(2)}%`;
const cleanLabel = value => String(value).replaceAll('�', '-');
function node(tag, text, className) { const el = document.createElement(tag); el.textContent = text; if(className) el.className = className; return el; }
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
function mark(step) { for(let i=1;i<=4;i++) $(`step${i}`).classList.toggle('active', i === step); }
async function api(path, data) {
  const response = await fetch(path, data ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)} : {});
  const payload = await response.json();
  if(!response.ok) throw new Error(payload.error || 'Unable to complete this action.');
  return payload;
}
async function action(task) {
  if(busy) return;
  busy = true; document.querySelectorAll('button, select').forEach(el => el.disabled = true);
  try { await task(); } catch(error) { message(error.message, true); }
  finally { busy = false; document.querySelectorAll('button, select').forEach(el => el.disabled = false); }
}
function fact(container, label, value, note) {
  const el = node('div', '', 'fact'); el.append(node('span',label),node('strong',value),node('small',note)); container.append(el);
}
function facts() {
  const flow = currentCase.flow, box = $('facts'); box.replaceChildren();
  fact(box,'Destination port', number(flow['Destination Port']), 'Service identifier');
  fact(box,'Duration', `${number(flow['Flow Duration']/1000)} ms`, 'Recorded elapsed time');
  fact(box,'Packet rate', `${number(flow['Flow Packets/s'])}/s`, 'Packets per second');
  fact(box,'Outgoing packets',number(flow['Total Fwd Packets']),'Initiator → responder');
  fact(box,'Returning packets',number(flow['Total Backward Packets']),'Responder → initiator');
  fact(box,'Packet-size variation',`${number(flow['Packet Length Std'])} bytes`,'Standard deviation');
  $('features').replaceChildren();
  for(const [name,value] of Object.entries(flow)) { const row = node('tr',''); row.append(node('td',name),node('td',number(value))); $('features').append(row); }
}
async function nextCase() {
  await action(async () => {
    message('Opening a real test record…');
    const next = await api(`/api/case${currentCase ? '?previous='+currentCase.id : ''}`);
    currentCase = next; original = null; guess = null;
    ['model-section','experiment-section','truth-section','comparison'].forEach(id => $(id).hidden = true);
    $('truth').replaceChildren(); $('factor').value = '1';
    document.querySelectorAll('[data-guess]').forEach(button => button.classList.remove('selected'));
    $('case-name').textContent = next.name; facts(); preview(); mark(1);
    message('Observe the measurements, then choose your hypothesis.');
  });
}
function resultView(container, result) {
  container.replaceChildren();
  container.append(node('strong',result.prediction,result.prediction === 'ATTACK' ? 'attack' : 'benign'));
  container.append(node('p',`Attack probability: ${percent(result.attack_probability)}`));
  const meter = node('div','','meter'), fill = node('span',''); fill.style.width = percent(result.attack_probability); meter.append(fill); container.append(meter);
  container.append(node('p',result.attack_type ? `Predicted type: ${cleanLabel(result.attack_type)} · type confidence ${percent(result.attack_confidence)}` : 'Stage 2 is skipped because this flow was predicted benign.'));
}
function shapView(container, result) {
  container.replaceChildren();
  if(!result.shap?.length) { container.append(node('p', 'An explanation is unavailable for this prediction.')); return; }
  const max = Math.max(...result.shap.map(item=>Math.abs(item.shap_value)),1e-12);
  for(const item of result.shap) {
    const positive = item.shap_value >= 0, row = node('div','','shap-row'), heading = node('div','','shap-heading');
    heading.append(node('strong',item.feature),node('span',`${positive ? '+' : '−'}${(Math.abs(item.shap_value)*100).toFixed(2)} percentage points`,positive?'attack':'benign'));
    row.append(heading,node('p',`Measured value: ${number(item.feature_value)} · ${item.meaning}`));
    const bar = node('div','','shap-bar'), fill=node('span','',positive?'attack':'benign'); fill.style.width = `${Math.abs(item.shap_value)/max*100}%`; bar.append(fill); row.append(bar);
    row.append(node('p',`This measurement ${positive?'increased':'decreased'} the model's attack probability relative to its baseline, alongside the other features.`)); container.append(row);
  }
}
async function chooseGuess(value) {
  await action(async () => {
    message('Computing the model decision and explanation…');
    const response = await api('/api/analyse',{id:currentCase.id});
    guess = value; original = response.result;
    document.querySelectorAll('[data-guess]').forEach(button => button.classList.toggle('selected',button.dataset.guess===value));
    $('model-title').textContent = 'Here is what the model thinks.';
    $('guess-note').textContent = `Your hypothesis: ${value === 'UNSURE' ? 'unsure' : value.toLowerCase()}. Model prediction: ${original.prediction.toLowerCase()}.`;
    resultView($('original-result'),original); shapView($('shap'),original);
    $('baseline').textContent = original.shap_base_value == null ? '' : `Baseline attack probability: ${percent(original.shap_base_value)} → predicted probability: ${percent(original.attack_probability)}. The ten contributions shown are a subset; all 65 sum to the full change.`;
    const threat = original.threat_analysis; $('guidance').hidden = !threat;
    if(threat) { $('threat-description').textContent = `${threat.severity} severity · ${threat.description}`; $('mitigation').replaceChildren(...(threat.mitigation || []).map(text=>node('li',text))); }
    ['model-section','experiment-section','truth-section'].forEach(id=>$(id).hidden=false);
    mark(2); message('Now try a timing experiment, or reveal the original dataset label.'); $('model-section').scrollIntoView({behavior:'smooth',block:'start'});
  });
}
function preview() {
  if(!currentCase) return;
  const factor = Number($('factor').value), flow = currentCase.flow; $('preview').replaceChildren();
  fact($('preview'),'Simulated duration',`${number(flow['Flow Duration']*factor/1000)} ms`,`${factor}× original duration`);
  fact($('preview'),'Simulated packet rate',`${number(flow['Flow Packets/s']/factor)}/s`,'Rate adjusted with duration');
  fact($('preview'),'Packet counts','Unchanged','Same packets and bytes');
}
$('new-case').addEventListener('click',nextCase);
document.querySelectorAll('[data-guess]').forEach(button=>button.addEventListener('click',()=>chooseGuess(button.dataset.guess)));
$('factor').addEventListener('change',()=>{preview(); $('comparison').hidden=true;});
$('experiment').addEventListener('click',()=>action(async()=>{
  message('Reanalysing the simulated measurements…');
  const response=await api('/api/analyse',{id:currentCase.id,factor:Number($('factor').value)});
  resultView($('compare-original'),original); resultView($('compare-modified'),response.result);
  const delta = (response.result.attack_probability-original.attack_probability)*100;
  $('delta').textContent = `Attack probability changed by ${delta>=0?'+':''}${delta.toFixed(2)} percentage points. ${original.prediction===response.result.prediction?'The verdict stayed the same.':'The verdict changed.'} ${response.simulated?'This result describes a simulated feature record.':'Original timing was selected, so no measurements changed.'}`;
  $('changes').replaceChildren(); for(const change of response.changes) { const row=node('tr','');row.append(node('td',change.feature),node('td',number(change.before)),node('td',number(change.after)));$('changes').append(row); }
  shapView($('experiment-shap'),response.result); $('comparison').hidden=false; mark(3); message('Compare the probabilities and explanations. A change does not have to flip the verdict.');
}));
$('reveal').addEventListener('click',()=>action(async()=>{
  const truth=await api('/api/reveal',{id:currentCase.id});
  const correct = truth.binary_label === original.prediction;
  $('truth').replaceChildren(node('h3',`Dataset label: ${cleanLabel(truth.label)}`),node('p',guess==='UNSURE'?'You chose unsure.':`Your hypothesis was ${guess===truth.binary_label?'correct':'incorrect'} for the original flow.`),node('p',`The model was ${correct?'correct':'incorrect'} on this original record. ${correct?'':truth.binary_label==='ATTACK'?'This is a missed attack (false negative).':'This is a false alert (false positive).'}`),node('p','A dataset label is the reference answer for this recorded case. It does not validate modified traffic or establish overall model accuracy.'));
  mark(4); message('Investigation complete. Open another case to explore a different record.');
}));
nextCase();
