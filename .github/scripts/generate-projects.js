const fs = require('fs');
const path = require('path');

console.log('🔍 Начинаю сканирование проектов...');

const projectsDir = './projects';
const projects = [];

if (!fs.existsSync(projectsDir)) {
    console.log('📁 Папка projects не найдена, создаю...');
    fs.mkdirSync(projectsDir, { recursive: true });
}

const folders = fs.readdirSync(projectsDir).filter(file => {
    const fullPath = path.join(projectsDir, file);
    return fs.statSync(fullPath).isDirectory();
});

console.log(`📂 Найдено папок: ${folders.length}`);

folders.forEach(folder => {
    const projectPath = path.join(projectsDir, folder);
    const infoPath = path.join(projectPath, 'info.json');
    const indexPath = path.join(projectPath, 'index.html');
    
    if (!fs.existsSync(indexPath)) {
        console.log(`⚠️  Пропускаю ${folder} - нет index.html`);
        return;
    }
    
    let projectInfo;
    
    if (fs.existsSync(infoPath)) {
        try {
            projectInfo = JSON.parse(fs.readFileSync(infoPath, 'utf8'));
            console.log(`✅ ${folder} - загружен из info.json`);
        } catch (error) {
            console.log(`❌ Ошибка чтения info.json в ${folder}: ${error.message}`);
            return;
        }
    } else {
        console.log(`ℹ️  ${folder} - создаю базовую информацию`);
        projectInfo = {
            title: folder.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            description: 'Описание проекта скоро появится',
            date: new Date().toISOString().split('T')[0]
        };
    }
    
    let imagePath = 'https://via.placeholder.com/400x300/667eea/ffffff?text=' + 
                    encodeURIComponent(projectInfo.title || folder);
    
    const possibleImages = ['preview.jpg', 'preview.png', 'preview.gif', 'preview.webp', 
                           'thumb.jpg', 'thumb.png', 'thumbnail.jpg', 'thumbnail.png'];
    
    for (const img of possibleImages) {
        const imgPath = path.join(projectPath, img);
        if (fs.existsSync(imgPath)) {
            imagePath = `projects/${folder}/${img}`;
            break;
        }
    }
    
    if (projectInfo.image) {
        imagePath = `projects/${folder}/${projectInfo.image}`;
    }
    
    const project = {
        id: folder,
        title: projectInfo.title || folder,
        description: projectInfo.description || 'Описание проекта',
        image: imagePath,
        link: `projects/${folder}/index.html`,
        date: projectInfo.date || new Date().toISOString().split('T')[0],
        tags: projectInfo.tags || []
    };
    
    projects.push(project);
});

projects.sort((a, b) => new Date(b.date) - new Date(a.date));

const outputPath = './projects.json';
fs.writeFileSync(outputPath, JSON.stringify(projects, null, 2));

console.log('\n✨ Результат:');
console.log(`📊 Сгенерировано проектов: ${projects.length}`);
console.log(`💾 Файл сохранён: ${outputPath}`);

if (projects.length > 0) {
    console.log('\n📋 Список проектов:');
    projects.forEach((p, i) => {
        console.log(`   ${i + 1}. ${p.title} (${p.date})`);
    });
}
