"""Add country/currency to WaterBrand, rename price_rub to price, dedupe brands

Revision ID: a7989a3058b6
Revises: f35af883eaba
Create Date: 2026-08-16 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7989a3058b6'
down_revision = 'f35af883eaba'
branch_labels = None
depends_on = None


# slug -> (country, currency, цена в этой валюте). Заполняет country/currency
# и переводит price_rub в цену в национальной валюте для строк, уже
# существующих на проде (seed.py их не трогает, он добавляет только новые
# slug'и) — те же значения, что теперь лежат в data/water_brands.csv.
_BACKFILL = {
    '3-rodnika-davr-shiringi': ('Узбекистан', 'UZS', 44136.0),
    'a-su-asu': ('Казахстан', 'KZT', 388.0),
    'adel-premium-water': ('Узбекистан', 'UZS', 7335.0),
    'agat-water-agat-system': ('Узбекистан', 'UZS', 4841.0),
    'akvadiva-aquadiva': ('Беларусь', 'BYN', 7.83),
    'alatau-alatau': ('Казахстан', 'KZT', 285.0),
    'alkimyogar-farm-hayot': ('Узбекистан', 'UZS', 7954.0),
    'aqua-minerale': ('Россия', 'RUB', 70.0),
    'aqualife-aquaminerale': ('Узбекистан', 'UZS', 5761.0),
    'aqvalife-denau-brightly-mega': ('Узбекистан', 'UZS', 3652.0),
    'areni-areni': ('Армения', 'AMD', 533.0),
    'arhyz': ('Россия', 'RUB', 136.0),
    'arzni-arzni': ('Армения', 'AMD', 707.0),
    'asyl-suv': ('Казахстан', 'KZT', 1592.0),
    'baikal-5-ozer': ('Россия', 'RUB', 110.0),
    'baikal-reserve': ('Россия', 'RUB', 107.0),
    'baikozha': ('Казахстан', 'KZT', 527.0),
    'bakhmaro-bahmaro': ('Грузия', 'GEL', 3.55),
    'balgari-baikal-pearl-zhemchuzhina-baykala': ('Россия', 'RUB', 220.0),
    'baykal-trading': ('Узбекистан', 'UZS', 4853.0),
    'billur-suv-servis-serebryanaya-kaplya': ('Узбекистан', 'UZS', 5245.0),
    'bjni-bzhni': ('Армения', 'AMD', 561.0),
    'bkul-aqua-purissima': ('Молдова', 'MDL', 24.0),
    'bonaqua': ('Россия', 'RUB', 55.0),
    'bonaqua-bonaqua-belarus': ('Беларусь', 'BYN', 2.12),
    'bonaqua-coca-cola-ichimligi': ('Узбекистан', 'UZS', 4675.0),
    'borjomi': ('Грузия', 'GEL', 4.17),
    'borovaya': ('Беларусь', 'BYN', 3.71),
    'brilliant-water-brilliant-products': ('Узбекистан', 'UZS', 10548.0),
    'c-inari': ('Молдова', 'MDL', 25.0),
    'cascade-ararat': ('Армения', 'AMD', 429.0),
    'chernogolovskaya-ochakovskaya': ('Россия', 'RUB', 157.0),
    'chimgan-water': ('Узбекистан', 'UZS', 3821.0),
    'chortoq-chortoq-mineral-water': ('Узбекистан', 'UZS', 7060.0),
    'crystal-ice-shabnam-silver': ('Узбекистан', 'UZS', 4558.0),
    'crystal-spring-kristall': ('Казахстан', 'KZT', 547.0),
    'darida': ('Беларусь', 'BYN', 2.83),
    'darida-mineralnaya': ('Беларусь', 'BYN', 2.27),
    'dilijan-dilizhan': ('Армения', 'AMD', 676.0),
    'dr-water-voolav-team': ('Узбекистан', 'UZS', 4106.0),
    'essentuki-4': ('Россия', 'RUB', 90.0),
    'evian': ('Франция', 'EUR', 1.99),
    'family-water-family-group': ('Узбекистан', 'UZS', 5550.0),
    'ferette-ferette-bottlers': ('Узбекистан', 'UZS', 22136.0),
    'fosso-aquadidi': ('Узбекистан', 'UZS', 3754.0),
    'fresco-samarkand-pulsar': ('Узбекистан', 'UZS', 5648.0),
    'frost-frost': ('Беларусь', 'BYN', 3.38),
    'garni-garni': ('Армения', 'AMD', 327.0),
    'gornaya-vershina': ('Россия', 'RUB', 91.0),
    'gura-c-inarului': ('Молдова', 'MDL', 29.0),
    'halyk-halyk': ('Казахстан', 'KZT', 222.0),
    'hayot-ozon-tehnologiyalari': ('Узбекистан', 'UZS', 5197.0),
    'hydrolife-hydrolife-bottlers': ('Узбекистан', 'UZS', 46946.0),
    'ideal-water': ('Узбекистан', 'UZS', 4440.0),
    'jermuk-dzhermuk': ('Армения', 'AMD', 504.0),
    'kalinov-drodnik-kalinovaya': ('Россия', 'RUB', 109.0),
    'kobi-kobi': ('Грузия', 'GEL', 4.6),
    'kokshetau-kokshetau': ('Казахстан', 'KZT', 339.0),
    'kulan-kulan': ('Казахстан', 'KZT', 388.0),
    'la-vista-bottlers': ('Узбекистан', 'UZS', 3916.0),
    'lipetskiy-byuvet': ('Россия', 'RUB', 104.0),
    'lisi-lisi': ('Грузия', 'GEL', 3.06),
    'magic-magic-texno': ('Узбекистан', 'UZS', 5864.0),
    'minarka-minskaya': ('Беларусь', 'BYN', 3.57),
    'mitbi': ('Грузия', 'GEL', 2.06),
    'monastyrskaya': ('Беларусь', 'BYN', 3.96),
    'mone-water-h2o-halal': ('Узбекистан', 'UZS', 4432.0),
    'nabeglavi-nabeglavi': ('Грузия', 'GEL', 4.25),
    'narzan': ('Россия', 'RUB', 85.0),
    'nestl-uzbekistan': ('Узбекистан', 'UZS', 4194.0),
    'nistru-dnestr': ('Молдова', 'MDL', 12.0),
    'om-om': ('Молдова', 'MDL', 26.0),
    'omskaya-sibirskaya-palitra': ('Россия', 'RUB', 342.0),
    'palats-palats': ('Беларусь', 'BYN', 1.58),
    'piligrim-kubay': ('Россия', 'RUB', 146.0),
    'protasovskaya': ('Беларусь', 'BYN', 2.99),
    'psyl-rysyl': ('Казахстан', 'KZT', 459.0),
    'rusola-nastoyaschaya-voda': ('Россия', 'RUB', 116.0),
    'rychal-su': ('Россия', 'RUB', 123.0),
    'sairme-sairme': ('Грузия', 'GEL', 2.6),
    'san-pellegrino': ('Италия', 'EUR', 4.03),
    'saryagash-saryagash': ('Казахстан', 'KZT', 399.0),
    'senezhskaya': ('Россия', 'RUB', 52.0),
    'seti-vendingovyh-vodomatov': ('Узбекистан', 'UZS', 4726.0),
    'sevan-sevan': ('Армения', 'AMD', 684.0),
    'shishkin-les': ('Россия', 'RUB', 60.0),
    'silver-spring-serebryanyy-klyuch': ('Беларусь', 'BYN', 2.08),
    'silverwater-silver-vita': ('Узбекистан', 'UZS', 3755.0),
    'sno-sno': ('Грузия', 'GEL', 2.91),
    'svyatochnik': ('Беларусь', 'BYN', 3.5),
    'svyatoy-istochnik': ('Россия', 'RUB', 65.0),
    'tamshy-tamshy': ('Казахстан', 'KZT', 195.0),
    'tassay-tasay': ('Казахстан', 'KZT', 918.0),
    'turan-turan': ('Казахстан', 'KZT', 306.0),
    'uvildy-serebryanyy-klyuch': ('Россия', 'RUB', 88.0),
    'v-u-varzaleu-bucovina': ('Молдова', 'MDL', 39.0),
    'veva-water': ('Узбекистан', 'UZS', 5671.0),
    'voda-kz-gornaya': ('Казахстан', 'KZT', 175.0),
    'volzhanka': ('Россия', 'RUB', 178.0),
    'zoltaya-kolodets-f-nt-na-z-olna': ('Молдова', 'MDL', 12.0),
}

# Пять брендов оказались задвоены: один и тот же бренд (Святой Источник,
# Бонаква, Ессентуки, Aqua Minerale, Шишкин Лес) уже был в каталоге и попал
# туда повторно из справочника СНГ под слегка другим написанием имени.
# Удаляем дубликаты, а исходную запись обогащаем более подробным
# происхождением/описанием из дубликата перед его удалением.
_DUPLICATE_SLUGS = ('akva-minerale-aqua-minerale', 'bonaqua-2', 'essentuki-4-17', 'shishkin-les-2', 'svyatoy-istochnik-2')

_ENRICH = {
    'aqua-minerale': ('PepsiCo / Подмосковье и регионы, Россия', 'Питьевая очищенная вода — Один из лидеров федеральной розницы и вендинга.'),
    'bonaqua': ('Coca-Cola / Мултон Партнерс, Россия', 'Питьевая вода (газ./негаз.) — Широчайшая дистрибуция во всех торговых сетях страны.'),
    'essentuki-4': ('Холдинг «МВК» / Кавказские Минеральные Воды, Россия', 'Лечебно-столовая минеральная вода — Легендарные минеральные воды с уникальным солевым составом.'),
    'shishkin-les': ('ООО «Шишкин Лес» / Подмосковье, Россия', 'Питьевая и артезианская вода — Популярная марка с собственным крупным сервисом доставки и розницей.'),
    'svyatoy-istochnik': ('IDS Borjomi Russia / Кострома, Липецк, Россия', 'Артезианская питьевая вода (0.5–5 л, 19 л) — Самый массовый и узнаваемый бренд питьевой воды в России.'),
}


def upgrade():
    with op.batch_alter_table('water_brands', schema=None) as batch_op:
        batch_op.add_column(sa.Column('currency', sa.String(length=8), nullable=False, server_default='RUB'))
        batch_op.add_column(sa.Column('country', sa.String(length=120), nullable=True))
        batch_op.alter_column('price_rub', new_column_name='price', existing_type=sa.Numeric(10, 2))

    connection = op.get_bind()
    water_brands = sa.table(
        "water_brands",
        sa.column("slug", sa.String),
        sa.column("country", sa.String),
        sa.column("currency", sa.String),
        sa.column("price", sa.Numeric),
        sa.column("origin", sa.String),
        sa.column("description", sa.Text),
    )

    for slug, (country, currency, price) in _BACKFILL.items():
        connection.execute(
            water_brands.update()
            .where(water_brands.c.slug == slug)
            .values(country=country, currency=currency, price=price)
        )

    for slug, (origin, description) in _ENRICH.items():
        connection.execute(
            water_brands.update()
            .where(water_brands.c.slug == slug)
            .values(origin=origin, description=description)
        )

    for slug in _DUPLICATE_SLUGS:
        connection.execute(water_brands.delete().where(water_brands.c.slug == slug))

    with op.batch_alter_table('water_brands', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_water_brands_country'), ['country'], unique=False)


def downgrade():
    with op.batch_alter_table('water_brands', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_water_brands_country'))
        batch_op.alter_column('price', new_column_name='price_rub', existing_type=sa.Numeric(10, 2))
        batch_op.drop_column('country')
        batch_op.drop_column('currency')
