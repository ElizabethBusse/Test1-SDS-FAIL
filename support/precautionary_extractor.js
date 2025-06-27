// await new Promise(resolve => setTimeout(resolve, 3000));

const puppeteer = require('puppeteer');
const fs = require('fs');

async function scrapeChemsafetyPrecautions() {
  const url = 'https://www.chemsafetypro.com/Topics/GHS/GHS_Precautionary_Statement.html';
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(url, { waitUntil: 'networkidle2' });
  await new Promise(resolve => setTimeout(resolve, 3000));

  const statements = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("table tbody tr"));
    const results = [];

    for (const row of rows) {
      const cells = row.querySelectorAll("td");
      if (cells.length === 2) {
        const code = cells[0].innerText.trim();
        const phrase = cells[1].innerText.trim();
        results.push({ code, phrase });
      }
    }

    return results;
  });

  fs.writeFileSync("chemsafety_precautionary.json", JSON.stringify(statements, null, 2), "utf-8");
  console.log(`✅ Extracted ${statements.length} precautionary statements.`);
  await browser.close();
}

scrapeChemsafetyPrecautions();