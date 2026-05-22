-- 1. Справочные таблицы (словари)

-- Справочник муниципалитетов
CREATE TABLE municipalities (
    id_municipality SERIAL PRIMARY KEY,
    municipality TEXT NOT NULL UNIQUE
);

-- Справочник владельцев/застройщиков
CREATE TABLE developers_owners (
    id_developer_or_owner SERIAL PRIMARY KEY,
    developer_or_owner TEXT NOT NULL UNIQUE
);

-- Справочник источников данных
CREATE TABLE data_sources (
    id_data_source SERIAL PRIMARY KEY,
    data_source TEXT NOT NULL UNIQUE
);

-- Справочник глав муниципалитетов
CREATE TABLE heads_of_municipalities (
    id_head_of_municipality SERIAL PRIMARY KEY,
    head_of_municipality TEXT NOT NULL
);

-- 2. Основная таблица объектов

CREATE TABLE objects (
    id_issuda BIGSERIAL PRIMARY KEY,
    inventory_number BIGINT,
    map_connection_code BIGINT,
    peculiarities TEXT,
    object_name TEXT,
    category_main SMALLINT,
    category_sub SMALLINT,
    address TEXT,
    property_type TEXT,
    liquidation_method TEXT, 
    liquidation_period SMALLINT,
    are_problems BOOLEAN,
    problems TEXT,
    liquidation_stage SMALLINT,
    object_purpose TEXT, 
    object_nonresidential_purpose TEXT,
    type TEXT,
    land_cadastral_number TEXT[],
    geometry GEOMETRY(MULTIPOINT, 32637),
    building_cadastral_number TEXT[],
    information_note TEXT,
    is_uc BOOLEAN,
    is_socially_significant BOOLEAN,
    is_bp BOOLEAN,
    bp_details TEXT,
    is_legally_cadastral TEXT,
    construction_readiness TEXT,
    are_construction_works BOOLEAN,
    financing TEXT,
    converted_from_uc BOOLEAN,
    is_department_help_needed BOOLEAN,
    construction_stage TEXT,
    is_court_needed BOOLEAN,
    jobs_number SMALLINT,
    object_area NUMERIC,
    formation_date DATE,
    formation_full_name TEXT,
    change_full_name TEXT,
    
    -- Внешние ключи (связи со справочниками)
    id_municipality INTEGER REFERENCES municipalities(id_municipality),
    id_developer_or_owner INTEGER REFERENCES developers_owners(id_developer_or_owner),
    id_data_source INTEGER REFERENCES data_sources(id_data_source)
);

-- Таблица связи объект + владелец
CREATE TABLE object_owners (
    id_issuda BIGINT REFERENCES objects(id_issuda) ON DELETE CASCADE,
    id_developer_or_owner INTEGER REFERENCES developers_owners(id_developer_or_owner) ON DELETE CASCADE,
    PRIMARY KEY (id_issuda, id_developer_or_owner)
);

-- 3. Расширение: МКД (многоквартирные дома)

CREATE TABLE mkd_info (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    mhp_decision TEXT, 
    shareholders_number SMALLINT,
    is_new_developer TEXT, -- пересмотреть, там все намешано
    damaged_ab_resettlement TEXT -- пересмотреть, там все намешано
);

-- 4. Расширение: ОКН (объекты культурного наследия)

CREATE TABLE okn_info (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    cultural_heritage_category TEXT, -- enum
    cultural_heritage_decision BOOLEAN
);

-- 5. Расширение: Самовольные объекты

CREATE TABLE uc_info (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    uc_liquidation_method TEXT, 
    uc_type TEXT, 
    is_notification_from_mdscs_to_lg_needed BOOLEAN,
    is_notified_from_mdscs_to_lg BOOLEAN,
    is_cadastral BOOLEAN,
    object_detection_date DATE,
    object_detection_quarter_num SMALLINT,
    object_detection_quarter_year SMALLINT, 
    land_category TEXT,
    land_permitted_use_type TEXT,
    are_obligations_to_citizens BOOLEAN,
    obligations_to_citizens_number BOOLEAN,
    land_property_type TEXT,
    is_registered_as_property TEXT,
    is_registered_as_property_ws TEXT,
    is_bp_for_uc_required BOOLEAN,
    is_bp_for_uc_executed BOOLEAN,
    bp_details_uc TEXT,
    is_matches_with_bp BOOLEAN,
    is_matches_with_ludr_lupp BOOLEAN,
    uc_data_source TEXT,
    uc_ld_name TEXT,
    uc_gb_name TEXT,
    uc_data_source_details TEXT,
    to_lg_notification_details TEXT,
    from_lg_notification_details TEXT,
    uc_preliminary_decision TEXT,
    uc_decision_confirmed_by_lg BOOLEAN, 
    uc_mdscs_decision TEXT,
    uc_exclusion_reason TEXT,
    tdcs_number SMALLINT
);

-- 6. Исполнители

CREATE TABLE executors (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    ga_curator TEXT,
    department TEXT,
    department_curator TEXT,
    ta_executor TEXT,
    lg_executor TEXT,
    lg_executor_comment TEXT,
    lg_dh_curator TEXT,
    id_head_of_municipality INTEGER REFERENCES heads_of_municipalities(id_head_of_municipality),
    mrcc_curator TEXT
);

-- 7. Статус объекта

CREATE TABLE object_statuses (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    execution_deadline DATE,
    is_executed BOOLEAN,
    is_canceled BOOLEAN,
    is_object_status_active BOOLEAN,
    is_closing_needed BOOLEAN,
    execution_method TEXT,
    object_closing_period_num SMALLINT,
    object_closing_period_year SMALLINT,
    lg_comment TEXT,
    department_comment TEXT,
    final_resolution TEXT,
    lg_decision_consent BOOLEAN,
    lg_decision_comment TEXT,
    uc_planned_liquidation_method TEXT
);

-- 8. Чек-лист

CREATE TABLE checklists (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    is_easement BOOLEAN,
    is_land_for_develover BOOLEAN,
    is_zscut BOOLEAN,
    zscut_name TEXT,
    zscut_comment TEXT,
    is_matches_with_lput BOOLEAN,
    is_matches_with_mp_ludr BOOLEAN,
    lg_result_consent BOOLEAN,
    check_list_execution_deadline DATE
);

-- 9. Судебные процедуры

CREATE TABLE court_procedures (
    id_issuda BIGINT PRIMARY KEY REFERENCES objects(id_issuda),
    sue_quarter_num SMALLINT,
    sue_quarter_year SMALLINT,
    judicial_body TEXT,
    court_case_number TEXT,
    next_court_hearing_date DATE,
    is_examination_appointed BOOLEAN,
    is_examination_held BOOLEAN,
    is_court_decision_made BOOLEAN,
    is_court_decision_executed BOOLEAN,
    is_writ_of_execution_obtained BOOLEAN,
    is_enforcement_proceedings_on BOOLEAN,
    enforcement_proceedings_details TEXT,
    enforcement_proceedings_debtor TEXT,
    is_enforcement_proceedings_off BOOLEAN
);