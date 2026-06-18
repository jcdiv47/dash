-- <query inspect_mall_store_columns>
-- <description>Inspect available columns for the copied mall and store tables.</description>
-- <query>
SELECT
    table_schema,
    table_name,
    ordinal_position,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('malls', 'stores')
ORDER BY table_name, ordinal_position;
-- </query>

-- <query count_malls>
-- <description>Count mall records in the copied public table.</description>
-- <query>
SELECT COUNT(*) AS mall_count
FROM public.malls;
-- </query>

-- <query count_stores>
-- <description>Count store records in the copied public table.</description>
-- <query>
SELECT COUNT(*) AS store_count
FROM public.stores;
-- </query>

-- <query top_malls_by_store_count>
-- <description>Top malls by number of imported store records.</description>
-- <query>
SELECT
    m.id AS mall_id,
    m.name AS mall_name,
    m.city,
    m.province,
    COUNT(*) AS store_count
FROM public.stores s
JOIN public.malls m ON m.id = s.mall_id
GROUP BY m.id, m.name, m.city, m.province
ORDER BY store_count DESC
LIMIT 20;
-- </query>

-- <query store_count_by_category>
-- <description>Store count by English and Chinese category.</description>
-- <query>
SELECT
    category,
    category_cn,
    COUNT(*) AS store_count
FROM public.stores
GROUP BY category, category_cn
ORDER BY store_count DESC;
-- </query>

-- <query mall_count_by_city>
-- <description>Mall count by city and province.</description>
-- <query>
SELECT
    province,
    city,
    COUNT(*) AS mall_count
FROM public.malls
GROUP BY province, city
ORDER BY mall_count DESC;
-- </query>

-- <query store_coverage>
-- <description>Compare total malls with malls represented by at least one store.</description>
-- <query>
SELECT
    COUNT(*) AS total_malls,
    COUNT(*) FILTER (WHERE store_counts.store_count > 0) AS malls_with_stores,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE store_counts.store_count > 0) / NULLIF(COUNT(*), 0),
        2
    ) AS pct_malls_with_stores
FROM public.malls m
LEFT JOIN (
    SELECT mall_id, COUNT(*) AS store_count
    FROM public.stores
    GROUP BY mall_id
) store_counts ON store_counts.mall_id = m.id;
-- </query>

-- <query sample_malls>
-- <description>Preview mall rows after confirming the table exists.</description>
-- <query>
SELECT *
FROM public.malls
LIMIT 20;
-- </query>

-- <query sample_stores>
-- <description>Preview store rows after confirming the table exists.</description>
-- <query>
SELECT *
FROM public.stores
LIMIT 20;
-- </query>

-- <query list_public_dash_objects>
-- <description>List public source objects and dash derived objects visible to Dash.</description>
-- <query>
SELECT
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema IN ('public', 'dash')
ORDER BY table_schema, table_name;
-- </query>
