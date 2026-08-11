// Загружаем список проектов
fetch('projects.json')
    .then(response => {
        if (!response.ok) {
            throw new Error('projects.json не найден');
        }
        return response.json();
    })
    .then(projects => {
        const container = document.getElementById('projects-container');
        container.innerHTML = ''; // Очищаем loading
        
        if (projects.length === 0) {
            container.innerHTML = `
                <div class="no-projects">
                    <h2>🚀 Первый проект скоро появится!</h2>
                    <p style="margin-top: 20px; font-size: 0.9em; opacity: 0.8;">
                        Каждый великий путь начинается с первого шага...
                    </p>
                </div>
            `;
            return;
        }
        
        // Создаём карточки проектов
        projects.forEach((project, index) => {
            const card = createProjectCard(project, index);
            container.appendChild(card);
        });
        
        // Анимация появления карточек
        animateCards();
    })
    .catch(error => {
        console.error('Ошибка загрузки проектов:', error);
        const container = document.getElementById('projects-container');
        container.innerHTML = `
            <div class="error">
                <h2>⚠️ Проекты временно недоступны</h2>
                <p style="margin-top: 20px; font-size: 0.9em;">
                    Попробуйте обновить страницу
                </p>
            </div>
        `;
    });

function createProjectCard(project, index) {
    const card = document.createElement('div');
    card.className = 'project-card';
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';
    
    // Создаём теги если они есть
    let tagsHTML = '';
    if (project.tags && project.tags.length > 0) {
        tagsHTML = '<div class="project-tags">';
        project.tags.forEach(tag => {
            tagsHTML += `<span class="tag">${tag}</span>`;
        });
        tagsHTML += '</div>';
    }
    
    // Форматируем дату
    let dateHTML = '';
    if (project.date) {
        const date = new Date(project.date);
        const formattedDate = date.toLocaleDateString('ru-RU', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        dateHTML = `<p style="font-size: 0.9em; color: #999; margin-bottom: 15px;">📅 ${formattedDate}</p>`;
    }
    
    card.innerHTML = `
        <div class="project-image">
            <img src="${encodeURI(project.image)}"
                 alt="${project.title}"
                 onerror="this.src='https://via.placeholder.com/400x300/667eea/ffffff?text=${encodeURIComponent(project.title)}'">
        </div>
        <div class="project-content">
            <h3>${project.title}</h3>
            ${dateHTML}
            <p>${project.description}</p>
            ${tagsHTML}
            <a href="${encodeURI(project.link)}" class="project-link">Открыть проект →</a>
        </div>
    `;
    
    return card;
}

function animateCards() {
    const cards = document.querySelectorAll('.project-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.transition = 'all 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 150);
    });
}

// Добавляем плавную прокрутку
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
