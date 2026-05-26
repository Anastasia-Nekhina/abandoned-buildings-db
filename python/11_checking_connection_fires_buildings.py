import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import KDTree

fires = pd.read_csv("fires_objects_link.csv") 
buildings = pd.read_csv("objects_with_end_date.csv") 

# Исходное распределение: среднее расстояние реальных пожаров до зданий
real_mean_dist = fires["dist_nearest_bld"].mean()
print(f"Реальное среднее расстояние: {real_mean_dist:.2f} м")

# Рандомизация дат (99 раз)
np.random.seed(42)
random_means = []
n_iter = 99

# Для ускорения заранее превращаем координаты здания в tree
bld_coords = buildings[["x", "y"]].values
tree = KDTree(bld_coords)

for _ in range(n_iter):
    shuffled_dates = fires["fire_date"].sample(frac=1, replace=False).values
    
    rand_dists = []
    for (_, fire), shuffled_date in zip(fires.iterrows(), shuffled_dates):
        # Ищем 10 ближайших зданий
        dists, idxs = tree.query([fire["x"], fire["y"]], k=10)
        
        # Среди них находим первое активное на shuffled_date
        found = False
        for d, idx in zip(dists, idxs):
            if buildings.iloc[idx]["end_date"] >= shuffled_date:
                rand_dists.append(d)
                found = True
                break
        if not found:
            rand_dists.append(np.nan)
    
    random_means.append(np.nanmean(rand_dists))
    print(f"Итерация {_+1}/{n_iter} завершена")

# Сравнение с p-value
random_means = np.array(random_means)
p_value = (np.sum(random_means <= real_mean_dist) + 1) / (n_iter + 1)

print(f"P-value: {p_value:.4f}")

plt.figure(figsize=(8,4))
plt.hist(random_means, bins=30, color='grey', alpha=0.7, label='Случайные средние')
plt.axvline(real_mean_dist, color='red', lw=2, label=f'Реальное ({real_mean_dist:.1f} м)')
plt.xlabel("Среднее расстояние до ближайшего здания (м)")
plt.ylabel("Частота")
plt.title(f"Тест влияния заброшенных зданий на близость пожаров\np = {p_value:.4f}")
plt.legend()
plt.tight_layout()
plt.savefig("cdf_test.png", dpi=150)
plt.show()