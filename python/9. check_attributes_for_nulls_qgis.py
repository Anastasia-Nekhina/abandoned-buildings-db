import pandas as pd
import numpy as np

df = pd.read_excel('C:\My_files\stratified_sample_120_for_formulas.xlsx')
all_columns = df.columns.tolist()

# Анализ пропусков
missing_stats = df.isnull().sum()
missing_percent = 100 * missing_stats / len(df)
missing_df = pd.DataFrame({'missing_count': missing_stats, 'missing_percent': missing_percent})
missing_df = missing_df[missing_df['missing_count'] > 0].sort_values('missing_percent', ascending=False)

print("ПРОПУСКИ В СТОЛБЦАХ\n", missing_df)

# Анализ уникальных значений
unique_counts = df.nunique()
single_value_cols = unique_counts[unique_counts == 1].index.tolist()
print(f"\nСТОЛБЦЫ С ОДНИМ УНИКАЛЬНЫМ ЗНАЧЕНИЕМ ({len(single_value_cols)} шт)\n", single_value_cols)

# Для категориальных столбцов покажем частоты
categorical_cols = df.select_dtypes(include=['object']).columns
for col in categorical_cols:
    print(f"\n{col}: {df[col].value_counts().to_dict()}")