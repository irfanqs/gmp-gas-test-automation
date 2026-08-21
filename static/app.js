let records = [];
const form = document.querySelector('#upload-form');
const statusBox = document.querySelector('#status');
const review = document.querySelector('#review');
const tableBox = document.querySelector('#table');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function renderTable() {
  if (!records.length) return;
  const columns = Object.keys(records[0]);
  tableBox.innerHTML = `<table><thead><tr>${columns.map(column => `<th>${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${records.map((row, index) => `<tr>${columns.map(column => `<td><input data-row="${index}" data-column="${escapeHtml(column)}" value="${escapeHtml(row[column])}"></td>`).join('')}</tr>`).join('')}</tbody></table>`;
  tableBox.querySelectorAll('input').forEach(input => input.addEventListener('input', event => {
    records[Number(event.target.dataset.row)][event.target.dataset.column] = event.target.value;
  }));
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.querySelector('#extract-button');
  button.disabled = true;
  statusBox.className = '';
  statusBox.textContent = 'Mengirim PDF ke DeepSeek-OCR dan membaca formulir...';
  try {
    const response = await fetch('/extract', { method:'POST', body:new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error([data.error, ...(data.details || [])].filter(Boolean).join('\n'));
    records = data.records;
    statusBox.className = 'ok';
    statusBox.textContent = `${records.length} baris berhasil diekstrak.${data.warnings.length ? `\nPeringatan:\n${data.warnings.join('\n')}` : ''}`;
    renderTable(); review.style.display = 'block';
  } catch (error) { statusBox.className = 'error'; statusBox.textContent = error.message; }
  finally { button.disabled = false; }
});

document.querySelector('#generate-button').addEventListener('click', async () => {
  const button = document.querySelector('#generate-button');
  button.disabled = true;
  try {
    const response = await fetch('/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({test_type:document.querySelector('#test_type').value, records}) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    document.querySelector('#downloads').innerHTML = `<a href="${data.excel_url}">Unduh Excel</a><a href="${data.pdf_url}">Unduh Grafik PDF</a>${data.charts.map(chart => `<a href="${chart.png_url}">Unduh ${escapeHtml(chart.label)} JPG</a>`).join('')}`;
  } catch (error) { statusBox.className = 'error'; statusBox.textContent = error.message; }
  finally { button.disabled = false; }
});
