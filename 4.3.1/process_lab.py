import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import linregress

# ========================
# КАЛИБРОВКА
# ========================
CALIB = 912.11   # пкс/мм  (микроскоп 4x, 1 мм = 912.11 пкс)

b_pix = 217
b_mm  = b_pix / CALIB              # ширина щели, мм
sigma_b_mm = 5.0 / CALIB           # погрешность ~5 пкс

# ========================
# ДИФРАКЦИЯ ФРЕНЕЛЯ
# ========================
m_all = np.array([1, 2, 3, 4, 5, 6])
z_all = np.array([14.04, 10.9, 7.69, 6.11, 5.13, 4.38])   # мм

# m=1 — выброс (при большом z первая полоса едва различима)
mask = m_all >= 2
m_fit = m_all[mask]
z_fit = z_all[mask]

# МНК через начало координат: z = C * (1/m),  C = b²/(4λ)
x_fr = 1.0 / m_fit
C_fr = np.dot(x_fr, z_fit) / np.dot(x_fr, x_fr)           # мм

# Погрешность наклона через СКО остатков
residuals = z_fit - C_fr * x_fr
sigma_res = np.std(residuals, ddof=1)
sigma_C   = sigma_res / np.sqrt(np.dot(x_fr, x_fr))

# Длина волны и её погрешность
lam = b_mm**2 / (4.0 * C_fr)      # мм
sigma_lam = lam * np.sqrt((2 * sigma_b_mm / b_mm)**2 + (sigma_C / C_fr)**2)

# λ из каждой точки (для таблицы)
lam_each = b_mm**2 / (4.0 * m_all * z_all)

# ========================
# ДИФРАКЦИЯ ФРАУНГОФЕРА
# ========================
n_fr  = np.array([1, 2, 3, 4, 5])
x_pix = np.array([155.0, 205.0, 255.5, 307.0, 356.5])
x_mm  = x_pix / CALIB

slope_fraun, x0_fraun, r_fraun, _, se_fraun = linregress(n_fr, x_mm)
# slope_fraun = λf/b  (мм)
f_mm = slope_fraun * b_mm / lam    # фокусное расстояние линзы, мм

# ========================
# ВЫВОД
# ========================
print("=" * 55)
print("КАЛИБРОВКА")
print(f"  b = {b_pix} пкс = {b_mm:.4f} мм")
print()
print("ДИФРАКЦИЯ ФРЕНЕЛЯ  (МНК через нуль, m = 2..6)")
print(f"  Наклон  C  =  b²/4λ  =  {C_fr:.3f} ± {sigma_C:.3f}  мм")
print(f"  λ  =  {lam*1e6:.1f}  ±  {sigma_lam*1e6:.1f}  нм")
print()
print("  λ из каждой точки:")
for mi, zi, li in zip(m_all, z_all, lam_each):
    tag = "  ← выброс" if mi == 1 else ""
    print(f"    m={mi}, z={zi:.2f} мм  →  λ = {li*1e6:.0f} нм{tag}")
print()
print("ДИФРАКЦИЯ ФРАУНГОФЕРА  (линейный МНК x_n vs n)")
print(f"  Шаг  Δx = λf/b  =  {slope_fraun:.5f}  мм  (se = {se_fraun:.6f} мм)")
print(f"  Центр паттерна  x₀  =  {x0_fraun:.4f}  мм")
print(f"  R²  =  {r_fraun**2:.6f}")
print(f"  Фокусное расстояние  f  =  {f_mm:.1f}  мм  (λ из Френеля)")
print("=" * 55)

# ========================
# ГРАФИКИ
# ========================

# --- График 1: Дифракция Френеля  z vs 1/m ---
fig, ax = plt.subplots(figsize=(6.5, 4.2))
x_line = np.linspace(0.14, 1.06, 200)
ax.plot(x_line, C_fr * x_line, 'k--', linewidth=1.4,
        label=f'МНК: $C = {C_fr:.1f}$ мм')
ax.scatter(1.0 / m_fit, z_fit, color='k', s=55, zorder=5,
           label='$m = 2{-}6$')
ax.scatter(1.0 / m_all[0], z_all[0], marker='x', color='r', s=90,
           linewidths=2.0, zorder=6,
           label=f'Выброс ($m=1$,  $z={z_all[0]}$ мм)')
ax.set_xlabel('$1/m$', fontsize=12)
ax.set_ylabel('$z$,  мм', fontsize=12)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fresnel_fit.png', dpi=150, bbox_inches='tight')
plt.close()

# --- График 2: Дифракция Фраунгофера  x_n vs n ---
fig, ax = plt.subplots(figsize=(6.5, 4.2))
n_line = np.linspace(0.5, 5.5, 100)
ax.plot(n_line, slope_fraun * n_line + x0_fraun, 'k--', linewidth=1.4,
        label=f'МНК: $\\Delta x = {slope_fraun*1e3:.2f}\\times10^{{-2}}$ мм')
ax.scatter(n_fr, x_mm, color='k', s=55, zorder=5, label='Минимумы')
ax.set_xlabel('Номер минимума $n$', fontsize=12)
ax.set_ylabel('Координата $x_n$,  мм', fontsize=12)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fraunhofer_fit.png', dpi=150, bbox_inches='tight')
plt.close()

print("fresnel_fit.png  и  fraunhofer_fit.png  сохранены.")
