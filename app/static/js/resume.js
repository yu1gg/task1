(() => {
  'use strict';
  const form = document.getElementById('resume-editor');
  if (!form) return;
  const initial = JSON.parse(document.getElementById('resume-initial').textContent);
  const source = initial && typeof initial === 'object' ? initial : {};
  let dirty = JSON.parse(document.getElementById('resume-has-error').textContent);
  const fields = document.getElementById('resume-fields');
  const groups = [
    ['education', '教育经历', 3, [['school','学校'],['major','专业'],['degree','学历'],['period','时间']]],
    ['skills','专业技能',12,[['name','技能'],['evidence','事实证据']]],
    ['projects','项目经历',3,[['name','项目名称'],['role','角色'],['period','时间'],['bullets','描述（每行一条，最多3条，每条60字）']]],
    ['internships','实习经历',3,[['company','公司'],['role','角色'],['period','时间'],['bullets','描述（每行一条，最多3条，每条60字）']]],
    ['awards','获奖情况',5,[['value','奖项']]],
  ];
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  let nextId = 0;
  function input(parent, key, label, value, limit, multiline=false) {
    const wrap = node('div', undefined, 'mb-2');
    const id = `resume-field-${++nextId}`;
    const lab = node('label', label, 'form-label'); lab.htmlFor = id;
    const el = node(multiline ? 'textarea' : 'input', undefined, 'form-control');
    el.id = id; el.dataset.field = key;
    if (limit) el.maxLength = limit;
    el.value = typeof value === 'string' ? value : '';
    if (multiline) el.rows = 3;
    wrap.append(lab, el); parent.append(wrap);
    return el;
  }
  for (const [key,label,max] of [['name','姓名',64],['phone','电话',40],['email','邮箱',120],['target_job','求职意向',120],['summary','个人简介（最多120字）',120]]) {
    const el = input(fields,key,label,source[key],max,key==='summary');
    el.dataset.scalar = 'true';
    if (key==='name') el.required = true;
  }
  function addEntry(container, key, specs, entry={}) {
    const box = node('div', undefined, 'border rounded p-2 mb-2'); box.dataset.entry = 'true';
    for (const [field,label] of specs) {
      const value = key==='awards' ? entry : field==='bullets' && Array.isArray(entry[field]) ? entry[field].join('\n') : entry[field];
      input(box,field,label,value,field==='bullets' ? 1000 : 120,field==='bullets');
    }
    const remove = node('button','移除此项','btn btn-sm btn-outline-danger'); remove.type='button';
    remove.addEventListener('click', () => {box.remove(); changed();});
    box.append(remove); container.append(box);
  }
  for (const [key,label,max,specs] of groups) {
    const section=node('section',undefined,'my-3'); section.append(node('h2',label,'h6'));
    const entries=node('div'); entries.dataset.group=key;
    for(const entry of Array.isArray(source[key]) ? source[key] : []) addEntry(entries,key,specs,entry);
    const add=node('button',`添加${label}（最多${max}项）`,'btn btn-sm btn-outline-primary'); add.type='button';
    add.addEventListener('click',()=>{
      if(entries.children.length>=max) { document.getElementById('save-status').textContent=`${label}最多${max}项`; return; }
      addEntry(entries,key,specs,key==='awards'?'':{}); changed();
    });
    section.append(entries,add); fields.append(section);
  }
  function collect() {
    const data={};
    fields.querySelectorAll('[data-scalar]').forEach(el=>data[el.dataset.field]=el.value.trim());
    for(const [key] of groups) {
      data[key]=[];
      fields.querySelector(`[data-group="${key}"]`).querySelectorAll('[data-entry]').forEach(box=>{
        const entry={}; box.querySelectorAll('[data-field]').forEach(el=>entry[el.dataset.field]=el.dataset.field==='bullets' ? el.value.split('\n').map(v=>v.trim()).filter(Boolean) : el.value.trim());
        if(Object.values(entry).some(v=>Array.isArray(v)?v.length:v)) data[key].push(key==='awards'?entry.value:entry);
      });
    }
    return data;
  }
  function count(value) {
    if(typeof value==='string') return Array.from(value).length;
    if(Array.isArray(value)) return value.reduce((a,v)=>a+count(v),0);
    return Object.values(value).reduce((a,v)=>a+count(v),0);
  }
  function preview(data) {
    const paper=document.getElementById('resume-preview'); paper.replaceChildren();
    const header=node('header',undefined,'resume-header'); header.append(node('h1',data.name),node('p',[data.phone,data.email].filter(Boolean).join(' · ')));
    if(data.target_job) header.append(node('p',`求职意向：${data.target_job}`)); paper.append(header);
    const section=(label)=>{const s=node('section'); s.append(node('h2',label));paper.append(s);return s;};
    if(data.summary) section('个人简介').append(node('p',data.summary));
    for(const [key,label] of groups) {
      if(!data[key].length) continue;
      const s=section(label);
      for(const e of data[key]) {
        const box=node('div',undefined,'resume-entry');
        if(key==='awards') box.append(node('p',`• ${e}`));
        else if(key==='skills') box.append(node('p',`• ${e.name}${e.evidence?'：'+e.evidence:''}`));
        else {
          const p=node('p');p.append(node('strong',e.school||e.name||e.company||''));
          p.append(document.createTextNode(' · '+[e.major,e.degree,e.role].filter(Boolean).join(' · ')+' ')); p.append(node('span',e.period));box.append(p);
          if(e.bullets){const ul=node('ul');e.bullets.forEach(v=>ul.append(node('li',v)));box.append(ul);}
        }
        s.append(box);
      }
    }
    const n=count(data);
    const overHeight=paper.scrollHeight>1515;
    document.getElementById('length-status').textContent=`正文 ${n}/1200 字。${n>1200?'超出字数限制，请精简。':''}${overHeight?'排版可能超过1.5页，请精简并核对打印预览。':''}`;
    return n;
  }
  function changed(){dirty=true; preview(collect());document.getElementById('save-status').textContent='有未保存修改，请先保存再打印或下载。';}
  form.addEventListener('input',changed);
  form.addEventListener('submit',e=>{
    const data=collect();
    if(preview(data)>1200){e.preventDefault();return;}
    document.getElementById('content-json').value=JSON.stringify(data);
    dirty=false;
  });
  document.querySelectorAll('.saved-action').forEach(el=>el.addEventListener('click',e=>{if(dirty){e.preventDefault();document.getElementById('save-status').textContent='请先保存当前修改，再打印或下载。';}}));
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  const paper=document.getElementById('resume-preview');
  const fitPreview=()=>{paper.style.zoom=Math.min(1,paper.parentElement.clientWidth/paper.offsetWidth);};
  new ResizeObserver(fitPreview).observe(paper.parentElement);
  fitPreview();
  document.fonts.ready.then(()=>preview(collect()));
})();
