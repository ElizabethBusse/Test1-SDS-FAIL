// scrape_pubchem_ghs_annex1.js
const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('https://pubchem.ncbi.nlm.nih.gov/ghs/', {waitUntil: 'networkidle2'});
  await new Promise(resolve => setTimeout(resolve, 3000));

  const data = await page.evaluate(() => {
    const sections = [...document.querySelectorAll('h2')];
    const result = {};

    sections.forEach(h2 => {
      const key = h2.innerText.trim();
      const table = h2.nextElementSibling;
      if (table && table.tagName === 'TABLE') {
        const headers = [...table.querySelectorAll('thead tr th')].map(th => th.innerText.trim());
        const rows = [...table.querySelectorAll('tbody tr')].map(tr => {
          const cells = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
          return headers.reduce((acc, h, i) => { acc[h] = cells[i]; return acc; }, {});
        });
        result[key] = rows;
      }
    });

    return result;
  });

  fs.writeFileSync('ghs_annex1_pubchem.json', JSON.stringify(data, null, 2));
  console.log('✅ Saved as ghs_annex1_pubchem.json');
  await browser.close();
})();