with_variable(
    'clean_name',
    replace(
        trim(regexp_replace(
            coalesce("name", ''),
            '(городской|муниципальный|сельский)\\s+округ|округ\\s+(городской|муниципальный|сельский)',
            ''
        )),
        'ё', 'е'
    ),
    with_variable(
        'matched',
        aggregate(
            layer:='municipalities',
            aggregate:='array_agg',
            expression:=replace("municipality", 'ё', 'е'),
            filter:= replace("municipality", 'ё', 'е') ILIKE ('%' || @clean_name || '%')
        ),
        array_to_string(@matched, ', ')
    )
)