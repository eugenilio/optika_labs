import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
from scipy.signal import find_peaks

plt.rcParams.update({
    'font.family': 'DejaVu Serif',
    'font.size': 12,
    'axes.labelsize': 13,
    'legend.fontsize': 11,
    'figure.dpi': 150,
})

# ── load data ──────────────────────────────────────────────────────────────
raw = pd.read_csv('data.csv', comment='#')
df_a = raw[raw['type'] == 'angle'].copy().reset_index(drop=True)
df_p = raw[raw['type'] == 'position'].copy().reset_index(drop=True)

def compute_V(h1, h2, h3, h4):
    V1 = 2*np.sqrt(h1*h2) / (h1 + h2)
    V  = (h4 - h3) / (h4 + h3)
    return V1, V

# ── PART 1: angular dependence ─────────────────────────────────────────────
alpha = df_a['param'].values.astype(float)
V1_a, V_a = compute_V(df_a['h1'].values, df_a['h2'].values,
                       df_a['h3'].values, df_a['h4'].values)
V3 = V_a / V1_a

# normalise to value at alpha = 0 (reference angle)
V3_at_0 = V3[alpha == 0][0]
V3_norm  = V3 / V3_at_0

print("=== Part 1: angular dependence ===")
print(f"V3(0°) = {V3_at_0:.3f}  (normalisation denominator)")
print(f"\nalpha   delta    V1      V       V3      V3/V3(0)")
for i in range(len(alpha)):
    delta = df_a['h1'].values[i] / df_a['h2'].values[i]
    print(f"{alpha[i]:5.0f}  {delta:.3f}   {V1_a[i]:.3f}   {V_a[i]:.3f}   "
          f"{V3[i]:.3f}   {V3_norm[i]:.3f}")

# ── plot V3 — points only ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(alpha, V3_norm, 'ko', ms=6, label=r'$\mathcal{V}_3/\mathcal{V}_3(0°)$ (эксп.)')

a_th = np.linspace(0, 180, 500)
a_th_rad = np.deg2rad(a_th)
ax.plot(a_th, np.abs(np.cos(a_th_rad)), 'b--', lw=1.5, label=r'$|\cos\alpha|$')
ax.plot(a_th, np.cos(a_th_rad)**2,      'r:',  lw=1.5, label=r'$\cos^2\!\alpha$')

ax.set_xlabel(r'$\alpha$, °')
ax.set_ylabel(r'$\gamma_3\,/\,\gamma_3(0°)$')
ax.legend()
ax.grid(True, linestyle=':', alpha=0.5)
ax.set_xlim(-5, 185)
ax.set_ylim(0, None)
fig.tight_layout()
fig.savefig('plot_angle.png')
plt.close(fig)
print("\nSaved plot_angle.png")

# ── PART 2: path-difference dependence ────────────────────────────────────
x   = df_p['param'].values.astype(float)
ell = 2 * x
V1_p, V_p = compute_V(df_p['h1'].values, df_p['h2'].values,
                       df_p['h3'].values, df_p['h4'].values)
V2 = V_p / V1_p

print("\n=== Part 2: path-difference dependence ===")
print(f"\n{'x,cm':>6}  {'ell,cm':>6}  {'V1':>6}  {'V':>6}  {'V2':>6}")
for i in range(len(x)):
    print(f"{x[i]:6.1f}  {ell[i]:6.1f}  {V1_p[i]:6.3f}  {V_p[i]:6.3f}  {V2[i]:6.3f}")

# find global minimum → ell ≈ L
idx_min  = np.argmin(V2)
ell_min  = ell[idx_min]

# secondary maximum after the minimum
peaks_after, _ = find_peaks(V2[idx_min:], height=0.10, distance=2)
peaks_after   += idx_min
ell_sec = ell[peaks_after[np.argmax(V2[peaks_after])]]
L_est   = ell_sec / 2
sigma_x = 2.0                    # reading uncertainty in x, cm
sigma_L = sigma_x                # propagated to L (ell_sec = 2*x, L = ell_sec/2)

