// Генерирует sitemap.xml из уже готового projects.json — запускается сразу
// после generate-projects.js (см. .github/workflows/update-projects.yml),
// поэтому список проектов всегда синхронизирован автоматически, без
// ручного обновления при каждом новом проекте.
//
// Внешние проекты (Render и т.п., link начинается с http) в карту сайта не
// включаем — это не наш домен, свою карту сайта им туда класть незачем.
const fs = require('fs');

const SITE_URL = 'https://www.robutpit.com';

const projects = JSON.parse(fs.readFileSync('./projects.json', 'utf8'));

const urls = [
    { loc: `${SITE_URL}/`, changefreq: 'weekly', priority: '1.0' },
    ...projects
        .filter(p => !p.link.startsWith('http://') && !p.link.startsWith('https://'))
        .map(p => ({
            loc: `${SITE_URL}/${encodeURI(p.link)}`,
            changefreq: 'monthly',
            priority: '0.7',
        })),
];

const body = urls
    .map(u => `  <url><loc>${u.loc}</loc><changefreq>${u.changefreq}</changefreq><priority>${u.priority}</priority></url>`)
    .join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;

fs.writeFileSync('./sitemap.xml', xml);
console.log(`🗺️  sitemap.xml сгенерирован: ${urls.length} ссылок.`);
