#!/usr/bin/env node
/**
 * Серверный скрипт для генерации Word-отчетов (Node.js)
 * 
 * Использование:
 * 1. Установите зависимости: npm install docx fs
 * 2. Запустите: node server-docx-generator.js
 * 
 * Этот скрипт демонстрирует генерацию Word-отчета на сервере.
 * В веб-приложении генерация происходит в браузере через docx CDN.
 */

const { Document, Packer, Paragraph, TextRun, AlignmentType } = require('docx');
const fs = require('fs');

// Пример данных расчета
const exampleData = {
    machine: '6Р81',
    N_st: 5.5,
    cutterType: 'Торцовые',
    toolMaterial: 'Быстрорежущая сталь Р6М5',
    operation: 'Фрезерование плоскостей',
    t: 4,
    Sz: 0.3,
    T: 150,
    D: 160,
    z: 18,
    B: 2,
    Cv: 41,
    q: 0.25,
    x: 0.1,
    y: 0.4,
    u: 0.15,
    p: 0,
    m: 0.2,
    Kv: 0.8,
    V: 35.42,
    n_calc: 70.5,
    n_accepted: 80,
    Vf: 40.21,
    Sm: 432,
    Sz_fact: 0.3,
    Cp: 82.5,
    x_p: 0.95,
    y_p: 0.8,
    u_p: 1.1,
    q_p: 1.1,
    w_p: 0,
    Kp: 1.0,
    Pz: 1250.5,
    N_rez: 0.822,
    N_trebuemaya: 1.028,
    eta: 0.8,
    powerCheck: true,
    l: 100,
    l1: 5,
    l2: 5,
    L_total: 110,
    To: 0.255
};

function generateWordReport(data) {
    const r = data;

    const doc = new Document({
        sections: [{
            properties: {
                page: {
                    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
                }
            },
            children: [
                // Заголовок
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    spacing: { after: 200 },
                    children: [
                        new TextRun({
                            text: "РАСЧЕТ РЕЖИМОВ РЕЗАНИЯ ПРИ ФРЕЗЕРОВАНИИ",
                            bold: true,
                            size: 28
                        })
                    ]
                }),

                // Оборудование
                new Paragraph({
                    spacing: { before: 200, after: 100 },
                    children: [
                        new TextRun({ text: "Оборудование – ", bold: true }),
                        new TextRun(`${r.machine}  Nст=${r.N_st} кВт`)
                    ]
                }),

                // Режущий инструмент
                new Paragraph({
                    spacing: { after: 100 },
                    children: [
                        new TextRun({ text: "Режущий инструмент – ", bold: true }),
                        new TextRun(`${r.cutterType}, ${r.toolMaterial}`)
                    ]
                }),

                // Операция
                new Paragraph({
                    spacing: { after: 100 },
                    children: [
                        new TextRun({ text: "1-переход. ", bold: true }),
                        new TextRun(r.operation)
                    ]
                }),

                // Глубина резания
                new Paragraph({
                    spacing: { before: 200, after: 100 },
                    children: [
                        new TextRun({ text: "Глубина резания. ", bold: true }),
                        new TextRun(`t = ${r.t} мм`)
                    ]
                }),

                // Подача
                new Paragraph({
                    spacing: { after: 100 },
                    children: [
                        new TextRun({ text: "Подача. ", bold: true }),
                        new TextRun(`Sz = ${r.Sz} мм/зуб`)
                    ]
                }),

                new Paragraph({
                    spacing: { after: 200 },
                    children: [
                        new TextRun("В зависимости от диаметра обработки размера державки, обработываемого материала и глубины резания.")
                    ]
                }),

                // 3. Допустимая скорость резания
                new Paragraph({
                    spacing: { before: 200, after: 100 },
                    children: [
                        new TextRun({ text: "3. Допустимая скорость резания", bold: true, size: 24 })
                    ]
                }),

                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    spacing: { after: 100 },
                    children: [
                        new TextRun({ text: "V = Cv / (T^m × D^q × t^x × Sz^y × B^u × z^p) × Kv, м/мин", italics: true })
                    ]
                }),

                // Параметры
                new Paragraph({ children: [new TextRun(`T = ${r.T} мин – стойкость инструмента`)] }),
                new Paragraph({ children: [new TextRun(`D = ${r.D} мм,     z = ${r.z},     B = ${r.B} мм`)] }),
                
                // Коэффициенты
                new Paragraph({ spacing: { before: 100 }, children: [new TextRun(`Cv = ${r.Cv}`)] }),
                new Paragraph({ children: [new TextRun(`x = ${r.x}`)] }),
                new Paragraph({ children: [new TextRun(`y = ${r.y}`)] }),
                new Paragraph({ children: [new TextRun(`m = ${r.m}`)] }),
                new Paragraph({ children: [new TextRun(`p = ${r.p}`)] }),
                new Paragraph({ children: [new TextRun(`u = ${r.u}`)] }),
                new Paragraph({ children: [new TextRun(`q = ${r.q}`)] }),

                // Поправочные коэффициенты
                new Paragraph({
                    spacing: { before: 100, after: 50 },
                    children: [new TextRun({ text: "Kv – поправочный коэффициент.", bold: true })]
                }),
                new Paragraph({ children: [new TextRun(`Kv = ${r.Kv.toFixed(3)}`)] }),

                // Результат V
                new Paragraph({
                    spacing: { before: 100, after: 200 },
                    children: [
                        new TextRun({ text: `V = ${r.V.toFixed(2)} м/мин`, bold: true, size: 24 })
                    ]
                }),

                // 4. Расчеты числа оборудования
                new Paragraph({
                    spacing: { before: 200, after: 100 },
                    children: [
                        new TextRun({ text: "4. Расчет числа оборотов", bold: true, size: 24 })
                    ]
                }),

                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    spacing: { after: 100 },
                    children: [
                        new TextRun({ text: "n = (1000 × V) / (π × D), об/мин", italics: true })
                    ]
                }),

                new Paragraph({
                    spacing: { after: 200 },
                    children: [
                        new TextRun({ text: `n расч = ${r.n_calc.toFixed(1)} об/мин`, bold: true })
                    ]
                }),

                // Продолжение с остальными разделами...
                // (Здесь можно добавить остальные секции по аналогии)

                // Дата
                new Paragraph({
                    alignment: AlignmentType.RIGHT,
                    spacing: { before: 300 },
                    children: [
                        new TextRun({
                            text: `Дата расчета: ${new Date().toLocaleDateString('ru-RU')}`,
                            italics: true,
                            size: 20
                        })
                    ]
                })
            ]
        }]
    });

    return doc;
}

// Генерация и сохранение документа
console.log('🔄 Генерация Word-отчета...');

const doc = generateWordReport(exampleData);

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync('Режимы_резания_пример.docx', buffer);
    console.log('✅ Word-отчет успешно создан: Режимы_резания_пример.docx');
    console.log('📊 Размер файла:', (buffer.length / 1024).toFixed(2), 'KB');
}).catch(error => {
    console.error('❌ Ошибка при генерации отчета:', error);
});

module.exports = { generateWordReport };