c = 3e10   # cm/s
Delta_nu_m       = c / (2 * L_est)
sigma_Delta_nu_m = Delta_nu_m * (sigma_L / L_est)

# ell_1/2 via spline extrapolation to ell=0
left_mask = np.arange(len(ell)) <= idx_min
ell_left  = np.concatenate([[0], ell[left_mask]])
V2_left   = np.concatenate([[1.0], V2[left_mask]])
spl       = UnivariateSpline(ell_left, V2_left, s=0.05, k=4)
ell_dense = np.linspace(0, ell_left[-1], 1000)
V2_smooth = spl(ell_dense)
cross     = np.where(np.diff((V2_smooth >= 0.5).astype(int)) < 0)[0]
i0        = cross[0]
ell_half  = float(np.interp(0.5, [V2_smooth[i0+1], V2_smooth[i0]],
                                  [ell_dense[i0+1], ell_dense[i0]]))
# conservative uncertainty: first data point is at ell=20 with V2=0.41,
# so ell_half lies somewhere in [0, 20]. Assign ±4 cm.
sigma_ell_half = 4.0

Delta_nu      = 0.6 * c / ell_half
sigma_Delta_nu = Delta_nu * (sigma_ell_half / ell_half)

n_modes      = 1 + 1.2 * L_est / ell_half
sigma_n      = 1.2 * np.sqrt((sigma_L / ell_half)**2
                              + (L_est * sigma_ell_half / ell_half**2)**2)

L_coh       = c / Delta_nu
sigma_L_coh = L_coh * (sigma_ell_half / ell_half)

print(f"\nGlobal V2 minimum at x={x[idx_min]:.0f} cm, ell={ell_min:.0f} cm")
print(f"Secondary maximum at ell={ell_sec:.0f} cm")
print(f"\n=== Report values (with uncertainties) ===")
print(f"L          = {L_est:.0f} ± {sigma_L:.0f} cm")
print(f"Delta_nu_m = {Delta_nu_m/1e9:.3f} ± {sigma_Delta_nu_m/1e9:.3f} GHz")
print(f"ell_1/2    = {ell_half:.1f} ± {sigma_ell_half:.0f} cm  (extrapolated)")
print(f"Delta_nu   = {Delta_nu/1e9:.2f} ± {sigma_Delta_nu/1e9:.2f} GHz")
print(f"n_modes    = {n_modes:.1f} ± {sigma_n:.1f}  => {round(n_modes):.0f} ± {round(sigma_n):.0f}")
print(f"L_coh      = {L_coh:.0f} ± {sigma_L_coh:.0f} cm")

# ── plot V2 — points only ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(ell, V2, 'ko', ms=5, label=r'$\mathcal{V}_2$ (эксп.)')

# reference lines
ax.axhline(0.5, color='gray', ls='--', lw=1, label='$0.5$')
ax.axvline(ell_half, color='green', ls='--', lw=1.2,
           label=rf'$\ell_{{1/2}}\approx{ell_half:.0f}$ см')
ax.text(ell_half + 2, 0.92, rf'$\ell_{{1/2}}$', color='green', fontsize=10)
ax.axvline(ell_min,  color='purple', ls='-.', lw=1.2,
           label=rf'минимум ($\ell={ell_min:.0f}$ см $\approx L$)')
ax.text(ell_min + 2, 0.92, r'$L$', color='purple', fontsize=10)
ax.plot(ell[peaks_after], V2[peaks_after], 'rs', ms=8, zorder=5,
        label=rf'$2L={ell_sec:.0f}$ см (вторичный макс.)')

ax.set_xlabel(r'$\ell = 2x$, см')
ax.set_ylabel(r'$\gamma_2$')
ax.legend(fontsize=10)
ax.grid(True, linestyle=':', alpha=0.5)
ax.set_ylim(0, 1.05)
fig.tight_layout()
fig.savefig('plot_position.png')
plt.close(fig)
print("\nSaved plot_position.png")
